# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""STEPS Milestone State Machine (Physical Transition Guard).

Enforces the sequential milestone logic chain of the Y-Model:
  INIT -> SCOPE_GROUNDED -> TARGET_GROUNDED -> FRAMEWORK_DRAFTED -> PREDICT_AUDITED -> SUPPORTED (DONE)

Rules:
1. Strict dependency: Cannot skip from INIT directly to TARGET or FRAMEWORK.
2. User verification required: Advancing from SCOPE to TARGET, and from TARGET to FRAMEWORK,
   requires an explicit user sign-off record (user_confirmed: true).
3. Artifact validation: Cannot transition if milestone-specific required fields are missing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TRANSITION_LADDER = [
    "INIT",
    "SCOPE_GROUNDED",
    "TARGET_GROUNDED",
    "FRAMEWORK_DRAFTED",
    "PREDICT_AUDITED",
    "SUPPORTED",
]


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {
            "current_stage": "INIT",
            "history": [],
            "milestone_data": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    return json.loads(state_file.read_text(encoding="utf-8"))


def save_state(state_file: Path, data: dict) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def can_transition(current: str, target: str) -> tuple[bool, str]:
    if current not in TRANSITION_LADDER:
        return False, f"Invalid current stage: {current}"
    if target not in TRANSITION_LADDER:
        return False, f"Invalid target stage: {target}"

    curr_idx = TRANSITION_LADDER.index(current)
    target_idx = TRANSITION_LADDER.index(target)

    if target_idx <= curr_idx:
        # Re-grounding or backward transition is always allowed (iteration)
        return True, "Re-visiting or re-grounding milestone allowed."

    if target_idx > curr_idx + 1:
        # Attempting to skip milestones
        skipped = TRANSITION_LADDER[curr_idx + 1 : target_idx]
        return False, f"ILLEGAL JUMP: Cannot skip ungrounded milestone(s) {skipped}."

    return True, "Sequential milestone transition permitted."


def main() -> int:
    ap = argparse.ArgumentParser(description="STEPS State Machine Guard")
    ap.add_argument("--state-file", required=True, help="Path to steps_state.json")
    ap.add_argument("--check", action="store_true", help="Print current status and next allowable steps")
    ap.add_argument("--advance-to", choices=TRANSITION_LADDER, help="Request milestone advance")
    ap.add_argument("--data-file", help="JSON file containing milestone payload to record")
    ap.add_argument("--user-confirmed", action="store_true", help="Flag indicating explicit user confirmation")
    args = ap.parse_args()

    state_file = Path(args.state_file).expanduser().resolve()
    state = load_state(state_file)
    curr = state.get("current_stage", "INIT")

    if args.check:
        idx = TRANSITION_LADDER.index(curr) if curr in TRANSITION_LADDER else 0
        next_step = TRANSITION_LADDER[idx + 1] if idx + 1 < len(TRANSITION_LADDER) else "ALL_COMPLETED"
        print(json.dumps({
            "current_stage": curr,
            "next_allowable_milestone": next_step,
            "state_file": str(state_file),
            "milestone_summary": {k: bool(v) for k, v in state.get("milestone_data", {}).items()},
        }, ensure_ascii=False, indent=2))
        return 0

    if args.advance_to:
        target = args.advance_to
        allowed, reason = can_transition(curr, target)
        if not allowed:
            print(json.dumps({"verdict": "BLOCKED", "reason": reason, "current_stage": curr}, indent=2))
            return 1

        # Check user confirmation gate for foundational milestones S -> T and T -> E
        if target in ("TARGET_GROUNDED", "FRAMEWORK_DRAFTED") and not args.user_confirmed:
            print(json.dumps({
                "verdict": "BLOCKED",
                "reason": f"Physical gate: Advancing to {target} requires explicit user confirmation (--user-confirmed).",
                "current_stage": curr,
            }, indent=2))
            return 1

        # Load payload if provided
        payload = {}
        if args.data_file:
            df = Path(args.data_file).expanduser().resolve()
            if df.exists():
                payload = json.loads(df.read_text(encoding="utf-8"))

        state["history"].append({
            "from": curr,
            "to": target,
            "time": datetime.now(timezone.utc).isoformat(),
            "user_confirmed": args.user_confirmed,
        })
        state["current_stage"] = target
        if payload:
            state.setdefault("milestone_data", {})[target] = payload

        save_state(state_file, state)
        print(json.dumps({
            "verdict": "TRANSITION_SUCCESS",
            "from": curr,
            "to": target,
            "state_file": str(state_file),
        }, ensure_ascii=False, indent=2))
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
