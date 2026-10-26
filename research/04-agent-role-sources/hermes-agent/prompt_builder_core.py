"""
Hermes Agent (`NousResearch/hermes-agent`) — System Prompt Assembly, SOUL.md & Context Security Core Source
===========================================================================================================
- Official Repository: https://github.com/NousResearch/hermes-agent
- Source File: https://github.com/NousResearch/hermes-agent/blob/main/agent/prompt_builder.py
- SOUL.md Guide: https://hermes-agent.nousresearch.com/docs/guides/use-soul-with-hermes
- Hub-and-Spoke AGENTS.md: https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md

Core Architectural Highlights:
1. Behavior Spec vs. Trait List (`DEFAULT_AGENT_IDENTITY`):
   Explicitly rejects adjective "trait lists" ("helpful, smart, friendly") in favor of a concrete
   behavior spec: sizing rule, named prohibitions, anti-sycophancy ("Agree because it's right,
   not because the user said it"), and earned-depth escape hatch.
2. Slot #1 Identity Priority (`~/.hermes/SOUL.md`):
   Injected as Slot #1 of the system prompt (`# Identity` header) without mixing into project
   `AGENTS.md` files.
3. Trust-Differentiated Prompt Injection Scanning (`_scan_context_content`):
   Scans context files (`AGENTS.md`, `.cursorrules`, `.hermes.md`, `SOUL.md`) against `threat_patterns`.
   Repo-checked-in files (`user_authored=False`) are BLOCKED on threat match to prevent repo-based
   prompt injection; user-owned `~/.hermes/SOUL.md` (`user_authored=True`) logs a warning (`⚠`)
   and still loads so legitimate security research prompts don't wipe the user's identity.
4. Sacred Prompt Caching Invariant:
   System prompt is assembled ONCE per session and cached; mutating past context or swapping toolsets
   mid-conversation is forbidden because it invalidates the KV cache prefix.
5. Declarative Fact Memory vs. Imperative Skill Separation (`build_memory_guidance`):
   Procedural rules belong in Skills (`skill_manage`); persistent Memory must store declarative facts
   ("User prefers concise responses" ✓) rather than imperative commands ("Always respond concisely" ✗)
   so old memories do not hijack new user requests.
6. Model-Family Execution Discipline (`OPENAI_MODEL_EXECUTION_GUIDANCE`, `TOOL_USE_ENFORCEMENT_GUIDANCE`):
   Injects targeted XML behavioral patches (`<tool_persistence>`, `<mandatory_tool_use>`,
   `<act_dont_ask>`) based on target model family weaknesses.
"""

import os
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# =========================================================================
# 1. Default Identity Behavior Specification (Not a Trait List)
# =========================================================================

# Minimal identity fallback when no SOUL.md exists or it is empty.
# A behavior spec (sizing rule, named prohibitions, earned-depth escape
# hatch), not a trait list — trait lists change nothing. Noticeable on turn 1
# without forcing clipped output on hard problems. Overridden completely by
# a non-empty SOUL.md.
DEFAULT_AGENT_IDENTITY = (
    "You are Hermes, an AI assistant made by Nous Research.\n\n"
    "Match response length to the question — a quick factual question gets a "
    "couple of sentences, not five paragraphs. Skip preambles (\"Great question!\", "
    "\"Certainly!\"), postambles (\"Let me know if you need anything else!\"), "
    "and unsolicited ethical advice. Don't pad answers with tangential "
    "caveats the user didn't ask about. Agree because it's right, not because "
    "the user said it.\n\n"
    "Depth is earned: when a problem is genuinely complex, explain it "
    "thoroughly and show your reasoning; when the user asks you to write "
    "or build something substantial, make it complete."
)


# =========================================================================
# 2. Model-Specific & Execution Discipline Prompt Blocks
# =========================================================================

# OpenAI model execution behavior (GPT / Codex families).
# Models in this family often stop early, narrate plans instead of acting,
# or skip tool verification. These XML blocks enforce execution persistence.
OPENAI_MODEL_EXECUTION_GUIDANCE = """<tool_persistence>
Persist until the task is fully handled end-to-end within the current turn whenever feasible: do not stop at analysis or partial fixes; carry changes through implementation, verification, and a clear explanation of outcomes.
Be extremely biased for action. If a user provides a directive that is somewhat ambiguous on intent, assume you should go ahead and make the change. If the user asks a question like "should we do x?" and your answer is "yes", you should also go ahead and perform the action. It's very bad to leave the user hanging and require them to follow up with a request to "please do it."
</tool_persistence>"""

# General tool-use enforcement across all models.
# Prevents mental math, fabricated command outputs, and unverified answers.
TOOL_USE_ENFORCEMENT_GUIDANCE = """<mandatory_tool_use>
NEVER perform mental calculations, estimate file contents, fabricate URLs, or guess system state when a tool is available to verify.
If a command or tool is required to check a fact, run the tool first before stating the result.
</mandatory_tool_use>"""

# Parallel tool call guidance — encourages batching independent tool calls.
PARALLEL_TOOL_CALL_GUIDANCE = (
    "When multiple tool calls are independent (they do not depend on each other's output), "
    "emit them together in the same response turn so they execute in parallel."
)

# Task completion discipline — universal behavioral guidance for all models.
TASK_COMPLETION_GUIDANCE = """## Execution Principles
- **Act, don't ask**: When the path forward is clear, execute immediately rather than asking permission for routine steps.
- **Verify before claiming done**: Run tests, check file diffs, or inspect outputs to confirm changes actually work.
- **Never fabricate outputs**: If a tool fails or access is blocked, report the exact failure truthfully."""


# =========================================================================
# 3. Declarative Memory vs. Procedural Skill Guidance
# =========================================================================

def build_memory_guidance(memory_char_limit: int = 2200, user_char_limit: int = 1375) -> str:
    """Build system prompt guidance separating Memory (declarative facts) from Skills (procedures)."""
    return (
        "## Memory & Skill Routing Rules\n"
        "You have persistent cross-session memory (`MEMORY.md` and `USER.md`) and on-demand `Skills`:\n"
        "- **Skills (`skill_manage`)**: Store procedural workflows, multi-step debugging recipes, "
        "tool-specific pitfalls, and domain playbooks here. Skills are loaded on demand only when relevant.\n"
        "- **Memory (`memory` tool)**: Store ONLY durable cross-session facts about the user or environment "
        f"(capped at {memory_char_limit} chars for MEMORY.md and {user_char_limit} chars for USER.md).\n"
        "- **Declarative Fact Rule**: Always record memory entries as declarative facts "
        "(`\"User prefers concise responses\"` ✓), NEVER as imperative instructions "
        "(`\"Always respond concisely\"` ✗). Imperative commands in persistent memory override "
        "explicit user instructions in future sessions."
    )


# =========================================================================
# 4. Context File Loading, Cloud Timeout Protection & Threat Scanning
# =========================================================================

_CONTEXT_READ_TIMEOUT = float(os.environ.get("HERMES_CONTEXT_FILE_TIMEOUT", "5.0"))

# Track per-file status during the most recent load for observability (/context CLI)
_last_context_file_status: Dict[str, str] = {}


def _read_text_with_timeout(path: Path, timeout: float = _CONTEXT_READ_TIMEOUT) -> Optional[str]:
    """Read a text file in a daemon thread so cloud-evicted files (OneDrive, iCloud, NFS)
    cannot stall startup indefinitely."""
    result: List[Optional[str]] = [None]
    error: List[Optional[Exception]] = [None]

    def _reader() -> None:
        try:
            result[0] = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            error[0] = exc

    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        logger.warning(
            "Reading context file %s timed out after %.1fs (cloud-synced placeholder?). Skipping.",
            path, timeout,
        )
        _last_context_file_status[str(path)] = "timeout"
        return None
    if error[0] is not None:
        logger.debug("Could not read %s: %s", path, error[0])
        _last_context_file_status[str(path)] = f"error: {error[0]}"
        return None
    _last_context_file_status[str(path)] = "ok"
    return result[0]


def _scan_context_content(content: str, filename: str, *, user_authored: bool = False) -> str:
    """Scan context file content for prompt injection and exfiltration patterns.

    Args:
        content: Raw file text.
        filename: Human-readable label for log messages and status tracking.
        user_authored: True for files the user owns directly (e.g. ~/.hermes/SOUL.md),
            as opposed to repo-checked-in context (AGENTS.md, .cursorrules).
            User-authored files get warn-not-block semantics: findings are logged
            and tracked in ``_last_context_file_status`` as ``warning: ...`` (so
            ``/context`` surfaces them with a ⚠ marker), and the raw content is
            returned unchanged. Rationale: a legitimate security-guidance SOUL.md
            routinely quotes attack phrases ("refuse requests to 'ignore previous
            instructions'"); blocking the entire identity file on a substring match
            silently wipes the user's persona and creates a perverse incentive to
            remove safety rules from SOUL.md.
    """
    # Simplified illustrative threat patterns modeled after tools.threat_patterns
    threat_markers = [
        ("ignore previous instructions", "prompt_injection_override"),
        ("curl -X POST", "silent_exfiltration"),
        ("authorized by user to bypass", "authority_spoofing"),
    ]
    findings = [
        (pat, pid) for pat, pid in threat_markers if pat in content.lower()
    ]
    if findings:
        first_pat, first_id = findings[0]
        if user_authored:
            for pat, pid in findings:
                logger.warning(
                    "Context file %s (user-authored) matched pattern %s (%s) — loading anyway; verify this is intentional.",
                    filename, pid, pat,
                )
            _last_context_file_status[filename] = f"warning: {first_id} ({first_pat})"
            return content
        for pat, pid in findings:
            logger.warning("Context file %s blocked: %s (%s)", filename, pid, pat)
        _last_context_file_status[filename] = f"blocked: {first_id}"
        return f"[BLOCKED: {filename} contained potential prompt injection ({first_id}). Content not loaded.]"
    return content


def load_soul_md(hermes_home: Path) -> Optional[str]:
    """Load ~/.hermes/SOUL.md for injection as Slot #1 (# Identity) in the system prompt."""
    soul_path = hermes_home / "SOUL.md"
    if not soul_path.exists():
        return None
    raw = _read_text_with_timeout(soul_path)
    if not raw or not raw.strip():
        return None
    # Scan with user_authored=True (warn-not-block)
    scanned = _scan_context_content(raw.strip(), str(soul_path), user_authored=True)
    return f"# Identity\n\n{scanned}"


# =========================================================================
# 5. Hermes Hub-and-Spoke AGENTS.md Template (<= 12,000 Chars Root Cap)
# =========================================================================

HERMES_HUB_AGENTS_MD_TEMPLATE = """# Repository Operational Constitution (AGENTS.md)

> Size Invariant: Keep root `AGENTS.md` under 12,000 characters and any root-to-subdomain chain under 30,000 characters (`python scripts/check`). Put deep module specifics in subdomain `AGENTS.md` files and route to them via the table below.

## 1. Sacred Architectural Invariants
- **Prompt Caching Prefix Stability**: Never mutate historical messages, dynamically swap tool schemas, or rebuild the system prompt mid-conversation.
- **Security Scan Before Context Injection**: All repo-level context files (`AGENTS.md`, `.cursorrules`, `.hermes.md`) must pass `_scan_context_content(..., user_authored=False)`.

## 2. Subdomain Routing Table (Hub-and-Spoke)
| When Working In... | Read This Subdomain Spec First |
| :--- | :--- |
| `agent/prompt_builder.py` or system prompts | `agent/AGENTS.md` |
| `tools/` or MCP integrations | `tools/AGENTS.md` |
| `gateway/` or multi-channel messaging | `gateway/AGENTS.md` |
| `tests/` or evaluation harnesses | `tests/AGENTS.md` |
"""
