#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
ROLLBACK_SCRIPT="$ORIS_REPO/scripts/dev_employee_native_openclaw_nginx_rollback_20260617.sh"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_PORT="18789"
CONSOLE_PORT="18893"
DOMAIN="control.orisfy.com"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-reject-v2-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/diagnosis.log"
RESULT_JSON="$TMP_ROOT/diagnosis.json"
ROLLBACK_OUTPUT="$TMP_ROOT/rollback.out"
AUTH_JSON="$TMP_ROOT/auth-safe.json"
JOURNAL_RAW="$TMP_ROOT/openclaw-gateway-journal.raw"
JOURNAL_JSON="$TMP_ROOT/journal-safe.json"
CONSOLE_JSON="$TMP_ROOT/console-api.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_rejection"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rejection-v2-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rejection-v2-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
ROLLBACK_RESULT="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_IS_OPENCLAW="unknown"
OPENCLAW_AUTH_MODE="unknown"
TOKEN_CONFIGURED="unknown"
PASSWORD_CONFIGURED="unknown"
PROCESS_SECRET_KEY_COUNT="unknown"
CONFIG_TOKEN_MATCHES_PROCESS_SECRET="unknown"
CONFIG_PASSWORD_MATCHES_PROCESS_SECRET="unknown"
DASHBOARD_NO_OPEN_SUPPORTED="unknown"
RECENT_AUTH_MISMATCH_COUNT="unknown"
RECENT_UNAUTHORIZED_COUNT="unknown"
RECENT_ORIGIN_ERROR_COUNT="unknown"
RECENT_WEBSOCKET_EVENT_COUNT="unknown"
CONSOLE_API_PATH_COUNT="unknown"
CONSOLE_404_PATH_COUNT="unknown"
PRODUCT_BASELINE_PRESERVED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_REJECTION_DIAGNOSIS_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "ROLLBACK_RESULT=$ROLLBACK_RESULT"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_IS_OPENCLAW=$PUBLIC_ROOT_IS_OPENCLAW"
  echo "OPENCLAW_AUTH_MODE=$OPENCLAW_AUTH_MODE"
  echo "TOKEN_CONFIGURED=$TOKEN_CONFIGURED"
  echo "PASSWORD_CONFIGURED=$PASSWORD_CONFIGURED"
  echo "PROCESS_SECRET_KEY_COUNT=$PROCESS_SECRET_KEY_COUNT"
  echo "CONFIG_TOKEN_MATCHES_PROCESS_SECRET=$CONFIG_TOKEN_MATCHES_PROCESS_SECRET"
  echo "CONFIG_PASSWORD_MATCHES_PROCESS_SECRET=$CONFIG_PASSWORD_MATCHES_PROCESS_SECRET"
  echo "DASHBOARD_NO_OPEN_SUPPORTED=$DASHBOARD_NO_OPEN_SUPPORTED"
  echo "RECENT_AUTH_MISMATCH_COUNT=$RECENT_AUTH_MISMATCH_COUNT"
  echo "RECENT_UNAUTHORIZED_COUNT=$RECENT_UNAUTHORIZED_COUNT"
  echo "RECENT_ORIGIN_ERROR_COUNT=$RECENT_ORIGIN_ERROR_COUNT"
  echo "RECENT_WEBSOCKET_EVENT_COUNT=$RECENT_WEBSOCKET_EVENT_COUNT"
  echo "CONSOLE_API_PATH_COUNT=$CONSOLE_API_PATH_COUNT"
  echo "CONSOLE_404_PATH_COUNT=$CONSOLE_404_PATH_COUNT"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "OPENCLAW_SERVICE_RESTARTED=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  summary
  exit 1
}

http_body_status() {
  local url="$1"
  local body="$2"
  curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$body" -w '%{http_code}' "$url" 2>/dev/null || true
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in bash git curl python3 sha256sum systemctl journalctl ss; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$ROLLBACK_SCRIPT" ] || fail_now "rollback_script_missing" "PULL_ORIS_MAIN_AND_RETRY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "INSPECT_OPENCLAW_INSTALLATION"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=ROLLBACK_REJECTED_NATIVE_UI_AND_READ_ONLY_DIAGNOSIS_V2"
log "SECRET_VALUES_RECORDED=NO"
log "CURRENT_TASK_UPDATED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"
log "OPENCLAW_CONFIG_MUTATED=NO"
log "OPENCLAW_SERVICE_RESTARTED=NO"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head_before_rollback" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_before_rollback" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status_before_rollback" "REVIEW_PRODUCT_BASELINE"

PRE_PUBLIC_BODY="$TMP_ROOT/pre-public-root.body"
DIRECT_BODY="$TMP_ROOT/direct-openclaw.body"
PRE_PUBLIC_STATUS="$(http_body_status "https://$DOMAIN/" "$PRE_PUBLIC_BODY")"
DIRECT_STATUS="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' -o "$DIRECT_BODY" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PRE_PUBLIC_SHA="$(sha256sum "$PRE_PUBLIC_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_BODY" 2>/dev/null | awk '{print $1}')"

if [ "$PRE_PUBLIC_STATUS" = "200" ] && [ "$DIRECT_STATUS" = "200" ] && [ -n "$PRE_PUBLIC_SHA" ] && [ "$PRE_PUBLIC_SHA" = "$DIRECT_SHA" ]; then
  if bash "$ROLLBACK_SCRIPT" > "$ROLLBACK_OUTPUT" 2>&1; then
    ROLLBACK_RESULT="ROLLED_BACK"
  else
    python3 - "$ROLLBACK_OUTPUT" <<'PY_ROLLBACK_FAILURE' >> "$RUN_LOG"
import re
import sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(encoding="utf-8",errors="replace")
for line in text.splitlines():
    if re.match(r"^(RESULT|FAILURE_CODE|NGINX_TEST|NGINX_RELOAD|PUBLIC_ROOT_STATUS|NEXT_ACTION)=",line):
        print("ROLLBACK_"+line)
PY_ROLLBACK_FAILURE
    fail_now "nginx_rollback_failed" "READ_ROLLBACK_EVIDENCE_AND_REPAIR_PUBLIC_ROUTE"
  fi
else
  ROLLBACK_RESULT="ALREADY_NOT_OPENCLAW_ROOT"
fi

if [ -s "$ROLLBACK_OUTPUT" ]; then
  python3 - "$ROLLBACK_OUTPUT" <<'PY_ROLLBACK_SUMMARY' >> "$RUN_LOG"
import re
import sys
from pathlib import Path
text=Path(sys.argv[1]).read_text(encoding="utf-8",errors="replace")
for line in text.splitlines():
    if re.match(r"^(RESULT|FAILURE_CODE|BACKUP_FILE|NGINX_TEST|NGINX_RELOAD|PUBLIC_ROOT_STATUS|EVIDENCE_COMMIT|EVIDENCE_REMOTE_VERIFIED|NEXT_ACTION)=",line):
        print("ROLLBACK_"+line)
PY_ROLLBACK_SUMMARY
fi

PUBLIC_BODY="$TMP_ROOT/public-root.body"
PUBLIC_ROOT_STATUS="$(http_body_status "https://$DOMAIN/" "$PUBLIC_BODY")"
PUBLIC_SHA="$(sha256sum "$PUBLIC_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA_AFTER="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null | sha256sum | awk '{print $1}')"
if [ -n "$PUBLIC_SHA" ] && [ "$PUBLIC_SHA" = "$DIRECT_SHA_AFTER" ]; then
  PUBLIC_ROOT_IS_OPENCLAW="YES"
else
  PUBLIC_ROOT_IS_OPENCLAW="NO"
fi
log "ROLLBACK_RESULT=$ROLLBACK_RESULT"
log "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
log "PUBLIC_ROOT_IS_OPENCLAW=$PUBLIC_ROOT_IS_OPENCLAW"
[ "$PUBLIC_ROOT_IS_OPENCLAW" = "NO" ] || fail_now "rollback_did_not_remove_openclaw_from_root" "INSPECT_EFFECTIVE_NGINX_CONFIG"
case "$PUBLIC_ROOT_STATUS" in
  200|301|302|401|403) ;;
  *) fail_now "public_root_unhealthy_after_rollback" "INSPECT_EFFECTIVE_NGINX_CONFIG" ;;
esac

OPENCLAW_PID="$(systemctl --user show openclaw-gateway.service -p MainPID --value 2>/dev/null || true)"
python3 - "$OPENCLAW_CONFIG" "$OPENCLAW_PID" "$AUTH_JSON" <<'PY_AUTH_SAFE'
import hashlib
import json
import sys
from pathlib import Path

source=Path(sys.argv[1])
pid=sys.argv[2]
out=Path(sys.argv[3])
data=json.loads(source.read_text(encoding="utf-8"))

def get_path(root,path):
    value=root
    for part in path:
        if not isinstance(value,dict) or part not in value:
            return None
        value=value[part]
    return value

auth=get_path(data,["gateway","auth"])
if not isinstance(auth,dict):
    auth=get_path(data,["auth"])
if not isinstance(auth,dict):
    auth={}

mode=auth.get("mode") if isinstance(auth.get("mode"),str) else "unknown"
config_token=auth.get("token") if isinstance(auth.get("token"),str) else None
config_password=auth.get("password") if isinstance(auth.get("password"),str) else None

env={}
if pid.isdigit() and int(pid)>0:
    p=Path("/proc")/pid/"environ"
    try:
        raw=p.read_bytes()
        for item in raw.split(b"\0"):
            if b"=" not in item:
                continue
            key,value=item.split(b"=",1)
            env[key.decode("utf-8","replace")]=value.decode("utf-8","replace")
    except Exception:
        pass

secret_env={}
for key,value in env.items():
    upper=key.upper()
    if "OPENCLAW" in upper and any(word in upper for word in ("TOKEN","PASSWORD","SECRET","CREDENTIAL")):
        secret_env[key]=value

def matches_any(config_value):
    if not config_value:
        return None
    values=[v for v in secret_env.values() if v]
    if not values:
        return None
    return any(config_value==v for v in values)

control_ui=get_path(data,["gateway","controlUi"])
if not isinstance(control_ui,dict):
    control_ui=get_path(data,["controlUi"])
if not isinstance(control_ui,dict):
    control_ui={}
allowed=control_ui.get("allowedOrigins")
allowed_count=len(allowed) if isinstance(allowed,list) else 0

payload={
    "config_path":str(source),
    "config_mode":"0o%o"%(source.stat().st_mode & 0o777),
    "auth_mode":mode,
    "token_configured":bool(config_token),
    "password_configured":bool(config_password),
    "process_secret_key_names":sorted(secret_env),
    "process_secret_key_count":len(secret_env),
    "config_token_matches_any_process_secret":matches_any(config_token),
    "config_password_matches_any_process_secret":matches_any(config_password),
    "allowed_origin_count":allowed_count,
    "allow_insecure_auth_configured":isinstance(control_ui.get("allowInsecureAuth"),bool),
    "allow_insecure_auth_enabled":control_ui.get("allowInsecureAuth") is True,
    "secret_values_recorded":False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_AUTH_SAFE
[ "$?" -eq 0 ] || fail_now "openclaw_auth_safe_analysis_failed" "INSPECT_OPENCLAW_CONFIG_FORMAT"

OPENCLAW_AUTH_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["auth_mode"])' "$AUTH_JSON")"
TOKEN_CONFIGURED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["token_configured"] else "NO")' "$AUTH_JSON")"
PASSWORD_CONFIGURED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["password_configured"] else "NO")' "$AUTH_JSON")"
PROCESS_SECRET_KEY_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["process_secret_key_count"])' "$AUTH_JSON")"
CONFIG_TOKEN_MATCHES_PROCESS_SECRET="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["config_token_matches_any_process_secret"]; print("NOT_APPLICABLE" if v is None else ("YES" if v else "NO"))' "$AUTH_JSON")"
CONFIG_PASSWORD_MATCHES_PROCESS_SECRET="$(python3 -c 'import json,sys; v=json.load(open(sys.argv[1]))["config_password_matches_any_process_secret"]; print("NOT_APPLICABLE" if v is None else ("YES" if v else "NO"))' "$AUTH_JSON")"
python3 -m json.tool "$AUTH_JSON" >> "$RUN_LOG" 2>/dev/null || true

OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
if [ -n "$OPENCLAW_BIN" ] && "$OPENCLAW_BIN" dashboard --help 2>&1 | grep -q -- '--no-open'; then
  DASHBOARD_NO_OPEN_SUPPORTED="YES"
elif [ -n "$OPENCLAW_BIN" ]; then
  DASHBOARD_NO_OPEN_SUPPORTED="NO"
else
  DASHBOARD_NO_OPEN_SUPPORTED="NO_BINARY"
fi
log "DASHBOARD_NO_OPEN_SUPPORTED=$DASHBOARD_NO_OPEN_SUPPORTED"

journalctl --user -u openclaw-gateway.service --since "3 hours ago" -n 800 --no-pager > "$JOURNAL_RAW" 2>/dev/null || true
python3 - "$JOURNAL_RAW" "$JOURNAL_JSON" <<'PY_JOURNAL_SAFE'
import json
import re
import sys
from pathlib import Path

source=Path(sys.argv[1])
out=Path(sys.argv[2])
counts={"auth_mismatch":0,"unauthorized":0,"forbidden":0,"origin":0,"websocket":0}
patterns={
    "auth_mismatch":re.compile(r"auth(?:entication)?[^\n]{0,100}mismatch|credential[^\n]{0,100}(?:reject|mismatch)|invalid[^\n]{0,60}(?:token|password|credential)",re.I),
    "unauthorized":re.compile(r"unauthori[sz]ed|\b401\b",re.I),
    "forbidden":re.compile(r"forbidden|\b403\b",re.I),
    "origin":re.compile(r"origin[^\n]{0,100}(?:reject|deny|not allowed|invalid)|allowedOrigins",re.I),
    "websocket":re.compile(r"websocket|\bupgrade\b|\bwss?://",re.I),
}
secret=re.compile(r"(?i)(token|password|secret|authorization|credential)(\s*[=:]\s*|\s+)([^\s,;]+)")
long_id=re.compile(r"\b[a-f0-9]{24,}\b",re.I)
url_query=re.compile(r"(https?://[^\s?]+)\?[^\s]+")
events=[]
text=source.read_text(encoding="utf-8",errors="replace") if source.exists() else ""
for raw in text.splitlines():
    classes=[]
    for name,pattern in patterns.items():
        if pattern.search(raw):
            counts[name]+=1
            classes.append(name)
    if not classes:
        continue
    line=secret.sub(r"\1\2<redacted>",raw)
    line=long_id.sub("<redacted-id>",line)
    line=url_query.sub(r"\1?<redacted-query>",line)
    events.append({"classes":classes,"message":line[:500]})
out.write_text(json.dumps({"counts":counts,"events":events[-120:],"secret_values_recorded":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_JOURNAL_SAFE
[ "$?" -eq 0 ] || fail_now "gateway_journal_safe_analysis_failed" "INSPECT_GATEWAY_JOURNAL_ACCESS"
RECENT_AUTH_MISMATCH_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["auth_mismatch"])' "$JOURNAL_JSON")"
RECENT_UNAUTHORIZED_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["unauthorized"])' "$JOURNAL_JSON")"
RECENT_ORIGIN_ERROR_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["origin"])' "$JOURNAL_JSON")"
RECENT_WEBSOCKET_EVENT_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["counts"]["websocket"])' "$JOURNAL_JSON")"
python3 -m json.tool "$JOURNAL_JSON" >> "$RUN_LOG" 2>/dev/null || true

CONSOLE_ROOT="$TMP_ROOT/console-root.html"
curl -sS --max-time 10 "http://127.0.0.1:$CONSOLE_PORT/" -o "$CONSOLE_ROOT" 2>/dev/null || true
python3 - "$CONSOLE_ROOT" "$CONSOLE_PORT" "$CONSOLE_JSON" "$TMP_ROOT" <<'PY_CONSOLE_SAFE'
import html.parser
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urljoin,urlsplit

root=Path(sys.argv[1])
port=sys.argv[2]
out=Path(sys.argv[3])
tmp=Path(sys.argv[4])

class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        for key in ("src","href"):
            value=data.get(key)
            if value and value not in self.assets:
                self.assets.append(value)

text=root.read_text(encoding="utf-8",errors="replace") if root.exists() else ""
parser=Parser()
try:
    parser.feed(text)
except Exception:
    pass
parts=[text]
assets=[]
for index,asset in enumerate(parser.assets[:40]):
    url=urljoin(f"http://127.0.0.1:{port}/",asset)
    parsed=urlsplit(url)
    if parsed.hostname not in ("127.0.0.1","localhost"):
        continue
    if str(parsed.port or port)!=str(port):
        continue
    target=tmp/f"console-asset-{index}.body"
    try:
        process=subprocess.run(["curl","-sS","--max-time","10",url,"-o",str(target)],timeout=15)
        if process.returncode==0 and target.exists() and target.stat().st_size<=6_000_000:
            parts.append(target.read_text(encoding="utf-8",errors="replace"))
            assets.append(parsed.path)
    except Exception:
        pass
joined="\n".join(parts)
paths=set()
patterns=[
    r"[\"'`](/api/[A-Za-z0-9_./:-]{1,180})[?\"'`]",
    r"fetch\(\s*[\"'`](/[^\"'`]{1,180})[\"'`]",
]
for pattern in patterns:
    for match in re.findall(pattern,joined):
        if match.startswith("/api/"):
            paths.add(match.split("?",1)[0].rstrip("/"))
results=[]
for path in sorted(paths):
    try:
        process=subprocess.run(["curl","-sS","--max-time","5","-o","/dev/null","-w","%{http_code}",f"http://127.0.0.1:{port}{path}"],text=True,capture_output=True,timeout=10)
        status=process.stdout.strip() or "000"
    except Exception:
        status="000"
    results.append({"path":path,"get_status":status})
payload={
    "assets_scanned":assets,
    "api_paths":results,
    "path_count":len(results),
    "status_404_count":sum(1 for item in results if item["get_status"]=="404"),
    "secret_values_recorded":False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_CONSOLE_SAFE
[ "$?" -eq 0 ] || fail_now "console_api_safe_analysis_failed" "INSPECT_CONSOLE_ASSETS"
CONSOLE_API_PATH_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["path_count"])' "$CONSOLE_JSON")"
CONSOLE_404_PATH_COUNT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status_404_count"])' "$CONSOLE_JSON")"
python3 -m json.tool "$CONSOLE_JSON" >> "$RUN_LOG" 2>/dev/null || true

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
else
  fail_now "product_baseline_changed_during_rejection_handling" "RESTORE_PRODUCT_BASELINE"
fi

RESULT="ROLLED_BACK_AND_DIAGNOSED"
NEXT_ACTION="READ_REJECTION_EVIDENCE_AND_BUILD_CREDENTIAL_ROTATION_AND_ROUTING_V2"

export TASK_ID STAMP RESULT FAILURE_CODE ROLLBACK_RESULT PUBLIC_ROOT_STATUS PUBLIC_ROOT_IS_OPENCLAW OPENCLAW_AUTH_MODE TOKEN_CONFIGURED PASSWORD_CONFIGURED PROCESS_SECRET_KEY_COUNT CONFIG_TOKEN_MATCHES_PROCESS_SECRET CONFIG_PASSWORD_MATCHES_PROCESS_SECRET DASHBOARD_NO_OPEN_SUPPORTED RECENT_AUTH_MISMATCH_COUNT RECENT_UNAUTHORIZED_COUNT RECENT_ORIGIN_ERROR_COUNT RECENT_WEBSOCKET_EVENT_COUNT CONSOLE_API_PATH_COUNT CONSOLE_404_PATH_COUNT PRODUCT_BASELINE_PRESERVED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$AUTH_JSON" "$JOURNAL_JSON" "$CONSOLE_JSON" "$RESULT_JSON" <<'PY_RESULT'
import json
import os
import sys
from pathlib import Path

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

payload={
    "task_id":os.environ.get("TASK_ID"),
    "checked_at":os.environ.get("STAMP"),
    "result":os.environ.get("RESULT"),
    "failure_code":os.environ.get("FAILURE_CODE"),
    "rollback_result":os.environ.get("ROLLBACK_RESULT"),
    "public":{
        "root_status":os.environ.get("PUBLIC_ROOT_STATUS"),
        "root_is_openclaw":os.environ.get("PUBLIC_ROOT_IS_OPENCLAW")=="YES",
    },
    "openclaw_auth":load(sys.argv[1]),
    "recent_gateway_events":load(sys.argv[2]),
    "console_api_discovery":load(sys.argv[3]),
    "safety":{
        "product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES",
        "current_task_updated":False,
        "product_task_submitted":False,
        "product_repository_mutated":False,
        "openclaw_config_mutated":False,
        "openclaw_service_restarted":False,
        "secret_values_recorded":False,
    },
    "next_action":os.environ.get("NEXT_ACTION"),
    "evidence":{
        "log_path":os.environ.get("EVIDENCE_LOG_REL"),
        "json_path":os.environ.get("EVIDENCE_JSON_REL"),
        "self_commit_sha_omitted_to_prevent_post_commit_log_drift":True,
    },
}
Path(sys.argv[4]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re
import sys
from pathlib import Path
patterns=[
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)(token|password|secret|authorization|credential)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b|configured\b|unknown\b|token\b|password\b)[A-Za-z0-9._~+/-]{12,}"),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding="utf-8",errors="replace")
    if any(pattern.search(text) for pattern in patterns):
        raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then
  SECRET_SCAN="PASS"
else
  fail_now "diagnosis_evidence_secret_scan_failed" "REPAIR_DIAGNOSIS_REDACTION"
fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json
import sys
from pathlib import Path
source_log,target_log,source_json,target_json=map(Path,sys.argv[1:])
lines=[line.rstrip(" \t\r") for line in source_log.read_text(encoding="utf-8",errors="replace").splitlines()]
target_log.write_text("\n".join(lines)+"\n",encoding="utf-8")
payload=json.loads(source_json.read_text(encoding="utf-8"))
target_json.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_REJECTION_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw rejection diagnosis v2 $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then
  EVIDENCE_REMOTE_VERIFIED="YES"
else
  RESULT="FAILED"
  FAILURE_CODE="evidence_remote_sha_mismatch"
  NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"
fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
