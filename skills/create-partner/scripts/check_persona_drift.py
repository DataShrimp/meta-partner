# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Detect content drift between a dsh persona prefix and the role files it claims to summarize.

The persona prefix is a hand-maintained copy of part of SOUL.md. Copies drift, and this
kind of drift has no runtime symptom: the model keeps working, just with an outdated
contract. This script makes the drift a number.

It compares the *clauses* the source declares against the ones the prefix reproduces,
using token-level coverage rather than char similarity, because a prefix can be short and
still be complete, or long and still omit a rule.

Read-only. Exit codes: 0 ok, 1 hard failure, 2 unverifiable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CLAUSE_MARKERS = {
    "sizing": ["sizing", "篇幅", "concise", "terse", "<= 3 sentences"],
    "prohibitions": ["prohibition", "never open", "never output", "禁令", "hollow"],
    "anti_sycophancy": ["sycophan", "agree because", "谄媚", "epistemic"],
    "meta_orchestration": ["meta-orchestration", "co-architect", "meta-prompt compiler"],
    "dual_track": ["dual-track", "track 1", "track 2", "blind-spot", "盲区"],
    "escape_hatch": ["escape hatch", "earned-depth", "逃生舱"],
    "memory_hygiene": ["declarative", "memody", "memory.md", "imperative"],
    "verification_gate": ["verif", "gate", "validate", "校验", "门禁"],
}

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "be", "by", "for",
    "on", "at", "as", "it", "its", "that", "this", "with", "from", "not", "do", "does",
    "never", "always", "must", "should", "you", "your", "we", "our", "if", "then",
}


def find_prefix_blocks(patch_text: str) -> list[tuple[str, int]]:
    """Return (prefix_value, line_index) for every `prefix:` head in the file.

    A profile patch may insert several presets, each with its own persona; the
    first block in the file is not necessarily the one being audited.
    """
    heads = []
    for i, l in enumerate(patch_text.splitlines()):
        if l.strip().startswith("prefix:"):
            heads.append((l.split("prefix:", 1)[1].strip(), i))
    return heads


def extract_prefix(patch_text: str, block_index: int = 0) -> tuple[str, int | None]:
    """Pull one persona prefix out of a patch or preset composition file.

    Accepts both authoring shapes: the literal block form (`prefix: |`) and the
    dumped-scalar form (`prefix: '...'` or `prefix: >-`-style flow), because a
    scaffolded preset round-trips through yaml.safe_dump and comes back as a
    quoted scalar with escaped newlines. `block_index` selects among multiple
    preset inserts in one file; callers that mean a specific preset should
    locate it via find_prefix_blocks plus the surrounding context instead of
    assuming file order.
    """
    lines = patch_text.splitlines()
    heads = [(i, l) for i, l in enumerate(lines) if l.strip().startswith("prefix:")]
    if not heads:
        return "", None
    if block_index >= len(heads):
        return "", None
    start, head_line = heads[block_index]
    head = head_line
    value = head.split("prefix:", 1)[1].strip()

    if value in ("|", "|-", "|+", ">", ">-", ">+"):
        indent = len(head) - len(head.lstrip())
        body: list[str] = []
        for line in lines[start + 1:]:
            stripped = line.strip()
            if stripped and (len(line) - len(line.lstrip())) <= indent - 2:
                break
            body.append(stripped)
        return "\n".join(l for l in body if l), start + 1

    # Dumped scalar: yaml folds the value across continuation lines. Two dumped
    # styles occur — double-quoted with literal \n escapes (multi-line values)
    # and single-quoted folded prose. Rather than hand-parsing either, collect
    # every continuation line until the next mapping key and let the yaml
    # parser itself decode the result.
    if value not in ("",) and not value[0].isalnum() and value[0] not in "|>":
        key_indent = len(head) - len(head.lstrip())
        collected = [value]
        for line in lines[start + 1:]:
            if line.strip() and (len(line) - len(line.lstrip())) <= key_indent:
                break
            collected.append(line.strip())
        import yaml
        joined = "\n".join(collected)
        # A trailing quote may have been stripped as a dedent boundary; restore
        # the opening style so the parser sees a complete scalar.
        if joined[0] == "'" and not joined.rstrip().endswith("'"):
            joined += "'"
        elif joined[0] == '"' and not joined.rstrip().endswith('"'):
            joined += '"'
        try:
            return str(yaml.safe_load(joined) or ""), start + 1
        except yaml.YAMLError:
            return joined, start + 1
    import yaml

    try:
        return str(yaml.safe_load(value) or ""), start + 1
    except yaml.YAMLError:
        return value, start + 1


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def clause_present(text: str, keys: list[str]) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keys)


# A prefix carrying this phrase declares itself an anchor: it names the authority and
# refuses to duplicate it. Detection is phrase-based so the declaration stays visible
# to a human reading the patch file.
ANCHOR_MARKER = "anchor, not a summary"

POINTER_FILES = ("SOUL.md", "AGENTS.md", "MEMORY.md")


def _analyze_anchor(prefix: str, line_no: int | None, patch_path: Path, role_dir: Path) -> dict:
    """Validate anchor mode: referenced files exist and the pull pointer is installed."""
    # Extract every Markdown file name the anchor mentions, not just the three expected
    # ones: an anchor that points at a file which does not exist is worse than one that
    # omits a file, because it sends the model to a 404.
    named = sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]*\.md\b", prefix)))
    referenced = [f for f in POINTER_FILES if f in prefix]
    absent_in_prefix = [f for f in POINTER_FILES if f not in prefix]
    missing_on_disk = [f for f in named if not (role_dir / f).exists()]

    # The anchor only works if something tells the model to read those files.
    # Two channels count: the anchor text itself carries the role directory path
    # (self-contained, the normal shape), or the global AGENTS.md carries a
    # bootstrap pointer (the legacy fallback shape). Either suffices.
    pointer_ok, pointer_detail = False, "not checked"
    if str(role_dir) in prefix:
        pointer_ok = True
        pointer_detail = f"anchor text carries the role directory path ({role_dir})"
    else:
        global_agents = Path.home() / ".dsh/AGENTS.md"
        if global_agents.exists():
            text = global_agents.read_text(encoding="utf-8")
            pointer_ok = str(role_dir) in text and "SOUL.md" in text
            pointer_detail = (
                f"{global_agents} carries the bootstrap pointer"
                if pointer_ok
                else f"anchor names no role path and {global_agents} lacks a pointer to it"
            )
        else:
            pointer_detail = "anchor names no role path and ~/.dsh/AGENTS.md does not exist"

    # Misrouting guard: an anchor that carries a path into a DIFFERENT role
    # directory (one that itself holds a SOUL.md) sends the model to another
    # role's files even when a fallback pointer exists elsewhere. Copy-pasting
    # another preset's anchor is exactly how this happens.
    cross_role = []
    for other in sorted(set(re.findall(r"/(?:[\w.-]+/)+", prefix))):
        cand = Path(other)
        if cand.is_dir() and (cand / "SOUL.md").exists() and cand.resolve() != role_dir.resolve():
            cross_role.append(str(cand))

    too_long = len(prefix) > 900
    problems = []
    if missing_on_disk:
        problems.append(f"referenced but absent: {missing_on_disk}")
    if absent_in_prefix:
        problems.append(f"anchor omits: {absent_in_prefix}")
    if not pointer_ok:
        problems.append(pointer_detail)
    if cross_role:
        problems.append(
            f"anchor points at a different role directory: {cross_role} "
            f"(expected {role_dir}); a copied anchor sends this preset's sessions "
            f"to another role's files"
        )
    if too_long:
        problems.append(f"anchor is {len(prefix)} chars; an anchor over 900 chars is a summary")

    return {
        "verdict": "FAIL" if problems else "PASS",
        "mode": "anchor",
        "patch": str(patch_path),
        "prefix_line": line_no,
        "prefix_chars": len(prefix),
        "referenced": referenced,
        "named_files": named,
        "pointer_detail": pointer_detail,
        "cross_role_paths": cross_role,
        "problems": problems,
        "note": (
            "Anchor mode: the prefix declares itself a pointer, so clause coverage is not "
            "asserted. What is asserted instead is that the pointed-at files exist and that "
            "the pull pointer which sends the model to them is installed."
        ),
    }


def locate_preset_block(patch_text: str, preset_id: str) -> int | None:
    """Return the prefix block index belonging to one preset insert.

    A profile patch may insert several presets; each insert's config carries
    `id: <preset-id>`. Walk the text keeping only prefix heads that appear
    AFTER the requested id and BEFORE the next sibling insert id — that window
    is the preset's own persona.
    """
    import re as _re

    lines = patch_text.splitlines()
    heads = [i for i, l in enumerate(lines) if l.strip().startswith("prefix:")]
    if not heads:
        return None
    id_line = None
    for i, l in enumerate(lines):
        if l.strip() == f"id: {preset_id}":
            id_line = i
            break
    if id_line is None:
        return 0 if len(heads) == 1 else None
    # Next insert id at equal-or-shallower indent closes the window.
    window_open = False
    for i, l in enumerate(lines):
        if i == id_line:
            window_open = True
            continue
        if window_open:
            if l.strip().startswith("id: ") and l.strip() != f"id: {preset_id}" and _indent(l) <= _indent(lines[id_line]):
                break
            if l.strip().startswith("prefix:"):
                for h in heads:
                    if h == i:
                        return heads.index(h)
    return None


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def analyze(
    patch_path: Path,
    role_dir: Path,
    max_missing: int = 0,
    strict_tokens: bool = False,
    preset_id: str = "",
) -> dict:
    """Compare one patch's persona prefix against SOUL.md. Importable; never raises on drift."""
    if not patch_path.exists():
        return {"verdict": "FAIL", "error": f"patch not found: {patch_path}"}

    text = patch_path.read_text(encoding="utf-8")
    block = 0
    if preset_id:
        block = locate_preset_block(text, preset_id) or 0
    prefix, line_no = extract_prefix(text, block)
    if not prefix:
        return {
            "verdict": "UNVERIFIABLE",
            "error": "no persona prefix block in the patch file",
            "patch": str(patch_path),
        }

    # An anchor deliberately reproduces no clauses, so clause coverage is the wrong
    # assertion for it. Anchor mode moves the burden to a different invariant: the
    # files it points at must exist, and the pull-based pointer must exist, because
    # without that pointer the model never learns it should read them.
    if ANCHOR_MARKER in prefix.lower():
        return _analyze_anchor(prefix, line_no, patch_path, role_dir)

    soul_path = role_dir / "SOUL.md"
    if not soul_path.exists():
        return {"verdict": "FAIL", "error": f"no SOUL.md under {role_dir}"}
    soul = soul_path.read_text(encoding="utf-8")

    present = [name for name, keys in CLAUSE_MARKERS.items() if clause_present(soul, keys)]
    missing = [name for name in present if not clause_present(prefix, CLAUSE_MARKERS[name])]
    unexpected = [
        name for name, keys in CLAUSE_MARKERS.items()
        if name not in present and clause_present(prefix, keys)
    ]

    soul_tok, prefix_tok = tokens(soul), tokens(prefix)
    vocab_cov = len(soul_tok & prefix_tok) / len(soul_tok) if soul_tok else 0.0
    char_ratio = len(prefix) / len(soul) if soul else 0.0

    hard_fail = len(missing) > max_missing
    if strict_tokens and vocab_cov < 0.60:
        hard_fail = True

    return {
        "verdict": "FAIL" if hard_fail else "PASS",
        "patch": str(patch_path),
        "prefix_line": line_no,
        "source": str(soul_path),
        "prefix_chars": len(prefix),
        "source_chars": len(soul),
        "char_ratio": round(char_ratio, 3),
        "source_clauses": present,
        "clauses_missing_in_prefix": missing,
        "clauses_only_in_prefix": unexpected,
        "token_vocabulary_coverage": round(vocab_cov, 3),
        "note": (
            "The prefix claims SOUL.md is authoritative while reproducing part of it. "
            "Missing clauses mean the copy has drifted: either trim the prefix to an anchor "
            "or regenerate it, do not let both versions stand."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare a persona prefix against its source role files.")
    ap.add_argument("--patch", default="", help="Cordis patch file holding the persona prefix")
    ap.add_argument("--role-dir", default="", help="role directory (SOUL.md is the source of record)")
    ap.add_argument("--dsh-home", default="", help="override $DSH_HOME (used to find the desktop patch)")
    ap.add_argument("--profile", default="desktop", help="profile whose patch file to read")
    ap.add_argument("--preset-id", default="",
                    help="when the patch inserts several presets, audit this one's persona block")
    ap.add_argument("--max-missing", type=int, default=0,
                    help="how many source clauses the prefix may omit before failing (default 0)")
    ap.add_argument("--strict-tokens", action="store_true",
                    help="also fail when the prefix drops more than 40%% of SOUL token vocabulary")
    args = ap.parse_args()

    home = Path(args.dsh_home).expanduser() if args.dsh_home else Path.home() / ".dsh"
    patch_path = Path(args.patch).expanduser() if args.patch else (
        home / "profiles" / args.profile / "cordis.patch.yml"
    )
    if not args.role_dir:
        print(json.dumps({"verdict": "FAIL", "error": "--role-dir is required"}, indent=2))
        return 1

    report = analyze(
        patch_path,
        Path(args.role_dir).expanduser(),
        max_missing=args.max_missing,
        strict_tokens=args.strict_tokens,
        preset_id=args.preset_id,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return {"PASS": 0, "FAIL": 1, "UNVERIFIABLE": 2}[report["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
