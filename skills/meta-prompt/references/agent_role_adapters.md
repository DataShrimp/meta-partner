# Cross-Platform Agent Role Adapters & Compilation Blueprints (`agent_role_adapters.md`)

> **Phase-Gated Loading Rule**: Load this reference file ONLY when compiling, refactoring, or adapting an **Agent Role / Persona Definition** across target Agent tools (OpenClaw, Hermes Agent, Claude Code, OpenAI Codex, or Cursor/Copilot).

---

## 1. Universal Canonical Role Intermediate Representation (IR)

Before emitting tool-specific Markdown files, decompose any requested Agent Role into 5 orthogonal cognitive slots so persona, operational rules, and infrastructure never tangle into a "Ball of Mud":

1. **Slot A — Identity & Behavioral Spec (`Who to be`)**:
   - **Archetype & Voice**: Grounded peer/specialist perspective (no adjective trait lists like "smart, friendly, helpful").
   - **Sizing & Density Rule**: Concise answers for simple queries; full architectural depth for complex tasks (**Earned-Depth Escape Hatch**).
   - **Named Prohibitions & Anti-Sycophancy**: Ban filler openings (`"Great question!"`, `"Certainly!"`), ban unsolicited moralizing, and enforce epistemic honesty (`"Agree because the evidence/code supports it, not because the user said it"`).
2. **Slot B — Operational SOP & Verification Gates (`What to do`)**:
   - Step-by-step execution loop (Inspect -> Plan/Verify Assumptions -> Implement -> Run Verification Gate).
   - Explicit `Done When` acceptance criteria and `MUST` / `NEVER` boundaries.
3. **Slot C — Host Sandbox & Tool Contract (`Hard Boundaries`)**:
   - Tool allowlist (`tools`), tool denylist (`disallowedTools` / `tools.deny`), filesystem sandbox mode (`read-only`, `workspace-write`, `worktree`), and model tier (`opus` / `sonnet` / `haiku`).
4. **Slot D — Environment & Routing Map (`Where things are & When to delegate`)**:
   - Repository paths, build/test commands, Hub-and-Spoke submodule routing table, and positive/negative routing triggers (`Use PROACTIVELY when...` / `Do NOT use when...`).
5. **Slot E — Memory & Evolution Policy (`What to remember`)**:
   - Declarative facts only (`"User prefers X"` ✓, never imperative `"Always do X"` ✗); procedural workflows graduate to `Skills`, and validated recurring rules graduate to `AGENTS.md`.

---

## 2. Target Adapter 1: OpenClaw (7-File Cognitive Separation Suite + `openclaw.json`)

- **When to Use**: User specifies **OpenClaw** or requests a multi-file personal/project autonomous agent workspace.
- **Compilation Output Structure**:
  1. `IDENTITY.md` (3–5 lines: Name, Archetype, Emoji, Avatar path)
  2. `SOUL.md` (Slot A: Voice, Sizing Rule, Named Prohibitions, Anti-Sycophancy — `< 2,500 chars`)
  3. `AGENTS.md` (Slot B: Operational SOP, Sub-agent delegation policy, Safety redlines — `< 4,000 chars`)
  4. `USER.md` (Human collaborator profile, timezone, tech stack, delivery preferences — `< 1,200 chars`)
  5. `TOOLS.md` (Slot D: Local paths, service URLs, CLI conventions — NO permissions here)
  6. `MEMORY.md` (Slot E: Declarative learned patterns with weekly pruning & graduation rule — `< 2,500 chars`)
  7. `HEARTBEAT.md` (Periodic autonomous check-in checklist — `< 600 chars`)
  8. `openclaw.json` (Slot C: Hard enforcement — `promptMode: "full"` for main agent, `"minimal"` for sub-agents, `bootstrapMaxChars`, `sandbox.mode`, `tools.deny`)

---

## 3. Target Adapter 2: Hermes Agent (`SOUL.md` + Hub-and-Spoke `AGENTS.md`)

- **When to Use**: User specifies **Hermes Agent (`NousResearch/hermes-agent`)**.
- **Compilation Output Structure**:
  1. `<user-home>/.hermes/SOUL.md` (Injected as Slot #1 `# Identity`):
     - Strict 3-part Behavior Spec (Sizing Rule + Named Prohibitions + Earned-Depth Escape Hatch).
     - Compatible with `_scan_context_content(..., user_authored=True)`.
  2. `<repo-root>/AGENTS.md` (Capped at `<= 12,000 chars`; full root-to-subdomain chain `<= 30,000 chars`):
     - Sacred architectural invariants (including KV Cache prefix stability).
     - Model-family execution discipline blocks (`<tool_persistence>`, `<mandatory_tool_use>`, `<act_dont_ask>`).
     - **Hub-and-Spoke Routing Table** mapping subdirectories to local `<subdir>/AGENTS.md` files.
  3. Memory Governance Rule:
     - Enforce declarative facts in `MEMORY.md` (`<= 2,200 chars`) and `USER.md` (`<= 1,375 chars`); route all procedural workflows to `skill_manage`.

---

## 4. Target Adapter 3: Claude Code (`.claude/agents/<role>.md` & `CLAUDE.md`)

- **When to Use**: User specifies **Claude Code** or requests specialized Subagents (e.g., Code Reviewer, Security Auditor, Feature Implementer, Test Architect).
- **Compilation Output Structure**:
  ```yaml
  ---
  name: <kebab-case-role-name>
  description: >
    Use this agent PROACTIVELY when [explicit trigger conditions and file/task signals].
    Do NOT use when [near-miss exclusions handled by other agents].
  tools: <comma-separated minimal tool allowlist, e.g., Read, Grep, Glob, Bash>
  disallowedTools: <comma-separated blocked tools, e.g., Write, Edit for read-only roles>
  model: <opus | sonnet | haiku | inherit>
  permissionMode: <default | acceptEdits | plan | dontAsk>
  maxTurns: <10-30>
  isolation: <worktree (include for parallel code-mutating roles)>
  omitClaudeMd: <true for lightweight utility roles | false for core repo roles>
  effort: <low | medium | high | max>
  ---
  ```
  Followed by the Markdown body containing:
  1. **Role Mandate & Epistemic Stance** (Behavior spec, anti-sycophancy, read-only or mutation scope).
  2. **Deterministic Execution Protocol** (Exact `git diff` / inspection commands to run first).
  3. **Evaluation Matrix / Quality Gates** (Severity tiers `[CRITICAL / HIGH / MEDIUM / LOW]` or verification commands).
  4. **Signal-Only Handoff Contract** (Exact output structure returned to the parent agent, starting with `VERDICT: PASS | FAIL` and `file_path:line_number` citations).

---

## 5. Target Adapter 4: OpenAI Codex & Universal `AGENTS.md` Cascade

- **When to Use**: User specifies **OpenAI Codex**, cross-platform **AGENTS.md**, or a Monorepo multi-directory role setup.
- **Compilation Output Structure**:
  1. **Root `AGENTS.md`**: Exact build/lint/test commands, coding conventions, and global verification gates (kept compact so the full cascade stays well under `project_doc_max_bytes = 32 KiB`).
  2. **Subdirectory `AGENTS.override.md`**: Placed in high-risk subdirectories (e.g., `services/payments/AGENTS.override.md`, `infra/terraform/AGENTS.override.md`) to override general rules via directory proximity and recency bias.

---

## 6. Target Adapter 5: Cursor & GitHub Copilot (`.cursor/rules/` & `.github/agents/`)

- **When to Use**: User specifies **Cursor** or **GitHub Copilot Coding Agent**.
- **Compilation Output Structure**:
  - For Cursor (`.cursor/rules/<role-name>.mdc`): YAML frontmatter with `description`, `globs` (target file patterns), and `alwaysApply: false`, paired with concise domain rules and verification steps.
  - For GitHub Copilot (`.github/copilot-instructions.md` + `.github/agents/<role-name>.agent.md`): Repository-wide build/test truths in `copilot-instructions.md` and specialized persona + tool boundaries in `.github/agents/<role-name>.agent.md`.
