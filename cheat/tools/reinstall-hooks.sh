#!/usr/bin/env bash
# Rewrite a content project's .cheat-hooks/ scripts from this skill's cheat/hooks/.
# Replaces upstream `install.sh --reinstall-hooks`. Does not touch state, rubric,
# predictions, videos or .claude/settings.json.
#
# Usage: bash <CHEAT_DIR>/tools/reinstall-hooks.sh <project-dir>
set -euo pipefail

PROJECT_DIR="${1:-}"
CHEAT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )"

if [[ -z "$PROJECT_DIR" || ! -d "$PROJECT_DIR" ]]; then
  echo "Usage: bash $CHEAT_DIR/tools/reinstall-hooks.sh <project-dir>" >&2
  exit 1
fi
if [[ ! -f "$PROJECT_DIR/.cheat-state.json" ]]; then
  echo "$PROJECT_DIR has no .cheat-state.json. Say \"初始化 cheat-on-content\" in that project first." >&2
  exit 1
fi

HOOK_DST="$PROJECT_DIR/.cheat-hooks"
mkdir -p "$HOOK_DST"
for hook_script in prediction-immutability.sh session-start.sh log-event.sh; do
  if [[ -f "$CHEAT_DIR/hooks/$hook_script" ]]; then
    cp "$CHEAT_DIR/hooks/$hook_script" "$HOOK_DST/$hook_script"
    chmod +x "$HOOK_DST/$hook_script"
    echo "updated: .cheat-hooks/$hook_script"
  else
    echo "missing in skill: hooks/$hook_script (skipped)" >&2
  fi
done
echo "Hook scripts reinstalled. State, rubric, predictions, videos and .claude/settings.json were not touched."
