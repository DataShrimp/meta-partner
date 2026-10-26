#!/usr/bin/env bash
set -euo pipefail

# Install the create-partner skill into a DeepSeek Harness skill root.
# Read-only by design: preflight first, then one symlink, then verify.
#
#   --dry-run            print every action without touching the filesystem
#   --root <dsh|agents>  which user skill root (default: dsh, rank 400)
#   --dsh-home <dir>     override $DSH_HOME
#   --help               this text

SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SKILL_NAME="$(python3 - "$SKILL_DIR/SKILL.md" <<'PY'
import re, sys, pathlib
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
for line in m.group(1).splitlines():
    k, _, v = line.partition(":")
    if k.strip() == "name":
        print(v.strip()); break
PY
)"

DRY_RUN=0
ROOT_KIND="dsh"
DSH_HOME_DIR="${DSH_HOME:-$HOME/.dsh}"

usage() {
  sed -n '3,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --root) ROOT_KIND="$2"; shift 2 ;;
    --dsh-home) DSH_HOME_DIR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$ROOT_KIND" in
  dsh)    TARGET_ROOT="$DSH_HOME_DIR/skills" ;;
  agents) TARGET_ROOT="$HOME/.agents/skills" ;;
  *) echo "error: --root must be 'dsh' or 'agents'" >&2; exit 2 ;;
esac

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then echo "[dry-run] $*"; else "$@"; fi
}

echo "==> [1/3] preflight"
# Skill install only needs skill-root checks; pnpm and profile state matter for
# bundle mounts, not for a symlink into ~/.dsh/skills.
PREFLIGHT_ARGS=(--scope skill --skill-dir "$SKILL_DIR" --name "$SKILL_NAME")
if [[ "$DRY_RUN" -eq 0 ]]; then
  python3 "$SKILL_DIR/scripts/dsh_preflight.py" "${PREFLIGHT_ARGS[@]}" >/tmp/create-partner-preflight.json || {
    status=$?
    python3 - /tmp/create-partner-preflight.json <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"preflight verdict: {d['verdict']} {d['counts']}")
for c in d["checks"]:
    if c["status"] != "pass":
        print(f"  [{c['status']}] {c['id']}: {c['evidence']}")
PY
    if [[ "$status" -eq 1 ]]; then
      echo "error: preflight reported a hard failure; refusing to install" >&2
      exit 1
    fi
    echo "warning: preflight returned unverifiable (permissions); continuing" >&2
  }
else
  python3 "$SKILL_DIR/scripts/dsh_preflight.py" "${PREFLIGHT_ARGS[@]}" >/dev/null || true
fi

echo "==> [2/3] link $SKILL_NAME into $TARGET_ROOT (rank 400/500)"
run mkdir -p "$TARGET_ROOT"
if [[ -e "$TARGET_ROOT/$SKILL_NAME" && ! -L "$TARGET_ROOT/$SKILL_NAME" ]]; then
  echo "error: $TARGET_ROOT/$SKILL_NAME exists and is not a symlink; refusing to overwrite" >&2
  exit 1
fi
run ln -sfn "$SKILL_DIR" "$TARGET_ROOT/$SKILL_NAME"

echo "==> [3/3] verify"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[dry-run] would verify $TARGET_ROOT/$SKILL_NAME/SKILL.md"
  exit 0
fi
readlink "$TARGET_ROOT/$SKILL_NAME"
test -r "$TARGET_ROOT/$SKILL_NAME/SKILL.md" && echo "OK: SKILL.md readable through the link"
python3 "$SKILL_DIR/scripts/dsh_preflight.py" --scope skill --skill-dir "$TARGET_ROOT/$SKILL_NAME" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('post-install name check:', d['verdict'])"
echo "Done. The skill appears in the catalog on the next session."
