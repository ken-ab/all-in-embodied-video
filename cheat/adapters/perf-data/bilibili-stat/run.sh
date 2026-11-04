#!/usr/bin/env bash
#
# bilibili-stat adapter wrapper
#
# Called by /cheat-retro when state.data_collection=adapter and platform=bilibili.
#
# Usage:
#   bash run.sh <bvid_or_url> <video_folder> [<script_path>]
#
# Example:
#   bash run.sh BV1cUoUY9Ecr ~/my-channel/videos/2026-05-04_BV1cUoUY9Ecr_AI接入MC
#
# B站视频数据(view)与评论(reply)都是公开接口——无需登录、无需 wbi 签名、无需浏览器。
# 纯 httpx，因此这个 adapter 没有 `crawler.py login` 步骤，clone 下来配好依赖即可用。
#
# Output: writes report.md INTO the video_folder.
# Exit codes:
#   0 = success (report.md written)
#   2 = adapter dependency missing (httpx not installed)
#   3 = other failure (network, parse error, bad bvid, etc.)

set -uo pipefail

BVID="${1:-}"
VIDEO_FOLDER="${2:-}"
SCRIPT_PATH="${3:-}"

if [[ -z "$BVID" || -z "$VIDEO_FOLDER" ]]; then
  echo "Usage: bash run.sh <bvid_or_url> <video_folder> [<script_path>]" >&2
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
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "❌ python not found — install Python 3.10+ first" >&2
  exit 2
fi

# Verify httpx is installed
if ! "$PYTHON" -c "import httpx" 2>/dev/null; then
  cat >&2 <<EOF
❌ httpx not installed.

Install:
  pip install -r "$ADAPTER_DIR/requirements.txt"

Then re-run /cheat-retro.
EOF
  exit 2
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
RUN_DIR="$( mktemp -d "$PROJECT_ROOT/.cheat-cache/bilibili-stat-run.XXXXXX" )"
cleanup_run_dir() { rm -rf "$RUN_DIR"; }
trap cleanup_run_dir EXIT
export CHEAT_VIDEOS_DIR="$RUN_DIR"

# A stale report must never be mistaken for this run's result.
rm -f "$VIDEO_FOLDER/report.md"

echo "[bilibili-stat] fetching $BVID into $VIDEO_FOLDER"
if [[ -n "$SCRIPT_ARG" ]]; then
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$BVID" "$SCRIPT_ARG"
else
  "$PYTHON" "$ADAPTER_DIR/review.py" video "$BVID"
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
