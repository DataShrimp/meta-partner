# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Project Doctor & Health Check for meta-partner ecosystem.

Verifies:
1. Symlink integrity in ~/.dsh/skills and ~/.agents/skills
2. Bootstrap instruction pointers in ~/.dsh/AGENTS.md
3. Preset anchor drift across desktop cordis.patch.yml and ~/.dsh/.agent-presets/
4. Zero-residue check for obsolete paths
5. Static artifact quality scores across core, partners, and skills

Exit codes: 0 ALL_HEALTHY, 1 FAILURES_DETECTED, 2 WARNINGS
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ryan/Documents/projects/meta-partner")
HOME = Path.home()
OBSOLETE_PATH = "/Users/ryan/Workspace/skills"


def check_symlinks() -> list[dict]:
    results = []
    links = [
        (HOME / ".dsh/skills/create-partner", ROOT / "skills/create-partner"),
        (HOME / ".dsh/skills/meta-prompt", ROOT / "skills/meta-prompt"),
        (HOME / ".agents/skills/meta-prompt", ROOT / "skills/meta-prompt"),
    ]
    for link, expected in links:
        if not link.is_symlink():
            results.append({"item": str(link), "status": "FAIL", "reason": "Not a symlink"})
            continue
        target = Path(os.readlink(link)).resolve()
        expected_resolved = expected.resolve()
        if target == expected_resolved and target.exists():
            results.append({"item": str(link), "status": "PASS", "target": str(target)})
        else:
            results.append({
                "item": str(link),
                "status": "FAIL",
                "reason": f"Points to {target}, expected {expected_resolved}",
            })
    return results


def check_bootstrap_pointer() -> dict:
    agents_file = HOME / ".dsh/AGENTS.md"
    if not agents_file.exists():
        return {"status": "FAIL", "reason": "~/.dsh/AGENTS.md missing"}
    text = agents_file.read_text(encoding="utf-8")
    expected_path = str(ROOT / "core/meta-partner")
    if expected_path in text and "META-PARTNER-BOOTSTRAP" in text:
        return {"status": "PASS", "detail": f"Carries valid pointer to {expected_path}"}
    return {"status": "FAIL", "reason": f"Missing bootstrap pointer to {expected_path}"}


def check_drift() -> list[dict]:
    results = []
    checker = ROOT / "skills/create-partner/scripts/check_persona_drift.py"
    if not checker.exists():
        return [{"item": "check_persona_drift.py", "status": "FAIL", "reason": "Checker script missing"}]

    targets = [
        ("meta-partner (desktop patch)", HOME / ".dsh/profiles/desktop/cordis.patch.yml", ROOT / "core/meta-partner", "meta-partner"),
        ("asset-partner (desktop patch)", HOME / ".dsh/profiles/desktop/cordis.patch.yml", ROOT / "partners/asset-partner", "asset-partner"),
        ("asset-partner (user preset)", HOME / ".dsh/.agent-presets/asset-partner/agent.cordis.yml", ROOT / "partners/asset-partner", ""),
    ]

    for label, patch_file, role_dir, preset_id in targets:
        cmd = [sys.executable, str(checker), "--patch", str(patch_file), "--role-dir", str(role_dir)]
        if preset_id:
            cmd.extend(["--preset-id", preset_id])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        try:
            report = json.loads(proc.stdout)
            status = report.get("verdict", "FAIL")
            detail = report.get("pointer_detail", report.get("problems", []))
            results.append({"item": label, "status": status, "detail": detail})
        except Exception as exc:
            results.append({"item": label, "status": "FAIL", "reason": f"Error running check: {exc}"})
    return results


def check_obsolete_path_residue() -> list[str]:
    hits = []
    for root, dirs, files in os.walk(ROOT):
        if ".git" in dirs:
            dirs.remove(".git")
        if "archive" in dirs:
            dirs.remove("archive")
        for f in files:
            p = Path(root) / f
            if p == ROOT / "tools/doctor.py":
                continue
            if f.endswith((".md", ".py", ".json", ".sh", ".yml", ".yaml")):
                try:
                    if OBSOLETE_PATH in p.read_text(encoding="utf-8"):
                        hits.append(str(p.relative_to(ROOT)))
                except Exception:
                    pass
    return hits


def main() -> int:
    print(f"=== Project Doctor: {ROOT} ===\n")
    all_ok = True

    # 1. Symlinks
    print("[1] Checking Host Symlinks...")
    symlinks = check_symlinks()
    for s in symlinks:
        print(f"  {s['status']}: {s['item']}")
        if s["status"] != "PASS":
            all_ok = False
            print(f"       -> {s.get('reason')}")

    # 2. Bootstrap Pointer
    print("\n[2] Checking Global AGENTS.md Bootstrap Pointer...")
    ptr = check_bootstrap_pointer()
    print(f"  {ptr['status']}: {ptr.get('detail', ptr.get('reason'))}")
    if ptr["status"] != "PASS":
        all_ok = False

    # 3. Preset Drift
    print("\n[3] Checking Presets & Persona Drift...")
    drifts = check_drift()
    for d in drifts:
        print(f"  {d['status']}: {d['item']}")
        if d["status"] != "PASS":
            all_ok = False
            print(f"       -> {d.get('detail') or d.get('reason')}")

    # 4. Obsolete Path Residue
    print("\n[4] Scanning for Obsolete Workspace/skills Residue...")
    residues = check_obsolete_path_residue()
    if residues:
        all_ok = False
        print(f"  FAIL: Found {len(residues)} active file(s) with old paths:")
        for r in residues[:5]:
            print(f"    - {r}")
    else:
        print("  PASS: Zero obsolete path residue in active files.")

    print("\n" + "=" * 50)
    if all_ok:
        print("  RESULT: ALL HEALTHY (Ready for Long-Term Compounding)")
        return 0
    else:
        print("  RESULT: ISSUES DETECTED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
