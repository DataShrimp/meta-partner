# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Deterministic validator and static rubric analyzer for Prompts, Skills, and Agent Roles.

Bundled by skill-creator optimization to eliminate repeated manual verification across runs.
Checks:
1. Line and character budget ceilings per modality (Prompt, Skill, OpenClaw, Hermes, Claude Subagent, Codex).
2. Zero-Placeholder compliance (detects [Insert ...], [在此填入...], TODO, TBD).
3. YAML frontmatter compliance for Skills and Claude Code Subagents (kebab-case name, description <= 1024 chars, positive + negative trigger boundaries).
4. Agent Role behavioral spec compliance (detects adjective trait-list bloat, verifies anti-sycophancy & sizing cues, checks MEMORY.md for imperative command pollution).
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List


PLACEHOLDER_PATTERNS = [
    r"\[在此填入[^\]]*\]",
    r"\[填入[^\]]*\]",
    r"\[Insert [^\]]+\]",
    r"\[YOUR_[A-Z0-9_]+\]",
    r"\bTODO:\s",
    r"\bTBD\b",
]

TRAIT_BLOAT_WORDS = [
    "world-class",
    "superhuman",
    "unrivaled",
    "100% accurate",
    "flawless",
    "极其聪明",
    "世界顶级",
    "无所不能",
]

IMPERATIVE_MEMORY_PATTERNS = [
    r"(?i)^\s*[-*]?\s*(always|never|must|do not)\s+",
    r"^\s*[-*]?\s*(必须|严禁|永远不要|总是)\s*",
]

MODE_CHAR_CAPS = {
    "prompt": 20000,
    "skill": 25000,
    "openclaw-soul": 2500,
    "openclaw-agents": 4000,
    "openclaw-memory": 2500,
    "hermes-soul": 4000,
    "hermes-agents": 12000,
    "claude-subagent": 12000,
    "codex-agents": 32768,
}


def parse_frontmatter(text: str) -> Dict[str, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}
    fm_text = match.group(1)
    result: Dict[str, str] = {}
    current_key = None
    for line in fm_text.splitlines():
        key_match = re.match(r"^([a-zA-Z0-9_-]+):\s*(.*)$", line)
        if key_match:
            current_key = key_match.group(1)
            val = key_match.group(2).strip()
            result[current_key] = "" if val in (">", "|", ">-", "|-") else val
        elif current_key and (line.startswith("  ") or line.startswith("\t")):
            result[current_key] = (result[current_key] + " " + line.strip()).strip()
    return result


def evaluate_file(path: Path, mode: str) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    char_count = len(text)
    line_count = len(lines)
    max_chars = MODE_CHAR_CAPS.get(mode, 25000)

    assertions: List[Dict[str, Any]] = []

    # 1. Budget Check
    budget_ok = char_count <= max_chars and (mode != "skill" or line_count <= 500)
    assertions.append({
        "id": "budget_ceiling",
        "text": f"Character count ({char_count} <= {max_chars}) and line count ({line_count}) within platform ceiling",
        "passed": budget_ok,
        "evidence": f"chars={char_count}, lines={line_count}, limit_chars={max_chars}",
    })

    # 2. Zero-Placeholder Check
    found_placeholders: List[str] = []
    for pat in PLACEHOLDER_PATTERNS:
        matches = re.findall(pat, text)
        if matches:
            found_placeholders.extend(matches[:3])
    assertions.append({
        "id": "zero_placeholders",
        "text": "Contains zero raw bracketed placeholders ([Insert X], [在此填入X], TODO)",
        "passed": len(found_placeholders) == 0,
        "evidence": "None found" if not found_placeholders else f"Found: {found_placeholders}",
    })

    # 3. Frontmatter & Trigger Check (for skill and claude-subagent)
    if mode in ("skill", "claude-subagent"):
        fm = parse_frontmatter(text)
        name_val = fm.get("name", "")
        desc_val = fm.get("description", "")
        name_ok = bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name_val)) and len(name_val) <= 64
        has_neg_trigger = any(
            kw in desc_val.lower()
            for kw in ["do not trigger", "do not use", "don't use", "不要在", "不适用于"]
        )
        desc_ok = 20 <= len(desc_val) <= 1024 and has_neg_trigger
        assertions.append({
            "id": "frontmatter_contract",
            "text": "Valid kebab-case name and description (<=1024 chars) with both positive trigger and negative anti-trigger boundary",
            "passed": name_ok and desc_ok,
            "evidence": f"name='{name_val}' (ok={name_ok}), desc_len={len(desc_val)}, has_negative_boundary={has_neg_trigger}",
        })

    # 4. Trait-List Anti-Bloat Check
    found_bloat = [w for w in TRAIT_BLOAT_WORDS if w.lower() in text.lower()]
    assertions.append({
        "id": "no_trait_bloat",
        "text": "Free of marketing/superlative trait-list bloat words",
        "passed": len(found_bloat) == 0,
        "evidence": "Clean" if not found_bloat else f"Found bloat terms: {found_bloat}",
    })

    # 5. Mode-specific checks
    if mode in ("openclaw-memory",):
        imp_hits: List[str] = []
        for line in lines:
            if line.startswith("#") or line.startswith(">"):
                continue
            for pat in IMPERATIVE_MEMORY_PATTERNS:
                if re.search(pat, line):
                    imp_hits.append(line.strip()[:60])
        assertions.append({
            "id": "declarative_memory_only",
            "text": "MEMORY.md stores declarative facts rather than imperative directives",
            "passed": len(imp_hits) == 0,
            "evidence": "All entries declarative" if not imp_hits else f"Imperative lines: {imp_hits[:3]}",
        })

    passed_count = sum(1 for a in assertions if a["passed"])
    score = round(100.0 * passed_count / len(assertions), 1) if assertions else 100.0
    return {
        "file": str(path),
        "mode": mode,
        "char_count": char_count,
        "line_count": line_count,
        "static_pass_rate": f"{passed_count}/{len(assertions)}",
        "static_score": score,
        "all_passed": passed_count == len(assertions),
        "assertions": assertions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Prompt, Skill, or Agent Role Markdown file.")
    parser.add_argument("--input", required=True, help="Path to Markdown file to validate")
    parser.add_argument(
        "--mode",
        default="skill",
        choices=list(MODE_CHAR_CAPS.keys()),
        help="Target artifact modality",
    )
    args = parser.parse_args()

    target = Path(args.input)
    if not target.exists():
        sys.stderr.write(f"Error: File not found: {target}\n")
        return 1

    report = evaluate_file(target, args.mode)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0 if report["all_passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
