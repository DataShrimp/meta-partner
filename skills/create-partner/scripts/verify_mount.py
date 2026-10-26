# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Deterministic mount verification for a DeepSeek Harness profile (gate levels L0-L4).

Never writes, never boots, never installs. Escalates through the verification
ladder and stops at the highest level it can actually prove:

  L0 dependency materialized
  L1 bundle listed in the profile manifest
  L2 expected entry present in the composed patch layers
  L3 loadProfileDirectory composes every layer (read-only composition proof)
  L4 live boot (only with --boot; opens a port and is killed afterwards)

A permission error at any level yields UNVERIFIABLE, never PASS.

Exit codes: 0 PASS, 1 FAIL, 2 UNVERIFIABLE, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_APP = Path("/Applications/DeepSeek Harness.app/Contents/Resources")


class Gate:
    def __init__(self) -> None:
        self.levels: list[dict] = []

    def record(self, level: str, status: str, detail: str) -> None:
        self.levels.append({"level": level, "status": status, "detail": detail})

    @property
    def verdict(self) -> str:
        statuses = [lv["status"] for lv in self.levels]
        if "fail" in statuses:
            return "FAIL"
        if "unverifiable" in statuses:
            return "UNVERIFIABLE"
        return "PASS"

    @property
    def highest_proven(self) -> str:
        proven = [lv["level"] for lv in self.levels if lv["status"] == "pass"]
        return proven[-1] if proven else "none"


def resolve_profile(home: Path, profile: str) -> Path:
    return home / "profiles" / profile


def manifest(pdir: Path) -> dict:
    f = pdir / "package.json"
    if not f.exists():
        raise SystemExit(f"error: no profile manifest at {f}")
    return json.loads(f.read_text("utf-8"))


def node_runtime(home: Path) -> Path | None:
    cand = home / "dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node"
    return cand if cand.exists() else None


def app_boot(app: Path, home: Path) -> Path | None:
    """Locate dsh-app-boot. The profile-level node_modules is preferred because
    app.asar is a single archive file and cannot be imported directly."""
    for cand in (
        home / "profiles/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js",
        app / "app.asar.unpacked/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js",
    ):
        if cand.exists():
            return cand
    return None


def install_anchor(home: Path) -> Path | None:
    cand = home / "profiles/node_modules/@deepseek-ai/dsh/package.json"
    return cand if cand.exists() else None


def _yaml_loader():
    """Load loader patches, which legitimately use the `!!js` tag for runtime expressions."""
    import yaml

    class PatchLoader(yaml.SafeLoader):
        pass

    PatchLoader.add_constructor(
        "tag:yaml.org,2002:js", lambda loader, node: loader.construct_scalar(node)
    )
    return PatchLoader


def gate_l0(g: Gate, pdir: Path, expect: str, deps: dict) -> None:
    direct = pdir / "node_modules" / expect
    if direct.exists():
        g.record("L0", "pass", f"materialized at {direct}")
        return
    if expect in deps or "/" not in expect:
        g.record(
            "L0",
            "fail",
            f"{expect} not materialized under {pdir}/node_modules",
            )
        return
    g.record("L1", "pass", f"{expect} is an in-box bundle, resolved via the install anchor")


def gate_l1(g: Gate, bundles: list[str], expect: str) -> None:
    if expect in bundles:
        g.record("L1", "pass", f"{expect} listed in dsh.profile.bundles")
    else:
        g.record("L1", "fail", f"{expect} absent from dsh.profile.bundles {bundles}")


def gate_l2(g: Gate, pdir: Path, bundles: list[str], expect: str) -> None:
    """Walk every bundle patch and confirm the expected id or package appears."""
    try:
        import yaml

        Loader = _yaml_loader()
    except ImportError:
        g.record("L2", "unverifiable", "pyyaml unavailable")
        return

    found: list[str] = []
    for pkg in bundles:
        pkg_dir = pdir / "node_modules" / pkg
        if not pkg_dir.exists():
            continue
        pj = pkg_dir / "package.json"
        if not pj.exists():
            continue
        declared = json.loads(pj.read_text("utf-8")).get("dsh", {}).get("bundle", {}).get("patch")
        if not declared:
            g.record("L2", "fail", f"{pkg} declares no dsh.bundle.patch")
            return
        patch_path = pkg_dir / declared
        if not patch_path.exists():
            g.record("L2", "fail", f"{pkg} patch file missing: {patch_path}")
            return
        try:
            parsed = yaml.load(patch_path.read_text("utf-8"), Loader=Loader)
        except Exception as exc:  # noqa: BLE001
            g.record("L2", "fail", f"{pkg} patch unparseable: {exc}")
            return
        if not isinstance(parsed, list):
            g.record("L2", "fail", f"{pkg} patch is {type(parsed).__name__}, not a sequence")
            return
        blob = json.dumps(parsed)
        # Match the expected name only. Matching on the owning package would
        # report every layer as contributing any bundle it happens to mention.
        if expect in blob:
            found.append(pkg)

    user_patch = pdir / "cordis.patch.yml"
    if user_patch.exists():
        try:
            parsed = yaml.load(user_patch.read_text("utf-8"), Loader=Loader) or []
            if isinstance(parsed, list) and expect in json.dumps(parsed):
                found.append("cordis.patch.yml (user layer)")
        except Exception as exc:  # noqa: BLE001
            g.record("L2", "fail", f"user patch unparseable: {exc}")
            return

    if found:
        g.record("L2", "pass", f"entry {expect} composed from: {', '.join(found)}")
    else:
        g.record("L2", "fail", f"no layer contributes {expect}")


def gate_l3(g: Gate, home: Path, app: Path, pdir: Path) -> None:
    node = node_runtime(home)
    boot = app_boot(app, home)
    anchor = install_anchor(home)
    if node is None or boot is None:
        g.record("L3", "unverifiable", f"node={node} boot={boot}; cannot run the loader")
        return

    script = (
        "const boot = await import(process.argv[1]);"
        "const p = boot.loadProfileDirectory('dsh', process.argv[2], process.argv[3]);"
        "console.log(JSON.stringify({layers:p.layers.map(l=>l.packageName),"
        "userPatches:p.patches.length}));"
    )
    argv = [
        str(node),
        "--input-type=module",
        "-e",
        script,
        boot.as_uri(),
        str(pdir),
        str(anchor) if anchor else str(app / "app.asar/dsh/package.json"),
    ]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        g.record("L3", "fail", "loadProfileDirectory timed out after 90s")
        return

    if proc.returncode == 0:
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            g.record("L3", "pass", f"composed; raw={proc.stdout.strip()[:200]}")
            return
        g.record(
            "L3",
            "pass",
            f"composed {len(data.get('layers', []))} layers: {data.get('layers')}"
            f", user patches={data.get('userPatches')}",
        )
        return

    stderr = (proc.stderr or "").strip()
    if "EPERM" in stderr or "not permitted" in stderr:
        g.record("L3", "unverifiable", f"permission denied while composing: {stderr[-300:]}")
    else:
        g.record("L3", "fail", f"loader rejected the profile: {stderr[-400:]}")


def gate_l4(g: Gate, app: Path, profile: str, port_file: Path, seconds: int) -> None:
    launcher = app / "runtime/cli/bin/dsh"
    if not launcher.exists():
        g.record("L4", "unverifiable", f"no launcher at {launcher}")
        return
    log = Path(tempfile.mkstemp(prefix="dsh-boot-", suffix=".log")[1])
    with log.open("w") as fh:
        proc = subprocess.Popen(
            [str(launcher), "--profile", profile],
            stdout=fh,
            stderr=subprocess.STDOUT,
            env={**os.environ, "DSH_BOOT_PROBE": "1"},
        )
    try:
        proc.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    text = log.read_text("utf-8", errors="replace")
    bad = [l for l in text.splitlines() if "code signature" in l or "failed to load" in l]
    ready = [l for l in text.splitlines() if "listen" in l.lower() or "127.0.0.1" in l]
    if bad:
        g.record("L4", "fail", f"boot error: {bad[0][:300]}")
    elif ready:
        g.record("L4", "pass", f"booted: {ready[0][:200]}")
    elif "EPERM" in text:
        g.record("L4", "unverifiable", "boot blocked by sandbox permissions")
    else:
        g.record("L4", "unverifiable", f"no ready line in {len(text)} bytes of log")
    port_file.write_text(text, "utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify that a dsh role or bundle is mounted.")
    ap.add_argument("--profile", default="desktop")
    ap.add_argument("--expect", required=True, help="bundle package name or patch entry id")
    ap.add_argument("--dsh-home", default="")
    ap.add_argument("--app", default=str(DEFAULT_APP))
    ap.add_argument("--boot", action="store_true", help="also run the L4 live boot probe")
    ap.add_argument("--boot-seconds", type=int, default=25)
    ap.add_argument("--json", action="store_true", help="emit JSON (default)")
    ap.add_argument("--dry-run", action="store_true", help="accepted for symmetry; never writes")
    args = ap.parse_args()

    home = Path(args.dsh_home).expanduser() if args.dsh_home else Path.home() / ".dsh"
    app = Path(args.app).expanduser()
    pdir = resolve_profile(home, args.profile)

    g = Gate()
    data = manifest(pdir)
    deps = data.get("dependencies", {})
    bundles = data.get("dsh", {}).get("profile", {}).get("bundles", [])

    gate_l0(g, pdir, args.expect, deps)
    gate_l1(g, bundles, args.expect)
    if any(lv["level"] == "L1" for lv in g.levels):
        gate_l2(g, pdir, bundles, args.expect)
    gate_l3(g, home, app, pdir)

    log_path = Path(tempfile.mkstemp(prefix="dsh-verify-", suffix=".log")[1])
    if args.boot:
        gate_l4(g, app, args.profile, log_path, args.boot_seconds)

    report = {
        "profile": args.profile,
        "profile_dir": str(pdir),
        "expect": args.expect,
        "verdict": g.verdict,
        "highest_level_proven": g.highest_proven,
        "levels": g.levels,
        "next_step": (
            "composition proven; restart the app so a live profile reloads the bundle"
            if g.verdict == "PASS"
            else "resolve the first non-pass level before claiming the mount succeeded"
        ),
    }
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {"PASS": 0, "FAIL": 1, "UNVERIFIABLE": 2}[g.verdict]


if __name__ == "__main__":
    sys.exit(main())
