#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
OPENCLAW_PORT="18789"
DOMAIN="control.orisfy.com"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
PRIVATE_DIR="$HOME/.openclaw/private"
BACKUP_DIR="$HOME/.openclaw/backups"
DASHBOARD_URL_FILE="$PRIVATE_DIR/control-orisfy-dashboard-url-current.txt"
TOKEN_FILE="$PRIVATE_DIR/control-orisfy-gateway-token-current.txt"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-token-finalize-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/finalize.log"
RESULT_JSON="$TMP_ROOT/finalize.json"
DASHBOARD_RAW="$TMP_ROOT/dashboard.raw"
DASHBOARD_SAFE="$TMP_ROOT/dashboard-safe.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/openclaw_credential_rotation"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/openclaw-token-rotation-finalize-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/openclaw-token-rotation-finalize-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
TOKEN_ROTATION_CONFIRMED="NO"
SERVICE_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_IS_OPENCLAW="unknown"
DASHBOARD_URL_GENERATED="NO"
DASHBOARD_URL_TOKEN_EMBEDDED="unknown"
TOKEN_FILE_GENERATED="NO"
PRIVATE_FILES_MODE_0600="NO"
PRODUCT_BASELINE_PRESERVED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_TOKEN_ROTATION_FINALIZE_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "TOKEN_ROTATION_CONFIRMED=$TOKEN_ROTATION_CONFIRMED"
  echo "SERVICE_STATE=$SERVICE_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_IS_OPENCLAW=$PUBLIC_ROOT_IS_OPENCLAW"
  echo "DASHBOARD_URL_GENERATED=$DASHBOARD_URL_GENERATED"
  echo "DASHBOARD_URL_TOKEN_EMBEDDED=$DASHBOARD_URL_TOKEN_EMBEDDED"
  echo "TOKEN_FILE_GENERATED=$TOKEN_FILE_GENERATED"
  echo "PRIVATE_FILES_MODE_0600=$PRIVATE_FILES_MODE_0600"
  echo "DASHBOARD_URL_FILE=$DASHBOARD_URL_FILE"
  echo "TOKEN_FILE=$TOKEN_FILE"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "OPENCLAW_SERVICE_RESTARTED=NO"
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

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum systemctl stat find sort awk; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "INSPECT_OPENCLAW_INSTALLATION"
OPENCLAW_BIN="$(command -v openclaw 2>/dev/null || true)"
[ -n "$OPENCLAW_BIN" ] || fail_now "openclaw_binary_missing" "RESTORE_EXISTING_OPENCLAW_BINARY"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=FINALIZE_ALREADY_ROTATED_OPENCLAW_TOKEN"
log "SECRET_VALUES_RECORDED=NO"
log "OPENCLAW_CONFIG_MUTATED=NO"
log "OPENCLAW_SERVICE_RESTARTED=NO"
log "NGINX_CHANGED=NO"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status" "REVIEW_PRODUCT_BASELINE"

LATEST_BACKUP="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'openclaw.json.before-token-rotation-*.bak' -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1{$1=""; sub(/^ /,""); print; exit}')"
[ -n "$LATEST_BACKUP" ] && [ -f "$LATEST_BACKUP" ] || fail_now "token_rotation_backup_missing" "INSPECT_OPENCLAW_BACKUPS"

python3 - "$OPENCLAW_CONFIG" "$LATEST_BACKUP" "$TMP_ROOT/rotation-check.json" <<'PY_ROTATION_CHECK'
import hashlib,json,stat,sys
from pathlib import Path
current_path=Path(sys.argv[1]); backup_path=Path(sys.argv[2]); out=Path(sys.argv[3])
current=json.loads(current_path.read_text(encoding="utf-8"))
backup=json.loads(backup_path.read_text(encoding="utf-8"))
current_auth=current.get("gateway",{}).get("auth",{})
backup_auth=backup.get("gateway",{}).get("auth",{})
current_token=current_auth.get("token")
backup_token=backup_auth.get("token")
if current_auth.get("mode")!="token": raise SystemExit("current auth mode is not token")
if not isinstance(current_token,str) or not current_token: raise SystemExit("current token missing")
if not isinstance(backup_token,str) or not backup_token: raise SystemExit("backup token missing")
payload={
  "rotation_confirmed": current_token != backup_token,
  "current_fingerprint": hashlib.sha256(current_token.encode()).hexdigest(),
  "backup_fingerprint": hashlib.sha256(backup_token.encode()).hexdigest(),
  "config_mode":"0o%o"%stat.S_IMODE(current_path.stat().st_mode),
  "backup_mode":"0o%o"%stat.S_IMODE(backup_path.stat().st_mode),
  "secret_values_recorded":False,
}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_ROTATION_CHECK
[ "$?" -eq 0 ] || fail_now "token_rotation_confirmation_failed" "INSPECT_CURRENT_AND_BACKUP_OPENCLAW_CONFIG"
TOKEN_ROTATION_CONFIRMED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["rotation_confirmed"] else "NO")' "$TMP_ROOT/rotation-check.json")"
[ "$TOKEN_ROTATION_CONFIRMED" = "YES" ] || fail_now "token_matches_pre_rotation_backup" "ROTATE_OPENCLAW_TOKEN_AGAIN"
[ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["config_mode"])' "$TMP_ROOT/rotation-check.json")" = "0o600" ] || fail_now "openclaw_config_permissions_not_0600" "RESTORE_OPENCLAW_CONFIG_PERMISSIONS"

SERVICE_STATE="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"
DIRECT_ROOT_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$OPENCLAW_PORT/" 2>/dev/null || true)"
[ "$SERVICE_STATE" = "active" ] || fail_now "openclaw_gateway_not_active" "INSPECT_OPENCLAW_SERVICE"
[ "$DIRECT_ROOT_STATUS" = "200" ] || fail_now "openclaw_direct_root_unhealthy" "INSPECT_OPENCLAW_SERVICE"

PUBLIC_BODY="$TMP_ROOT/public-root.body"
DIRECT_BODY="$TMP_ROOT/direct-root.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_BODY" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
curl -sS --max-time 10 -H 'Cache-Control: no-cache' "http://127.0.0.1:$OPENCLAW_PORT/" -o "$DIRECT_BODY" 2>/dev/null || true
PUBLIC_SHA="$(sha256sum "$PUBLIC_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_BODY" 2>/dev/null | awk '{print $1}')"
if [ -n "$PUBLIC_SHA" ] && [ "$PUBLIC_SHA" = "$DIRECT_SHA" ]; then PUBLIC_ROOT_IS_OPENCLAW="YES"; else PUBLIC_ROOT_IS_OPENCLAW="NO"; fi
[ "$PUBLIC_ROOT_IS_OPENCLAW" = "NO" ] || fail_now "public_root_unexpectedly_openclaw" "ROLL_BACK_NGINX_BEFORE_CONTINUING"
case "$PUBLIC_ROOT_STATUS" in 200|301|302|401|403) ;; *) fail_now "public_root_unhealthy" "INSPECT_EFFECTIVE_NGINX_CONFIG" ;; esac

"$OPENCLAW_BIN" dashboard --no-open > "$DASHBOARD_RAW" 2>&1
[ "$?" -eq 0 ] || fail_now "openclaw_dashboard_output_failed" "INSPECT_OPENCLAW_DASHBOARD_HELP"
mkdir -p "$PRIVATE_DIR" || fail_now "private_directory_create_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"
chmod 700 "$PRIVATE_DIR" || fail_now "private_directory_permission_failed" "CHECK_OPENCLAW_DIRECTORY_PERMISSIONS"

python3 - "$DASHBOARD_RAW" "$OPENCLAW_CONFIG" "$DASHBOARD_URL_FILE" "$TOKEN_FILE" "$DOMAIN" "$DASHBOARD_SAFE" <<'PY_DASHBOARD_FINALIZE'
import json,os,re,sys
from pathlib import Path
from urllib.parse import parse_qsl,unquote,urlsplit,urlunsplit
raw_path=Path(sys.argv[1])
config_path=Path(sys.argv[2])
url_path=Path(sys.argv[3])
token_path=Path(sys.argv[4])
domain=sys.argv[5]
safe_path=Path(sys.argv[6])
raw=raw_path.read_text(encoding="utf-8",errors="replace")
raw=re.sub(r"\x1b\[[0-9;]*[A-Za-z]","",raw)
config=json.loads(config_path.read_text(encoding="utf-8"))
token=config.get("gateway",{}).get("auth",{}).get("token")
if not isinstance(token,str) or not token:
    raise SystemExit("current token missing")
urls=[]
for match in re.findall(r"https?://[^\s<>]+",raw):
    candidate=match.strip(" \t\r\n'\"`.,;)]}>")
    if candidate and candidate not in urls:
        urls.append(candidate)
if not urls:
    raise SystemExit("dashboard URL not found")
selected=None
embedded=False
for candidate in urls:
    decoded=unquote(candidate)
    if token in decoded:
        selected=candidate
        embedded=True
        break
if selected is None:
    selected=urls[0]
parsed=urlsplit(selected)
if not parsed.scheme or not parsed.netloc:
    raise SystemExit("dashboard URL invalid")
public_url=urlunsplit(("https",domain,parsed.path or "/",parsed.query,parsed.fragment))
if embedded and token not in unquote(public_url):
    raise SystemExit("embedded token lost while publicizing URL")
url_path.write_text(public_url+"\n",encoding="utf-8")
token_path.write_text(token+"\n",encoding="utf-8")
os.chmod(url_path,0o600)
os.chmod(token_path,0o600)

def key_names(component):
    names=[]
    pieces=[component]
    if "?" in component:
        pieces.append(component.split("?",1)[1])
    for piece in pieces:
        for key,_ in parse_qsl(piece,keep_blank_values=True):
            if key and key not in names:
                names.append(key)
    for key in re.findall(r"(?:^|[?&#/])([A-Za-z][A-Za-z0-9_-]{1,40})=",component):
        if key not in names:
            names.append(key)
    return names[:30]

safe={
  "url_candidate_count":len(urls),
  "selected_path":parsed.path or "/",
  "selected_query_keys":key_names(parsed.query),
  "selected_fragment_keys":key_names(parsed.fragment),
  "token_embedded_in_selected_url":embedded,
  "token_present_anywhere_in_dashboard_output":token in unquote(raw),
  "dashboard_url_file":str(url_path),
  "token_file":str(token_path),
  "dashboard_url_file_mode":"0o%o"%(url_path.stat().st_mode & 0o777),
  "token_file_mode":"0o%o"%(token_path.stat().st_mode & 0o777),
  "secret_values_recorded":False,
}
safe_path.write_text(json.dumps(safe,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_DASHBOARD_FINALIZE
[ "$?" -eq 0 ] || fail_now "dashboard_private_artifact_generation_failed" "INSPECT_DASHBOARD_OUTPUT_LOCALLY_WITHOUT_SHARING_SECRETS"

DASHBOARD_URL_GENERATED="YES"
TOKEN_FILE_GENERATED="YES"
DASHBOARD_URL_TOKEN_EMBEDDED="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["token_embedded_in_selected_url"] else "NO")' "$DASHBOARD_SAFE")"
if [ "$(stat -c '%a' "$DASHBOARD_URL_FILE" 2>/dev/null)" = "600" ] && [ "$(stat -c '%a' "$TOKEN_FILE" 2>/dev/null)" = "600" ]; then
  PRIVATE_FILES_MODE_0600="YES"
else
  fail_now "private_credential_files_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"
fi

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then
  PRODUCT_BASELINE_PRESERVED="YES"
else
  fail_now "product_baseline_changed_during_finalize" "RESTORE_PRODUCT_BASELINE"
fi

RESULT="FINALIZED"
NEXT_ACTION="BUILD_AND_RUN_NATIVE_OPENCLAW_NGINX_MIGRATION_V2"

export TASK_ID STAMP RESULT FAILURE_CODE TOKEN_ROTATION_CONFIRMED SERVICE_STATE DIRECT_ROOT_STATUS PUBLIC_ROOT_STATUS PUBLIC_ROOT_IS_OPENCLAW DASHBOARD_URL_GENERATED DASHBOARD_URL_TOKEN_EMBEDDED TOKEN_FILE_GENERATED PRIVATE_FILES_MODE_0600 DASHBOARD_URL_FILE TOKEN_FILE PRODUCT_BASELINE_PRESERVED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL LATEST_BACKUP
python3 - "$TMP_ROOT/rotation-check.json" "$DASHBOARD_SAFE" "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
rotation=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
dashboard=json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
payload={
  "task_id":os.environ.get("TASK_ID"),
  "checked_at":os.environ.get("STAMP"),
  "result":os.environ.get("RESULT"),
  "failure_code":os.environ.get("FAILURE_CODE"),
  "rotation_confirmation":rotation,
  "gateway":{"service_state":os.environ.get("SERVICE_STATE"),"direct_root_status":os.environ.get("DIRECT_ROOT_STATUS")},
  "public":{"root_status":os.environ.get("PUBLIC_ROOT_STATUS"),"root_is_openclaw":os.environ.get("PUBLIC_ROOT_IS_OPENCLAW")=="YES"},
  "dashboard":dashboard,
  "safety":{
    "product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES",
    "openclaw_config_mutated":False,
    "openclaw_service_restarted":False,
    "nginx_changed":False,
    "product_task_submitted":False,
    "product_repository_mutated":False,
    "secret_values_recorded":False,
  },
  "next_action":os.environ.get("NEXT_ACTION"),
  "evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True},
}
Path(sys.argv[3]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re,sys
from pathlib import Path
patterns=[
 re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
 re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
 re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
 re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
 re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
 re.compile(r"https://control\.orisfy\.com/[^\s]*(?:token|auth)[^\s]*",re.I),
 re.compile(r"(?i)(gateway[_ -]?token|password|authorization|credential)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b)[A-Za-z0-9._~+/-]{20,}"),
]
for filename in sys.argv[1:]:
    text=Path(filename).read_text(encoding="utf-8",errors="replace")
    if any(pattern.search(text) for pattern in patterns):
        raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "finalize_evidence_secret_scan_failed" "REPAIR_FINALIZE_REDACTION"; fi

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json,sys
from pathlib import Path
source_log,target_log,source_json,target_json=map(Path,sys.argv[1:])
target_log.write_text("\n".join(line.rstrip(" \t\r") for line in source_log.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
target_json.write_text(json.dumps(json.loads(source_json.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_FINALIZE_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): finalize OpenClaw token rotation $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
