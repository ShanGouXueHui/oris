#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="inspect-effective-public-nginx-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/inspect-effective-nginx-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/inspect-effective-nginx-$STAMP.json"
NGINX_RAW="/tmp/oris-nginx-effective-$STAMP.txt"
PARSED_JSON="$LOG_DIR/effective-nginx-routes-$STAMP.json"
PUBLIC_HEADERS="/tmp/oris-public-post-headers-$STAMP.txt"
LOCAL_TLS_HEADERS="/tmp/oris-local-tls-post-headers-$STAMP.txt"
LOCAL_HTTP_HEADERS="/tmp/oris-local-http-post-headers-$STAMP.txt"
GIT_OUTPUT="/tmp/oris-effective-nginx-git-$STAMP.log"
PUBLIC_HOST="control.orisfy.com"

RESULT="FAILED"
NGINX_DUMP="NOT_RUN"
MATCHING_SERVER_BLOCKS="0"
EFFECTIVE_HTTPS_CONFIG=""
EFFECTIVE_HTTP_CONFIG=""
DUPLICATE_HTTPS_COUNT="0"
DUPLICATE_HTTP_COUNT="0"
METHOD_GUARD_LOCATIONS="0"
PUBLIC_POST_HTTP="000"
LOCAL_TLS_POST_HTTP="000"
LOCAL_HTTP_POST_HTTP="000"
DIRECT_APP_POST_HTTP="000"
EDGE_BYPASS_CONCLUSION="unknown"
SERVICES_CHANGED="NO"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_EFFECTIVE_NGINX_EVIDENCE"

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

log() { printf '%s\n' "$*" | tee -a "$RUN_LOG"; }

write_evidence() {
  python3 - "$EVIDENCE_JSON" "$PARSED_JSON" <<PY
import json
import os
import sys
parsed={}
if os.path.isfile(sys.argv[2]):
    parsed=json.load(open(sys.argv[2],encoding='utf-8'))
payload={
  'task_id':'$TASK_ID',
  'checked_at':'$(date -Is)',
  'result':'$RESULT',
  'failure_code':'$FAILURE_CODE' or None,
  'nginx_dump':'$NGINX_DUMP',
  'matching_server_blocks':int('$MATCHING_SERVER_BLOCKS'),
  'effective_https_config':'$EFFECTIVE_HTTPS_CONFIG' or None,
  'effective_http_config':'$EFFECTIVE_HTTP_CONFIG' or None,
  'duplicate_https_count':int('$DUPLICATE_HTTPS_COUNT'),
  'duplicate_http_count':int('$DUPLICATE_HTTP_COUNT'),
  'method_guard_locations':int('$METHOD_GUARD_LOCATIONS'),
  'public_post_http':'$PUBLIC_POST_HTTP',
  'local_tls_post_http':'$LOCAL_TLS_POST_HTTP',
  'local_http_post_http':'$LOCAL_HTTP_POST_HTTP',
  'direct_app_post_http':'$DIRECT_APP_POST_HTTP',
  'edge_bypass_conclusion':'$EDGE_BYPASS_CONCLUSION',
  'parsed_routes':parsed,
  'services_changed':False,
  'real_product_task_submitted':False,
  'real_product_change':False,
  'next_action':'$NEXT_ACTION'
}
open(sys.argv[1],'w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" "${PARSED_JSON#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_ADD_FAILED"; return 1; }
  git commit --only -m "chore(dev-employee): record effective Nginx inspection $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_COMMIT_FAILED"; return 1; }
  git push origin main > "$GIT_OUTPUT" 2>&1 || { LOG_COMMIT="LOG_PUSH_FAILED"; return 1; }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "NGINX_DUMP=$NGINX_DUMP"
  echo "MATCHING_SERVER_BLOCKS=$MATCHING_SERVER_BLOCKS"
  echo "EFFECTIVE_HTTPS_CONFIG=$EFFECTIVE_HTTPS_CONFIG"
  echo "EFFECTIVE_HTTP_CONFIG=$EFFECTIVE_HTTP_CONFIG"
  echo "DUPLICATE_HTTPS_COUNT=$DUPLICATE_HTTPS_COUNT"
  echo "DUPLICATE_HTTP_COUNT=$DUPLICATE_HTTP_COUNT"
  echo "METHOD_GUARD_LOCATIONS=$METHOD_GUARD_LOCATIONS"
  echo "PUBLIC_POST_HTTP=$PUBLIC_POST_HTTP"
  echo "LOCAL_TLS_POST_HTTP=$LOCAL_TLS_POST_HTTP"
  echo "LOCAL_HTTP_POST_HTTP=$LOCAL_HTTP_POST_HTTP"
  echo "DIRECT_APP_POST_HTTP=$DIRECT_APP_POST_HTTP"
  echo "EDGE_BYPASS_CONCLUSION=$EDGE_BYPASS_CONCLUSION"
  echo "SERVICES_CHANGED=$SERVICES_CHANGED"
  echo "FAILURE_CODE=$FAILURE_CODE"
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
  write_evidence
  commit_logs || true
  summary
  rm -f "$NGINX_RAW" "$PUBLIC_HEADERS" "$LOCAL_TLS_HEADERS" "$LOCAL_HTTP_HEADERS" "$GIT_OUTPUT"
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_ORIS_GIT_STATE"
git restore --source=HEAD --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_worktree_sync_failed" "INSPECT_ORIS_GIT_STATE"

sudo nginx -T > "$NGINX_RAW" 2>> "$RUN_LOG" || fail "nginx_dump_failed" "INSPECT_NGINX_CONFIGURATION"
NGINX_DUMP="PASS"

python3 - "$NGINX_RAW" "$PARSED_JSON" <<'PY' >> "$RUN_LOG" 2>&1
import json
import re
import sys
from pathlib import Path

raw=Path(sys.argv[1]).read_text(encoding='utf-8',errors='replace')
lines=raw.splitlines()
current_file='unknown'
file_for_line=[]
for line in lines:
    match=re.match(r'# configuration file (.+):$',line)
    if match:
        current_file=match.group(1)
    file_for_line.append(current_file)

blocks=[]
for index,line in enumerate(lines):
    if not re.match(r'^\s*server\s*\{',line.split('#',1)[0]):
        continue
    depth=0
    end=None
    for cursor in range(index,len(lines)):
        clean=lines[cursor].split('#',1)[0]
        depth += clean.count('{')-clean.count('}')
        if depth==0 and cursor>index:
            end=cursor
            break
    if end is None:
        continue
    block='\n'.join(lines[index:end+1])
    if not re.search(r'\bserver_name\b[^;]*\bcontrol\.orisfy\.com\b',block):
        continue
    listens=[]
    for value in re.findall(r'^\s*listen\s+([^;]+);',block,re.M):
        listens.append(re.sub(r'\s+',' ',value.strip()))
    locations=[]
    for match in re.finditer(r'^\s*location\s+([^\{]+)\{',block,re.M):
        locations.append(re.sub(r'\s+',' ',match.group(1).strip()))
    proxy_pass=re.findall(r'^\s*proxy_pass\s+([^;]+);',block,re.M)
    includes=re.findall(r'^\s*include\s+([^;]+);',block,re.M)
    auth_basic=bool(re.search(r'^\s*auth_basic\s+',block,re.M))
    guards=[]
    for pattern,label in [
        (r'limit_except\s+[^\{]+\{','limit_except'),
        (r'\$request_method','request_method_if'),
        (r'\bdeny\s+all\s*;','deny_all'),
        (r'\breturn\s+403\s*;','return_403'),
    ]:
        if re.search(pattern,block,re.I): guards.append(label)
    blocks.append({
        'order':len(blocks)+1,
        'config_file':file_for_line[index],
        'start_line_in_dump':index+1,
        'listens':listens,
        'locations':locations,
        'proxy_pass':proxy_pass,
        'includes':includes,
        'auth_basic_present':auth_basic,
        'method_guards':guards,
    })

https=[b for b in blocks if any('443' in item for item in b['listens'])]
http=[b for b in blocks if any(re.search(r'(^|:)80(?:\s|$)',item) for item in b['listens'])]
result={
    'result':'PASS',
    'matching_server_blocks':len(blocks),
    'effective_https':https[0] if https else None,
    'effective_http':http[0] if http else None,
    'duplicate_https_count':max(0,len(https)-1),
    'duplicate_http_count':max(0,len(http)-1),
    'all_blocks':blocks,
    'secret_values_recorded':False,
}
Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MATCHING_SERVER_BLOCKS=%s' % len(blocks))
print('EFFECTIVE_HTTPS_CONFIG=%s' % ((https[0]['config_file']) if https else ''))
print('EFFECTIVE_HTTP_CONFIG=%s' % ((http[0]['config_file']) if http else ''))
print('DUPLICATE_HTTPS_COUNT=%s' % max(0,len(https)-1))
print('DUPLICATE_HTTP_COUNT=%s' % max(0,len(http)-1))
print('METHOD_GUARD_LOCATIONS=%s' % sum(1 for b in blocks if b['method_guards']))
PY
[ "$?" -eq 0 ] || fail "nginx_dump_parse_failed" "INSPECT_NGINX_DUMP"

MATCHING_SERVER_BLOCKS="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["matching_server_blocks"])' "$PARSED_JSON")"
EFFECTIVE_HTTPS_CONFIG="$(python3 -c 'import json,sys;p=json.load(open(sys.argv[1]));print((p.get("effective_https") or {}).get("config_file") or "")' "$PARSED_JSON")"
EFFECTIVE_HTTP_CONFIG="$(python3 -c 'import json,sys;p=json.load(open(sys.argv[1]));print((p.get("effective_http") or {}).get("config_file") or "")' "$PARSED_JSON")"
DUPLICATE_HTTPS_COUNT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["duplicate_https_count"])' "$PARSED_JSON")"
DUPLICATE_HTTP_COUNT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["duplicate_http_count"])' "$PARSED_JSON")"
METHOD_GUARD_LOCATIONS="$(python3 -c 'import json,sys;print(sum(1 for b in json.load(open(sys.argv[1]))["all_blocks"] if b["method_guards"]))' "$PARSED_JSON")"

PUBLIC_POST_HTTP="$(curl -sS -D "$PUBLIC_HEADERS" -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/chat/messages" 2>/dev/null || true)"
LOCAL_TLS_POST_HTTP="$(curl -k -sS --resolve "$PUBLIC_HOST:443:127.0.0.1" -D "$LOCAL_TLS_HEADERS" -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "https://$PUBLIC_HOST/api/chat/messages" 2>/dev/null || true)"
LOCAL_HTTP_POST_HTTP="$(curl -sS -H "Host: $PUBLIC_HOST" -D "$LOCAL_HTTP_HEADERS" -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "http://127.0.0.1/api/chat/messages" 2>/dev/null || true)"
DIRECT_APP_POST_HTTP="$(curl -sS -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' --data '{}' "http://127.0.0.1:18893/api/chat/messages" 2>/dev/null || true)"

log "PUBLIC_POST_HTTP=$PUBLIC_POST_HTTP"
log "LOCAL_TLS_POST_HTTP=$LOCAL_TLS_POST_HTTP"
log "LOCAL_HTTP_POST_HTTP=$LOCAL_HTTP_POST_HTTP"
log "DIRECT_APP_POST_HTTP=$DIRECT_APP_POST_HTTP"

if [ "$PUBLIC_POST_HTTP" = "$LOCAL_TLS_POST_HTTP" ]; then
  EDGE_BYPASS_CONCLUSION="same_result_public_and_local_tls"
else
  EDGE_BYPASS_CONCLUSION="public_edge_differs_from_local_tls"
fi

RESULT="PASS"
if [ -n "$EFFECTIVE_HTTPS_CONFIG" ]; then
  NEXT_ACTION="PATCH_EFFECTIVE_HTTPS_SERVER_ONLY"
else
  NEXT_ACTION="REPAIR_NGINX_SERVER_DISCOVERY"
fi
write_evidence
commit_logs || { RESULT="FAILED"; FAILURE_CODE="inspection_evidence_push_failed"; NEXT_ACTION="RESOLVE_INSPECTION_EVIDENCE_PUSH"; }
summary
rm -f "$NGINX_RAW" "$PUBLIC_HEADERS" "$LOCAL_TLS_HEADERS" "$LOCAL_HTTP_HEADERS" "$GIT_OUTPUT"
[ "$RESULT" = "PASS" ] && exit 0
exit 1
