#!/usr/bin/env bash
# Regression test for the douyin-session, xhs-explore, bilibili-stat and linkedin-session run.sh wrappers.
#
# Upstream picked "the first report.md newer than the target folder" anywhere
# under videos/, copied it, and (douyin) rm -rf'd that folder — so a retro could
# grab another episode's report and delete that episode's data. The wrappers now
# make review.py write into a private temp dir. This test checks that:
#   1. a successful run writes this run's report into the target folder
#   2. other episodes' folders are never read or deleted
#   3. a failed run leaves no report (stale or foreign) behind
#   4. more than one report from a single run is rejected
#   5. the temp dir is always cleaned up
#
# Run: bash cheat/adapters/perf-data/test_run_isolation.sh
set -uo pipefail

HERE="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

run_case() {
  local adapter="$1" auth="$2"
  local tmp; tmp="$(mktemp -d)"
  local project="$tmp/project" target="$tmp/project/videos/2026-11-05_day13" other="$tmp/project/videos/2026-11-04_day12"
  local fake="$tmp/fake-python"
  mkdir -p "$project/$auth" "$target" "$other"
  printf '{}\n' > "$project/.cheat-state.json"
  printf 'stale report\n' > "$target/report.md"
  sleep 1
  printf 'day12 report\n' > "$other/report.md"   # newer than the target folder: the upstream trap

  cat > "$fake" <<'FAKE'
#!/usr/bin/env bash
if [[ "${1:-}" == "-c" ]]; then exit 0; fi          # "import playwright" check
case "${FAKE_MODE:-ok}" in
  ok)   mkdir -p "$CHEAT_VIDEOS_DIR/auto-title"; printf 'fresh report %s\n' "$3" > "$CHEAT_VIDEOS_DIR/auto-title/report.md"; exit 0 ;;
  two)  mkdir -p "$CHEAT_VIDEOS_DIR/a" "$CHEAT_VIDEOS_DIR/b"; echo x > "$CHEAT_VIDEOS_DIR/a/report.md"; echo y > "$CHEAT_VIDEOS_DIR/b/report.md"; exit 0 ;;
  fail) exit 5 ;;
esac
FAKE
  chmod +x "$fake"

  echo "== $adapter"
  CHEAT_PYTHON="$fake" FAKE_MODE=ok bash "$HERE/$adapter/run.sh" ID13 "$target" >/dev/null 2>&1; local st=$?
  check "$adapter success exits 0" '[[ $st == 0 ]]'
  check "$adapter writes this run report" 'grep -q "fresh report ID13" "$target/report.md"'
  check "$adapter leaves other episode intact" '[[ -f "$other/report.md" ]] && grep -q "day12 report" "$other/report.md"'
  check "$adapter cleans temp dir" '[[ -z "$(ls -A "$project/.cheat-cache" 2>/dev/null)" ]]'

  printf 'stale report\n' > "$target/report.md"
  CHEAT_PYTHON="$fake" FAKE_MODE=fail bash "$HERE/$adapter/run.sh" ID13 "$target" >/dev/null 2>&1; st=$?
  check "$adapter crawler failure exits 3" '[[ $st == 3 ]]'
  check "$adapter failure leaves no report" '[[ ! -e "$target/report.md" ]]'
  check "$adapter failure leaves other episode intact" 'grep -q "day12 report" "$other/report.md"'

  CHEAT_PYTHON="$fake" FAKE_MODE=two bash "$HERE/$adapter/run.sh" ID13 "$target" >/dev/null 2>&1; st=$?
  check "$adapter rejects two reports" '[[ $st == 3 && ! -e "$target/report.md" ]]'
  check "$adapter cleans temp dir after failures" '[[ -z "$(ls -A "$project/.cheat-cache" 2>/dev/null)" ]]'
  rm -rf "$tmp"
}

run_case douyin-session .auth
run_case xhs-explore .auth-xhs
run_case bilibili-stat .auth-bilibili-unused
run_case linkedin-session .auth-linkedin

[[ $fail == 0 ]] && echo "ALL PASS" || { echo "SOME FAILED"; exit 1; }
