# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Scaffold a dsh agent preset for an existing role directory (Tier P).

A role is files; an Agent is a preset. The COPY is delegated to the official
@deepseek-ai/dsh-agent-presets `copyComposition()` API — the same code the
runtime's own roster uses — so id validation, destination-root resolution,
rollback-on-failure, and metadata rendering stay owned by the platform and
survive DSH upgrades unchanged. This script contributes only what the platform
does not know: the role-specific persona anchor and the display metadata.

What remains ours, deliberately:
  - build_anchor(): a generated, role-specific anchor (never a copy of another
    preset's anchor text — a copied anchor sends sessions to another role).
  - metadata rewrite (name/description from the role's identity).
  - the static drift gate: the generated anchor must pass
    check_persona_drift.py or the whole preset is deleted, not delivered.

Exit codes: 0 created/verified, 1 hard failure, 2 unverifiable, 3 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PRESET_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SLOTS = ("SOUL.md", "AGENTS.md", "TOOLS.md", "MEMORY.md", "IDENTITY.md")

NODE_CANDIDATES = (
    Path.home() / ".dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node",
)
PKG_CANDIDATES = (
    Path.home() / ".dsh/profiles/node_modules/@deepseek-ai/dsh-agent-presets/lib/index.js",
)


def _first_existing(paths: tuple[Path, ...]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def official_copy(node: Path, pkg: Path, preset_id: str, name: str) -> tuple[bool, str]:
    """Call the platform's copyComposition via the managed Node.

    Returns (ok, detail). Uses discoverPresets so the source resolves the way
    the roster resolves it (first-root-wins), not by a guessed filesystem path.

    The module specifier must stay a raw path string: percent-encoding the
    `@` in `@deepseek-ai` (what Path.as_uri() does) breaks Node's relative
    import resolution inside the package, so the import dies with
    ERR_MODULE_NOT_FOUND even though the file exists.
    """
    script = (
        # NOTE: under `node -e`, argv has no script placeholder: user args start
        # at argv[1], so pkg=argv[1], id=argv[2], name=argv[3]. Using argv[2] for
        # the module imports `undefined` and dies with ERR_MODULE_NOT_FOUND.
        "const m = await import(process.argv[1]);"
        "const roots = ["
        "  { path: m.SHIPPED_PRESET_ROOT, trust: 'system' },"
        "  { path: process.env.HOME + '/.dsh/.agent-presets', trust: 'user' },"
        "];"
        "const presets = await m.discoverPresets(roots, process.argv[1]);"
        "const std = presets.find(p => p.id === 'standard');"
        "if (!std) throw new Error('standard preset not found in any root');"
        "const dir = await m.copyComposition(roots, std, process.argv[2], process.argv[3]);"
        "console.log(dir);"
    )
    proc = subprocess.run(
        [str(node), "--input-type=module", "-e", script, "file://" + str(pkg), preset_id, name],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return True, proc.stdout.strip().splitlines()[-1]
    detail = (proc.stderr or proc.stdout or "unknown error").strip()[-400:]
    return False, detail


def build_anchor(role_dir: Path) -> str:
    """Generate an anchor persona prefix. Never copy another preset's anchor."""
    return (
        "You are the role named by the files below, running on the {{model}} model.\n"
        "\n"
        "Behavioral authority lives in the role files, not here. Read all five slots before\n"
        "acting on any domain request, and update MEMORY.md afterwards:\n"
        "  SOUL.md     - stance, Y-Model STEPS paradigm, sizing rule, prohibitions\n"
        "  AGENTS.md   - STEPS milestone operating procedure and gotchas\n"
        "  TOOLS.md    - environment paths and CLI map\n"
        "  MEMORY.md   - declarative facts and state\n"
        "  IDENTITY.md - name, archetype, primary loop\n"
        f"All under {role_dir}/\n"
        "\n"
        "This prefix is an anchor, not a summary: it deliberately reproduces no clause, so\n"
        "editing those files can never drift from it.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a user-root agent preset for a role directory.")
    ap.add_argument("--id", required=True, help="preset id, [a-z0-9][a-z0-9-]*")
    ap.add_argument("--role-dir", required=True, help="role directory holding the five slots")
    ap.add_argument("--name", required=True, help="display name shown in the agent picker")
    ap.add_argument("--description", required=True, help="one-line description for the picker")
    ap.add_argument("--dsh-home", default="", help="override $DSH_HOME")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing preset directory (refuses without this flag)")
    ap.add_argument("--verify-only", action="store_true",
                    help="do not create anything; verify an existing preset")
    args = ap.parse_args()

    home = Path(args.dsh_home).expanduser() if args.dsh_home else Path.home() / ".dsh"
    role_dir = Path(args.role_dir).expanduser().resolve()
    dest = home / ".agent-presets" / args.id

    checks: list[dict] = []

    def add(cid: str, status: str, detail: str) -> None:
        checks.append({"id": cid, "status": status, "detail": detail})

    def emit(payload: dict) -> None:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    # 1. Argument validity (fail fast before touching the runtime).
    if not PRESET_ID.match(args.id):
        emit({"verdict": "FAIL", "error": f"preset id '{args.id}' violates [a-z0-9][a-z0-9-]*"})
        return 1

    # 2. Role directory sanity.
    missing_slots = [s for s in SLOTS if not (role_dir / s).exists()]
    if missing_slots:
        emit({
            "verdict": "FAIL",
            "error": f"role directory {role_dir} lacks slots: {missing_slots}",
            "hint": "compile the role slots first; a preset without its files is an empty identity",
        })
        return 1
    add("role-slots", "pass", f"all five slots present under {role_dir}")

    # 3. Verify-only mode.
    if args.verify_only:
        if not dest.exists():
            emit({"verdict": "FAIL", "error": f"no preset at {dest}"})
            return 1
        from check_persona_drift import analyze  # sibling script
        report = analyze(dest / "agent.cordis.yml", role_dir)
        report["checks"] = checks
        emit(report)
        return {"PASS": 0, "FAIL": 1, "UNVERIFIABLE": 2}[report["verdict"]]

    # 4. Refuse to overwrite without --force.
    if dest.exists() and not args.force:
        emit({
            "verdict": "FAIL",
            "error": f"{dest} already exists",
            "hint": "pass --force to replace it, or choose another id",
        })
        return 1

    # 5. Platform copy via the official API.
    node = _first_existing(NODE_CANDIDATES)
    pkg = _first_existing(PKG_CANDIDATES)
    if node is None or pkg is None:
        emit({
            "verdict": "UNVERIFIABLE",
            "error": f"managed node ({node}) or presets package ({pkg}) not found",
            "hint": "fallback: run inside a cordis-preset session and use agentPresets.copy()",
        })
        return 2

    if dest.exists():
        shutil.rmtree(dest)
    ok, detail = official_copy(node, pkg, args.id, args.name)
    if not ok or not dest.exists():
        emit({
            "verdict": "FAIL",
            "error": f"official copyComposition failed: {detail}",
        })
        return 1
    add("official-copy", "pass", f"platform copyComposition() created {dest}")

    # 6. Rewrite persona + metadata — the part the platform cannot know.
    import yaml

    class PatchLoader(yaml.SafeLoader):
        pass

    PatchLoader.add_constructor(
        "tag:yaml.org,2002:js", lambda loader, node: loader.construct_scalar(node)
    )

    comp = dest / "agent.cordis.yml"
    tree = yaml.load(comp.read_text(encoding="utf-8"), Loader=PatchLoader)
    persona = next(e for e in tree if e.get("id") == "persona")
    persona["config"]["prefix"] = build_anchor(role_dir)
    persona["config"]["suffix"] = ""
    comp.write_text(yaml.safe_dump(tree, allow_unicode=True, sort_keys=False), encoding="utf-8")
    add("persona-anchor", "pass", "persona prefix rewritten as a role-specific anchor")

    meta = dest / "preset.yml"
    mtree = yaml.load(meta.read_text(encoding="utf-8"), Loader=PatchLoader) or {}
    mtree["name"] = args.name
    mtree["description"] = args.description
    meta.write_text(yaml.safe_dump(mtree, allow_unicode=True, sort_keys=False), encoding="utf-8")
    add("preset-meta", "pass", f"name='{args.name}'")

    # 7. Static gate: the anchor we just wrote must pass the drift checker.
    from check_persona_drift import analyze
    report = analyze(comp, role_dir)
    if report["verdict"] != "PASS":
        shutil.rmtree(dest, ignore_errors=True)
        emit({
            "verdict": "FAIL",
            "error": "generated anchor failed its own drift check; preset removed",
            "drift_report": report,
        })
        return 1
    add("anchor-gate", "pass", report.get("pointer_detail", "anchor valid"))

    emit({
        "verdict": "PASS",
        "preset_dir": str(dest),
        "preset_id": args.id,
        "checks": checks,
        "next_step": (
            "preset registry mounts once per process: restart the desktop app, "
            f"then pick '{args.name}' in the agent selector of a NEW session"
        ),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
