#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
SESSION_JSON="$ORIS/run/dev_employee_browser_tests/current.json"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/commercial_hardening"
RUN_LOG="$LOG_DIR/browser-form-abort-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/browser-form-abort-$STAMP.json"
GIT_OUTPUT="/tmp/oris-browser-form-abort-git-$STAMP.log"

RESULT="FAILED"
CANCELLED_TASKS="0"
BRIDGE_RESTORED="NO"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
FAILURE_CODE=""
LOG_COMMIT=""
NEXT_ACTION="INSPECT_BROWSER_TEST_ABORT"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

restore_stash() {
  if [ "$LOCAL_STASH" = "CREATED" ]; then
    git stash pop >> "$RUN_LOG" 2>&1
    if [ "$?" -eq 0 ]; then
      LOCAL_STASH="RESTORED"
      LOCAL_STASH_RESTORE="PASS"
    else
      LOCAL_STASH_RESTORE="FAILED"
    fi
  fi
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
  "checked_at":"$(date -Is)",
  "result":"$RESULT",
  "failure_code":"$FAILURE_CODE",
  "cancelled_tasks":int("$CANCELLED_TASKS"),
  "bridge_restored":"$BRIDGE_RESTORED",
  "product_sha_unchanged":"$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean":"$PRODUCT_WORKTREE_CLEAN",
  "services":{
    "bridge":"$(service_state "$BRIDGE_SERVICE")",
    "intake":"$(service_state "$INTAKE_SERVICE")",
    "web_console":"$(service_state "$WEB_SERVICE")"
  },
  "next_action":"$NEXT_ACTION"
}
open("$EVIDENCE_JSON","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_ADD_FAILED"
    return 1
  }
  git diff --cached --quiet -- "${files[@]}"
  local rc="$?"
  if [ "$rc" -eq 0 ]; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  [ "$rc" -eq 1 ] || {
    LOG_COMMIT="LOG_DIFF_FAILED"
    return 1
  }
  git commit --only -m "test(dev-employee): abort form browser test $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_COMMIT_FAILED"
    return 1
  }
  git push origin main > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_PUSH_FAILED"
    return 1
  }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=abort-form-browser-test-20260616"
  echo "CANCELLED_TASKS=$CANCELLED_TASKS"
  echo "BRIDGE_RESTORED=$BRIDGE_RESTORED"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  restore_stash
  write_evidence
  commit_logs || true
  summary
  exit 1
}

if [ "$(id -un)" != "admin" ]; then
  FAILURE_CODE="wrong_linux_user"
  NEXT_ACTION="RUN_AS_ADMIN"
  write_evidence
  summary
  exit 1
fi

cd "$ORIS" || {
  FAILURE_CODE="oris_directory_missing"
  NEXT_ACTION="RESTORE_ORIS_REPOSITORY"
  write_evidence
  summary
  exit 1
}

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ]; then
  git stash push -m "temp-before-abort-form-browser-$STAMP" -- . >> "$RUN_LOG" 2>&1 || fail "tracked_change_stash_failed" "INSPECT_GIT_STATE"
  LOCAL_STASH="CREATED"
fi

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git rebase origin/main >> "$RUN_LOG" 2>&1 || fail "oris_rebase_failed" "INSPECT_ORIS_REBASE"

[ -f "$SESSION_JSON" ] || fail "browser_session_missing" "RUN_BROWSER_PREPARE_SCRIPT"
[ "$(service_state "$BRIDGE_SERVICE")" = "inactive" ] || fail "bridge_not_paused" "INSPECT_BROWSER_TEST_SAFETY"
[ "$(service_state "$INTAKE_SERVICE")" = "active" ] || fail "intake_not_active" "INSPECT_INTAKE_SERVICE"

readarray -t VALUES < <(python3 - "$SESSION_JSON" "$ORIS" <<'PY'
import json
import sys
from datetime import datetime
from pathlib import Path

session_path=Path(sys.argv[1])
oris=Path(sys.argv[2])
session=json.load(open(session_path,encoding='utf-8'))
prepared=datetime.fromisoformat(session['prepared_at'])
project_key=session['project_key']
ids=[]
for path in sorted((oris/'orchestration/dev_employee_intake_catalog').glob('*.json')):
    try:
        data=json.load(open(path,encoding='utf-8'))
    except Exception:
        continue
    if data.get('project_key') != project_key:
        continue
    created=data.get('created_at')
    if not created:
        continue
    try:
        created_dt=datetime.fromisoformat(created)
    except Exception:
        continue
    if created_dt < prepared:
        continue
    task_id=str(data.get('task_id') or '')
    if not task_id:
        continue
    queued=oris/'orchestration/dev_employee_queue'/f'{task_id}.queued.json'
    running=oris/'orchestration/dev_employee_queue'/f'{task_id}.running.json'
    if running.exists():
        raise SystemExit(f'running task found during safe abort: {task_id}')
    if queued.exists():
        ids.append(task_id)
print(session['product_path'])
print(session['product_baseline_sha'])
for task_id in ids:
    print(task_id)
PY
)
[ "$?" -eq 0 ] || fail "browser_session_scan_failed" "INSPECT_BROWSER_SESSION"

PRODUCT="${VALUES[0]}"
BASELINE_SHA="${VALUES[1]}"
TASK_IDS=("${VALUES[@]:2}")

for task_id in "${TASK_IDS[@]}"; do
  [ -n "$task_id" ] || continue
  python3 - "$task_id" <<'PY' >> "$RUN_LOG" 2>&1
import sys
from scripts.dev_employee_queue_kernel import DEFAULT_KERNEL

task_id=sys.argv[1]
result=DEFAULT_KERNEL.request_cancel(
    task_id,
    requested_by='browser-test-abort',
    reason='Form-based browser test aborted after UX review'
)
print(result)
PY
  [ "$?" -eq 0 ] || fail "queued_task_cancel_failed" "INSPECT_QUEUE_STATE"
  CANCELLED_TASKS="$((CANCELLED_TASKS + 1))"
done

ACTIVE_RECORDS="$(find "$ORIS/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) -print 2>/dev/null | sort)"
[ -z "$ACTIVE_RECORDS" ] || fail "active_queue_records_remain" "INSPECT_ACTIVE_QUEUE"

PRODUCT_LOCAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_SHA="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ "$PRODUCT_LOCAL_SHA" = "$BASELINE_SHA" ] && [ "$PRODUCT_REMOTE_SHA" = "$BASELINE_SHA" ]; then
  PRODUCT_SHA_UNCHANGED="PASS"
else
  fail "product_sha_changed" "INSPECT_PRODUCT_REPOSITORY"
fi
if [ -z "$PRODUCT_DIRTY" ]; then
  PRODUCT_WORKTREE_CLEAN="PASS"
else
  fail "product_worktree_dirty" "INSPECT_PRODUCT_REPOSITORY"
fi

systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "bridge_restart_failed" "INSPECT_BRIDGE_SERVICE"
for _attempt in 1 2 3 4 5 6 7 8 9 10; do
  if [ "$(service_state "$BRIDGE_SERVICE")" = "active" ]; then
    BRIDGE_RESTORED="YES"
    break
  fi
  sleep 1
done
[ "$BRIDGE_RESTORED" = "YES" ] || fail "bridge_not_active" "INSPECT_BRIDGE_SERVICE"

python3 - "$SESSION_JSON" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
from datetime import datetime

path=sys.argv[1]
data=json.load(open(path,encoding='utf-8'))
data['status']='aborted_after_ux_review'
data['aborted_at']=datetime.now().astimezone().isoformat(timespec='seconds')
data['reason']='The form/JSON engineering console is not the intended conversational product experience.'
open(path,'w',encoding='utf-8').write(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
PY

RESULT="PASS"
NEXT_ACTION="BUILD_CONVERSATIONAL_OPENCLAW_WEB_EXPERIENCE"
restore_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
fi
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="abort_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
