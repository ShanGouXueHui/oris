#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="fix-public-chat-post-403-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/fix-public-chat-post-403-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/fix-public-chat-post-403-$STAMP.json"
DIRECT_SMOKE="$LOG_DIR/direct-chat-post-smoke-$STAMP.json"
NGINX_AUDIT="$LOG_DIR/public-chat-nginx-audit-$STAMP.json"
PRIVATE_BACKUP="$HOME/.local/state/oris/nginx_backups/$STAMP"
PATCHED_CONFIG="/tmp/oris-control-nginx-patched-$STAMP.conf"
GIT_OUTPUT="/tmp/oris-chat-post-403-git-$STAMP.log"

WEB_SERVICE="oris-dev-employee-web-console.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
OPENCLAW_SERVICE="openclaw-gateway.service"
PUBLIC_HOST="control.orisfy.com"

RESULT="FAILED"
DIRECT_APP_POST="NOT_RUN"
NGINX_CONFIG_FOUND="NO"
NGINX_METHOD_GUARD_DETECTED="NO"
NGINX_EXACT_CHAT_LOCATION="NOT_RUN"
NGINX_CONFIG_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
PUBLIC_UNAUTH_GET="NOT_RUN"
PUBLIC_UNAUTH_POST="NOT_RUN"
PUBLIC_POST_GATE="NOT_VERIFIED"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
CONFIG_BACKUP="NOT_RUN"
ROLLBACK="NOT_NEEDED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_PUBLIC_CHAT_POST_EVIDENCE"
NGINX_CONFIG=""
NGINX_CONFIG_REAL=""
BACKUP_SHA256=""

mkdir -p "$LOG_DIR" "$PRIVATE_BACKUP"
chmod 700 "$PRIVATE_BACKUP"
: > "$RUN_LOG"

log() { printf '%s\n' "$*" | tee -a "$RUN_LOG"; }
service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }

restore_nginx() {
  if [ "$CONFIG_BACKUP" != "PASS" ] || [ -z "$NGINX_CONFIG_REAL" ]; then
    return
  fi
  log "NGINX_ROLLBACK=START"
  sudo install -o root -g root -m 0644 "$PRIVATE_BACKUP/original.conf" "$NGINX_CONFIG_REAL" >> "$RUN_LOG" 2>&1 || {
    ROLLBACK="FAILED"
    return
  }
  sudo nginx -t >> "$RUN_LOG" 2>&1 || {
    ROLLBACK="FAILED"
    return
  }
  sudo systemctl reload nginx >> "$RUN_LOG" 2>&1 || {
    ROLLBACK="FAILED"
    return
  }
  ROLLBACK="PASS"
  log "NGINX_ROLLBACK=PASS"
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
  "task_id":"$TASK_ID",
  "checked_at":"$(date -Is)",
  "result":"$RESULT",
  "failure_code":"$FAILURE_CODE" or None,
  "direct_app_post":"$DIRECT_APP_POST",
  "nginx_config_found":"$NGINX_CONFIG_FOUND",
  "nginx_config_path":"$NGINX_CONFIG_REAL" or None,
  "nginx_method_guard_detected":"$NGINX_METHOD_GUARD_DETECTED",
  "nginx_exact_chat_location":"$NGINX_EXACT_CHAT_LOCATION",
  "nginx_config_test":"$NGINX_CONFIG_TEST",
  "nginx_reload":"$NGINX_RELOAD",
  "public_unauth_get":"$PUBLIC_UNAUTH_GET",
  "public_unauth_post":"$PUBLIC_UNAUTH_POST",
  "public_post_gate":"$PUBLIC_POST_GATE",
  "config_backup":"$CONFIG_BACKUP",
  "backup_sha256":"$BACKUP_SHA256" or None,
  "rollback":"$ROLLBACK",
  "product_sha_unchanged":"$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean":"$PRODUCT_WORKTREE_CLEAN",
  "services":{
    "openclaw_gateway":"$(service_state "$OPENCLAW_SERVICE")",
    "bridge":"$(service_state "$BRIDGE_SERVICE")",
    "intake":"$(service_state "$INTAKE_SERVICE")",
    "web_console":"$(service_state "$WEB_SERVICE")",
    "nginx":"$(systemctl is-active nginx 2>/dev/null || true)"
  },
  "openclaw_reinstalled":False,
  "agent_harness_changed":False,
  "real_product_task_submitted":False,
  "real_product_change":False,
  "next_action":"$NEXT_ACTION"
}
open("$EVIDENCE_JSON","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" "${DIRECT_SMOKE#$ORIS/}" "${NGINX_AUDIT#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_ADD_FAILED"; return 1; }
  git commit --only -m "test(dev-employee): verify public chat POST repair $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_COMMIT_FAILED"; return 1; }
  git push origin main > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_PUSH_FAILED"; return 1; }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "DIRECT_APP_POST=$DIRECT_APP_POST"
  echo "NGINX_CONFIG_FOUND=$NGINX_CONFIG_FOUND"
  echo "NGINX_METHOD_GUARD_DETECTED=$NGINX_METHOD_GUARD_DETECTED"
  echo "NGINX_EXACT_CHAT_LOCATION=$NGINX_EXACT_CHAT_LOCATION"
  echo "NGINX_CONFIG_TEST=$NGINX_CONFIG_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "PUBLIC_UNAUTH_GET=$PUBLIC_UNAUTH_GET"
  echo "PUBLIC_UNAUTH_POST=$PUBLIC_UNAUTH_POST"
  echo "PUBLIC_POST_GATE=$PUBLIC_POST_GATE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "CONFIG_BACKUP=$CONFIG_BACKUP"
  echo "ROLLBACK=$ROLLBACK"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state "$OPENCLAW_SERVICE")"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "NGINX_SERVICE=$(systemctl is-active nginx 2>/dev/null || true)"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"; NEXT_ACTION="$2"; RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  if [ "$NGINX_RELOAD" = "PASS" ] && [ "$PUBLIC_POST_GATE" != "PASS" ]; then
    restore_nginx
  fi
  write_evidence
  commit_logs || true
  summary
  rm -f "$PATCHED_CONFIG" "$GIT_OUTPUT"
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_ORIS_GIT_STATE"
git restore --source=HEAD --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_worktree_sync_failed" "INSPECT_ORIS_GIT_STATE"

BASE_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
BASE_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
[ -n "$BASE_PRODUCT_SHA" ] && [ "$BASE_PRODUCT_SHA" = "$BASE_PRODUCT_REMOTE" ] || fail "product_baseline_sha_mismatch" "INSPECT_PRODUCT_REPOSITORY"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_baseline_dirty" "INSPECT_PRODUCT_REPOSITORY"

python3 - "$DIRECT_SMOKE" "$ORIS" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
import urllib.request
from pathlib import Path

out=Path(sys.argv[1]); root=Path(sys.argv[2])
with urllib.request.urlopen('http://127.0.0.1:18893/api/chat/bootstrap',timeout=20) as response:
    bootstrap=json.loads(response.read().decode('utf-8'))
sid=bootstrap['session_id']; csrf=bootstrap['csrf_token']
body=json.dumps({'session_id':sid,'message':'帮助'},ensure_ascii=False).encode('utf-8')
request=urllib.request.Request('http://127.0.0.1:18893/api/chat/messages',data=body,method='POST',headers={'Content-Type':'application/json','X-ORIS-Chat-CSRF':csrf})
with urllib.request.urlopen(request,timeout=30) as response:
    status=response.status; payload=json.loads(response.read().decode('utf-8'))
session=payload.get('session') or {}
assert status == 200
assert session.get('current_task_id') is None
assert any(item.get('role')=='assistant' and '直接告诉我' in str(item.get('content')) for item in session.get('messages') or [])
queue=list((root/'orchestration/dev_employee_queue').glob('*.queued.json'))+list((root/'orchestration/dev_employee_queue').glob('*.running.json'))
assert not queue
session_path=root/'orchestration/dev_employee_chat_sessions'/('%s.json' % sid)
lock_path=root/'run/dev_employee_chat_locks'/('%s.lock' % sid)
if session_path.exists(): session_path.unlink()
if lock_path.exists(): lock_path.unlink()
out.write_text(json.dumps({'result':'PASS','http_status':status,'task_created':False,'queue_empty':True},indent=2)+'\n',encoding='utf-8')
PY
[ "$?" -eq 0 ] || fail "direct_chat_post_failed" "INSPECT_WEB_CONSOLE_SERVICE"
DIRECT_APP_POST="PASS"

NGINX_CONFIG="$(sudo grep -RIlE 'server_name[^;]*control\.orisfy\.com' /etc/nginx/sites-enabled /etc/nginx/conf.d 2>/dev/null | head -n 1)"
[ -n "$NGINX_CONFIG" ] || fail "control_nginx_config_not_found" "INSPECT_NGINX_CONFIGURATION"
NGINX_CONFIG_REAL="$(readlink -f "$NGINX_CONFIG")"
[ -f "$NGINX_CONFIG_REAL" ] || fail "control_nginx_config_realpath_missing" "INSPECT_NGINX_CONFIGURATION"
NGINX_CONFIG_FOUND="YES"

sudo cp -p "$NGINX_CONFIG_REAL" "$PRIVATE_BACKUP/original.conf" >> "$RUN_LOG" 2>&1 || fail "nginx_backup_failed" "INSPECT_NGINX_PERMISSIONS"
chmod 600 "$PRIVATE_BACKUP/original.conf"
BACKUP_SHA256="$(sha256sum "$PRIVATE_BACKUP/original.conf" | awk '{print $1}')"
CONFIG_BACKUP="PASS"

python3 - "$NGINX_CONFIG_REAL" "$PATCHED_CONFIG" "$NGINX_AUDIT" <<'PY' >> "$RUN_LOG" 2>&1
import json
import re
import sys
from pathlib import Path

source=Path(sys.argv[1]); target=Path(sys.argv[2]); audit=Path(sys.argv[3])
text=source.read_text(encoding='utf-8')
lines=text.splitlines(True)
server_name_re=re.compile(r'\bserver_name\b[^;]*\bcontrol\.orisfy\.com\b')
server_start_re=re.compile(r'^\s*server\s*\{')
name_index=next((i for i,line in enumerate(lines) if server_name_re.search(line.split('#',1)[0])),None)
if name_index is None: raise SystemExit('target server_name not found')
start=next((i for i in range(name_index,-1,-1) if server_start_re.search(lines[i].split('#',1)[0])),None)
if start is None: raise SystemExit('target server block start not found')
depth=0; end=None
for i in range(start,len(lines)):
    clean=lines[i].split('#',1)[0]
    depth += clean.count('{')-clean.count('}')
    if depth==0 and i>start:
        end=i; break
if end is None: raise SystemExit('target server block end not found')
block=''.join(lines[start:end+1])
method_guard=bool(re.search(r'limit_except\s+GET|request_method[^\n]*(?:GET|HEAD)[^\n]*(?:403|405)|return\s+403',block,re.I))
marker='# ORIS_CHAT_MESSAGES_BEGIN'
exact_present=marker in block or bool(re.search(r'location\s*=\s*/api/chat/messages\s*\{',block))
changed=False
if not exact_present:
    indent=re.match(r'^(\s*)',lines[end]).group(1)+'    '
    snippet=(
        '\n'+indent+'# ORIS_CHAT_MESSAGES_BEGIN\n'
        +indent+'location = /api/chat/messages {\n'
        +indent+'    proxy_pass http://127.0.0.1:18893;\n'
        +indent+'    proxy_http_version 1.1;\n'
        +indent+'    proxy_pass_request_headers on;\n'
        +indent+'    proxy_set_header Host $host;\n'
        +indent+'    proxy_set_header X-Real-IP $remote_addr;\n'
        +indent+'    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n'
        +indent+'    proxy_set_header X-Forwarded-Proto $scheme;\n'
        +indent+'    proxy_set_header X-Forwarded-User $remote_user;\n'
        +indent+'    proxy_set_header X-ORIS-Chat-CSRF $http_x_oris_chat_csrf;\n'
        +indent+'    client_max_body_size 64k;\n'
        +indent+'    proxy_connect_timeout 10s;\n'
        +indent+'    proxy_read_timeout 120s;\n'
        +indent+'}\n'
        +indent+'# ORIS_CHAT_MESSAGES_END\n'
    )
    lines.insert(end,snippet)
    changed=True
target.write_text(''.join(lines),encoding='utf-8')
audit.write_text(json.dumps({
    'result':'PASS','config_path':str(source),'server_block_start_line':start+1,
    'server_block_end_line':end+1,'method_guard_detected':method_guard,
    'exact_location_preexisting':exact_present,'config_changed':changed,
    'secret_values_recorded':False
},indent=2)+'\n',encoding='utf-8')
print('METHOD_GUARD_DETECTED=%s' % ('YES' if method_guard else 'NO'))
print('EXACT_LOCATION_PREEXISTING=%s' % ('YES' if exact_present else 'NO'))
print('CONFIG_CHANGED=%s' % ('YES' if changed else 'NO'))
PY
[ "$?" -eq 0 ] || fail "nginx_config_patch_generation_failed" "INSPECT_NGINX_SERVER_BLOCK"

NGINX_METHOD_GUARD_DETECTED="$(python3 -c 'import json,sys;print("YES" if json.load(open(sys.argv[1]))["method_guard_detected"] else "NO")' "$NGINX_AUDIT")"
CONFIG_CHANGED="$(python3 -c 'import json,sys;print("YES" if json.load(open(sys.argv[1]))["config_changed"] else "NO")' "$NGINX_AUDIT")"

if [ "$CONFIG_CHANGED" = "YES" ]; then
  sudo install -o root -g root -m 0644 "$PATCHED_CONFIG" "$NGINX_CONFIG_REAL" >> "$RUN_LOG" 2>&1 || fail "nginx_config_install_failed" "INSPECT_NGINX_PERMISSIONS"
fi
NGINX_EXACT_CHAT_LOCATION="PASS"

sudo nginx -t >> "$RUN_LOG" 2>&1 || fail "nginx_config_test_failed" "ROLLBACK_NGINX_CONFIG"
NGINX_CONFIG_TEST="PASS"
sudo systemctl reload nginx >> "$RUN_LOG" 2>&1 || fail "nginx_reload_failed" "ROLLBACK_NGINX_CONFIG"
NGINX_RELOAD="PASS"
sleep 2

GET_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "https://$PUBLIC_HOST/" 2>/dev/null || true)"
POST_CODE="$(curl -sS -o /tmp/oris-public-chat-post-$STAMP.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/chat/messages" 2>/dev/null || true)"
PUBLIC_UNAUTH_GET="$GET_CODE"
PUBLIC_UNAUTH_POST="$POST_CODE"
log "PUBLIC_UNAUTH_GET_HTTP=$GET_CODE"
log "PUBLIC_UNAUTH_POST_HTTP=$POST_CODE"

# Both unauthenticated requests must now be challenged by Basic Auth. A 403 on
# POST means a method guard still intercepts the request before authentication.
[ "$GET_CODE" = "401" ] || fail "public_get_auth_gate_unexpected" "INSPECT_PUBLIC_REVERSE_PROXY"
[ "$POST_CODE" = "401" ] || fail "public_post_still_blocked" "INSPECT_SERVER_LEVEL_METHOD_GUARD"
PUBLIC_POST_GATE="PASS"

FINAL_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
FINAL_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
[ "$FINAL_PRODUCT_SHA" = "$BASE_PRODUCT_SHA" ] && [ "$FINAL_PRODUCT_REMOTE" = "$BASE_PRODUCT_SHA" ] || fail "product_sha_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_SHA_UNCHANGED="PASS"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_worktree_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_WORKTREE_CLEAN="PASS"

for service in "$OPENCLAW_SERVICE" "$BRIDGE_SERVICE" "$INTAKE_SERVICE" "$WEB_SERVICE"; do
  [ "$(service_state "$service")" = "active" ] || fail "user_service_not_active" "INSPECT_USER_SERVICES"
done
[ "$(systemctl is-active nginx 2>/dev/null || true)" = "active" ] || fail "nginx_not_active" "INSPECT_NGINX_SERVICE"

RESULT="PASS"
NEXT_ACTION="RETRY_BROWSER_HELP_AND_STATUS"
write_evidence
commit_logs || { RESULT="FAILED"; FAILURE_CODE="repair_evidence_push_failed"; NEXT_ACTION="RESOLVE_REPAIR_EVIDENCE_PUSH"; }
summary
rm -f "$PATCHED_CONFIG" "$GIT_OUTPUT" /tmp/oris-public-chat-post-$STAMP.body
[ "$RESULT" = "PASS" ] && exit 0
exit 1
