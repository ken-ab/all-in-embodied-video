#!/usr/bin/env bash
#
# douyin-session adapter wrapper
#
# Called by /cheat-retro when state.data_collection=adapter and platform=douyin.
#
# Usage:
#   bash run.sh <aweme_id> <video_folder> [<script_path>]
#
# Example:
#   bash run.sh 7234567890123456789 ~/my-channel/videos/2026-05-04_abc123_停止期待
#
# Output: writes report.md INTO the video_folder.
# Exit codes:
#   0 = success (report.md written)
#   1 = login expired or required
#   2 = adapter dependency missing (playwright not installed)
#   3 = other failure (network, parse error, etc.)

set -uo pipefail

AWEME_ID="${1:-}"
VIDEO_FOLDER="${2:-}"
SCRIPT_PATH="${3:-}"

if [[ -z "$AWEME_ID" || -z "$VIDEO_FOLDER" ]]; then
  echo "Usage: bash run.sh <aweme_id> <video_folder> [<script_path>]" >&2
  exit 3
fi

# Resolve adapter source dir (where this script lives)
ADAPTER_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Find Python — prefer venv in user's project root if exists
PYTHON=""
# Walk up from VIDEO_FOLDER to find project root (.cheat-state.json)
PROJECT_ROOT="$( realpath "$VIDEO_FOLDER" )"
while [[ "$PROJECT_ROOT" != "/" && ! -f "$PROJECT_ROOT/.cheat-state.json" ]]; do
  PROJECT_ROOT="$( dirname "$PROJECT_ROOT" )"
done
if [[ ! -f "$PROJECT_ROOT/.cheat-state.json" ]]; then
  echo "❌ Cannot find project root (.cheat-state.json) from $VIDEO_FOLDER" >&2
  exit 3
fi
if [[ -n "${CHEAT_PYTHON:-}" ]]; then
  PYTHON="$CHEAT_PYTHON"
elif [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PYTHON="$PROJECT_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "❌ python3 not found — install Python 3.10+ first" >&2
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

# Verify auth/ exists in project root (cookie persistence)
if [[ ! -d "$PROJECT_ROOT/.auth" ]]; then
  cat >&2 <<EOF
❌ Not logged in to 抖音 创作者中心.

First-time login (one-shot):
  cd "$PROJECT_ROOT"
  source .venv/bin/activate
  $PYTHON "$ADAPTER_DIR/crawler.py" login

A Chromium window will pop up — scan QR with your phone to log in.
Cookie will be saved to .auth/ for future runs.
EOF
  exit 1
fi

# Make sure video_folder exists
mkdir -p "$VIDEO_FOLDER"

# Resolve script path (optional — if given, copy to video_folder/script.txt for renderer)
SCRIPT_ARG=""
if [[ -n "$SCRIPT_PATH" && -f "$SCRIPT_PATH" ]]; then
  SCRIPT_ARG="$SCRIPT_PATH"
fi

# Run from PROJECT_ROOT so auth dirs are found.
cd "$PROJECT_ROOT"
export CHEAT_PROJECT_ROOT="$PROJECT_ROOT"

# review.py writes CHEAT_VIDEOS_DIR/<auto-named-folder>/report.md. Point it at a
# fresh private temp dir so this run can only ever pick up its own report, never
# another episode's, and only that temp dir is ever deleted. (Upstream searched
# the shared videos/ parent for the first newer report.md and rm -rf'd its folder.)
mkdir -p "$PROJECT_ROOT/.cheat-cache"
RUN_DIR="$( mktemp -d "$PROJECT_ROOT/.cheat-cache/douyin-session-run.XXXXXX" )"
cleanup_run_dir() { rm -rf "$RUN_DIR"; }
trap cleanup_run_dir EXIT
export CHEAT_VIDEOS_DIR="$RUN_DIR"

# A stale report must never be mistaken for this run's result.
rm -f "$VIDEO_FOLDER/report.md"

echo "[douyin-session] fetching aweme_id=$AWEME_ID into $VIDEO_FOLDER"
if [[ -n "$SCRIPT_ARG" ]]; then
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$AWEME_ID" "$SCRIPT_ARG"
else
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$AWEME_ID"
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
