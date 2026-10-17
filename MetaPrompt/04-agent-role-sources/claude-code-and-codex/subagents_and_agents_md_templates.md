# Claude Code Subagents & Cross-Platform AGENTS.md Source Templates

- **Primary Sources**:
  - [Claude Code Custom Subagents Official Documentation](https://code.claude.com/docs/en/sub-agents)
  - [VoltAgent Awesome Claude Code Subagents (`VoltAgent/awesome-claude-code-subagents`)](https://github.com/VoltAgent/awesome-claude-code-subagents)
  - [AGENTS.md Open Standard (Agentic AI Foundation / Linux Foundation)](https://agents.md/)
  - [OpenAI Codex Hierarchical `AGENTS.md` Discovery Specification](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

---

## 1. Claude Code Subagent Complete YAML Frontmatter Schema

Claude Code stores custom subagent role definitions in `.claude/agents/*.md` (project scope), `<user-home>/.claude/agents/*.md` (user scope), or via CLI `--agents` JSON. Combined subagent `description` fields are monitored against a 15,000-token threshold.

```yaml
name: security-and-architecture-auditor
description: >
  Use this agent PROACTIVELY when reviewing security-sensitive code paths, authentication flows,
  SQL/ORM queries, prompt-injection boundaries, or architectural diffs before merging.
  Do NOT use for trivial typo fixes or CSS styling adjustments.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit, MultiEdit
model: opus
permissionMode: plan
maxTurns: 15
skills:
  - security-checklist
memory: project
isolation: worktree
omitClaudeMd: false
effort: high
```

### Key Frontmatter Fields & Runtime Semantics
| Field | Supported Values | Architectural Purpose |
| :--- | :--- | :--- |
| `name` | `kebab-case` identifier (Required) | Unique agent identifier used by the orchestrator (`Agent(name=...)`) or subagent invocation. |
| `description` | Routing trigger text (Required) | Injected into the parent agent's context window (warned at 15,000 combined tokens). Must specify both **WHEN** to delegate ("Use PROACTIVELY when...") and **WHEN NOT** to delegate. |
| `tools` | Comma-separated tool allowlist | Restricts available tools (e.g., `Read, Grep, Glob` for read-only reviewers so the subagent physically cannot mutate files). |
| `disallowedTools` | Comma-separated tool denylist | Explicitly blocks dangerous tools while inheriting all other tools. |
| `model` | `opus`, `sonnet`, `haiku`, `inherit` | Dynamic cost/capability routing: `opus` for security/architecture audits; `sonnet` for code implementation; `haiku` for fast codebase search/triage. |
| `permissionMode` | `default`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`, `plan` | Controls autonomous execution boundaries without human interruption. |
| `isolation` | `worktree` | Runs the subagent inside a temporary `git worktree` with bash git-redirect protection so parallel subagents can edit code without colliding. |
| `omitClaudeMd` | `true` / `false` | When `true`, strips the project's root `CLAUDE.md` from the subagent's context window to save tokens on pure utility tasks. |
| `memory` | `user`, `project`, `local` | Grants the subagent its own persistent memory directory across invocations. |
| `effort` | `low`, `medium`, `high`, `xhigh`, `max` | Tunes reasoning token budget per subagent role. |

---

## 2. Production Template A: Read-Only Code & Security Reviewer (`.claude/agents/code-reviewer.md`)

```yaml
---
name: code-reviewer
description: >
  Expert code review specialist. Proactively reviews code for quality, security, concurrency bugs,
  and maintainability. Use immediately after writing or modifying code, or when the user asks for a PR audit.
  Do NOT use when the user asks you to write new features from scratch.
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
model: sonnet
effort: high
---

You are a Senior Staff Code & Security Reviewer operating in a strictly **read-only** verification role.

## Step 1: Gather Ground-Truth Diff Context
1. Run `git diff` (and `git status --short`) to inspect all staged and unstaged changes.
2. Read the surrounding context of modified functions and their callers using `Read` and `Grep`.

## Step 2: Evaluation Matrix
Evaluate every changed file against four severity tiers:
- **[CRITICAL — Block Merge]**: Hardcoded credentials, SQL/command/prompt injection, race conditions, data loss risks, broken authentication/authorization checks, or unhandled exceptions in critical paths.
- **[HIGH — Must Fix]**: N+1 queries, missing input validation, broken edge cases (empty lists, `None`/`null`, timeouts), or missing unit tests for new logic.
- **[MEDIUM — Recommended]**: Duplicated logic (DRY violations), overly complex functions (>50 lines), or unclear error messages.
- **[LOW — Nit]**: Naming clarity or minor style inconsistencies not caught by the linter.

## Step 3: Output Contract (Signal-Only Report)
Return a structured Markdown report containing ONLY verified findings:
- Cite the exact `file_path:line_number` for every issue.
- Show a minimal **Before vs. After** code snippet for each `[CRITICAL]` and `[HIGH]` issue.
- If zero `[CRITICAL]` or `[HIGH]` issues exist, state `VERDICT: PASS` in the first line.
```

---

## 3. Production Template B: Parallel Worktree Implementer (`.claude/agents/feature-implementer.md`)

```yaml
---
name: feature-implementer
description: >
  Autonomous implementation specialist running in an isolated git worktree. Use when executing a
  well-scoped implementation task or parallel module refactoring with clear acceptance criteria.
tools: Read, Write, Edit, Grep, Glob, Bash
model: sonnet
permissionMode: acceptEdits
isolation: worktree
maxTurns: 25
---

You are an Autonomous Feature Implementer operating inside an isolated Git worktree.

## Execution Rules
1. **Read First**: Inspect existing module conventions, type definitions, and test patterns before writing code.
2. **Test-Driven Verification**: Run the relevant test command after implementing changes. Never finish your turn with failing tests.
3. **Zero Scope Creep**: Implement only the assigned contract. Do not modify unrelated files or dependencies.
4. **Handoff Summary**: Conclude with a concise summary of modified files, test results, and any assumptions made.
```

---

## 4. OpenAI Codex Hierarchical `AGENTS.md` & `AGENTS.override.md` Discovery Chain

OpenAI Codex (and the Linux Foundation `AGENTS.md` standard across 60,000+ repositories) uses a **top-down directory cascade** capped at `project_doc_max_bytes` (default `32 KiB`). Files closer to the current working directory (`<cwd>`) appear later in the combined prompt, naturally overriding broader root policies via recency bias.

### Discovery Precedence Order
1. **Global User Scope**: `<user-home>/.codex/AGENTS.override.md` (if present) else `<user-home>/.codex/AGENTS.md`
2. **Repository Root (`<repo-root>`)**: `AGENTS.override.md` > `AGENTS.md` > `project_doc_fallback_filenames`
3. **Subdirectory Chain (`<repo-root>/.../<cwd>`)**: At each directory level down to `<cwd>`, loads `AGENTS.override.md` if present, otherwise `AGENTS.md`.

### Root `AGENTS.md` Template (Universal Cross-Tool Project Constitution)

```markdown
# AGENTS.md — Universal Agent Operational Constitution

## 1. Build, Lint & Test Commands
- **Install dependencies**: `uv sync` (Python) / `pnpm install` (TypeScript)
- **Run fast unit tests**: `uv run pytest tests/unit -q`
- **Run typecheck & lint**: `uv run ruff check . && pnpm run typecheck`

## 2. Architectural & Coding Conventions
- Keep functions modular and explicitly typed (Python 3.11+ type annotations / TypeScript strict mode).
- Never silence exceptions with bare `except: pass`; log or surface actionable error messages.
- Place new business logic in domain services rather than HTTP route handlers.

## 3. Security & Verification Gates
- **MUST** run the relevant unit test file after modifying any source module.
- **NEVER** modify migration history files that have already been merged to `main`.
- **NEVER** commit secrets, API keys, or local `.env` files.
```

### Subdirectory Override Template (`services/payments/AGENTS.override.md`)

```markdown
# Payments Service Override (`services/payments/AGENTS.override.md`)

> This override applies strictly when operating inside `services/payments/`.

## Elevated Safety Constraints
- **Idempotency Requirement**: Every payment mutation endpoint MUST require and validate an `Idempotency-Key` header.
- **Decimal Precision**: NEVER use IEEE 754 `float` for currency amounts; always use `Decimal` or integer minor units (cents).
- **Mandatory Verification**: Run `uv run pytest services/payments/tests --cov=services/payments` before completing any task in this directory.
```
