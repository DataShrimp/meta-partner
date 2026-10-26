---
name: create-partner
description: Compile a DeepSeek Harness Agent Role (5-slot SOUL/AGENTS/TOOLS/MEMORY/IDENTITY) or persona preset and mount it into a dsh profile as a valid bundle. Covers preflight, patch-shape and dsh.bundle checks, and loadProfileDirectory gates. Trigger when creating, installing, repairing, or verifying a DSH agent role or role bundle. DO NOT TRIGGER when installing a third-party plugin, editing app code, or authoring a plain SKILL.md (use skill-creator).
user-invocable: true
---

# create-partner — Compile an Agent Role and Mount It into DeepSeek Harness

A role is not a skill. A skill is loaded on demand through the `skill` tool; a role is
long-lived identity that must be injected into the system prompt and bound to a sandbox
contract. `dsh` has **three mutually exclusive mount tiers**, and choosing the wrong one is
the single most common failure. Diagnose the tier before writing any file.

## Gotchas

These are verified against `dsh` source and a real install session. Each has a reference id
used by `references/dsh-install-pitfalls.md`; cite the id when reporting a failure.

1. **P02 — The `desktop` profile is locked.** `dsh plugin --profile desktop …` exits with
   `profile "desktop" is managed exclusively by the Electron application`
   (`@deepseek-ai/dsh/lib/bin.js`, `rejectElectronProfile`). Desktop roles mount only via a
   workspace package plus a manual `dsh.profile.bundles` entry.
2. **P01 — Profiles are isolated.** A role mounted into `web` never appears in the `desktop`
   GUI. Confirm which profile actually serves the URL the user is looking at before debugging
   anything else.
3. **P08 — A bundle patch is a top-level YAML array.** A file starting with `plugins:` is a
   mapping and fails with `must be a top-level YAML array of loader patch entries`. The
   package must also declare `dsh.bundle.patch` in its own `package.json`; otherwise the
   loader throws `declares no dsh.bundle`.
4. **P04/P05 — `dsh plugin` is a bare pnpm forwarder.** If pnpm is not on `PATH` the command
   exits `127`. The app ships its own pnpm under
   `…/runtime/primary-runtime/dependencies/pnpm/bin/pnpm.mjs`; create a shim on `PATH` rather
   than installing pnpm globally.
5. **P06 — Sandbox denies writes outside the workspace.** `--dump-config` and
   `pnpm store status` both write (`cordis.yml`, store project links) and fail with `EPERM`
   when the profile directory is outside the sandbox. That is a permission failure, not a
   broken mount — report it as such instead of "mount failed".
6. **P07 — Boot from the app launcher, never from an npx cache.** A cached `dsh` boot dies on
   macOS ad-hoc code-signature validation of `koffi.node`. Use
   `/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh`.
7. **P10 — Skill roots shadow silently.** Ranks are 100 project-dsh, 200 project-agents,
   300 custom, 400 user-dsh (`~/.dsh/skills`), 500 user-agents (`~/.agents/skills`), 600
   bundled. The **lowest rank wins**; a same-name skill in a higher-rank root disappears with
   only a warning. Always check for an occupied name in all roots first.
8. **Roles must not carry double-brace variables.** `renderPrompt()` interpolates section
   text strictly and throws on any unregistered variable. There is **no** `interpolate: false`
   option on `systemPrompt.section()` — the property is ignored. Keep the invariant instead:
   role slot files contain no double-brace placeholders.
9. **P11 — Directory name and frontmatter `name` are independent,** but the loaded skill's
   `resourceBase` is the directory containing `SKILL.md`. Any `scripts/` or `references/`
   must sit beside it or the loader will not find them.
10. **P17 — Composition YAML uses `!!js` runtime expressions.** Shipped preset files carry
   rows like `disabled: !!js process.platform === 'win32'`. A plain `yaml.safe_load` throws
   `could not determine a constructor for the tag`; register a pass-through constructor for
   `tag:yaml.org,2002:js` before parsing any `agent.cordis.yml`.
11. **A role directory is not an Agent.** Four mount tiers exist and they are not
   interchangeable: identity is chosen per session (**preset**), capability is loaded per
   task (**skill**), always-on contract goes in the instruction chain (**AGENTS.md**), and
   process-wide layers are **profile bundles**. Mounting role files as an `AGENTS.md`
   bootstrap block broadcasts them into **every** session of **every** agent — that is a
   contract channel, not an identity channel. A partner that should appear in the agent
   picker needs a preset, and only a preset.

## Workflow

### Step 1 — Ground the decision

Read the collaborator's `MEMORY.md` and the target role directory before proposing anything.
Decide in one pass — the decision is **which of the four tiers the artifact is**, not where
its files happen to live:

- **Tier P — Agent preset (identity, chosen per session).** The tier for a partner that
  must appear in the GUI agent picker as its own AI. A user-root preset under
  `~/.dsh/.agent-presets/<id>/`: composition copied from shipped `standard`, persona prefix
  rewritten as a role-specific anchor. No profile edits, no patch files. Sessions pick it
  explicitly; switching requires an empty session.
- **Tier A — Role files only (identity via pull pointer).** Role files symlinked into
  `~/.dsh/skills/<name>`; the model reaches them through an `AGENTS.md` pointer or persona
  prefix. Cheapest, but the identity is never session-scoped and **never appears in the
  picker**. Suitable for supporting material, not for a partner.
- **Tier B — Custom profile (process-wide bundle).** Role ships as a bundle installed with
  `dsh plugin --profile <name> add <path-or-spec>`. Needs a pnpm shim and a writable profile.
- **Tier C — Desktop profile (process-wide bundle).** Only path: a real directory under
  `<profile>/packages/<pkg>`, a `workspace:*` dependency, the package name appended to
  `dsh.profile.bundles`, then `pnpm install --ignore-scripts` in the profile. No symlinks in
  the package tree; the desktop gate rejects them.

Default to **Tier P for anything the user calls a partner, agent, or role**. The tell-tale
question: "should the user pick this identity when starting a session?" If yes, it is Tier P.

Never use the `~/.dsh/AGENTS.md` instruction chain to mount a role's identity: that channel
is unconditional, broadcasts into every session of every agent, and cannot be turned off per
session. It is reserved for cross-agent operating contracts.

State the chosen tier, its cost, and what it does **not** give the user (that is Track 2).

### Step 2 — Run preflight before touching the filesystem

```bash
python3 scripts/dsh_preflight.py --scope skill --skill-dir . --name <skill-name>
python3 scripts/dsh_preflight.py --scope mount --profile <name> --role-dir <role-dir>
```

`--scope skill` checks only skill-root facts (name validity, description cap, shadowing
across the six roots). `--scope mount` checks the profile and, when `--role-dir` is given,
the persona-drift comparison. The split exists because a Tier A install is one symlink and
must not fail on bundle-only requirements such as pnpm availability.

The mount scope reports: resolved app launcher, managed pnpm path, profile existence and
lock state, sandbox writability, bundle patch shape and `dsh.bundle` declaration, brace
violations in injectable slots, and **persona drift** — whether the profile's persona prefix
still reproduces the clauses `SOUL.md` declares. Fix every `fail` before continuing; treat
each `warn` as a line item to surface to the user.

Persona drift deserves its own note: the prefix is a hand-maintained partial copy of
`SOUL.md`, so it can silently lose a clause while still looking authoritative. Measure it,
never eyeball it:

```bash
python3 scripts/check_persona_drift.py --profile <name> --role-dir <role-dir> [--preset-id <id>]
```

`--preset-id` matters whenever the profile patch inserts more than one preset: the
checker audits that preset's own persona block. Without it, the first `prefix:` in
the file is audited — which may belong to another role and will report a
cross-role failure that is real for the wrong block.

A persona prefix has exactly two valid shapes, and the checker enforces which one is in
force by looking for the marker phrase `anchor, not a summary`:

| Shape | What it asserts | When it passes |
| :--- | :--- | :--- |
| **Summary** (default) | The prefix reproduces every clause `SOUL.md` declares. | No source clause is missing from the prefix. |
| **Anchor** (marker present) | The prefix deliberately duplicates nothing and points at the role files. | Every `.md` it names exists, it names at least `SOUL.md`/`AGENTS.md`/`MEMORY.md`, it stays under 900 characters, and the `~/.dsh/AGENTS.md` pull pointer is installed. |

Anchor mode is the structurally safer choice: a summary drifts every time the source
changes, while an anchor cannot drift because it contains nothing to drift. Its cost is that
it depends on the pull pointer being present — without that pointer the model never learns
to read the files at all, which is why the checker verifies the pointer rather than trusting
it.

Prefer anchor mode on the first design pass. Reach for summary mode only when the host has
no pull pointer mechanism, or when the first-turn behavior must be sharp before any tool
call happens.

### Step 3 — Compile the role slots via Y-Model STEPS

Every role created by this skill must have real substance and operational soul, strictly
structured across the 5 STEPS milestones (Scope -> Target -> Element -> Predict -> Support).
Adhere to the core stance: **实事求是 · 解放思想 · 知行合一** (anti-sycophantic peer collaboration).

Milestones must be grounded sequentially (节点扎实): never draft operational workflows before
the problem Scope is isolated and Target metrics are falsifiable.

A role is five orthogonal slots plus a host adapter:

| Slot | File | Contract & Y-Model Alignment |
| :--- | :--- | :--- |
| Identity | `IDENTITY.md` | Name, archetype, primary loop — maps to Scope & Core Focus |
| Who to be | `SOUL.md` | Epistemic stance (实事求是/知行合一), sizing rule, prohibitions, depth escape hatch |
| What to do | `AGENTS.md` | Sequential STEPS milestone workflow, gotchas first, falsifiable handoff contract |
| Environment | `TOOLS.md` | Real absolute paths, CLI invocations, discovery roots |
| Memory | `MEMORY.md` | Declarative facts only (<= 2,500 chars); no imperative sentences |

Behavior must be compiled as rules, not adjectives: a list of personality words does not
shift the output distribution, while a sizing rule plus a named prohibition does. In addition,
the role must embody the **4-fork progression posture (做事的姿势)**: Facts (实事求是),
Theory (解放思想/科学类比), Hypotheses (假设驱动), and Causal Modeling (提炼建模 1.0).
Always specify concrete Support mechanisms (scripts, review habits, memory gates) so the
role is capable of true 知行合一 rather than suffering support amnesia.

Keep `SOUL.md` free of per-turn timestamps so the prompt prefix stays cache-stable. Load
`references/role-5-slot-spec.md` only when compiling or refactoring role files; skip it when
mounting an existing role.

### Step 4 — Mount

Tier P (partners — the default for roles):

```bash
python3 scripts/scaffold_preset.py --id <partner-id> --role-dir <role-dir> \
  --name "<display name>" --description "<one line>"
```

Delegates the copy to the platform: the shipped `@deepseek-ai/dsh-agent-presets`
`copyComposition()` API performs the whole-directory copy (id validation,
writable-root resolution, rollback on failure, metadata rendering — all owned
by the runtime and upgrade-proof). This script adds only what the platform
cannot know: a generated role-specific anchor persona (never a copy of another
preset's anchor — a copied anchor sends this preset's sessions to another
role's files), display metadata, and the drift checker as its own gate — a
preset whose generated anchor fails is deleted, not delivered. Re-verify any
time with `--verify-only`.

Two integration facts, learned by breaking both: the module specifier must be
a raw `file://<path>` string (percent-encoding the `@` in `@deepseek-ai` breaks
Node's relative import resolution inside the package), and under `node -e`
user arguments start at `argv[1]`, not `argv[2]` — there is no script
placeholder. An `import(undefined)` failure is the signature of the second.

Tier A:

```bash
ln -sfn <role-adapters-dir> "$DSH_HOME/skills/<name>"
```

Tier B:

```bash
export PATH=<shim-dir>:$PATH                    # shim execs the managed pnpm.mjs
dsh plugin --profile <name> add <absolute-path-or-git-spec>
```

Tier C: write `<profile>/packages/<pkg>`, then in the profile add the dependency and the
bundle entry, then `pnpm install --ignore-scripts`. Never run `dsh plugin` against `desktop`.

### Step 5 — Verify with a deterministic gate

```bash
python3 scripts/verify_mount.py --profile <name> --expect <pkg-or-skill-name> --json   # Tiers B/C
python3 scripts/scaffold_preset.py --id <id> --role-dir <role-dir> \
  --name <n> --description <d> --verify-only                                          # Tier P
```

It resolves the profile manifest, checks each bundle declares `dsh.bundle.patch`, asserts the
patch file parses as a top-level sequence, confirms the expected entry is present, and — when
a Node runtime is available — calls `loadProfileDirectory` to prove the layers compose. For
Tier P, `scaffold_preset.py --verify-only` re-runs the anchor gate. Treat an `unverifiable`
verdict caused by a sandbox `EPERM` as inconclusive, never as success.

One limit no script can lift: the preset registry mounts **once per process**. A preset
created after the app started is invisible until restart, and no static check can prove the
picker will list it — say so instead of implying verification is complete.

### Step 6 — Record and compound

Append declarative facts to `MEMORY.md`: which tier now carries which role, the preset or
profile path, and the launcher path. New pitfalls get a fresh id in
`references/dsh-install-pitfalls.md` and a matching line in `evals/evals.json`; do not leave
them in chat history only.

## Output contract

Report in this order:

1. **Tier decision** — one line: tier, target (profile or user preset root), and the reason
   the other tiers are wrong.
2. **Preflight table** — only `fail` and `warn` rows, each with its check id.
3. **Files written or changed** — absolute paths.
4. **Verification** — the gate verdict verbatim, plus the static validator score.
5. **What is still unverified** — name each check that could not run and why; for Tier P,
   the restart-then-picker step belongs here.

Never report a mount as successful on the strength of a symlink existing. Existence is not
composition; only the loader proves composition.

## References

- `references/dsh-install-pitfalls.md` — Load when a check fails or an unfamiliar error
  appears. P01-P16 with source-level evidence and the exact remedy for each.
- `references/role-5-slot-spec.md` — Load when authoring or refactoring role slot files.
- `references/verification-gates.md` — Load when designing a new gate or when
  `--dump-config` is unavailable.
- `scripts/dsh_preflight.py`, `scripts/verify_mount.py`, `scripts/check_persona_drift.py`,
  `scripts/scaffold_preset.py` — deterministic; never re-derive their output by reading
  files by hand.
