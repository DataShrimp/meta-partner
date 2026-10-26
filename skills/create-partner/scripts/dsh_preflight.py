# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Read-only preflight for mounting a DeepSeek Harness agent role.

Deterministic checks only: this script never writes, never installs, never boots.
Every finding carries a P-id that maps to references/dsh-install-pitfalls.md.

Exit codes: 0 all pass, 1 at least one fail, 2 at least one unverifiable, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

SKILL_ROOTS = [
    ("project-dsh", ".dsh/skills", 100),
    ("project-agents", ".agents/skills", 200),
    ("user-dsh", "~/.dsh/skills", 400),
    ("user-agents", "~/.agents/skills", 500),
]
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DOUBLE_BRACE = re.compile(r"\{\{[^{}]*\}\}")
FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class Preflight:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, cid: str, status: str, evidence: str, remedy: str = "") -> None:
        self.checks.append(
            {"id": cid, "status": status, "evidence": evidence, "remedy": remedy}
        )

    def verdict(self) -> str:
        statuses = {c["status"] for c in self.checks}
        if "fail" in statuses:
            return "FAIL"
        if "unverifiable" in statuses:
            return "UNVERIFIABLE"
        return "PASS"


def _exists(p: Path) -> bool:
    try:
        return p.exists()
    except OSError:
        return False


def _writable(p: Path) -> tuple[bool, str]:
    """Return (writable, reason). Never mutates the target."""
    probe = p
    while not _exists(probe):
        if probe.parent == probe:
            return False, f"no existing ancestor for {p}"
        probe = probe.parent
    if not os.access(probe, os.W_OK):
        return False, f"{probe} is not writable by uid {os.getuid()}"
    return True, f"writable at {probe}"


def check_runtime(pf: Preflight, app: Path) -> dict:
    launcher = app / "runtime/cli/bin/dsh"
    if launcher.exists():
        pf.add("P07-launcher", "pass", f"{launcher}")
    else:
        pf.add(
            "P07-launcher",
            "fail",
            f"missing {launcher}",
            "boot from the app launcher, never an npx cache (ad-hoc koffi signature)",
        )

    runtime = Path.home() / ".dsh/dsh-runtimes/dsh-primary-runtime/dependencies"
    node = runtime / "node/bin/node"
    pnpm = runtime / "pnpm/bin/pnpm.mjs"
    if node.exists() and pnpm.exists():
        pf.add("P05-managed-toolchain", "pass", f"node={node} pnpm={pnpm}")
    else:
        pf.add(
            "P05-managed-toolchain",
            "warn",
            f"node exists={node.exists()} pnpm exists={pnpm.exists()}",
            "create a durable shim in front of the managed pnpm.mjs; /tmp shims do not survive",
        )

    # Missing pnpm only blocks Tier B/C bundle installs. It must be visible but it must
    # not turn an otherwise-ready role into a hard failure, so it is a warn: the operator
    # decides whether this turn actually needs to install anything.
    on_path = shutil.which("pnpm")
    if on_path:
        pf.add("P04-pnpm-path", "pass", on_path)
    else:
        pf.add(
            "P04-pnpm-path",
            "warn",
            "pnpm is not on PATH; `dsh plugin add/remove` would exit 127",
            "before any bundle install, prepend a shim that execs the managed pnpm.mjs "
            "with the managed node",
        )
    return {"node": str(node), "pnpm": str(pnpm), "pnpm_on_path": on_path}


def check_profile(pf: Preflight, home: Path, profile: str) -> dict:
    pdir = home / "profiles" / profile
    manifest = pdir / "package.json"
    if not manifest.exists():
        pf.add(
            "P01-profile",
            "fail",
            f"no profile manifest at {manifest}",
            "create it with `dsh plugin --profile <name> add <pkg>` or pick an existing profile",
        )
        return {"dir": str(pdir), "bundles": [], "dependencies": {}}

    data = json.loads(manifest.read_text("utf-8"))
    bundles = data.get("dsh", {}).get("profile", {}).get("bundles", [])
    deps = data.get("dependencies", {})
    pf.add(
        "P01-profile",
        "pass",
        f"{pdir} bundles={bundles} deps={sorted(deps)}",
    )

    if profile == "desktop":
        pf.add(
            "P02-desktop-lock",
            "warn",
            "desktop is CLI-locked: `dsh plugin --profile desktop` will error",
            "mount via <profile>/packages/<pkg> + workspace:* dependency + bundles entry "
            "+ `pnpm install --ignore-scripts`",
        )
    else:
        pf.add("P02-desktop-lock", "pass", f"{profile} is CLI-manageable")

    for pkg in bundles:
        pkg_dir = pdir / "node_modules" / pkg
        in_box = pkg not in deps and pkg.startswith("@deepseek-ai/")
        if in_box:
            # Shipped bundles resolve through the install anchor, not the profile's
            # node_modules; they are not dependencies and are never reconciled.
            pf.add("P03-bundle-dependency", "pass", f"{pkg}: in-box bundle (install-anchor resolved)")
            continue
        if not _exists(pkg_dir):
            local = pdir / "packages" / pkg.split("/")[-1]
            pf.add(
                "P03-bundle-dependency",
                "warn",
                f"{pkg}: no node_modules entry (local candidate exists={_exists(local)})",
                "run `pnpm install --ignore-scripts` in the profile, or fix the dependency spec",
            )
            continue
        pkg_json = pkg_dir / "package.json"
        if not pkg_json.exists():
            pf.add("P08-bundle-decl", "fail", f"{pkg}: unreadable package.json")
            continue
        meta = json.loads(pkg_json.read_text("utf-8"))
        patch = meta.get("dsh", {}).get("bundle", {}).get("patch")
        if patch is None:
            pf.add(
                "P08-bundle-decl",
                "fail",
                f"{pkg} declares no dsh.bundle.patch",
                "the loader rejects any bundle without it",
            )
            continue
        patch_path = (pkg_dir / patch).resolve()
        if not patch_path.exists():
            pf.add("P08-bundle-decl", "fail", f"{pkg}: patch file {patch_path} missing")
            continue
        try:
            import yaml

            parsed = yaml.safe_load(patch_path.read_text("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface any parse detail
            pf.add("P08-patch-shape", "fail", f"{pkg}: parse error {exc}")
            continue
        if isinstance(parsed, list):
            pf.add("P08-patch-shape", "pass", f"{pkg}: top-level sequence ({len(parsed)} entries)")
        else:
            pf.add(
                "P08-patch-shape",
                "fail",
                f"{pkg}: patch is {type(parsed).__name__}, not a sequence",
                "a file starting with `plugins:` is a mapping and will not load",
            )

    writable, reason = _writable(pdir)
    pf.add(
        "P06-profile-writable",
        "pass" if writable else "unverifiable",
        reason,
        "" if writable else "dump-config and pnpm install need write access; use the read-only "
        "loadProfileDirectory gate instead, or request a scoped permission",
    )
    return {"dir": str(pdir), "bundles": bundles, "dependencies": deps}


def check_skill_name(pf: Preflight, name: str) -> list[dict]:
    hits = []
    for label, rel, rank in SKILL_ROOTS:
        root = Path(rel).expanduser()
        if not root.is_absolute():
            root = Path.cwd() / rel
        cand = root / name
        if _exists(cand):
            kind = "symlink" if cand.is_symlink() else "dir"
            target = os.readlink(cand) if cand.is_symlink() else ""
            hits.append({"root": label, "rank": rank, "path": str(cand), "kind": kind})
            pf.add(
                "P10-name-shadow",
                "warn" if rank > 100 else "pass",
                f"{name} occupied at rank {rank} ({label}, {kind}) {target}".strip(),
                "lowest rank wins; a same-name entry in a higher-rank root is shadowed silently",
            )
    if not hits:
        pf.add("P10-name-shadow", "pass", f"{name} free across all {len(SKILL_ROOTS)} roots")
    dupes = [h for h in hits]
    if len(dupes) > 1:
        pf.add(
            "P10-duplicate-copy",
            "warn",
            f"{name} present in {len(dupes)} roots: "
            + ", ".join(f"{h['root']}({h['rank']})" for h in dupes),
            "delete the higher-rank copy so the survivor cannot diverge",
        )
    return hits


def check_skill_dir(pf: Preflight, skill_dir: Path) -> dict:
    sk = skill_dir / "SKILL.md"
    if not sk.exists():
        pf.add("P14-skill-file", "warn", f"no SKILL.md under {skill_dir}")
        return {}
    text = sk.read_text("utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        pf.add("P13-frontmatter", "fail", f"{sk}: missing YAML frontmatter")
        return {}
    fm_raw = match.group(1)
    fm: dict[str, str] = {}
    key = None
    for line in fm_raw.splitlines():
        m = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fm[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fm[key] = (fm.get(key, "") + " " + line.strip()).strip()

    name = fm.get("name", "")
    if not SKILL_NAME.match(name):
        pf.add("P13-frontmatter", "fail", f"name '{name}' violates {SKILL_NAME.pattern}")
    else:
        pf.add("P13-frontmatter", "pass", f"name={name}")

    desc = fm.get("description", "")
    if len(desc) > 450:
        pf.add(
            "P14-desc-cap",
            "warn",
            f"description is {len(desc)} chars",
            "catalog truncates at 500; keep under 450 so the negative boundary survives",
        )
    else:
        pf.add("P14-desc-cap", "pass", f"description is {len(desc)} chars")

    if re.search(r"disableModelInvocation|modelInvocable|userInvocable", fm_raw):
        pf.add(
            "P13-legacy-key",
            "fail",
            "legacy camelCase invocation key present",
            "use disable-model-invocation / user-invocable; legacy keys make the file ignored",
        )
    else:
        pf.add("P13-legacy-key", "pass", "canonical invocation keys")

    dir_name = skill_dir.resolve().name
    if name and name != dir_name:
        pf.add(
            "P11-name-mismatch",
            "warn",
            f"directory '{dir_name}' != frontmatter '{name}'",
            "resourceBase is the directory; renaming one does not rename the other",
        )
    else:
        pf.add("P11-name-mismatch", "pass", f"directory matches frontmatter ({name})")
    return {"frontmatter": fm, "path": str(sk)}


def check_persona_drift(pf: Preflight, home: Path, profile: str, role_dir: Path, preset_id: str = "") -> dict | None:
    """Compare the profile's persona prefix against SOUL.md.

    The prefix is a hand-maintained partial copy; it drifts silently. This is a string
    comparison, so it belongs here rather than in a model's judgement. When the patch
    inserts several presets, `preset_id` selects the right persona block; without it
    the first block in the file is audited, which may belong to another role.
    """
    patch = home / "profiles" / profile / "cordis.patch.yml"
    if not patch.exists():
        pf.add("F4-persona-drift", "unverifiable", f"no patch file at {patch}")
        return None
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from check_persona_drift import analyze  # noqa: PLC0415 - sibling script, resolved at call time
    except Exception as exc:  # noqa: BLE001 - a missing sibling must not abort preflight
        pf.add("F4-persona-drift", "unverifiable", f"cannot import check_persona_drift: {exc}")
        return None

    try:
        report = analyze(patch, role_dir, preset_id=preset_id)
    except Exception as exc:  # noqa: BLE001
        pf.add("F4-persona-drift", "unverifiable", f"drift analysis failed: {exc}")
        return None

    verdict = report.get("verdict")
    mode = report.get("mode", "summary")

    if verdict == "PASS" and mode == "anchor":
        pf.add(
            "F4-persona-drift",
            "pass",
            f"anchor mode ({report.get('prefix_chars')} chars) points at "
            f"{report.get('referenced')}; {report.get('pointer_detail')}",
        )
    elif verdict == "PASS":
        pf.add(
            "F4-persona-drift",
            "pass",
            f"summary mode reproduces all {len(report.get('source_clauses', []))} source clauses",
        )
    elif verdict == "FAIL" and mode == "anchor":
        # An anchor CAN break: a dangling file reference or a missing pull pointer means
        # no clause reaches the prompt at all.
        pf.add(
            "F4-persona-drift",
            "fail",
            f"anchor mode is broken: {report.get('problems')}",
            "an anchor only works when the files it names exist and the AGENTS.md pull "
            "pointer is installed; fix those before trusting the role",
        )
    elif verdict == "FAIL":
        pf.add(
            "F4-persona-drift",
            "fail",
            f"prefix omits {report.get('clauses_missing_in_prefix')} "
            f"(char_ratio={report.get('char_ratio')}, vocab={report.get('token_vocabulary_coverage')})",
            "trim the prefix to a pure anchor, or regenerate it from SOUL.md; never let two "
            "authoritative versions stand",
        )
    else:
        pf.add("F4-persona-drift", "unverifiable", str(report.get("error", "unknown")))
    return report


def check_role_dir(pf: Preflight, role_dir: Path) -> None:
    slots = ["IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md", "MEMORY.md"]
    missing = [s for s in slots if not (role_dir / s).exists()]
    if missing:
        pf.add("SLOT-missing", "warn", f"absent: {missing}", "see references/role-5-slot-spec.md")
    else:
        pf.add("SLOT-missing", "pass", "all five slots present")

    # Only files that can be injected into the system prompt are hard failures.
    # Documentation files (README, PROMPT_SKELETON) are read on demand, never
    # interpolated, so brace mentions there are prose, not hazards.
    injectable = {"IDENTITY.md", "SOUL.md", "AGENTS.md", "TOOLS.md", "MEMORY.md"}
    fatal, advisory = [], []
    for md in sorted(role_dir.glob("*.md")):
        hits = [m.group(0) for m in DOUBLE_BRACE.finditer(md.read_text("utf-8"))]
        if not hits:
            continue
        bucket = fatal if md.name in injectable else advisory
        bucket.extend(f"{md.name}:{h}" for h in hits)
    if fatal:
        pf.add(
            "P08-double-brace",
            "fail",
            f"injected slot files contain template variables: {fatal[:6]}",
            "renderPrompt interpolates strictly and throws on unregistered variables; "
            "there is no interpolate:false option — remove or escape the braces",
        )
    else:
        pf.add("P08-double-brace", "pass", f"no double-brace placeholders in {sorted(injectable)}")
    if advisory:
        pf.add(
            "P08-doc-brace",
            "warn",
            f"documentation files mention braces as prose: {advisory[:6]}",
            "safe while these files are only read on demand; escaping is required if one is ever "
            "mounted as a prompt section",
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only preflight for a dsh agent role mount.")
    ap.add_argument("--profile", default="desktop", help="target profile name")
    ap.add_argument("--preset-id", default="",
                    help="audit this preset persona block when the patch inserts several")
    ap.add_argument("--name", default="", help="skill name to check for shadowing")
    ap.add_argument("--skill-dir", default="", help="directory that holds the SKILL.md")
    ap.add_argument("--role-dir", default="", help="role directory holding the five slots")
    ap.add_argument(
        "--app",
        default="/Applications/DeepSeek Harness.app/Contents/Resources",
        help="DeepSeek Harness resources directory",
    )
    ap.add_argument("--dsh-home", default="", help="override $DSH_HOME")
    ap.add_argument(
        "--scope",
        choices=["skill", "mount", "all"],
        default="all",
        help="skill: skill-root checks only (no runtime/profile); mount: profile and bundle checks; all: both",
    )
    ap.add_argument("--json", action="store_true", help="emit JSON (default)")
    ap.add_argument("--dry-run", action="store_true", help="accepted for symmetry; this script never writes")
    args = ap.parse_args()

    home = Path(args.dsh_home).expanduser() if args.dsh_home else Path.home() / ".dsh"
    app = Path(args.app).expanduser()

    pf = Preflight()
    report: dict = {"profile": args.profile, "dsh_home": str(home), "scope": args.scope}
    # A Tier A install is one symlink into a skill root: it needs no pnpm, no profile
    # write access, and no bundle. Checking those here would fail an install that is
    # in fact perfectly valid, so the two scopes are kept separate.
    if args.scope in ("mount", "all"):
        report["runtime"] = check_runtime(pf, app)
        report["profile_state"] = check_profile(pf, home, args.profile)
    if args.name:
        report["name_hits"] = check_skill_name(pf, args.name)
    if args.skill_dir:
        report["skill"] = check_skill_dir(pf, Path(args.skill_dir).expanduser())
    if args.role_dir:
        rd = Path(args.role_dir).expanduser()
        check_role_dir(pf, rd)
        # Drift is a role-vs-preset concern; it only makes sense against a real profile.
        if args.scope in ("mount", "all"):
            report["persona_drift"] = check_persona_drift(pf, home, args.profile, rd, preset_id=args.preset_id)
    if args.skill_dir:
        # Directory identity is only meaningful for a real skill directory, not for
        # the staging root that merely contains one SKILL.md.
        sd = Path(args.skill_dir).expanduser()
        report["skill"]["directory_name"] = sd.name

    report["checks"] = pf.checks
    report["verdict"] = pf.verdict()
    counts: dict[str, int] = {}
    for c in pf.checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    report["counts"] = counts

    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return {"PASS": 0, "FAIL": 1, "UNVERIFIABLE": 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
