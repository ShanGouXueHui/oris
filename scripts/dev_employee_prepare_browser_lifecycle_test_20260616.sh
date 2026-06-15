#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
STAMP="$(date +%Y%m%d-%H%M%S)"
TASK_ID="browser-lifecycle-cancel-$STAMP"
RETRY_ID="$TASK_ID-r1"
SESSION_DIR="$ORIS/run/dev_employee_browser_tests"
SESSION_JSON="$SESSION_DIR/current.json"
LOG_DIR="$ORIS/logs/dev_employee/commercial_hardening"
RUN_LOG="$LOG_DIR/browser-lifecycle-prepare-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/browser-lifecycle-prepare-$STAMP.json"
GIT_OUTPUT="/tmp/oris-browser-lifecycle-git-$STAMP.log"

RESULT="FAILED"
PATCH_RESULT="NOT_RUN"
TEST_RESULT="NOT_RUN"
ACTIVE_QUEUE_GATE="NOT_RUN"
PRODUCT_BASELINE="NOT_RUN"
BRIDGE_PAUSED="NO"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_GITHUB_EVIDENCE"

mkdir -p "$SESSION_DIR" "$LOG_DIR"
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
payload = {
  "checked_at": "$(date -Is)",
  "result": "$RESULT",
  "failure_code": "$FAILURE_CODE",
  "task_id": "$TASK_ID",
  "expected_retry_task_id": "$RETRY_ID",
  "patch_result": "$PATCH_RESULT",
  "test_result": "$TEST_RESULT",
  "active_queue_gate": "$ACTIVE_QUEUE_GATE",
  "product_baseline": "$PRODUCT_BASELINE",
  "bridge_paused": "$BRIDGE_PAUSED",
  "services": {
    "bridge": "$(service_state "$BRIDGE_SERVICE")",
    "intake": "$(service_state "$INTAKE_SERVICE")",
    "web_console": "$(service_state "$WEB_SERVICE")"
  },
  "real_product_task_submitted": False,
  "codex_execution_expected": False,
  "next_action": "$NEXT_ACTION"
}
open("$EVIDENCE_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
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
  if [ "$rc" -ne 1 ]; then
    LOG_COMMIT="LOG_DIFF_FAILED"
    return 1
  fi
  git commit --only -m "test(dev-employee): prepare browser lifecycle acceptance $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
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
  echo "TASK_ID=commercial-hardening-queue-lifecycle-browser-acceptance-20260616"
  echo "BROWSER_TASK_ID=$TASK_ID"
  echo "EXPECTED_RETRY_TASK_ID=$RETRY_ID"
  echo "PATCH_RESULT=$PATCH_RESULT"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "PRODUCT_BASELINE=$PRODUCT_BASELINE"
  echo "BRIDGE_PAUSED=$BRIDGE_PAUSED"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "CODEX_EXECUTION_EXPECTED=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  if [ "$BRIDGE_PAUSED" = "YES" ]; then
    systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || true
    BRIDGE_PAUSED="NO"
  fi
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

log "===== timestamp ====="
log "$(date -Is)"
log "===== starting revision ====="
log "HEAD=$(git rev-parse HEAD 2>/dev/null || true)"

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ]; then
  git stash push -m "temp-before-browser-lifecycle-$STAMP" -- . >> "$RUN_LOG" 2>&1 || fail "tracked_change_stash_failed" "INSPECT_GIT_STATE"
  LOCAL_STASH="CREATED"
fi

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git rebase origin/main >> "$RUN_LOG" 2>&1 || fail "oris_rebase_failed" "INSPECT_ORIS_REBASE"

python3 - <<'PY' >> "$RUN_LOG" 2>&1
from pathlib import Path

path = Path("/home/admin/projects/oris/scripts/dev_employee_intake_api_v2.py")
text = path.read_text(encoding="utf-8")
old = '''def task_status(task_id: str) -> dict[str, Any]:
    result = v1.task_status(task_id)
    lifecycle = DEFAULT_KERNEL.lifecycle_summary(task_id)
'''
new = '''def task_status(task_id: str) -> dict[str, Any]:
    result = v1.task_status(task_id)
    cancelled_path = DEFAULT_KERNEL.task_path(task_id, "cancelled")
    if cancelled_path.exists():
        cancelled_data = read_json(cancelled_path)
        queue = result.get("queue") if isinstance(result.get("queue"), list) else []
        if not any(item.get("suffix") == "cancelled" for item in queue if isinstance(item, dict)):
            queue.append({"suffix": "cancelled", "path": str(cancelled_path), "data": cancelled_data})
        state = classify_task_state(cancelled_data.get("status") or "cancelled", cancelled_data)
        result.update(
            {
                "queue": queue,
                "status": str(cancelled_data.get("status") or "cancelled"),
                "canonical_status": state["canonical_status"],
                "active": state["active"],
                "terminal": state["terminal"],
                "failure_code": state["failure_code"],
            }
        )
    lifecycle = DEFAULT_KERNEL.lifecycle_summary(task_id)
'''
if new in text:
    print("CANCELLED_STATUS_PATCH=already")
elif text.count(old) == 1:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("CANCELLED_STATUS_PATCH=applied")
else:
    raise SystemExit(f"cancelled status patch anchor count={text.count(old)}")
PY
[ "$?" -eq 0 ] || fail "cancelled_status_patch_failed" "FIX_CANCELLED_STATUS_DISCOVERY"

python3 -m py_compile scripts/dev_employee_intake_api_v2.py >> "$RUN_LOG" 2>&1 || fail "intake_v2_compile_failed" "FIX_INTAKE_V2_STATIC_CHECK"
export PYTHONPATH="$ORIS:$ORIS/scripts"
python3 tests/test_dev_employee_intake_api_v2.py >> "$RUN_LOG" 2>&1 || fail "intake_v2_regression_failed" "FIX_INTAKE_V2_TESTS"
PATCH_RESULT="PASS"
TEST_RESULT="PASS"

if ! git diff --quiet -- scripts/dev_employee_intake_api_v2.py; then
  git add -- scripts/dev_employee_intake_api_v2.py >> "$RUN_LOG" 2>&1 || fail "intake_patch_git_add_failed" "INSPECT_GIT_STATE"
  git commit --only -m "fix(dev-employee): expose cancelled queue terminal state" -- scripts/dev_employee_intake_api_v2.py >> "$RUN_LOG" 2>&1 || fail "intake_patch_commit_failed" "INSPECT_GIT_COMMIT"
  git push origin main >> "$RUN_LOG" 2>&1 || fail "intake_patch_push_failed" "RESOLVE_ORIS_GIT_PUSH"
fi

systemctl --user restart "$INTAKE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "intake_restart_failed" "INSPECT_INTAKE_SERVICE"
sleep 2
[ "$(service_state "$INTAKE_SERVICE")" = "active" ] || fail "intake_not_active" "INSPECT_INTAKE_SERVICE"
[ "$(service_state "$WEB_SERVICE")" = "active" ] || fail "web_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
systemctl --user show "$INTAKE_SERVICE" -p ExecStart --value | grep -q 'dev_employee_intake_api_v2.py' || fail "intake_v2_not_effective" "INSPECT_INTAKE_OVERRIDE"
systemctl --user show "$WEB_SERVICE" -p ExecStart --value | grep -q 'dev_employee_web_console_v2.py' || fail "web_v2_not_effective" "INSPECT_WEB_OVERRIDE"
systemctl --user show "$BRIDGE_SERVICE" -p ExecStart --value | grep -q 'dev_employee_supervised_bridge_v3.py' || fail "bridge_v3_not_effective" "INSPECT_BRIDGE_OVERRIDE"

ACTIVE_RECORDS="$(find "$ORIS/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) -print 2>/dev/null | sort)"
if [ -n "$ACTIVE_RECORDS" ]; then
  log "===== active queue records ====="
  log "$ACTIVE_RECORDS"
  ACTIVE_QUEUE_GATE="FAILED"
  fail "active_queue_records_present" "INSPECT_ACTIVE_QUEUE"
fi
ACTIVE_QUEUE_GATE="PASS"

PRODUCT_LOCAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_SHA="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ -z "$PRODUCT_LOCAL_SHA" ] || [ "$PRODUCT_LOCAL_SHA" != "$PRODUCT_REMOTE_SHA" ] || [ -n "$PRODUCT_DIRTY" ]; then
  fail "product_baseline_not_clean" "INSPECT_PRODUCT_GIT_STATE"
fi
PRODUCT_BASELINE="PASS"

if [ -e "$ORIS/orchestration/dev_employee_intake_catalog/$TASK_ID.json" ] || [ -e "$ORIS/orchestration/dev_employee_intake_catalog/$RETRY_ID.json" ]; then
  fail "browser_task_id_collision" "RERUN_PREPARE_SCRIPT"
fi

systemctl --user stop "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "bridge_stop_failed" "INSPECT_BRIDGE_SERVICE"
sleep 1
[ "$(service_state "$BRIDGE_SERVICE")" = "inactive" ] || fail "bridge_not_inactive" "INSPECT_BRIDGE_SERVICE"
BRIDGE_PAUSED="YES"

python3 - "$SESSION_JSON" <<PY
import json
payload = {
  "session_id": "$STAMP",
  "prepared_at": "$(date -Is)",
  "task_id": "$TASK_ID",
  "expected_retry_task_id": "$RETRY_ID",
  "project_key": "oris-final-acceptance-api",
  "objective": "Lifecycle browser acceptance only. Keep this task queued so the operator can validate cancellation and explicit retry controls.",
  "constraints": [
    "Lifecycle control test only.",
    "Do not modify product files.",
    "Do not commit or push product changes."
  ],
  "expected_checks": [],
  "product_path": "$PRODUCT",
  "product_baseline_sha": "$PRODUCT_LOCAL_SHA",
  "product_baseline_remote_sha": "$PRODUCT_REMOTE_SHA",
  "bridge_expected_state_during_test": "inactive",
  "status": "prepared"
}
open("$SESSION_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
[ "$?" -eq 0 ] || fail "browser_session_write_failed" "INSPECT_SESSION_DIRECTORY"

RESULT="PASS"
NEXT_ACTION="LOGIN_WEB_AND_RUN_LIFECYCLE_TEST"
restore_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
  systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || true
  BRIDGE_PAUSED="NO"
fi
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="prepare_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
  systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || true
  BRIDGE_PAUSED="NO"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
