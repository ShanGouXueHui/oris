#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="commercial-hardening-queue-lifecycle-20260616"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/commercial_hardening"
RUN_LOG="$LOG_DIR/queue-lifecycle-deploy-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/queue-lifecycle-deploy-$STAMP.json"
AUTH_LOG="$LOG_DIR/queue-lifecycle-codex-preflight-$STAMP.json"
INTAKE_HEALTH="$LOG_DIR/queue-lifecycle-intake-health-$STAMP.json"
WEB_HEALTH="$LOG_DIR/queue-lifecycle-web-health-$STAMP.json"
COMPLETED_STATUS="$LOG_DIR/queue-lifecycle-completed-status-$STAMP.json"
STALE_RECOVERY="$LOG_DIR/queue-lifecycle-stale-recovery-$STAMP.json"
WEB_PAGE="$LOG_DIR/queue-lifecycle-web-page-$STAMP.html"
BACKUP_DIR="/tmp/oris-queue-lifecycle-overrides-$STAMP"

BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"
COMPLETED_TASK="goal-oris-final-acceptance-api-readonly-e2e-20260616-044030"

RESULT="FAILED"
TEST_RESULT="NOT_RUN"
STATIC_CHECKS="NOT_RUN"
CODEX_PREFLIGHT="NOT_RUN"
ACTIVE_QUEUE_GATE="NOT_RUN"
SERVICE_SWITCH="NOT_RUN"
LOOPBACK_SMOKE="NOT_RUN"
COMPATIBILITY_STATUS="NOT_RUN"
WEB_CONTROLS="NOT_RUN"
STALE_POLICY="NOT_RUN"
BRIDGE_WORKER_SLOT="NOT_VERIFIED"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_GITHUB_EVIDENCE"
OVERRIDES_INSTALLED="NO"

mkdir -p "$LOG_DIR" "$BACKUP_DIR"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

backup_override() {
  local service="$1"
  local source="$HOME/.config/systemd/user/$service.d/override.conf"
  local target="$BACKUP_DIR/$service.override.conf"
  mkdir -p "$HOME/.config/systemd/user/$service.d"
  if [ -f "$source" ]; then
    cp "$source" "$target"
  else
    : > "$BACKUP_DIR/$service.absent"
  fi
}

restore_override() {
  local service="$1"
  local target="$HOME/.config/systemd/user/$service.d/override.conf"
  local backup="$BACKUP_DIR/$service.override.conf"
  if [ -f "$backup" ]; then
    cp "$backup" "$target"
  elif [ -f "$BACKUP_DIR/$service.absent" ]; then
    rm -f "$target"
  fi
}

rollback_services() {
  if [ "$OVERRIDES_INSTALLED" != "YES" ]; then
    return
  fi
  log "ROLLBACK_SERVICES=START"
  restore_override "$BRIDGE_SERVICE"
  restore_override "$INTAKE_SERVICE"
  restore_override "$WEB_SERVICE"
  systemctl --user daemon-reload >> "$RUN_LOG" 2>&1 || true
  systemctl --user restart "$INTAKE_SERVICE" >> "$RUN_LOG" 2>&1 || true
  systemctl --user restart "$WEB_SERVICE" >> "$RUN_LOG" 2>&1 || true
  systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || true
  log "ROLLBACK_SERVICES=COMPLETE"
}

restore_local_stash() {
  if [ "$LOCAL_STASH" = "CREATED" ]; then
    git stash pop >> "$RUN_LOG" 2>&1
    if [ "$?" -eq 0 ]; then
      LOCAL_STASH_RESTORE="PASS"
      LOCAL_STASH="RESTORED"
    else
      LOCAL_STASH_RESTORE="FAILED"
    fi
  fi
}

commit_logs() {
  cd "$ORIS" || return 1
  local files=()
  for file in "$RUN_LOG" "$EVIDENCE_JSON" "$AUTH_LOG" "$INTAKE_HEALTH" "$WEB_HEALTH" "$COMPLETED_STATUS" "$STALE_RECOVERY"; do
    [ -f "$file" ] && files+=("${file#$ORIS/}")
  done
  if [ "${#files[@]}" -eq 0 ]; then
    LOG_COMMIT="NO_LOG_FILES"
    return 1
  fi
  git add -- "${files[@]}" >> "$RUN_LOG" 2>&1 || {
    LOG_COMMIT="LOG_ADD_FAILED"
    return 1
  }
  git diff --cached --quiet -- "${files[@]}"
  local diff_rc="$?"
  if [ "$diff_rc" -eq 0 ]; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  if [ "$diff_rc" -ne 1 ]; then
    LOG_COMMIT="LOG_DIFF_FAILED"
    return 1
  fi
  git commit --only -m "test(dev-employee): deploy queue lifecycle hardening $STAMP" -- "${files[@]}" >> "$RUN_LOG" 2>&1 || {
    LOG_COMMIT="LOG_COMMIT_FAILED"
    return 1
  }
  git push origin main >> "$RUN_LOG" 2>&1 || {
    LOG_COMMIT="LOG_PUSH_FAILED"
    return 1
  }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload = {
  "task_id": "$TASK_ID",
  "checked_at": "$(date -Is)",
  "result": "$RESULT",
  "failure_code": "$FAILURE_CODE",
  "static_checks": "$STATIC_CHECKS",
  "test_result": "$TEST_RESULT",
  "codex_preflight": "$CODEX_PREFLIGHT",
  "active_queue_gate": "$ACTIVE_QUEUE_GATE",
  "service_switch": "$SERVICE_SWITCH",
  "loopback_smoke": "$LOOPBACK_SMOKE",
  "compatibility_status": "$COMPATIBILITY_STATUS",
  "web_controls": "$WEB_CONTROLS",
  "stale_policy": "$STALE_POLICY",
  "bridge_worker_slot": "$BRIDGE_WORKER_SLOT",
  "services": {
    "bridge": "$(service_state "$BRIDGE_SERVICE")",
    "intake": "$(service_state "$INTAKE_SERVICE")",
    "web_console": "$(service_state "$WEB_SERVICE")"
  },
  "real_product_task_submitted": False,
  "browser_test_performed": False,
  "next_action": "$NEXT_ACTION"
}
open("$EVIDENCE_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "STATIC_CHECKS=$STATIC_CHECKS"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "CODEX_PREFLIGHT=$CODEX_PREFLIGHT"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "SERVICE_SWITCH=$SERVICE_SWITCH"
  echo "LOOPBACK_SMOKE=$LOOPBACK_SMOKE"
  echo "COMPATIBILITY_STATUS=$COMPATIBILITY_STATUS"
  echo "WEB_CONTROLS=$WEB_CONTROLS"
  echo "STALE_POLICY=$STALE_POLICY"
  echo "BRIDGE_WORKER_SLOT=$BRIDGE_WORKER_SLOT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "BROWSER_TEST_PERFORMED=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  rollback_services
  restore_local_stash
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
  git stash push -m "temp-before-queue-lifecycle-$STAMP" -- . >> "$RUN_LOG" 2>&1 || fail "tracked_change_stash_failed" "INSPECT_GIT_STATE"
  LOCAL_STASH="CREATED"
fi

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git rebase origin/main >> "$RUN_LOG" 2>&1 || fail "oris_rebase_failed" "INSPECT_ORIS_REBASE"

ACTIVE_RECORDS="$(find "$ORIS/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) -print 2>/dev/null | sort)"
if [ -n "$ACTIVE_RECORDS" ]; then
  log "===== active queue records ====="
  log "$ACTIVE_RECORDS"
  ACTIVE_QUEUE_GATE="FAILED"
  fail "active_queue_records_present" "INSPECT_AND_DRAIN_ACTIVE_QUEUE"
fi
ACTIVE_QUEUE_GATE="PASS"

python3 -m py_compile \
  scripts/dev_employee_task_states.py \
  scripts/dev_employee_queue_kernel.py \
  scripts/dev_employee_supervised_bridge_v3.py \
  scripts/dev_employee_intake_api_v2.py \
  scripts/dev_employee_web_console_v2.py \
  scripts/dev_employee_recover_stale_tasks.py \
  scripts/dev_employee_codex_auth_preflight.py >> "$RUN_LOG" 2>&1 || fail "python_compile_failed" "FIX_QUEUE_LIFECYCLE_STATIC_CHECKS"
STATIC_CHECKS="PASS"

export PYTHONPATH="$ORIS:$ORIS/scripts"
for test_file in \
  tests/test_dev_employee_task_states.py \
  tests/test_dev_employee_queue_kernel.py \
  tests/test_dev_employee_intake_api_v2.py \
  tests/test_dev_employee_web_console_v2.py \
  tests/test_dev_employee_codex_auth_preflight.py; do
  log "===== test $test_file ====="
  python3 "$test_file" >> "$RUN_LOG" 2>&1 || fail "platform_regression_tests_failed" "FIX_QUEUE_LIFECYCLE_TESTS"
done
TEST_RESULT="PASS"

python3 scripts/dev_employee_codex_auth_preflight.py \
  --codex-bin /home/admin/.npm-global/bin/codex \
  --workdir /home/admin/projects \
  --log "$AUTH_LOG" \
  --timeout 120 >> "$RUN_LOG" 2>&1 || fail "codex_preflight_failed" "REPAIR_CODEX_AUTH_BEFORE_SERVICE_SWITCH"
CODEX_PREFLIGHT="PASS"

for service in "$BRIDGE_SERVICE" "$INTAKE_SERVICE" "$WEB_SERVICE"; do
  backup_override "$service"
done
OVERRIDES_INSTALLED="YES"

cat > "$HOME/.config/systemd/user/$BRIDGE_SERVICE.d/override.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_supervised_bridge_v3.py --watch --interval 10
Environment=ORIS_DEV_EMPLOYEE_MAX_CONCURRENCY=1
Environment=ORIS_DEV_EMPLOYEE_LEASE_SECONDS=60
Environment=ORIS_DEV_EMPLOYEE_HEARTBEAT_SECONDS=10
Environment=ORIS_DEV_EMPLOYEE_EXECUTION_TIMEOUT_SECONDS=7200
EOF

cat > "$HOME/.config/systemd/user/$INTAKE_SERVICE.d/override.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_intake_api_v2.py
EOF

cat > "$HOME/.config/systemd/user/$WEB_SERVICE.d/override.conf" <<'EOF'
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_web_console_v2.py
EOF

systemctl --user stop "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "bridge_stop_failed" "INSPECT_BRIDGE_SERVICE"
systemctl --user daemon-reload >> "$RUN_LOG" 2>&1 || fail "systemd_daemon_reload_failed" "INSPECT_USER_SYSTEMD"
systemctl --user restart "$INTAKE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "intake_restart_failed" "INSPECT_INTAKE_SERVICE"
systemctl --user restart "$WEB_SERVICE" >> "$RUN_LOG" 2>&1 || fail "web_restart_failed" "INSPECT_WEB_CONSOLE_SERVICE"
systemctl --user restart "$BRIDGE_SERVICE" >> "$RUN_LOG" 2>&1 || fail "bridge_restart_failed" "INSPECT_BRIDGE_SERVICE"
sleep 3

if [ "$(service_state "$BRIDGE_SERVICE")" != "active" ] || [ "$(service_state "$INTAKE_SERVICE")" != "active" ] || [ "$(service_state "$WEB_SERVICE")" != "active" ]; then
  fail "service_not_active_after_switch" "INSPECT_USER_SERVICE_LOGS"
fi
SERVICE_SWITCH="PASS"

curl -fsS http://127.0.0.1:18892/health -o "$INTAKE_HEALTH" >> "$RUN_LOG" 2>&1 || fail "intake_health_failed" "INSPECT_INTAKE_SERVICE"
curl -fsS http://127.0.0.1:18893/health -o "$WEB_HEALTH" >> "$RUN_LOG" 2>&1 || fail "web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
python3 - "$INTAKE_HEALTH" "$WEB_HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json, sys
intake=json.load(open(sys.argv[1], encoding='utf-8'))
web=json.load(open(sys.argv[2], encoding='utf-8'))
assert intake.get('status') == 'ok'
assert intake.get('service') == 'dev_employee_intake_api_v2'
assert web.get('status') == 'ok'
assert web.get('service') == 'dev_employee_web_console_v2'
PY
[ "$?" -eq 0 ] || fail "health_contract_failed" "INSPECT_SERVICE_HEALTH_PAYLOADS"

UNAUTH_HTTP="$(curl -sS -o /tmp/oris-queue-lifecycle-unauth-$STAMP.json -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:18892/goals || true)"
[ "$UNAUTH_HTTP" = "401" ] || fail "unauthenticated_mutation_not_rejected" "INSPECT_INTAKE_AUTH_POLICY"
LOOPBACK_SMOKE="PASS"

curl -fsS "http://127.0.0.1:18892/goals/$COMPLETED_TASK" -o "$COMPLETED_STATUS" >> "$RUN_LOG" 2>&1 || fail "completed_status_lookup_failed" "INSPECT_STATUS_COMPATIBILITY"
python3 - "$COMPLETED_STATUS" <<'PY' >> "$RUN_LOG" 2>&1
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8'))
assert payload.get('canonical_status') == 'completed'
assert payload.get('terminal') is True
ev=payload.get('github_evidence') or {}
assert ev.get('product_commit_sha')
assert ev.get('oris_evidence_commit_sha')
assert isinstance(payload.get('lifecycle'), dict)
PY
[ "$?" -eq 0 ] || fail "completed_status_contract_failed" "INSPECT_STATUS_COMPATIBILITY"
COMPATIBILITY_STATUS="PASS"

curl -fsS http://127.0.0.1:18893/ -o "$WEB_PAGE" >> "$RUN_LOG" 2>&1 || fail "web_page_fetch_failed" "INSPECT_WEB_CONSOLE_SERVICE"
grep -q 'Cancel task' "$WEB_PAGE" && grep -q 'Retry terminal task' "$WEB_PAGE"
[ "$?" -eq 0 ] || fail "web_lifecycle_controls_missing" "FIX_WEB_CONSOLE_V2_PAGE"
WEB_CONTROLS="PASS"

python3 scripts/dev_employee_recover_stale_tasks.py --max-age-minutes 120 > "$STALE_RECOVERY" 2>> "$RUN_LOG" || fail "stale_recovery_failed" "INSPECT_STALE_RECOVERY"
python3 - "$STALE_RECOVERY" <<'PY' >> "$RUN_LOG" 2>&1
import json, sys
payload=json.load(open(sys.argv[1], encoding='utf-8'))
assert payload.get('policy') == 'terminal_reconcile_else_fail_lease_expired_no_automatic_requeue'
expired=((payload.get('lease_expiry') or {}).get('expired') or [])
assert not expired
PY
[ "$?" -eq 0 ] || fail "unexpected_stale_task_expiry" "INSPECT_STALE_TASK_RECORDS"
STALE_POLICY="PASS"

journalctl --user -u "$BRIDGE_SERVICE" -n 80 --no-pager > /tmp/oris-queue-lifecycle-bridge-journal-$STAMP.log 2>&1 || true
grep -q 'WORKER_SLOT_ACQUIRED' /tmp/oris-queue-lifecycle-bridge-journal-$STAMP.log
[ "$?" -eq 0 ] || fail "bridge_worker_slot_not_observed" "INSPECT_BRIDGE_V3_JOURNAL"
BRIDGE_WORKER_SLOT="PASS"

RESULT="PASS"
NEXT_ACTION="REQUEST_BROWSER_LIFECYCLE_TEST"
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="deployment_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
restore_local_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
fi
write_evidence
summary

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
