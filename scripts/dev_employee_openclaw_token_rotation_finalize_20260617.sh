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
for cmd in git curl python3 sha256sum systemctl stat; do
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
raw_path,config_path,url_path,token_path,domain,safe_path=map(Path,sys.argv[1:5])+[sys.argv[5],Path(sys.argv[6])]
PY_DASHBOARD_FINALIZE
