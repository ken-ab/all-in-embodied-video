#!/usr/bin/env bash
#
# linkedin-session adapter wrapper
#
# Called by /cheat-retro when state.data_collection=adapter and platform=linkedin.
#
# Usage:
#   bash run.sh <activity_id_or_url> <video_folder> [<script_path>]
#
# Example:
#   bash run.sh 7470493738918920193 ~/my-channel/videos/2026-05-04_7470493738918920193_post
#   bash run.sh https://www.linkedin.com/feed/update/urn:li:activity:7470493738918920193/ <folder>
#
# Output: writes report.md INTO the video_folder.
# Exit codes:
#   0 = success (report.md written)
#   1 = login expired or required (no .auth-linkedin/)
#   2 = adapter dependency missing (playwright not installed)
#   3 = other failure (network, parse error, bad activity id, etc.)

set -uo pipefail

ACTIVITY_ID="${1:-}"
VIDEO_FOLDER="${2:-}"
SCRIPT_PATH="${3:-}"

if [[ -z "$ACTIVITY_ID" || -z "$VIDEO_FOLDER" ]]; then
  echo "Usage: bash run.sh <activity_id_or_url> <video_folder> [<script_path>]" >&2
  exit 3
fi

# Resolve adapter source dir (where this script lives)
ADAPTER_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Find Python — prefer venv in user's project root if exists
PYTHON=""
PROJECT_ROOT="$( dirname "$( dirname "$( realpath "$VIDEO_FOLDER" )" )" )"
if [[ -n "${CHEAT_PYTHON:-}" ]]; then
  PYTHON="$CHEAT_PYTHON"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "❌ python not found — install Python 3.10+ first" >&2
  exit 2
fi

# Verify playwright is installed
if ! "$PYTHON" -c "import playwright" 2>/dev/null; then
  cat >&2 <<EOF
❌ playwright not installed.

Install in your project venv:
  cd "$PROJECT_ROOT"
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r "$ADAPTER_DIR/requirements.txt"
  playwright install chromium

Then re-run /cheat-retro.
EOF
  exit 2
fi

# Verify .auth-linkedin/ exists in project root (cookie persistence)
if [[ ! -d "$PROJECT_ROOT/.auth-linkedin" ]]; then
  cat >&2 <<EOF
❌ Not logged in to LinkedIn.

First-time login (one-shot):
  cd "$PROJECT_ROOT"
  source .venv/bin/activate
  $PYTHON "$ADAPTER_DIR/review.py" login

A Chromium window will pop up — log in to LinkedIn.
Cookie (li_at) will be saved to .auth-linkedin/ for future runs.
EOF
  exit 1
fi

# Make sure video_folder exists
mkdir -p "$VIDEO_FOLDER"

# Resolve script path (optional)
SCRIPT_ARG=""
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
  SCRIPT_ARG="$SCRIPT_PATH"
fi

# Run from PROJECT_ROOT so auth dirs are found.
cd "$PROJECT_ROOT"
export CHEAT_PROJECT_ROOT="$PROJECT_ROOT"

# review.py writes CHEAT_VIDEOS_DIR/<auto-named-folder>/report.md. Point it at a
# fresh private temp dir so this run can only pick up its own report, never
# another episode's, and only that temp dir is ever deleted.
mkdir -p "$PROJECT_ROOT/.cheat-cache"
RUN_DIR="$( mktemp -d "$PROJECT_ROOT/.cheat-cache/linkedin-session-run.XXXXXX" )"
cleanup_run_dir() { rm -rf "$RUN_DIR"; }
trap cleanup_run_dir EXIT
export CHEAT_VIDEOS_DIR="$RUN_DIR"

# A stale report must never be mistaken for this run's result.
rm -f "$VIDEO_FOLDER/report.md"

echo "[linkedin-session] fetching activity=$ACTIVITY_ID into $VIDEO_FOLDER"
if [[ -n "$SCRIPT_ARG" ]]; then
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$ACTIVITY_ID" "$SCRIPT_ARG"
else
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$ACTIVITY_ID"
fi
REVIEW_RC=$?
if [[ "$REVIEW_RC" != "0" ]]; then
  echo "❌ review.py exited with $REVIEW_RC — no report written" >&2
  exit 3
fi

REPORT_COUNT=$( find "$RUN_DIR" -name report.md -type f | wc -l | tr -d ' ' )
if [[ "$REPORT_COUNT" != "1" ]]; then
  echo "❌ expected exactly one report.md from review.py, found $REPORT_COUNT" >&2
  exit 3
fi
NEW_REPORT=$( find "$RUN_DIR" -name report.md -type f )
cp "$NEW_REPORT" "$VIDEO_FOLDER/report.md"
if [[ -f "$( dirname "$NEW_REPORT" )/script.txt" ]]; then
  cp "$( dirname "$NEW_REPORT" )/script.txt" "$VIDEO_FOLDER/script.txt"
fi

if [[ ! -f "$VIDEO_FOLDER/report.md" ]]; then
  echo "❌ report.md not produced — see review.py output above for details" >&2
  exit 3
fi

echo "✅ report.md written to $VIDEO_FOLDER/report.md"
exit 0
