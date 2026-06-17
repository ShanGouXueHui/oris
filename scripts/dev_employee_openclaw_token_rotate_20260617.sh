#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_SERVICE="openclaw-gateway.service"
OPENCLAW_PORT="18789"
DOMAIN="control.orisfy.com"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
PRIVATE_DIR="$HOME/.openclaw/private"
BACKUP_DIR="$HOME/.openclaw/backups"
DASHBOARD_URL_FILE="$PRIVATE_DIR/control-orisfy-dashboard-url-current.txt"
BACKUP_FILE="$BACKUP_DIR/openclaw.json.before-token-rotation-$STAMP.bak"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-token-rotation-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/rotation.log"
RESULT_JSON="$TMP_ROOT/rotation.json"
DASHBOARD_RAW="$TMP_ROOT/dashboard.raw"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_credential_rotation"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-token-rotation-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-token-rotation-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
TOKEN_ROTATED="NO"
CONFIG_MODE="unknown"
SERVICE_RESTART="NOT_RUN"
SERVICE_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_IS_OPENCLAW="unknown"
DASHBOARD_URL_GENERATED="NO"
DASHBOARD_URL_MATCHES_CONFIG="NO"
PRODUCT_BASELINE_PRESERVED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_TOKEN_ROTATION_FAILURE"

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
  echo "TOKEN_ROTATED=$TOKEN_ROTATED"
  echo "CONFIG_MODE=$CONFIG_MODE"
  echo "SERVICE_RESTART=$SERVICE_RESTART"
  echo "SERVICE_STATE=$SERVICE_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_IS_OPENCLAW=$PUBLIC_ROOT_IS_OPENCLAW"
  echo "DASHBOARD_URL_GENERATED=$DASHBOARD_URL_GENERATED"
  echo "DASHBOARD_URL_MATCHES_CONFIG=$DASHBOARD_URL_MATCHES_CONFIG"
  echo "DASHBOARD_URL_FILE=$DASHBOARD_URL_FILE"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
  echo "NGINX_CHANGED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
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

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in git curl python3 sha256sum systemctl ss; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "INSPECT_OPENCLAW_INSTALLATION"

OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
[ -n "$OPENCLAW_BIN" ] || fail_now "openclaw_binary_missing" "RESTORE_EXISTING_OPENCLAW_BINARY"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=SAFE_OPENCLAW_TOKEN_ROTATION"
log "OPENCLAW_CONFIG=$OPENCLAW_CONFIG"
log "OPENCLAW_SERVICE=$OPENCLAW_SERVICE"
log "SECRET_VALUES_RECORDED=NO"
log "OPENCLAW_REINSTALLED_OR_UPGRADED=NO"
log "NGINX_CHANGED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"

[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status" "REVIEW_PRODUCT_BASELINE"

PUBLIC_BEFORE="$TMP_ROOT/public-before.body"
DIRECT_BEFORE="$TMP_ROOT/direct-before.body"
PUBLIC_BEFORE_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_BEFORE" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
DIRECT_BEFORE_STATUS="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' -o "$DIRECT_BEFORE" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PUBLIC_BEFORE_SHA="$(sha256sum "$PUBLIC_BEFORE" 2>/dev/null | awk '{print $1}')"
DIRECT_BEFORE_SHA="$(sha256sum "$DIRECT_BEFORE" 2>/dev/null | awk '{print $1}')"
if [ "$PUBLIC_BEFORE_STATUS" = "200" ] && [ "$DIRECT_BEFORE_STATUS" = "200" ] && [ -n "$PUBLIC_BEFORE_SHA" ] && [ "$PUBLIC_BEFORE_SHA" = "$DIRECT_BEFORE_SHA" ]; then
  fail_now "public_root_unexpectedly_openclaw_before_rotation" "ROLL_BACK_NGINX_BEFORE_ROTATING_CREDENTIAL"
fi

mkdir -p "$PRIVATE_DIR" "$BACKUP_DIR" || fail_now "private_directory_create_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 700 "$PRIVATE_DIR" "$BACKUP_DIR" || fail_now "private_directory_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
cp "$OPENCLAW_CONFIG" "$BACKUP_FILE" || fail_now "openclaw_config_backup_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 600 "$BACKUP_FILE" || fail_now "openclaw_config_backup_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
log "CONFIG_BACKUP_FILE=$BACKUP_FILE"

python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/rotation-safe.json" <<'PY_ROTATE'
import hashlib
import json
import os
import secrets
import stat
import sys
from pathlib import Path

config_path=Path(sys.argv[1])
out_path=Path(sys.argv[2])
data=json.loads(config_path.read_text(encoding="utf-8"))

gateway=data.get("gateway")
if not isinstance(gateway,dict):
    raise SystemExit("gateway object missing")
auth=gateway.get("auth")
if not isinstance(auth,dict):
    raise SystemExit("gateway.auth object missing")
mode=auth.get("mode")
old_token=auth.get("token")
if mode != "token":
    raise SystemExit("gateway.auth.mode is not token")
if not isinstance(old_token,str) or not old_token:
    raise SystemExit("gateway.auth.token missing")

new_token=secrets.token_hex(32)
while new_token == old_token:
    new_token=secrets.token_hex(32)
auth["token"]=new_token

temporary=config_path.with_name(config_path.name+".rotation.tmp")
temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
os.chmod(temporary,0o600)
json.loads(temporary.read_text(encoding="utf-8"))
os.replace(temporary,config_path)
os.chmod(config_path,0o600)

payload={
    "mode":mode,
    "old_token_sha256":hashlib.sha256(old_token.encode()).hexdigest(),
    "new_token_sha256":hashlib.sha256(new_token.encode()).hexdigest(),
    "token_changed":old_token != new_token,
    "config_mode":"0o%o"%stat.S_IMODE(config_path.stat().st_mode),
    "secret_values_recorded":False,
}
out_path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_ROTATE
ROTATE_RC="$?"
if [ "$ROTATE_RC" -ne 0 ]; then
  fail_now "openclaw_token_rotation_failed" "INSPECT_OPENCLAW_CONFIG_STRUCTURE"
fi

TOKEN_ROTATED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["token_changed"] else "NO")' "$TMP_ROOT/rotation-safe.json")"
CONFIG_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["config_mode"])' "$TMP_ROOT/rotation-safe.json")"
[ "$TOKEN_ROTATED" = "YES" ] || fail_now "token_did_not_change" "INSPECT_TOKEN_GENERATION"
[ "$CONFIG_MODE" = "0o600" ] || fail_now "openclaw_config_permissions_not_0600" "RESTORE_OPENCLAW_CONFIG_PERMISSIONS"

if systemctl --user restart "$OPENCLAW_SERVICE" >> "$RUN_LOG" 2>&1; then
  SERVICE_RESTART="PASS"
else
  SERVICE_RESTART="FAILED"
  fail_now "openclaw_gateway_restart_failed" "INSPECT_OPENCLAW_SERVICE_LOGS_WITH_NEW_TOKEN_RETAINED"
fi

for attempt in 1 2 3 4 5 6 7 8 9 10; do
  SERVICE_STATE="$(systemctl --user is-active "$OPENCLAW_SERVICE" 2>/dev/null || true)"
  DIRECT_ROOT_STATUS="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
  if [ "$SERVICE_STATE" = "active" ] && [ "$DIRECT_ROOT_STATUS" = "200" ]; then
    break
  fi
  sleep 1
done
log "SERVICE_STATE=$SERVICE_STATE"
log "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
[ "$SERVICE_STATE" = "active" ] || fail_now "openclaw_gateway_not_active_after_rotation" "INSPECT_OPENCLAW_SERVICE_LOGS_WITH_NEW_TOKEN_RETAINED"
[ "$DIRECT_ROOT_STATUS" = "200" ] || fail_now "openclaw_root_unhealthy_after_rotation" "INSPECT_OPENCLAW_SERVICE_LOGS_WITH_NEW_TOKEN_RETAINED"

"$OPENCLAW_BIN" dashboard --no-open > "$DASHBOARD_RAW" 2>&1
DASHBOARD_RC="$?"
[ "$DASHBOARD_RC" -eq 0 ] || fail_now "openclaw_dashboard_url_generation_failed" "INSPECT_OPENCLAW_DASHBOARD_HELP"

python3 - "$DASHBOARD_RAW" "$OPENCLAW_CONFIG" "$DASHBOARD_URL_FILE" "$DOMAIN" "$TMP_ROOT/dashboard-safe.json" <<'PY_DASHBOARD'
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,urlunsplit

raw_path=Path(sys.argv[1])
config_path=Path(sys.argv[2])
out_path=Path(sys.argv[3])
domain=sys.argv[4]
safe_path=Path(sys.argv[5])
raw=raw_path.read_text(encoding="utf-8",errors="replace")
raw=re.sub(r"\x1b\[[0-9;]*[A-Za-z]","",raw)
urls=re.findall(r"https?://[^\s<>]+",raw)
if not urls:
    raise SystemExit("dashboard URL not found")
selected=None
for candidate in urls:
    if "token" in candidate.lower() or "auth" in candidate.lower():
        selected=candidate.rstrip(".,;)")
        break
if selected is None:
    selected=urls[0].rstrip(".,;)")
parsed=urlsplit(selected)
public_url=urlunsplit(("https",domain,parsed.path or "/",parsed.query,parsed.fragment))
config=json.loads(config_path.read_text(encoding="utf-8"))
token=config.get("gateway",{}).get("auth",{}).get("token")
if not isinstance(token,str) or not token:
    raise SystemExit("config token missing")

candidate_values=[]
query=parse_qs(parsed.query,keep_blank_values=True)
for key,values in query.items():
    if "token" in key.lower():
        candidate_values.extend(values)
fragment_query=parse_qs(parsed.fragment,keep_blank_values=True)
for key,values in fragment_query.items():
    if "token" in key.lower():
        candidate_values.extend(values)
for match in re.findall(r"(?:token|gatewayToken|authToken)=([^&#]+)",selected,flags=re.I):
    candidate_values.append(match)
matched=any(value==token for value in candidate_values)
if not matched:
    raise SystemExit("dashboard URL token does not match config token")

out_path.write_text(public_url+"\n",encoding="utf-8")
os.chmod(out_path,0o600)
safe={
    "dashboard_url_generated":True,
    "dashboard_url_matches_config":True,
    "dashboard_url_file":str(out_path),
    "dashboard_url_file_mode":"0o%o"%(out_path.stat().st_mode & 0o777),
    "dashboard_url_path":parsed.path or "/",
    "dashboard_url_has_query":bool(parsed.query),
    "dashboard_url_has_fragment":bool(parsed.fragment),
    "token_sha256":hashlib.sha256(token.encode()).hexdigest(),
    "secret_values_recorded":False,
}
safe_path.write_text(json.dumps(safe,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_DASHBOARD
DASHBOARD_PARSE_RC="$?"
if [ "$DASHBOARD_PARSE_RC" -ne 0 ]; then
  rm -f "$DASHBOARD_URL_FILE"
  fail_now "dashboard_url_validation_failed" "INSPECT_OPENCLAW_DASHBOARD_OUTPUT_LOCALLY"
fi

DASHBOARD_URL_GENERATED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["dashboard_url_generated"] else "NO")' "$TMP_ROOT/dashboard-safe.json")"
DASHBOARD_URL_MATCHES_CONFIG="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["dashboard_url_matches_config"] else "NO")' "$TMP_ROOT/dashboard-safe.json")"
[ "$DASHBOARD_URL_GENERATED" = "YES" ] || fail_now "dashboard_url_not_generated" "INSPECT_OPENCLAW_DASHBOARD_OUTPUT_LOCALLY"
[ "$DASHBOARD_URL_MATCHES_CONFIG" = "YES" ] || fail_now "dashboard_url_not_current_token" "INSPECT_OPENCLAW_DASHBOARD_OUTPUT_LOCALLY"
[ "$(stat -c '%a' "$DASHBOARD_URL_FILE" 2>/dev/null)" = "600" ] || fail_now "dashboard_url_file_permissions_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"

PUBLIC_AFTER="$TMP_ROOT/public-after.body"
DIRECT_AFTER="$TMP_ROOT/direct-after.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_AFTER" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
DIRECT_AFTER_STATUS="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' -o "$DIRECT_AFTER" -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
PUBLIC_AFTER_SHA="$(sha256sum "$PUBLIC_AFTER" 2>/dev/null | awk '{print $1}')"
DIRECT_AFTER_SHA="$(sha256sum "$DIRECT_AFTER" 2>/dev/null | awk '{print $1}')"
if [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ "$DIRECT_AFTER_STATUS" = "200" ] && [ -n "$PUBLIC_AFTER_SHA" ] && [ "$PUBLIC_AFTER_SHA" = "$DIRECT_AFTER_SHA" ]; then
  PUBLIC_ROOT_IS_OPENCLAW="YES"
else
  PUBLIC_ROOT_IS_OPENCLAW="NO"
fi
[ "$PUBLIC_ROOT_IS_OPENCLAW" = "NO" ] || fail_now "public_root_changed_during_token_rotation" "ROLL_BACK_NGINX_AND_INSPECT_EFFECTIVE_CONFIG"
case "$PUBLIC_ROOT_STATUS" in
  200|301|302|401|403) ;;
  *) fail_now "public_root_unhealthy_after_token_rotation" "INSPECT_EFFECTIVE_NGINX_CONFIG" ;;
esac

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
else
  fail_now "product_baseline_changed_during_token_rotation" "RESTORE_PRODUCT_BASELINE"
fi

RESULT="ROTATED"
NEXT_ACTION="RUN_NATIVE_OPENCLAW_NGINX_MIGRATION_V2"

export TASK_ID STAMP RESULT FAILURE_CODE TOKEN_ROTATED CONFIG_MODE SERVICE_RESTART SERVICE_STATE DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_IS_OPENCLAW DASHBOARD_URL_GENERATED DASHBOARD_URL_MATCHES_CONFIG DASHBOARD_URL_FILE PRODUCT_BASELINE_PRESERVED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL BACKUP_FILE
python3 - "$TMP_ROOT/rotation-safe.json" "$TMP_ROOT/dashboard-safe.json" "$RESULT_JSON" <<'PY_RESULT'
import json
import os
import sys
from pathlib import Path

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
rotation=load(sys.argv[1])
dashboard=load(sys.argv[2])
payload={
    "task_id":os.environ.get("TASK_ID"),
    "checked_at":os.environ.get("STAMP"),
    "result":os.environ.get("RESULT"),
    "failure_code":os.environ.get("FAILURE_CODE"),
    "token_rotation":{
        "rotated":os.environ.get("TOKEN_ROTATED")=="YES",
        "auth_mode":"token",
        "config_mode":os.environ.get("CONFIG_MODE"),
        "old_token_sha256":rotation.get("old_token_sha256"),
        "new_token_sha256":rotation.get("new_token_sha256"),
        "config_backup_file":os.environ.get("BACKUP_FILE"),
        "secret_values_recorded":False,
    },
    "gateway":{
        "service_restart":os.environ.get("SERVICE_RESTART"),
        "service_state":os.environ.get("SERVICE_STATE"),
        "direct_root_status":os.environ.get("DIRECT_ROOT_STATUS"),
    },
    "dashboard":dashboard,
    "public":{
        "root_status":os.environ.get("PUBLIC_ROOT_STATUS"),
        "root_is_openclaw":os.environ.get("PUBLIC_ROOT_IS_OPENCLAW")=="YES",
    },
    "safety":{
        "product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES",
        "nginx_changed":False,
        "product_task_submitted":False,
        "product_repository_mutated":False,
        "openclaw_reinstalled_or_upgraded":False,
        "secret_values_recorded":False,
    },
    "next_action":os.environ.get("NEXT_ACTION"),
    "evidence":{
        "log_path":os.environ.get("EVIDENCE_LOG_REL"),
        "json_path":os.environ.get("EVIDENCE_JSON_REL"),
        "self_commit_sha_omitted_to_prevent_post_commit_log_drift":True,
    },
}
Path(sys.argv[3]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
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
    re.compile(r"(?i)(token|password|secret|authorization|credential)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b|token\b|configured\b|rotated\b|changed\b|sha256\b)[A-Za-z0-9._~+/-]{20,}"),
    re.compile(r"https://control\.orisfy\.com/[^\s]*?(?:token|auth)[^\s]*",re.I),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding="utf-8",errors="replace")
    if any(pattern.search(text) for pattern in patterns):
        raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then
  SECRET_SCAN="PASS"
else
  fail_now "token_rotation_evidence_secret_scan_failed" "REPAIR_TOKEN_ROTATION_REDACTION"
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
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_TOKEN_ROTATION_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record OpenClaw token rotation $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
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
