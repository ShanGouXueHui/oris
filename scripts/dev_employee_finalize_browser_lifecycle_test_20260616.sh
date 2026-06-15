#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
SESSION_JSON="$ORIS/run/dev_employee_browser_tests/current.json"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/commercial_hardening"
RUN_LOG="$LOG_DIR/browser-lifecycle-finalize-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/browser-lifecycle-finalize-$STAMP.json"
ORIGINAL_STATUS_JSON="$LOG_DIR/browser-lifecycle-original-status-$STAMP.json"
RETRY_STATUS_JSON="$LOG_DIR/browser-lifecycle-retry-status-$STAMP.json"
AUDIT_EVIDENCE_JSON="$LOG_DIR/browser-lifecycle-audit-$STAMP.json"
SESSION_EVIDENCE_JSON="$LOG_DIR/browser-lifecycle-session-$STAMP.json"
GIT_OUTPUT="/tmp/oris-browser-lifecycle-finalize-git-$STAMP.log"

RESULT="FAILED"
TASK_ID=""
RETRY_ID=""
ORIGINAL_CANCELLED="NOT_VERIFIED"
RETRY_CANCELLED="NOT_VERIFIED"
RETRY_IDEMPOTENCY="NOT_VERIFIED"
EVENT_LEDGER="NOT_VERIFIED"
WEB_AUDIT="NOT_VERIFIED"
ACTIVE_QUEUE_GATE="NOT_RUN"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
CODEX_EXECUTED="NOT_VERIFIED"
BRIDGE_RESTORED="NO"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_BROWSER_ACCEPTANCE_EVIDENCE"

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

restore_bridge() {
  systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || return 1
  for _attempt in 1 2 3 4 5 6 7 8 9 10; do
    if [ "$(service_state "$BRIDGE_SERVICE")" = "active" ]; then
      SLOT_FILE="$ORIS/run/dev_employee_worker_slots/slot-0.lock"
      if [ -s "$SLOT_FILE" ]; then
        python3 - "$SLOT_FILE" <<'PY' >> "$RUN_LOG" 2>&1
import json
import os
import sys
payload=json.load(open(sys.argv[1], encoding='utf-8'))
assert payload.get('slot') == 0
assert payload.get('max_concurrency') == 1
pid=int(payload.get('worker_pid') or 0)
assert pid > 0
os.kill(pid, 0)
PY
        if [ "$?" -eq 0 ]; then
          BRIDGE_RESTORED="YES"
          return 0
        fi
      fi
    fi
    sleep 1
  done
  return 1
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
  "retry_task_id": "$RETRY_ID",
  "original_cancelled": "$ORIGINAL_CANCELLED",
  "retry_cancelled": "$RETRY_CANCELLED",
  "retry_idempotency": "$RETRY_IDEMPOTENCY",
  "event_ledger": "$EVENT_LEDGER",
  "web_audit": "$WEB_AUDIT",
  "active_queue_gate": "$ACTIVE_QUEUE_GATE",
  "product_sha_unchanged": "$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean": "$PRODUCT_WORKTREE_CLEAN",
  "codex_executed": "$CODEX_EXECUTED",
  "bridge_restored": "$BRIDGE_RESTORED",
  "services": {
    "bridge": "$(service_state "$BRIDGE_SERVICE")",
    "intake": "$(service_state "$INTAKE_SERVICE")",
    "web_console": "$(service_state "$WEB_SERVICE")"
  },
  "next_action": "$NEXT_ACTION"
}
open("$EVIDENCE_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
}

commit_logs() {
  local files=()
  for file in "$RUN_LOG" "$EVIDENCE_JSON" "$ORIGINAL_STATUS_JSON" "$RETRY_STATUS_JSON" "$AUDIT_EVIDENCE_JSON" "$SESSION_EVIDENCE_JSON"; do
    [ -f "$file" ] && files+=("${file#$ORIS/}")
  done
  [ "${#files[@]}" -gt 0 ] || {
    LOG_COMMIT="NO_LOG_FILES"
    return 1
  }
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
  git commit --only -m "test(dev-employee): verify browser lifecycle acceptance $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
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
  echo "RETRY_TASK_ID=$RETRY_ID"
  echo "ORIGINAL_CANCELLED=$ORIGINAL_CANCELLED"
  echo "RETRY_CANCELLED=$RETRY_CANCELLED"
  echo "RETRY_IDEMPOTENCY=$RETRY_IDEMPOTENCY"
  echo "EVENT_LEDGER=$EVENT_LEDGER"
  echo "WEB_AUDIT=$WEB_AUDIT"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "CODEX_EXECUTED=$CODEX_EXECUTED"
  echo "BRIDGE_RESTORED=$BRIDGE_RESTORED"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "WEB_LIFECYCLE_TASK_SUBMITTED=YES"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  restore_bridge || true
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

if [ ! -f "$SESSION_JSON" ]; then
  FAILURE_CODE="browser_session_missing"
  NEXT_ACTION="RUN_BROWSER_PREPARE_SCRIPT"
  write_evidence
  summary
  exit 1
fi

TASK_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["task_id"])' "$SESSION_JSON")"
RETRY_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["expected_retry_task_id"])' "$SESSION_JSON")"
BASELINE_SHA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product_baseline_sha"])' "$SESSION_JSON")"
PRODUCT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product_path"])' "$SESSION_JSON")"
cp "$SESSION_JSON" "$SESSION_EVIDENCE_JSON"

log "===== timestamp ====="
log "$(date -Is)"
log "BROWSER_TASK_ID=$TASK_ID"
log "RETRY_TASK_ID=$RETRY_ID"

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ]; then
  git stash push -m "temp-before-browser-lifecycle-finalize-$STAMP" -- . >> "$RUN_LOG" 2>&1 || fail "tracked_change_stash_failed" "INSPECT_GIT_STATE"
  LOCAL_STASH="CREATED"
fi

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git rebase origin/main >> "$RUN_LOG" 2>&1 || fail "oris_rebase_failed" "INSPECT_ORIS_REBASE"

[ "$(service_state "$INTAKE_SERVICE")" = "active" ] || fail "intake_not_active" "INSPECT_INTAKE_SERVICE"
[ "$(service_state "$WEB_SERVICE")" = "active" ] || fail "web_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
if [ "$(service_state "$BRIDGE_SERVICE")" = "active" ]; then
  fail "bridge_was_active_during_browser_test" "REVIEW_BROWSER_TEST_SAFETY"
fi

curl -fsS "http://127.0.0.1:18892/goals/$TASK_ID" -o "$ORIGINAL_STATUS_JSON" >> "$RUN_LOG" 2>&1 || fail "original_status_lookup_failed" "COMPLETE_WEB_TEST_STEPS"
curl -fsS "http://127.0.0.1:18892/goals/$RETRY_ID" -o "$RETRY_STATUS_JSON" >> "$RUN_LOG" 2>&1 || fail "retry_status_lookup_failed" "COMPLETE_WEB_TEST_STEPS"

python3 - "$ORIGINAL_STATUS_JSON" "$RETRY_STATUS_JSON" "$TASK_ID" "$RETRY_ID" "$ORIS" "$AUDIT_EVIDENCE_JSON" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
from pathlib import Path

original_path=Path(sys.argv[1])
retry_path=Path(sys.argv[2])
task_id=sys.argv[3]
retry_id=sys.argv[4]
oris=Path(sys.argv[5])
audit_output=Path(sys.argv[6])
original=json.load(open(original_path, encoding='utf-8'))
retry=json.load(open(retry_path, encoding='utf-8'))

for name, payload in [('original', original), ('retry', retry)]:
    assert payload.get('status') == 'cancelled', (name, payload.get('status'))
    assert payload.get('canonical_status') == 'cancelled', (name, payload.get('canonical_status'))
    assert payload.get('terminal') is True, (name, payload.get('terminal'))
    queue=payload.get('queue') or []
    assert any(item.get('suffix') == 'cancelled' for item in queue if isinstance(item, dict)), name

catalog_path=oris/'orchestration/dev_employee_intake_catalog'/f'{task_id}.json'
retry_catalog_path=oris/'orchestration/dev_employee_intake_catalog'/f'{retry_id}.json'
assert catalog_path.is_file()
assert retry_catalog_path.is_file()
catalog=json.load(open(catalog_path, encoding='utf-8'))
retry_catalog=json.load(open(retry_catalog_path, encoding='utf-8'))
assert catalog.get('latest_retry_task_id') == retry_id
retries=catalog.get('retries') or []
assert len(retries) == 1, retries
assert retries[0].get('task_id') == retry_id
assert retry_catalog.get('retry_of') == task_id
assert int(retry_catalog.get('attempt') or 0) == 2
assert not (oris/'orchestration/dev_employee_intake_catalog'/f'{task_id}-r2.json').exists()
assert not list((oris/'orchestration/dev_employee_queue').glob(f'{task_id}-r2.*.json'))

expected_events={
    task_id: {'task_accepted','task_validated','task_queued','task_cancelled','retry_created'},
    retry_id: {'task_accepted','task_validated','task_queued','task_cancelled'},
}
event_evidence={}
for current_id, required in expected_events.items():
    path=oris/'orchestration/dev_employee_events'/f'{current_id}.jsonl'
    assert path.is_file(), path
    events=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    types=[str(item.get('event_type')) for item in events]
    assert required.issubset(set(types)), (current_id, required-set(types))
    event_evidence[current_id]={
        'event_ledger': str(path),
        'event_types': types,
        'event_count': len(events),
    }

audit_events=[]
for path in sorted((oris/'logs/dev_employee/web_console_audit').glob('web_console_audit_*.jsonl')):
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        item=json.loads(line)
        if item.get('task_id') in {task_id, retry_id}:
            audit_events.append(item)

def count(action, current_id):
    return sum(1 for item in audit_events if item.get('action') == action and item.get('task_id') == current_id and item.get('result') in {'submitted','accepted'})

counts={
    'submit_original': count('submit_goal', task_id),
    'cancel_original': count('cancel', task_id),
    'retry_original': count('retry', task_id),
    'cancel_retry': count('cancel', retry_id),
}
assert counts['submit_original'] >= 1, counts
assert counts['cancel_original'] >= 1, counts
assert counts['retry_original'] >= 2, counts
assert counts['cancel_retry'] >= 1, counts
safe_audit=[
    {
        'ts': item.get('ts'),
        'method': item.get('method'),
        'path': item.get('path'),
        'action': item.get('action'),
        'result': item.get('result'),
        'upstream_status': item.get('upstream_status'),
        'task_id': item.get('task_id'),
    }
    for item in audit_events
]
audit_output.write_text(json.dumps({'counts': counts, 'events': safe_audit, 'event_ledgers': event_evidence}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
PY
[ "$?" -eq 0 ] || fail "browser_lifecycle_contract_failed" "REPEAT_OR_COMPLETE_WEB_TEST_STEPS"
ORIGINAL_CANCELLED="PASS"
RETRY_CANCELLED="PASS"
RETRY_IDEMPOTENCY="PASS"
EVENT_LEDGER="PASS"
WEB_AUDIT="PASS"

ACTIVE_RECORDS="$(find "$ORIS/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) -print 2>/dev/null | sort)"
if [ -n "$ACTIVE_RECORDS" ]; then
  log "===== unexpected active queue records ====="
  log "$ACTIVE_RECORDS"
  fail "active_queue_records_after_browser_test" "CANCEL_REMAINING_BROWSER_TASKS"
fi
ACTIVE_QUEUE_GATE="PASS"

PRODUCT_LOCAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_SHA="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ "$PRODUCT_LOCAL_SHA" = "$BASELINE_SHA" ] && [ "$PRODUCT_REMOTE_SHA" = "$BASELINE_SHA" ]; then
  PRODUCT_SHA_UNCHANGED="PASS"
else
  fail "product_sha_changed_during_browser_test" "INSPECT_PRODUCT_REPOSITORY"
fi
if [ -z "$PRODUCT_DIRTY" ]; then
  PRODUCT_WORKTREE_CLEAN="PASS"
else
  fail "product_worktree_changed_during_browser_test" "INSPECT_PRODUCT_REPOSITORY"
fi

if [ -e "$ORIS/logs/dev_employee/$TASK_ID.codex.log" ] || [ -e "$ORIS/logs/dev_employee/$RETRY_ID.codex.log" ] || [ -e "$ORIS/orchestration/task_runs/$TASK_ID.json" ] || [ -e "$ORIS/orchestration/task_runs/$RETRY_ID.json" ]; then
  fail "codex_execution_evidence_found" "REVIEW_BROWSER_TEST_SAFETY"
fi
CODEX_EXECUTED="NO"

restore_bridge || fail "bridge_restart_failed" "INSPECT_BRIDGE_SERVICE"
systemctl --user show "$BRIDGE_SERVICE" -p ExecStart --value | grep -q 'dev_employee_supervised_bridge_v3.py' || fail "bridge_v3_not_effective" "INSPECT_BRIDGE_OVERRIDE"

RESULT="PASS"
NEXT_ACTION="BROWSER_LIFECYCLE_ACCEPTANCE_COMPLETE"
restore_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
fi
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="browser_acceptance_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
