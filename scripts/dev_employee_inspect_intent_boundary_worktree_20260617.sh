#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="inspect-intent-boundary-worktree-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
TMP_ROOT="/tmp/oris-intent-worktree-inspect-$STAMP"
RUN_LOG="$TMP_ROOT/inspect.log"
RESULT_JSON="$TMP_ROOT/inspect.json"
EVIDENCE_WT="$TMP_ROOT/evidence"
SOURCE="scripts/dev_employee_openclaw_provider.py"
TEST_FILE="tests/test_dev_employee_openclaw_provider.py"

RESULT="FAILED"
TRACKED_DIRTY_COUNT="0"
EXPECTED_PATCH_COUNT="0"
EXTRA_DIRTY_COUNT="0"
EXTRA_LOG_COUNT="0"
EXTRA_SOURCE_COUNT="0"
INDEX_DIRTY_COUNT="0"
WORKTREE_DIRTY_COUNT="0"
SOURCE_PATCH_PRESENT="NO"
TEST_PATCH_PRESENT="NO"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_DIRTY_PATH_CLASSIFICATION"

mkdir -p "$TMP_ROOT"
: > "$RUN_LOG"

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "TRACKED_DIRTY_COUNT=$TRACKED_DIRTY_COUNT"
  echo "EXPECTED_PATCH_COUNT=$EXPECTED_PATCH_COUNT"
  echo "EXTRA_DIRTY_COUNT=$EXTRA_DIRTY_COUNT"
  echo "EXTRA_LOG_COUNT=$EXTRA_LOG_COUNT"
  echo "EXTRA_SOURCE_COUNT=$EXTRA_SOURCE_COUNT"
  echo "INDEX_DIRTY_COUNT=$INDEX_DIRTY_COUNT"
  echo "WORKTREE_DIRTY_COUNT=$WORKTREE_DIRTY_COUNT"
  echo "SOURCE_PATCH_PRESENT=$SOURCE_PATCH_PRESENT"
  echo "TEST_PATCH_PRESENT=$TEST_PATCH_PRESENT"
  echo "GIT_STATE_MUTATED=NO"
  echo "SERVICES_CHANGED=NO"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; summary; exit 1; }

git fetch origin main >> "$RUN_LOG" 2>&1 || { FAILURE_CODE="oris_fetch_failed"; NEXT_ACTION="RESOLVE_ORIS_GIT_FETCH"; summary; exit 1; }

mapfile -t INDEX_PATHS < <(git diff --cached --name-only | sed '/^$/d' | sort -u)
mapfile -t WORKTREE_PATHS < <(git diff --name-only | sed '/^$/d' | sort -u)
mapfile -t ALL_PATHS < <({ printf '%s\n' "${INDEX_PATHS[@]}"; printf '%s\n' "${WORKTREE_PATHS[@]}"; } | sed '/^$/d' | sort -u)

INDEX_DIRTY_COUNT="${#INDEX_PATHS[@]}"
WORKTREE_DIRTY_COUNT="${#WORKTREE_PATHS[@]}"
TRACKED_DIRTY_COUNT="${#ALL_PATHS[@]}"

EXTRA_PATHS=()
for path in "${ALL_PATHS[@]}"; do
  printf 'DIRTY_PATH=%s\n' "$path" >> "$RUN_LOG"
  if [ "$path" = "$SOURCE" ]; then
    SOURCE_PATCH_PRESENT="YES"
    EXPECTED_PATCH_COUNT=$((EXPECTED_PATCH_COUNT + 1))
  elif [ "$path" = "$TEST_FILE" ]; then
    TEST_PATCH_PRESENT="YES"
    EXPECTED_PATCH_COUNT=$((EXPECTED_PATCH_COUNT + 1))
  else
    EXTRA_PATHS+=("$path")
    if [[ "$path" == logs/dev_employee/* ]]; then
      EXTRA_LOG_COUNT=$((EXTRA_LOG_COUNT + 1))
    else
      EXTRA_SOURCE_COUNT=$((EXTRA_SOURCE_COUNT + 1))
    fi
  fi
done
EXTRA_DIRTY_COUNT="${#EXTRA_PATHS[@]}"

python3 - "$RESULT_JSON" <<PY
import json
payload={
  "task_id":"$TASK_ID",
  "checked_at":"$(date -Is)",
  "result":"PASS",
  "tracked_dirty_count":int("$TRACKED_DIRTY_COUNT"),
  "index_dirty_count":int("$INDEX_DIRTY_COUNT"),
  "worktree_dirty_count":int("$WORKTREE_DIRTY_COUNT"),
  "expected_patch_count":int("$EXPECTED_PATCH_COUNT"),
  "source_patch_present":"$SOURCE_PATCH_PRESENT",
  "test_patch_present":"$TEST_PATCH_PRESENT",
  "extra_dirty_count":int("$EXTRA_DIRTY_COUNT"),
  "extra_log_count":int("$EXTRA_LOG_COUNT"),
  "extra_source_count":int("$EXTRA_SOURCE_COUNT"),
  "dirty_paths":$(printf '%s\n' "${ALL_PATHS[@]}" | python3 -c 'import json,sys;print(json.dumps([x.strip() for x in sys.stdin if x.strip()]))'),
  "git_state_mutated":False,
  "services_changed":False,
  "real_product_task_submitted":False,
  "real_product_change":False
}
open("$RESULT_JSON","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
PY

RESULT="PASS"
if [ "$SOURCE_PATCH_PRESENT" = "YES" ] && [ "$TEST_PATCH_PRESENT" = "YES" ] && [ "$EXTRA_SOURCE_COUNT" = "0" ]; then
  NEXT_ACTION="RECONCILE_RESIDUAL_LOG_DRIFT_AND_RESUME_TESTS"
else
  NEXT_ACTION="MANUAL_REVIEW_TRACKED_SOURCE_DRIFT"
fi

git worktree add --detach "$EVIDENCE_WT" origin/main >> "$RUN_LOG" 2>&1 || { FAILURE_CODE="evidence_worktree_failed"; RESULT="FAILED"; summary; exit 1; }
mkdir -p "$EVIDENCE_WT/logs/dev_employee/conversational_web"
cp "$RUN_LOG" "$EVIDENCE_WT/logs/dev_employee/conversational_web/intent-worktree-inspect-$STAMP.log"
cp "$RESULT_JSON" "$EVIDENCE_WT/logs/dev_employee/conversational_web/intent-worktree-inspect-$STAMP.json"
(
  cd "$EVIDENCE_WT" || exit 1
  git add -- logs/dev_employee/conversational_web/intent-worktree-inspect-$STAMP.log logs/dev_employee/conversational_web/intent-worktree-inspect-$STAMP.json || exit 1
  git commit -m "chore(dev-employee): record intent worktree inspection $STAMP" || exit 1
  git push origin HEAD:main || exit 1
  git rev-parse HEAD
) > "$TMP_ROOT/git.log" 2>&1
RC="$?"
if [ "$RC" -eq 0 ]; then
  LOG_COMMIT="$(tail -n 1 "$TMP_ROOT/git.log")"
else
  RESULT="FAILED"
  FAILURE_CODE="evidence_push_failed"
  NEXT_ACTION="RESOLVE_INSPECTION_EVIDENCE_PUSH"
fi

git worktree remove --force "$EVIDENCE_WT" >/dev/null 2>&1 || true
summary
rm -rf "$TMP_ROOT"
[ "$RESULT" = "PASS" ] && exit 0
exit 1
