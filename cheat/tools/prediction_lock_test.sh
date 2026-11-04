#!/usr/bin/env bash
# Regression test for prediction_lock.py. Run: bash cheat/tools/prediction_lock_test.sh
set -uo pipefail
TOOL="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )/prediction_lock.py"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/predictions"; F="$WORK/predictions/2026-11-05_abc_test.md"
fail=0
expect() { local want="$1"; shift; "$@" >/dev/null 2>&1; local got=$?; if [[ "$got" != "$want" ]]; then echo "FAIL ($got != $want): $*"; fail=1; else echo "ok   ($got): ${*:2}"; fi; }

cat > "$F" <<'MD'
# 标题
**Platform**: douyin

## 预测 v1
**Bucket**: 1-3w
理由 A

## 复盘
（待填）
MD

expect 3 python3 "$TOOL" verify "$F"           # never locked
expect 0 python3 "$TOOL" lock "$F"
expect 0 python3 "$TOOL" verify "$F"
printf '\n### 实绩数据\n- 播放 2w\n' >> "$F"     # appending to 复盘 is allowed
expect 0 python3 "$TOOL" verify "$F"
python3 - "$F" <<'PY'
import sys; p=sys.argv[1]; s=open(p).read().replace("## 复盘","## 预测 v2\n**Bucket**: 3-10w\n\n## 复盘"); open(p,"w").write(s)
PY
expect 0 python3 "$TOOL" verify "$F"            # new v2 section does not break v1 lock
expect 0 python3 "$TOOL" lock "$F"               # v2 gets locked too
sed -i.bak 's/理由 A/理由 B/' "$F"
expect 1 python3 "$TOOL" verify "$F"             # editing v1 is caught
expect 1 python3 "$TOOL" lock "$F"               # and cannot be re-locked
mv "$F.bak" "$F"
expect 0 python3 "$TOOL" verify "$F"
sed -i.bak 's/^## 预测 v1$/## 想法/' "$F"
expect 1 python3 "$TOOL" verify "$F"             # renaming/removing a section is caught
expect 2 python3 "$TOOL" verify "$WORK/missing.md"

[[ $fail == 0 ]] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
