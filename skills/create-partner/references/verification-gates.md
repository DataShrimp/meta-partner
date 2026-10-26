# Verification Gates — Proving a Role Is Actually Mounted

Load when designing a gate, or when `--dump-config` is unavailable. The core rule: a role is
mounted when the loader composed it, not when a file exists.

## Gate ladder

| Level | Command | Proves | Cost | Fails when |
| :--- | :--- | :--- | :--- | :--- |
| L0 | `ls -l <profile>/node_modules/<pkg>` | Dependency resolved | free | Dangling link after a skipped install (P03) |
| L1 | parse `<profile>/package.json` | Bundle listed, patch declared | free | Manual edit omitted the bundle entry |
| L2 | parse each bundle's patch as a sequence | Patch shape valid (P08) | free | Mapping instead of array |
| L3 | `dsh --profile <name> --dump-config` | Full composition | needs profile write | `EPERM` outside sandbox (P06) |
| L4 | `loadProfileDirectory(...)` | Composition without writing | free, read-only | Patch references a missing file |
| L5 | boot with official launcher, grep log | Runtime mount, no import error | seconds, needs port | koffi signature (P07) |

`scripts/verify_mount.py` implements L0 through L4 and reports `unverifiable` whenever a
permission error prevents a level; it never reports success from a skipped level.

## Why L4 matters

`loadProfileDirectory(binName, profileDir, installAnchor)` reads the profile manifest, resolves
every `dsh.profile.bundles` entry to its package directory, requires each to declare
`dsh.bundle.patch`, parses each patch file, then parses the profile's own
`cordis.patch.yml`. It throws on the first structural defect and returns a composed object
otherwise. It writes nothing — that is why it works on a locked or read-only profile where
`--dump-config` cannot run.

Invoke it with the app's managed Node:

```bash
NODE=~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/node/bin/node
BOOT=~/.dsh/profiles/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js
"$NODE" --input-type=module -e "
const boot = await import('file://$BOOT');
const p = boot.loadProfileDirectory('dsh', '<profileDir>', '<installAnchor>');
console.log(JSON.stringify({ layers: p.layers.map(l => l.packageName) }));
"
```

## Distinguishing the three failure classes

Because `EPERM`, `declares no dsh.bundle`, and `must be a top-level YAML array` all surface as
one-line errors, classify before fixing:

1. **Permission** — `EPERM`, `operation not permitted`. The gate cannot run. Report
   `unverifiable`, drop to L4, or request scoped permission. Do not edit the bundle.
2. **Structure** — `declares no dsh.bundle`, `must be a top-level YAML array`, `failed to parse`.
   The bundle itself is malformed. Fix the artifact.
3. **Environment** — `code signature`, `not valid for use in process`, `pnpm not found`.
   The launcher or PATH is wrong. Fix the invocation, not the artifact.

A common wasted cycle is treating class 3 as class 2 and rewriting a correct bundle.

## Static artifact gate

Run the meta-prompt validator on every Markdown deliverable:

```bash
python3 /Users/ryan/Documents/projects/meta-partner/skills/meta-prompt/scripts/validate_artifact.py \
  --input <file> --mode skill
```

Score must be 100.0 before presentation. It checks budget ceilings, placeholder residue,
kebab-case name with a negative trigger boundary, and trait-list bloat.

## Evidence discipline

Report the verdict verbatim with the failing check id (P-number or level). Never summarize a
gate as "looks fine" — the whole point of the ladder is that each rung answers a different
question, and the highest rung actually reached is information the reader needs.
