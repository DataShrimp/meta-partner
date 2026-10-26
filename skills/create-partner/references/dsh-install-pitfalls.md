# DSH Install Pitfalls — P01 to P16

Every entry was observed in a real install session or read directly from the `dsh` runtime
source at `/Applications/DeepSeek Harness.app/Contents/Resources/app.asar/dsh/` and
`~/.dsh/profiles/node_modules/@deepseek-ai/`. When a check fails, identify the id and apply
exactly the stated remedy — several of these produce identical-looking errors from different
causes.

## Table of contents

1. [Profiles and isolation](#p01)
2. [Desktop profile lock](#p02)
3. [Desktop workspace package path](#p03)
4. [pnpm forwarding](#p04)
5. [Managed pnpm and shim](#p05)
6. [Sandbox EPERM](#p06)
7. [koffi signature failure](#p07)
8. [Bundle patch shape](#p08)
9. [Integrity LF normalization](#p09)
10. [Skill root ranks](#p10)
11. [Directory versus frontmatter name](#p11)
12. [Verification chain](#p12)
13. [Frontmatter key names](#p13)
14. [Catalog description cap](#p14)
15. [User invocation gesture](#p15)
16. [Managed distribution mode](#p16)
17. [js tags in composition YAML](#p17)
18. [Role directory is not an Agent](#p18)
19. [node -e argv and URI-encoded imports](#p19)

## P01
**Profiles are isolated.** Each profile is a separate plugin tree under
`$DSH_HOME/profiles/<name>`, composed at boot. A bundle installed into `web` is invisible to
`desktop`.
Remedy: before diagnosing, identify which profile serves the URL in question
(`lsof -nP -iTCP:<port> -sTCP:LISTEN`, then match the process to a profile directory).

## P02
**The `desktop` profile is walled off from the CLI.** `rejectElectronProfile` in
`@deepseek-ai/dsh/lib/bin.js` errors for both boot and `plugin` subcommands:
`profile "desktop" is managed exclusively by the Electron application`.
Remedy: mount into `desktop` only through P03's workspace-package path.

## P03
**The only supported desktop mount is a workspace package.** Four steps, all required:
`<profile>/packages/<pkg>/` as a real directory (no symlink inside it), the dependency
`"<pkg>": "workspace:*"` in `<profile>/package.json`, the package name appended to
`dsh.profile.bundles`, then `pnpm install --ignore-scripts` run in the profile directory.
Skipping the install leaves a dangling `node_modules` entry that resolves at compose time but
not at import time.

## P04
**`dsh plugin` forwards argv verbatim to pnpm and nothing else.** With no pnpm on `PATH` it
prints `pnpm not found on PATH` and returns `127`. It also rewrites bare relative path specs
(`.`, `../x`, `file:./x`) against the invoking directory, because pnpm itself runs with
`cwd` set to the profile.
Remedy: give it a working pnpm; do not pass `--force`, and do not try to run `pnpm add`
directly inside the profile — reconciliation of `dsh.profile.bundles` only happens when
`dsh plugin` is the entry point.

## P05
**The app ships its own pnpm; `/tmp` shims do not survive.** Use
`…/runtime/primary-runtime/dependencies/pnpm/bin/pnpm.mjs` executed by the managed Node.
A shim written under `/tmp` works until reboot or cleanup. Any shim must be created in a
durable location or recreated by the installer script.

## P06
**Sandbox denial looks like a broken mount.** With workspace-only write access:
`pnpm store status` in a profile outside the workspace fails with
`EPERM: operation not permitted, symlink …`, and `--dump-config` fails with
`EPERM: operation not permitted, open '<profile>/cordis.yml'` because it rewrites the profile
file before printing. Neither indicates a bad bundle.
Remedy: classify as `unverifiable` (permission), fall back to the read-only
`loadProfileDirectory` gate, or ask for a one-shot permission scoped to that profile.

## P07
**Never boot from an npx cache.** `@koromix/koffi-darwin-arm64` is adhoc-signed; macOS
refuses to map it into a differently-signed host and the boot dies with
`plugin tree failed to load … code signature … not valid for use in process`. The error is
emitted before any plugin of yours loads, which makes it look unrelated.
Remedy: strip `ELECTRON_RUN_AS_NODE` overrides and use
`/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh`.

## P08
**Bundle patch shape and declaration.** Two independent requirements:
the patch file must be a **top-level YAML sequence** (a mapping produces
`must be a top-level YAML array of loader patch entries`), and the package's own
`package.json` must declare `dsh.bundle.patch` (otherwise `declares no dsh.bundle`).
A bundle-mounted package also needs `dsh.client` only when it ships a browser half.

## P09
**Integrity mismatches on binaries are usually line-ending normalization.** A recorded
digest that normalizes CRLF to LF will not match a raw binary. Compare bytes against the
upstream file at the pinned commit before concluding tampering; in the observed case all
77 text files matched and the single "mismatch" was a 298,606-byte wasm identical to upstream.

## P10
**Skill roots shadow by rank, lowest wins.** `100` `<project>/.dsh/skills`, `200`
`<project>/.agents/skills`, `300` custom, `400` `~/.dsh/skills`, `500` `~/.agents/skills`,
`600` bundled. A same-name directory in a higher number silently loses; only a warning is
logged. A stale physical copy in `~/.agents/skills` therefore never surfaces until the
rank-400 symlink breaks. Check all roots before creating a name.

## P11
**Directory name ≠ frontmatter `name`,** and only the frontmatter name is authoritative for
catalog identity and `/name` invocation. However `resourceBase` is the directory holding
`SKILL.md`, so `scripts/` and `references/` resolve relative to it. Renaming the directory
does not rename the skill; renaming the frontmatter does not move the resources.

## P12
**Use the right gate for the situation.** Writable profile: `dsh --profile <name> --dump-config`
and grep for the expected bundle id. Locked or unwritable profile:
`loadProfileDirectory('dsh', profileDir, installAnchor)` from
`@deepseek-ai/dsh-app-boot`, which parses every layer without writing anything. Live check:
boot with the official launcher, read the log for `listen`/`ready`, then kill.
Composition proof requires the loader; a symlink proves nothing.

## P13
**Frontmatter invocation keys are kebab-case and legacy spellings throw.** `disable-model-invocation`
and `user-invocable` are canonical; `disableModelInvocation`, `modelInvocable`, and
`userInvocable` cause the file to be rejected with `unsupported; use "<canonical>"`.
The file is then ignored, not errored at boot, so a skill can silently vanish.

## P14
**The catalog truncates descriptions at 500 characters.** `dsh-tool-skill` default
`catalogDescriptionMaxLength` is 500. Keep compiled descriptions under 450 so the negative
boundary (`DO NOT TRIGGER when …`) is never cut off.

## P15
**`/name` only reaches user-invocable skills.** A skill with
`disable-model-invocation: true` never appears in the model catalog and is reachable only by
the user typing `/name`. Use it for destructive or operator-only procedures.

## P16
**Do not double-write a workspace-owned plugin.** If bytes are owned by a git checkout or a
workspace directory, a plugin's built-in self-updater must be disabled (the observed plugin
exposes `distribution: managed` for this). Two writers on one directory corrupt each other;
pick git as the owner and upgrade with `git fetch` + `git checkout`.

## P17
**Composition YAML carries `!!js` runtime expressions.** Shipped preset and profile files
use rows like `disabled: !!js process.platform === 'win32'`. A plain `yaml.safe_load`
throws `could not determine a constructor for the tag 'tag:yaml.org,2002:js'` on the first
such row. Remedy: register a pass-through constructor before parsing any `agent.cordis.yml`
or `cordis.patch.yml`; this bit both `verify_mount.py` and `scaffold_preset.py` in the same
week because each independently discovered it.

## P18
**A role directory is not an Agent.** Four mount tiers exist — preset (identity, chosen per
session), skill (capability, loaded per task), `AGENTS.md` instruction chain (always-on
contract, broadcast to every session), profile bundle (process-wide layer). They are not
interchangeable, and none implies another. The observed failure: a partner's role files were
mounted as an `AGENTS.md` bootstrap block, which broadcast its contract into every session
of every agent (including unrelated coding sessions) while the partner never appeared in
the agent picker — the one place the user expected it. Remedy: a partner gets a user-root
preset (`scaffold_preset.py`); the instruction chain is reserved for cross-agent contracts
only. The diagnostic question: "should the user pick this identity when starting a session?"
If yes, it needs a preset, whatever else it also has.

## P19
**Two silent traps when calling runtime packages from `node -e`.** First: `-e`
has no script placeholder, so user arguments start at `argv[1]` — reading
`argv[2]` imports `undefined` and dies with `ERR_MODULE_NOT_FOUND: Cannot find
package 'undefined'`, which reads like a broken dependency. Second: a module
specifier percent-encoded by `Path.as_uri()` turns `@deepseek-ai` into
`%40deepseek-ai`, breaking Node's relative import resolution inside the
package. Both surfaced while delegating the preset copy to the official
`copyComposition()` API; the fix is a raw `file://<path>` string and
`argv[1]`-based indexing. Rule: when an import failure names `undefined` or a
percent sign, suspect the invocation, never the package.
