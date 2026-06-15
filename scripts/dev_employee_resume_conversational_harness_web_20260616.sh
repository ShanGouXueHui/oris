#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="commercial-conversational-agent-harness-web-20260616"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/deploy-agent-harness-web-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/deploy-agent-harness-web-$STAMP.json"
PROVIDER_PROBE="$LOG_DIR/openclaw-provider-probe-harness-$STAMP.json"
HARNESS_PROBE="$LOG_DIR/agent-harness-probe-$STAMP.json"
WEB_HEALTH="$LOG_DIR/agent-harness-web-health-$STAMP.json"
WEB_SMOKE="$LOG_DIR/agent-harness-web-smoke-$STAMP.json"
ROOT_HTML="/tmp/oris-harness-root-$STAMP.html"
ADMIN_HTML="/tmp/oris-harness-admin-$STAMP.html"
GIT_OUTPUT="/tmp/oris-harness-git-$STAMP.log"
BACKUP_DIR="/tmp/oris-harness-web-backup-$STAMP"

WEB_SERVICE="oris-dev-employee-web-console.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
OPENCLAW_SERVICE="openclaw-gateway.service"
OPENCLAW_BIN="/home/admin/.npm-global/bin/openclaw"
WEB_OVERRIDE="$HOME/.config/systemd/user/$WEB_SERVICE.d/override.conf"

RESULT="FAILED"
STATIC_CHECKS="NOT_RUN"
TEST_RESULT="NOT_RUN"
ACTIVE_QUEUE_GATE="NOT_RUN"
OPENCLAW_GATEWAY="NOT_VERIFIED"
OPENCLAW_PROVIDER_PROBE="NOT_RUN"
AGENT_HARNESS_PROBE="NOT_RUN"
SERVICE_SWITCH="NOT_RUN"
CHAT_PAGE="NOT_RUN"
ADMIN_PAGE="NOT_RUN"
CHAT_API_SMOKE="NOT_RUN"
HARNESS_TRACE="NOT_RUN"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
LOCAL_STASH="NONE"
LOCAL_STASH_RESTORE="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_AGENT_HARNESS_WEB_EVIDENCE"
OVERRIDE_INSTALLED="NO"

mkdir -p "$LOG_DIR" "$BACKUP_DIR" "$(dirname "$WEB_OVERRIDE")"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

backup_override() {
  if [ -f "$WEB_OVERRIDE" ]; then
    cp "$WEB_OVERRIDE" "$BACKUP_DIR/web.override.conf"
  else
    : > "$BACKUP_DIR/web.override.absent"
  fi
}

restore_override() {
  if [ -f "$BACKUP_DIR/web.override.conf" ]; then
    cp "$BACKUP_DIR/web.override.conf" "$WEB_OVERRIDE"
  elif [ -f "$BACKUP_DIR/web.override.absent" ]; then
    rm -f "$WEB_OVERRIDE"
  fi
}

rollback_web() {
  if [ "$OVERRIDE_INSTALLED" != "YES" ]; then
    return
  fi
  log "WEB_ROLLBACK=START"
  restore_override
  systemctl --user daemon-reload >> "$RUN_LOG" 2>&1 || true
  systemctl --user restart "$WEB_SERVICE" >> "$RUN_LOG" 2>&1 || true
  log "WEB_ROLLBACK=COMPLETE"
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
  "task_id":"$TASK_ID",
  "checked_at":"$(date -Is)",
  "result":"$RESULT",
  "failure_code":"$FAILURE_CODE",
  "static_checks":"$STATIC_CHECKS",
  "test_result":"$TEST_RESULT",
  "active_queue_gate":"$ACTIVE_QUEUE_GATE",
  "openclaw_gateway":"$OPENCLAW_GATEWAY",
  "openclaw_provider_probe":"$OPENCLAW_PROVIDER_PROBE",
  "agent_harness_probe":"$AGENT_HARNESS_PROBE",
  "service_switch":"$SERVICE_SWITCH",
  "chat_page":"$CHAT_PAGE",
  "admin_page":"$ADMIN_PAGE",
  "chat_api_smoke":"$CHAT_API_SMOKE",
  "harness_trace":"$HARNESS_TRACE",
  "product_sha_unchanged":"$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean":"$PRODUCT_WORKTREE_CLEAN",
  "services":{
    "openclaw_gateway":"$(service_state "$OPENCLAW_SERVICE")",
    "bridge":"$(service_state "$BRIDGE_SERVICE")",
    "intake":"$(service_state "$INTAKE_SERVICE")",
    "web_console":"$(service_state "$WEB_SERVICE")"
  },
  "web_runtime":"dev_employee_web_console_v5.py",
  "agent_harness":"dev_employee_agent_harness.py",
  "harness_provider_mode":"openclaw",
  "harness_fallback_enabled":True,
  "openclaw_reinstalled":False,
  "real_product_task_submitted":False,
  "product_changed":False,
  "next_action":"$NEXT_ACTION"
}
open("$EVIDENCE_JSON","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
PY
}

commit_logs() {
  local files=()
  for file in "$RUN_LOG" "$EVIDENCE_JSON" "$PROVIDER_PROBE" "$HARNESS_PROBE" "$WEB_HEALTH" "$WEB_SMOKE"; do
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
  git commit --only -m "test(dev-employee): deploy Agent Harness Web $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
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
  echo "TASK_ID=$TASK_ID"
  echo "STATIC_CHECKS=$STATIC_CHECKS"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "OPENCLAW_GATEWAY=$OPENCLAW_GATEWAY"
  echo "OPENCLAW_PROVIDER_PROBE=$OPENCLAW_PROVIDER_PROBE"
  echo "AGENT_HARNESS_PROBE=$AGENT_HARNESS_PROBE"
  echo "SERVICE_SWITCH=$SERVICE_SWITCH"
  echo "CHAT_PAGE=$CHAT_PAGE"
  echo "ADMIN_PAGE=$ADMIN_PAGE"
  echo "CHAT_API_SMOKE=$CHAT_API_SMOKE"
  echo "HARNESS_TRACE=$HARNESS_TRACE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state "$OPENCLAW_SERVICE")"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "LOCAL_STASH=$LOCAL_STASH"
  echo "LOCAL_STASH_RESTORE=$LOCAL_STASH_RESTORE"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "OPENCLAW_REINSTALLED=NO"
  echo "AGENT_HARNESS_ADDED=YES"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  rollback_web
  restore_stash
  write_evidence
  commit_logs || true
  summary
  rm -f "$ROOT_HTML" "$ADMIN_HTML" "$GIT_OUTPUT" /tmp/oris-openclaw-health-$STAMP.json
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
  git stash push -m "temp-before-agent-harness-web-$STAMP" -- . >> "$RUN_LOG" 2>&1 || fail "tracked_change_stash_failed" "INSPECT_GIT_STATE"
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

PRODUCT_BASELINE_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_BASELINE_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_BASELINE_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ -z "$PRODUCT_BASELINE_SHA" ] || [ "$PRODUCT_BASELINE_SHA" != "$PRODUCT_BASELINE_REMOTE" ] || [ -n "$PRODUCT_BASELINE_DIRTY" ]; then
  fail "product_baseline_not_clean" "INSPECT_PRODUCT_REPOSITORY"
fi

python3 -m py_compile \
  scripts/dev_employee_agent_harness.py \
  scripts/dev_employee_chat_store.py \
  scripts/dev_employee_openclaw_provider.py \
  scripts/dev_employee_chat_orchestrator.py \
  scripts/dev_employee_web_console_v3.py \
  scripts/dev_employee_web_console_v5.py \
  scripts/dev_employee_probe_openclaw_provider.py >> "$RUN_LOG" 2>&1 || fail "python_compile_failed" "FIX_AGENT_HARNESS_STATIC_CHECKS"
STATIC_CHECKS="PASS"

export PYTHONPATH="$ORIS:$ORIS/scripts"
for test_file in \
  tests/test_dev_employee_agent_harness.py \
  tests/test_dev_employee_chat_store.py \
  tests/test_dev_employee_openclaw_provider.py \
  tests/test_dev_employee_chat_orchestrator.py \
  tests/test_dev_employee_web_console_v3.py \
  tests/test_dev_employee_queue_kernel.py \
  tests/test_dev_employee_task_states.py; do
  log "===== test $test_file ====="
  ORIS_OPENCLAW_BIN=/nonexistent/openclaw python3 "$test_file" >> "$RUN_LOG" 2>&1 || fail "agent_harness_tests_failed" "FIX_AGENT_HARNESS_TESTS"
done
TEST_RESULT="PASS"

[ -x "$OPENCLAW_BIN" ] || fail "openclaw_binary_missing" "RESTORE_OPENCLAW_INSTALLATION"
[ "$(service_state "$OPENCLAW_SERVICE")" = "active" ] || fail "openclaw_gateway_not_active" "REPAIR_OPENCLAW_GATEWAY"
OPENCLAW_HEALTH_HTTP="$(curl -sS -o /tmp/oris-openclaw-health-$STAMP.json -w '%{http_code}' http://127.0.0.1:18789/health || true)"
[ "$OPENCLAW_HEALTH_HTTP" = "200" ] || fail "openclaw_gateway_health_failed" "REPAIR_OPENCLAW_GATEWAY"
OPENCLAW_GATEWAY="PASS"

ORIS_OPENCLAW_BIN="$OPENCLAW_BIN" \
ORIS_OPENCLAW_REQUIRE_GATEWAY=1 \
ORIS_OPENCLAW_TIMEOUT_SECONDS=120 \
ORIS_OPENCLAW_THINKING=low \
python3 scripts/dev_employee_probe_openclaw_provider.py \
  --output "$PROVIDER_PROBE" \
  --binary "$OPENCLAW_BIN" \
  --timeout 120 >> "$RUN_LOG" 2>&1 || fail "openclaw_provider_contract_failed" "INSPECT_OPENCLAW_PROVIDER_PROBE"
OPENCLAW_PROVIDER_PROBE="PASS"

ORIS_OPENCLAW_BIN="$OPENCLAW_BIN" \
ORIS_OPENCLAW_REQUIRE_GATEWAY=1 \
ORIS_OPENCLAW_TIMEOUT_SECONDS=120 \
ORIS_OPENCLAW_THINKING=low \
ORIS_AGENT_HARNESS_PROVIDER=openclaw \
python3 - "$HARNESS_PROBE" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
from pathlib import Path

from scripts.dev_employee_agent_harness import AgentHarness

projects={
  'oris-final-acceptance-api': {
    'name':'ORIS Final Acceptance API',
    'type':'test_project',
    'notes':'Standalone test API project.',
    'allowed_scope':['app/','tests/','docs/'],
    'forbidden_scope':['private-config'],
  }
}
session={
  'session_id':'chat-agent-harness-contract-probe',
  'locale':'zh-CN',
  'selected_project':None,
  'current_task_id':None,
  'messages':[],
}
outcome=AgentHarness('openclaw').analyze(
  session=session,
  user_message='请在 ORIS Final Acceptance API 项目增加一个只读 /healthz 接口，并完成相应测试。',
  projects=projects,
  current_task=None,
)
result=outcome.result
assert result.intent == 'create_task'
assert result.project_key == 'oris-final-acceptance-api'
assert '/healthz' in (result.objective or '')
assert result.raw_metadata.get('agent_harness') is True
assert result.raw_metadata.get('harness_version') == '1.0'
assert outcome.selected_provider == 'openclaw_infer_gateway'
assert outcome.fallback_used is False
payload={
  'result':'PASS',
  'agent_harness':True,
  'harness_version':result.raw_metadata.get('harness_version'),
  'provider_mode':outcome.provider_mode,
  'selected_provider':outcome.selected_provider,
  'fallback_used':outcome.fallback_used,
  'intent':result.intent,
  'project_key':result.project_key,
  'objective_contains_healthz':'/healthz' in (result.objective or ''),
  'requires_confirmation':result.requires_confirmation,
  'real_product_task_submitted':False,
  'product_changed':False,
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(payload,ensure_ascii=False,sort_keys=True))
PY
[ "$?" -eq 0 ] || fail "agent_harness_contract_failed" "INSPECT_AGENT_HARNESS_PROBE"
AGENT_HARNESS_PROBE="PASS"

backup_override
OVERRIDE_INSTALLED="YES"
cat > "$WEB_OVERRIDE" <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_web_console_v5.py
Environment=ORIS_OPENCLAW_BIN=$OPENCLAW_BIN
Environment=ORIS_OPENCLAW_REQUIRE_GATEWAY=1
Environment=ORIS_OPENCLAW_TIMEOUT_SECONDS=90
Environment=ORIS_OPENCLAW_THINKING=low
Environment=ORIS_AGENT_HARNESS_PROVIDER=openclaw
Environment=ORIS_AGENT_HARNESS_ALLOW_FALLBACK=1
EOF

systemctl --user daemon-reload >> "$RUN_LOG" 2>&1 || fail "systemd_daemon_reload_failed" "INSPECT_USER_SYSTEMD"
systemctl --user restart "$WEB_SERVICE" >> "$RUN_LOG" 2>&1 || fail "web_restart_failed" "INSPECT_WEB_CONSOLE_SERVICE"
sleep 3
[ "$(service_state "$WEB_SERVICE")" = "active" ] || fail "web_service_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
systemctl --user show "$WEB_SERVICE" -p ExecStart --value | grep -q 'dev_employee_web_console_v5.py' || fail "web_v5_override_not_effective" "INSPECT_WEB_OVERRIDE"
[ "$(service_state "$INTAKE_SERVICE")" = "active" ] || fail "intake_not_active" "INSPECT_INTAKE_SERVICE"
[ "$(service_state "$BRIDGE_SERVICE")" = "active" ] || fail "bridge_not_active" "INSPECT_BRIDGE_SERVICE"
SERVICE_SWITCH="PASS"

curl -fsS http://127.0.0.1:18893/health -o "$WEB_HEALTH" >> "$RUN_LOG" 2>&1 || fail "web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
python3 - "$WEB_HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
payload=json.load(open(sys.argv[1],encoding='utf-8'))
assert payload.get('status') == 'ok'
assert payload.get('service') == 'dev_employee_web_console_v5'
assert payload.get('default_experience') == 'conversation'
assert payload.get('admin_route') == '/admin'
assert payload.get('agent_harness_enabled') is True
assert payload.get('agent_harness_version') == '1.0'
assert payload.get('agent_harness_provider_mode') == 'openclaw'
assert payload.get('openclaw_provider_configured') is True
assert payload.get('openclaw_provider_type') == 'OpenClawInferCLIProvider'
PY
[ "$?" -eq 0 ] || fail "web_health_contract_failed" "INSPECT_WEB_HEALTH_PAYLOAD"

curl -fsS http://127.0.0.1:18893/ -o "$ROOT_HTML" >> "$RUN_LOG" 2>&1 || fail "chat_page_fetch_failed" "INSPECT_WEB_CONSOLE_SERVICE"
grep -q 'ORIS AI 开发员工' "$ROOT_HTML" && \
grep -q '/api/chat/bootstrap' "$ROOT_HTML" && \
grep -q '/api/chat/messages' "$ROOT_HTML" && \
grep -q '工程管理台' "$ROOT_HTML"
[ "$?" -eq 0 ] || fail "chat_page_contract_missing" "FIX_CONVERSATIONAL_PAGE"
if grep -q 'Console API token' "$ROOT_HTML" || grep -q 'Expected checks' "$ROOT_HTML" || grep -q 'Submit goal' "$ROOT_HTML"; then
  fail "engineering_fields_exposed_on_chat_page" "FIX_CONVERSATIONAL_PAGE"
fi
CHAT_PAGE="PASS"

curl -fsS http://127.0.0.1:18893/admin -o "$ADMIN_HTML" >> "$RUN_LOG" 2>&1 || fail "admin_page_fetch_failed" "INSPECT_WEB_CONSOLE_SERVICE"
grep -q 'ORIS Admin Console — engineering diagnostics' "$ADMIN_HTML" && \
grep -q 'Submit goal' "$ADMIN_HTML" && \
grep -q 'Console API token' "$ADMIN_HTML"
[ "$?" -eq 0 ] || fail "admin_console_contract_missing" "FIX_ADMIN_ROUTE"
ADMIN_PAGE="PASS"

python3 - "$WEB_SMOKE" "$ORIS" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
import urllib.request
from pathlib import Path

out=Path(sys.argv[1])
oris=Path(sys.argv[2])
with urllib.request.urlopen('http://127.0.0.1:18893/api/chat/bootstrap', timeout=30) as response:
    bootstrap=json.loads(response.read().decode('utf-8'))
assert bootstrap.get('session_id')
assert bootstrap.get('csrf_token')
session_id=bootstrap['session_id']
csrf=bootstrap['csrf_token']
body=json.dumps({'session_id':session_id,'message':'帮助'},ensure_ascii=False).encode('utf-8')
request=urllib.request.Request(
    'http://127.0.0.1:18893/api/chat/messages',
    data=body,
    method='POST',
    headers={'Content-Type':'application/json','X-ORIS-Chat-CSRF':csrf},
)
with urllib.request.urlopen(request, timeout=30) as response:
    payload=json.loads(response.read().decode('utf-8'))
session=payload.get('session') or {}
assert session.get('session_id') == session_id
assert session.get('current_task_id') is None
assert session.get('provider') == 'deterministic_fallback'
messages=session.get('messages') or []
assert any(item.get('role') == 'user' and item.get('content') == '帮助' for item in messages)
assert any(item.get('role') == 'assistant' and '直接告诉我' in str(item.get('content')) for item in messages)
queue=list((oris/'orchestration/dev_employee_queue').glob('*.queued.json'))+list((oris/'orchestration/dev_employee_queue').glob('*.running.json'))
assert not queue, queue
trace_files=sorted((oris/'logs/dev_employee/agent_harness').glob('agent_harness_*.jsonl'))
assert trace_files
trace_events=[]
for path in trace_files:
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip():
            item=json.loads(line)
            if item.get('session_id') == session_id:
                trace_events.append(item)
assert trace_events
assert any(item.get('event') == 'harness_decision' and item.get('intent') == 'help' for item in trace_events)
assert all('prompt' not in item and 'message' not in item and 'objective' not in item for item in trace_events)
session_path=oris/'orchestration/dev_employee_chat_sessions'/f'{session_id}.json'
if session_path.exists():
    session_path.unlink()
lock_path=oris/'run/dev_employee_chat_locks'/f'{session_id}.lock'
if lock_path.exists():
    lock_path.unlink()
out.write_text(json.dumps({
    'result':'PASS',
    'session_created':True,
    'help_message_processed':True,
    'provider':'deterministic_fallback',
    'agent_harness_observed':True,
    'harness_trace_event_count':len(trace_events),
    'task_created':False,
    'queue_remained_empty':True,
    'test_session_removed':True,
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY
[ "$?" -eq 0 ] || fail "chat_api_or_harness_smoke_failed" "INSPECT_CHAT_API_SMOKE"
CHAT_API_SMOKE="PASS"
HARNESS_TRACE="PASS"

ACTIVE_RECORDS="$(find "$ORIS/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) -print 2>/dev/null | sort)"
[ -z "$ACTIVE_RECORDS" ] || fail "active_queue_created_during_deployment" "INSPECT_CHAT_OR_INTAKE_STATE"

PRODUCT_FINAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_FINAL_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_FINAL_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ "$PRODUCT_FINAL_SHA" = "$PRODUCT_BASELINE_SHA" ] && [ "$PRODUCT_FINAL_REMOTE" = "$PRODUCT_BASELINE_SHA" ]; then
  PRODUCT_SHA_UNCHANGED="PASS"
else
  fail "product_sha_changed_during_web_deployment" "INSPECT_PRODUCT_REPOSITORY"
fi
if [ -z "$PRODUCT_FINAL_DIRTY" ]; then
  PRODUCT_WORKTREE_CLEAN="PASS"
else
  fail "product_worktree_changed_during_web_deployment" "INSPECT_PRODUCT_REPOSITORY"
fi

RESULT="PASS"
NEXT_ACTION="REQUEST_CONVERSATIONAL_BROWSER_TEST"
restore_stash
if [ "$LOCAL_STASH_RESTORE" = "FAILED" ]; then
  RESULT="FAILED"
  FAILURE_CODE="local_tracked_change_restore_failed"
  NEXT_ACTION="INSPECT_GIT_STASH"
fi
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="agent_harness_web_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
summary
rm -f "$ROOT_HTML" "$ADMIN_HTML" "$GIT_OUTPUT" /tmp/oris-openclaw-health-$STAMP.json

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
