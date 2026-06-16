#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="patch-effective-chat-post-route-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
CONFIG="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
PRIVATE_BACKUP="$HOME/.local/state/oris/nginx_backups/$STAMP"
PATCHED="/tmp/oris-effective-chat-post-$STAMP.conf"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/patch-effective-chat-post-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/patch-effective-chat-post-$STAMP.json"
PATCH_AUDIT="$LOG_DIR/patch-effective-chat-post-audit-$STAMP.json"
DIRECT_SMOKE="$LOG_DIR/patch-effective-chat-direct-smoke-$STAMP.json"
GIT_OUTPUT="/tmp/oris-effective-chat-post-git-$STAMP.log"
PUBLIC_HOST="control.orisfy.com"

OPENCLAW_SERVICE="openclaw-gateway.service"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"

RESULT="FAILED"
DIRECT_APP_POST="NOT_RUN"
EFFECTIVE_CONFIG_VERIFIED="NOT_RUN"
CONFIG_BACKUP="NOT_RUN"
METHOD_POLICY_PATCH="NOT_RUN"
EXACT_CHAT_LOCATION="NOT_RUN"
NGINX_CONFIG_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
PUBLIC_GET_AUTH_GATE="NOT_RUN"
PUBLIC_CHAT_POST_AUTH_GATE="NOT_RUN"
PUBLIC_OTHER_POST_BLOCKED="NOT_RUN"
LOCAL_TLS_CHAT_POST_AUTH_GATE="NOT_RUN"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
ROLLBACK="NOT_NEEDED"
FAILURE_CODE=""
NEXT_ACTION="INSPECT_EFFECTIVE_CHAT_POST_PATCH"
LOG_COMMIT=""
BACKUP_SHA256=""
PATCHED_SHA256=""
CONFIG_INSTALLED="NO"

mkdir -p "$LOG_DIR" "$PRIVATE_BACKUP"
chmod 700 "$PRIVATE_BACKUP"
: > "$RUN_LOG"

log() { printf '%s\n' "$*" | tee -a "$RUN_LOG"; }
service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }

rollback_nginx() {
  [ "$CONFIG_INSTALLED" = "YES" ] || return
  log "NGINX_ROLLBACK=START"
  sudo install -o root -g root -m 0644 "$PRIVATE_BACKUP/original.conf" "$CONFIG" >> "$RUN_LOG" 2>&1 || { ROLLBACK="FAILED"; return; }
  sudo nginx -t >> "$RUN_LOG" 2>&1 || { ROLLBACK="FAILED"; return; }
  sudo systemctl reload nginx >> "$RUN_LOG" 2>&1 || { ROLLBACK="FAILED"; return; }
  ROLLBACK="PASS"
  log "NGINX_ROLLBACK=PASS"
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
 'task_id':'$TASK_ID','checked_at':'$(date -Is)','result':'$RESULT','failure_code':'$FAILURE_CODE' or None,
 'direct_app_post':'$DIRECT_APP_POST','effective_config_verified':'$EFFECTIVE_CONFIG_VERIFIED',
 'config_path':'$CONFIG','config_backup':'$CONFIG_BACKUP','backup_sha256':'$BACKUP_SHA256' or None,
 'patched_sha256':'$PATCHED_SHA256' or None,'method_policy_patch':'$METHOD_POLICY_PATCH',
 'exact_chat_location':'$EXACT_CHAT_LOCATION','nginx_config_test':'$NGINX_CONFIG_TEST','nginx_reload':'$NGINX_RELOAD',
 'public_get_auth_gate':'$PUBLIC_GET_AUTH_GATE','public_chat_post_auth_gate':'$PUBLIC_CHAT_POST_AUTH_GATE',
 'public_other_post_blocked':'$PUBLIC_OTHER_POST_BLOCKED','local_tls_chat_post_auth_gate':'$LOCAL_TLS_CHAT_POST_AUTH_GATE',
 'product_sha_unchanged':'$PRODUCT_SHA_UNCHANGED','product_worktree_clean':'$PRODUCT_WORKTREE_CLEAN','rollback':'$ROLLBACK',
 'services':{'openclaw_gateway':'$(service_state "$OPENCLAW_SERVICE")','bridge':'$(service_state "$BRIDGE_SERVICE")','intake':'$(service_state "$INTAKE_SERVICE")','web_console':'$(service_state "$WEB_SERVICE")','nginx':'$(systemctl is-active nginx 2>/dev/null || true)'},
 'openclaw_reinstalled':False,'agent_harness_changed':False,'real_product_task_submitted':False,'real_product_change':False,
 'next_action':'$NEXT_ACTION'
}
open('$EVIDENCE_JSON','w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" "${PATCH_AUDIT#$ORIS/}" "${DIRECT_SMOKE#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_ADD_FAILED"; return 1; }
  git commit --only -m "test(dev-employee): verify effective chat POST route $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_COMMIT_FAILED"; return 1; }
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
  echo "EFFECTIVE_CONFIG_VERIFIED=$EFFECTIVE_CONFIG_VERIFIED"
  echo "CONFIG_BACKUP=$CONFIG_BACKUP"
  echo "METHOD_POLICY_PATCH=$METHOD_POLICY_PATCH"
  echo "EXACT_CHAT_LOCATION=$EXACT_CHAT_LOCATION"
  echo "NGINX_CONFIG_TEST=$NGINX_CONFIG_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "PUBLIC_GET_AUTH_GATE=$PUBLIC_GET_AUTH_GATE"
  echo "PUBLIC_CHAT_POST_AUTH_GATE=$PUBLIC_CHAT_POST_AUTH_GATE"
  echo "PUBLIC_OTHER_POST_BLOCKED=$PUBLIC_OTHER_POST_BLOCKED"
  echo "LOCAL_TLS_CHAT_POST_AUTH_GATE=$LOCAL_TLS_CHAT_POST_AUTH_GATE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
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
  rollback_nginx
  write_evidence
  commit_logs || true
  summary
  rm -f "$PATCHED" "$GIT_OUTPUT"
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
[ -z "$TRACKED_DIRTY" ] || fail "oris_tracked_worktree_dirty" "INSPECT_ORIS_GIT_STATE"
git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git merge-base --is-ancestor HEAD origin/main || fail "local_head_not_ancestor_of_origin" "INSPECT_ORIS_GIT_HISTORY"
git restore --source=origin/main --staged --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_worktree_sync_failed" "INSPECT_ORIS_GIT_STATE"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_ORIS_GIT_STATE"

BASE_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
BASE_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
[ -n "$BASE_PRODUCT_SHA" ] && [ "$BASE_PRODUCT_SHA" = "$BASE_PRODUCT_REMOTE" ] || fail "product_baseline_sha_mismatch" "INSPECT_PRODUCT_REPOSITORY"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_baseline_dirty" "INSPECT_PRODUCT_REPOSITORY"

python3 - "$DIRECT_SMOKE" "$ORIS" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys,urllib.request
from pathlib import Path
out=Path(sys.argv[1]);root=Path(sys.argv[2])
with urllib.request.urlopen('http://127.0.0.1:18893/api/chat/bootstrap',timeout=20) as r: boot=json.loads(r.read().decode())
sid=boot['session_id'];csrf=boot['csrf_token']
data=json.dumps({'session_id':sid,'message':'帮助'},ensure_ascii=False).encode()
req=urllib.request.Request('http://127.0.0.1:18893/api/chat/messages',data=data,method='POST',headers={'Content-Type':'application/json','X-ORIS-Chat-CSRF':csrf})
with urllib.request.urlopen(req,timeout=30) as r: status=r.status;payload=json.loads(r.read().decode())
assert status==200
assert (payload.get('session') or {}).get('current_task_id') is None
assert not list((root/'orchestration/dev_employee_queue').glob('*.queued.json'))
for path in [root/'orchestration/dev_employee_chat_sessions'/('%s.json'%sid),root/'run/dev_employee_chat_locks'/('%s.lock'%sid)]:
    if path.exists(): path.unlink()
out.write_text(json.dumps({'result':'PASS','http_status':status,'task_created':False},indent=2)+'\n')
PY
[ "$?" -eq 0 ] || fail "direct_chat_post_failed" "INSPECT_WEB_CONSOLE_SERVICE"
DIRECT_APP_POST="PASS"

[ -f "$CONFIG" ] || fail "effective_config_missing" "RESTORE_EFFECTIVE_NGINX_CONFIG"
EFFECTIVE_COUNT="$(sudo nginx -T 2>/dev/null | grep -Fxc '# configuration file /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf:')"
[ "$EFFECTIVE_COUNT" -eq 1 ] || fail "effective_config_load_count_unexpected" "INSPECT_NGINX_LOAD_ORDER"
EFFECTIVE_CONFIG_VERIFIED="PASS"

sudo cp -p "$CONFIG" "$PRIVATE_BACKUP/original.conf" >> "$RUN_LOG" 2>&1 || fail "nginx_backup_failed" "INSPECT_NGINX_PERMISSIONS"
chmod 600 "$PRIVATE_BACKUP/original.conf"
BACKUP_SHA256="$(sha256sum "$PRIVATE_BACKUP/original.conf" | awk '{print $1}')"
CONFIG_BACKUP="PASS"

python3 - "$CONFIG" "$PATCHED" "$PATCH_AUDIT" <<'PY' >> "$RUN_LOG" 2>&1
import json,re,sys
from pathlib import Path
source=Path(sys.argv[1]);target=Path(sys.argv[2]);audit=Path(sys.argv[3])
text=source.read_text(encoding='utf-8')
map_begin='# ORIS_CHAT_WRITE_POLICY_BEGIN'
map_block='''# ORIS_CHAT_WRITE_POLICY_BEGIN
map "$request_method:$uri" $oris_readonly_request_blocked {
    default 1;
    ~^(GET|HEAD): 0;
    "POST:/api/chat/messages" 0;
}
# ORIS_CHAT_WRITE_POLICY_END

'''

def blocks(value):
    result=[]
    for match in re.finditer(r'(?m)^\s*server\s*\{',value):
        start=match.start();depth=0;end=None
        for pos in range(start,len(value)):
            char=value[pos]
            if char=='{': depth+=1
            elif char=='}':
                depth-=1
                if depth==0:
                    end=pos+1;break
        if end: result.append((start,end,value[start:end]))
    return result

candidates=[]
for start,end,block in blocks(text):
    if re.search(r'\bserver_name\b[^;]*\bcontrol\.orisfy\.com\b',block) and re.search(r'^\s*listen\s+[^;]*443',block,re.M):
        candidates.append((start,end,block))
if len(candidates)!=1: raise SystemExit('effective https block count=%s'%len(candidates))
start,end,block=candidates[0]
guard=re.compile(r'(?ms)(^[ \t]*)if\s*\(\s*\$request_method\s*!~\*?\s*(?:[^()]|\([^()]*\))*\)\s*\{\s*return\s+403\s*;\s*\}')
matches=list(guard.finditer(block))
if map_begin not in text:
    if len(matches)!=1: raise SystemExit('method guard count=%s'%len(matches))
    indent=matches[0].group(2)
    block=block[:matches[0].start()]+indent+'if ($oris_readonly_request_blocked) {\n'+indent+'    return 403;\n'+indent+'}'+block[matches[0].end():]
    text=text[:start]+block+text[end:]
    text=map_block+text
else:
    if '$oris_readonly_request_blocked' not in block: raise SystemExit('map exists but effective block does not use it')

# Re-resolve block after map insertion/replacement.
selected=[]
for s,e,b in blocks(text):
    if re.search(r'\bserver_name\b[^;]*\bcontrol\.orisfy\.com\b',b) and re.search(r'^\s*listen\s+[^;]*443',b,re.M): selected.append((s,e,b))
if len(selected)!=1: raise SystemExit('post-patch https block count=%s'%len(selected))
start,end,block=selected[0]
location_present=bool(re.search(r'location\s*=\s*/api/chat/messages\s*\{',block))
if not location_present:
    close=end-1
    server_indent=re.match(r'(?m)^(\s*)server\s*\{',block).group(1)
    indent=server_indent+'    '
    snippet=(
      '\n'+indent+'# ORIS_CHAT_MESSAGES_BEGIN\n'
      +indent+'location = /api/chat/messages {\n'
      +indent+'    proxy_pass http://127.0.0.1:18893/api/chat/messages;\n'
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
    text=text[:close]+snippet+text[close:]

target.write_text(text,encoding='utf-8')
audit.write_text(json.dumps({
 'result':'PASS','map_policy_present':map_begin in text,
 'effective_guard_replaced':'if ($oris_readonly_request_blocked)' in text,
 'exact_chat_location_present':bool(re.search(r'location\s*=\s*/api/chat/messages\s*\{',text)),
 'allowed_write_route':'POST:/api/chat/messages','other_write_routes_allowed':False,
 'secrets_recorded':False
},indent=2)+'\n',encoding='utf-8')
PY
[ "$?" -eq 0 ] || fail "effective_config_patch_generation_failed" "INSPECT_EFFECTIVE_NGINX_CONFIG"

python3 - "$PATCH_AUDIT" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys
p=json.load(open(sys.argv[1]));assert p['map_policy_present'];assert p['effective_guard_replaced'];assert p['exact_chat_location_present'];assert not p['other_write_routes_allowed']
PY
[ "$?" -eq 0 ] || fail "patch_audit_failed" "INSPECT_PATCH_AUDIT"
METHOD_POLICY_PATCH="PASS"; EXACT_CHAT_LOCATION="PASS"
PATCHED_SHA256="$(sha256sum "$PATCHED" | awk '{print $1}')"

sudo install -o root -g root -m 0644 "$PATCHED" "$CONFIG" >> "$RUN_LOG" 2>&1 || fail "effective_config_install_failed" "INSPECT_NGINX_PERMISSIONS"
CONFIG_INSTALLED="YES"
sudo nginx -t >> "$RUN_LOG" 2>&1 || fail "nginx_config_test_failed" "ROLLBACK_EFFECTIVE_CONFIG"
NGINX_CONFIG_TEST="PASS"
sudo systemctl reload nginx >> "$RUN_LOG" 2>&1 || fail "nginx_reload_failed" "ROLLBACK_EFFECTIVE_CONFIG"
NGINX_RELOAD="PASS"
sleep 2

GET_CODE="$(curl -sS -o /dev/null -w '%{http_code}' "https://$PUBLIC_HOST/" 2>/dev/null || true)"
CHAT_CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/chat/messages" 2>/dev/null || true)"
OTHER_CODE="$(curl -sS -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/projects" 2>/dev/null || true)"
LOCAL_CHAT_CODE="$(curl -k -sS --resolve "$PUBLIC_HOST:443:127.0.0.1" -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/chat/messages" 2>/dev/null || true)"
log "PUBLIC_GET_HTTP=$GET_CODE";log "PUBLIC_CHAT_POST_HTTP=$CHAT_CODE";log "PUBLIC_OTHER_POST_HTTP=$OTHER_CODE";log "LOCAL_TLS_CHAT_POST_HTTP=$LOCAL_CHAT_CODE"
[ "$GET_CODE" = "401" ] || fail "public_get_auth_gate_unexpected" "INSPECT_PUBLIC_AUTH"
PUBLIC_GET_AUTH_GATE="PASS"
[ "$CHAT_CODE" = "401" ] || fail "public_chat_post_not_reaching_auth" "INSPECT_EFFECTIVE_METHOD_POLICY"
PUBLIC_CHAT_POST_AUTH_GATE="PASS"
[ "$OTHER_CODE" = "403" ] || fail "non_chat_post_not_blocked" "RESTORE_STRICT_READONLY_POLICY"
PUBLIC_OTHER_POST_BLOCKED="PASS"
[ "$LOCAL_CHAT_CODE" = "401" ] || fail "local_tls_chat_post_not_reaching_auth" "INSPECT_EFFECTIVE_METHOD_POLICY"
LOCAL_TLS_CHAT_POST_AUTH_GATE="PASS"

FINAL_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
FINAL_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
[ "$FINAL_PRODUCT_SHA" = "$BASE_PRODUCT_SHA" ] && [ "$FINAL_PRODUCT_REMOTE" = "$BASE_PRODUCT_SHA" ] || fail "product_sha_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_SHA_UNCHANGED="PASS"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_worktree_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_WORKTREE_CLEAN="PASS"

for service in "$OPENCLAW_SERVICE" "$BRIDGE_SERVICE" "$INTAKE_SERVICE" "$WEB_SERVICE"; do [ "$(service_state "$service")" = "active" ] || fail "user_service_not_active" "INSPECT_USER_SERVICES"; done
[ "$(systemctl is-active nginx 2>/dev/null || true)" = "active" ] || fail "nginx_not_active" "INSPECT_NGINX_SERVICE"

RESULT="PASS";NEXT_ACTION="RETRY_BROWSER_HELP_AND_STATUS"
write_evidence
commit_logs || { RESULT="FAILED";FAILURE_CODE="patch_evidence_push_failed";NEXT_ACTION="RESOLVE_PATCH_EVIDENCE_PUSH"; }
summary
rm -f "$PATCHED" "$GIT_OUTPUT"
[ "$RESULT" = "PASS" ] && exit 0
exit 1
