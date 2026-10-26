# MEMORY.md — Declarative Meta-Flywheel Registry & Architectural State

> Governance: declarative facts and decisions only (<= 2,500 chars); workflows live in `SKILL.md`/`AGENTS.md`.

## Collaborator & Interaction Decisions
- Method: **Y-Model STEPS** (Scope -> Target -> Element -> Predict -> Support).
- Core posture: **实事求是 · 解放思想 · 知行合一**; peer problem-solving without sycophancy.
- Progression: 4 methods for infinite progress (定性定量, 科学类比, 假设驱动, 提炼建模) backed by 4 support infrastructures.
- Node grounding: STEPS milestones strictly dependent; downstream requires upstream grounding.
- Protocol: Dual-Track Parallel (MVP Track 1 + 4-Axis Blind-Spot Radar Track 2) in every response.
- Runtime: DeepSeek Harness (`dsh`); canonical role at `…/MetaPrompt/meta-partner/`.
- Engine: `meta-prompt` compiler — Prompts (A), Skills (B), Roles (C), Evals (D).

## DeepSeek Harness (`dsh`) Architectural Facts
- `dsh` runs on Cordis; prompts, tools, skills, presets are plugins.
- Mount tiers: **preset** = per-session identity, **skill** = per-task capability, `AGENTS.md` = always-on broadcast, **bundle** = process-wide. A partner needs a preset.
- `dsh-agent-presets` scans `~/.dsh/.agent-presets/` (copy-only); registry mounts once per process.
- Composition YAML uses `!!js` tags; parsing needs a pass-through constructor for `tag:yaml.org,2002:js` (P17).
- `PromptSection` takes only `name / order / text / complete`; no `interpolate: false` exists. `renderPrompt()` throws on unregistered double-brace variables; injectable slots stay brace-free.
- `dsh-tool-skill` caps catalog descriptions at 500 chars.
- `desktop` is Electron-locked (`dsh plugin --profile desktop` fails); mounts use `packages/<pkg>` + `workspace:*` + bundles entry + `pnpm install --ignore-scripts`.
- Skill root ranks 100-600; lowest wins, duplicates shadow silently.

## Active Flywheel Asset Inventory
- **`FRAMEWORK.md`** (V1.2) — Causal cognitive model (core posture, 4 methods for infinite progress, 4 support infrastructures).
- **`meta-prompt`** — compiler, 100.0; both skill roots symlink to it.
- **`meta-partner`** — foundational co-architect, Y-Model native, anchor persona (drift-free, validated).
- **`create-partner`** (`~/.dsh/skills/create-partner`) — role factory, 100.0; tiers P/A/B/C, P01-P19, 14 evals, 16 triggers.
- **`asset-partner-v3`** — storage & AI data role; Dual-Engine (ADAPTE-D + Hierarchy), 4 infrastructures (fast_index_search 4.2ms, hypotheses ledger, research framework, causal model).
