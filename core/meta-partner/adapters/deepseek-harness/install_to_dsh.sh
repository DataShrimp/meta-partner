#!/usr/bin/env bash
set -euo pipefail

# Non-interactive installer for Meta-Partner + Meta-Prompt into DeepSeek Harness (dsh)
# Supports: --dry-run, --help, --project-dir <dir>, --dsh-home <dir>

DRY_RUN=0
PROJECT_DIR=""
DEFAULT_USER_HOME="/Users/ryan"
if [[ "${HOME:-}" != *".gemini/users"* && -n "${HOME:-}" ]]; then
  DEFAULT_USER_HOME="$HOME"
fi
DSH_HOME_DIR="${DSH_HOME:-$DEFAULT_USER_HOME/.dsh}"
PARTNER_ROOT="/Users/ryan/Documents/projects/meta-partner/core/meta-partner"
META_PROMPT_ROOT="/Users/ryan/Documents/projects/meta-partner/skills/meta-prompt"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--dry-run] [--project-dir <path>] [--dsh-home <path>] [--help]

Installs Meta-Partner and Meta-Prompt into DeepSeek Harness (dsh) via three layers:
  1. Symlinks 'meta-partner' and 'meta-prompt' into \$DSH_HOME/skills/ (Rank 400 User DSH Skill Root)
  2. Optionally symlinks into <project-dir>/.dsh/skills/ (Rank 100 Project DSH Skill Root)
  3. Appends the non-destructive Meta-Partner bootstrap pointer to \$DSH_HOME/AGENTS.md
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --project-dir)
      PROJECT_DIR="$2"
      shift 2
      ;;
    --dsh-home)
      DSH_HOME_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

run_cmd() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[DRY-RUN] $*"
  else
    "$@"
  fi
}

echo "==> [1/3] Linking skills into User DSH Skill Root ($DSH_HOME_DIR/skills)..."
run_cmd mkdir -p "$DSH_HOME_DIR/skills"
run_cmd ln -sfn "$PARTNER_ROOT/adapters/deepseek-harness" "$DSH_HOME_DIR/skills/meta-partner"
run_cmd ln -sfn "$META_PROMPT_ROOT" "$DSH_HOME_DIR/skills/meta-prompt"

if [[ -n "$PROJECT_DIR" ]]; then
  echo "==> [2/3] Linking skills into Project DSH Skill Root ($PROJECT_DIR/.dsh/skills)..."
  run_cmd mkdir -p "$PROJECT_DIR/.dsh/skills"
  run_cmd ln -sfn "$PARTNER_ROOT/adapters/deepseek-harness" "$PROJECT_DIR/.dsh/skills/meta-partner"
  run_cmd ln -sfn "$META_PROMPT_ROOT" "$PROJECT_DIR/.dsh/skills/meta-prompt"
else
  echo "==> [2/3] Skipping project-scoped link (pass --project-dir <repo> to enable Rank 100 project override)."
fi

GLOBAL_AGENTS_MD="$DSH_HOME_DIR/AGENTS.md"
MARKER="<!-- META-PARTNER-BOOTSTRAP -->"

echo "==> [3/3] Ensuring global instruction chain pointer in $GLOBAL_AGENTS_MD..."
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DRY-RUN] Would ensure $MARKER block exists in $GLOBAL_AGENTS_MD"
else
  touch "$GLOBAL_AGENTS_MD"
  if ! grep -q "$MARKER" "$GLOBAL_AGENTS_MD"; then
    cat >> "$GLOBAL_AGENTS_MD" <<EOF

$MARKER
## Meta-Partner & AI Flywheel Operating Contract
- Before designing or modifying any AI workflow, Agent Role, or Skill, read:
  1. \`/Users/ryan/Documents/projects/meta-partner/core/meta-partner/SOUL.md\`
  2. \`/Users/ryan/Documents/projects/meta-partner/core/meta-partner/AGENTS.md\`
  3. \`/Users/ryan/Documents/projects/meta-partner/core/meta-partner/MEMORY.md\`
- Always operate in **Dual-Track Parallel Mode**: deliver a runnable Minimum Viable Prototype (Track 1) paired with a 4-Axis Blind-Spot Warning Radar (Track 2), and invoke the \`meta-prompt\` skill for compilation and \`validate_artifact.py\` for static verification.
EOF
    echo "Added Meta-Partner bootstrap pointer to $GLOBAL_AGENTS_MD."
  else
    echo "Meta-Partner bootstrap pointer already present in $GLOBAL_AGENTS_MD."
  fi
fi

echo "==> Done! Meta-Partner is ready for DeepSeek Harness."
