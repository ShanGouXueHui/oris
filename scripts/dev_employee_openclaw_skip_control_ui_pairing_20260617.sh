#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
CONFIG="$HOME/.openclaw/openclaw.json"
SERVICE="openclaw-gateway.service"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$HOME/.openclaw/backups"
BACKUP="$BACKUP_DIR/openclaw.json.before-control-ui-pairing-bypass-$STAMP.bak"
LOG_DIR="$ORIS_REPO/logs/dev_employee/openclaw_device_auth"
LOG_FILE="$LOG_DIR/control-ui-pairing-bypass-$STAMP.log"
EXPECTED_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"

RESULT="FAILED"
FAILURE_CODE=""
AUTH_MODE="unknown"
DEVICE_PAIRING_BYPASS="NO"
SERVICE_STATE="unknown"
DIRECT_ROOT_STATUS="000"
PUBLIC_ROOT_STATUS="000"
PRODUCT_BASELINE_PRESERVED="NO"

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "AUTH_MODE=$AUTH_MODE"
  echo "DEVICE_PAIRING_BYPASS=$DEVICE_PAIRING_BYPASS"
  echo "SERVICE_STATE=$SERVICE_STATE"
  echo "DIRECT_ROOT_STATUS=$DIRECT_ROOT_STATUS"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "BACKUP_FILE=$BACKUP"
  echo "LOG_FILE=${LOG_FILE#$ORIS_REPO/}"
  echo "TOKEN_OR_PASSWORD_VALUE_CHANGED=NO"
  echo "NGINX_CHANGED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "NEXT_ACTION=RESTART_BROWSER_ACCEPTANCE_V2_IN_FRESH_INCOGNITO_WINDOW"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() {
  FAILURE_CODE="$1"
  summary
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user"; fi
[ -f "$CONFIG" ] || fail_now "openclaw_config_missing"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing"
mkdir -p "$BACKUP_DIR" "$LOG_DIR" || fail_now "directory_create_failed"
chmod 700 "$BACKUP_DIR" || fail_now "backup_permission_failed"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_HEAD" ] || fail_now "unexpected_product_head"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_HEAD" ] || fail_now "unexpected_product_remote"
[ "$PRODUCT_STATUS_BEFORE" = " M README.md" ] || fail_now "unexpected_product_status"

PRE_JSON="$(mktemp /tmp/openclaw-pairing-pre-XXXXXX.json)"
POST_JSON="$(mktemp /tmp/openclaw-pairing-post-XXXXXX.json)"
trap 'rm -f "$PRE_JSON" "$POST_JSON"' EXIT

python3 - "$CONFIG" "$PRE_JSON" <<'PY'
import hashlib,json,stat,sys
from pathlib import Path
p=Path(sys.argv[1]); out=Path(sys.argv[2]); d=json.loads(p.read_text())
a=d.get("gateway",{}).get("auth",{}); mode=a.get("mode") or "token"
if mode not in {"token","password"}: raise SystemExit(2)
secret=a.get(mode)
if not isinstance(secret,str) or not secret: raise SystemExit(3)
c=d.get("gateway",{}).get("controlUi",{})
out.write_text(json.dumps({"mode":mode,"secret_sha":hashlib.sha256(secret.encode()).hexdigest(),"before":c.get("dangerouslyDisableDeviceAuth") is True,"mode_bits":oct(stat.S_IMODE(p.stat().st_mode))}))
PY
[ "$?" -eq 0 ] || fail_now "authenticated_mode_required"
AUTH_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$PRE_JSON")"

cp "$CONFIG" "$BACKUP" || fail_now "backup_failed"
chmod 600 "$BACKUP" || fail_now "backup_permission_failed"

python3 - "$CONFIG" <<'PY'
import json,os,sys
from pathlib import Path
p=Path(sys.argv[1]); d=json.loads(p.read_text())
g=d.setdefault("gateway",{}); c=g.setdefault("controlUi",{})
if not isinstance(c,dict): raise SystemExit(2)
c["dangerouslyDisableDeviceAuth"]=True
t=p.with_name(p.name+".tmp")
t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
os.chmod(t,0o600); json.loads(t.read_text()); os.replace(t,p); os.chmod(p,0o600)
PY
[ "$?" -eq 0 ] || { cp "$BACKUP" "$CONFIG"; chmod 600 "$CONFIG"; fail_now "config_update_failed"; }

if ! systemctl --user restart "$SERVICE" >> "$LOG_FILE" 2>&1; then
  cp "$BACKUP" "$CONFIG"; chmod 600 "$CONFIG"; systemctl --user restart "$SERVICE" >> "$LOG_FILE" 2>&1 || true
  fail_now "gateway_restart_failed"
fi

for i in 1 2 3 4 5 6 7 8 9 10; do
  SERVICE_STATE="$(systemctl --user is-active "$SERVICE" 2>/dev/null || true)"
  DIRECT_ROOT_STATUS="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:18789/ 2>/dev/null || true)"
  [ "$SERVICE_STATE" = "active" ] && [ "$DIRECT_ROOT_STATUS" = "200" ] && break
  sleep 1
done
if [ "$SERVICE_STATE" != "active" ] || [ "$DIRECT_ROOT_STATUS" != "200" ]; then
  cp "$BACKUP" "$CONFIG"; chmod 600 "$CONFIG"; systemctl --user restart "$SERVICE" >> "$LOG_FILE" 2>&1 || true
  fail_now "gateway_unhealthy_after_change"
fi

python3 - "$CONFIG" "$POST_JSON" <<'PY'
import hashlib,json,stat,sys
from pathlib import Path
p=Path(sys.argv[1]); out=Path(sys.argv[2]); d=json.loads(p.read_text())
a=d.get("gateway",{}).get("auth",{}); mode=a.get("mode") or "token"; secret=a.get(mode)
c=d.get("gateway",{}).get("controlUi",{})
out.write_text(json.dumps({"mode":mode,"secret_sha":hashlib.sha256(secret.encode()).hexdigest(),"after":c.get("dangerouslyDisableDeviceAuth") is True,"mode_bits":oct(stat.S_IMODE(p.stat().st_mode))}))
PY
[ "$?" -eq 0 ] || fail_now "postcheck_failed"

PRE_SECRET="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["secret_sha"])' "$PRE_JSON")"
POST_SECRET="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["secret_sha"])' "$POST_JSON")"
POST_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$POST_JSON")"
DEVICE_PAIRING_BYPASS="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["after"] else "NO")' "$POST_JSON")"
POST_PERMS="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode_bits"])' "$POST_JSON")"
if [ "$AUTH_MODE" != "$POST_MODE" ] || [ "$PRE_SECRET" != "$POST_SECRET" ] || [ "$DEVICE_PAIRING_BYPASS" != "YES" ] || [ "$POST_PERMS" != "0o600" ]; then
  cp "$BACKUP" "$CONFIG"; chmod 600 "$CONFIG"; systemctl --user restart "$SERVICE" >> "$LOG_FILE" 2>&1 || true
  fail_now "security_postcheck_failed"
fi

PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' https://control.orisfy.com/ 2>/dev/null || true)"
[ "$PUBLIC_ROOT_STATUS" = "200" ] || fail_now "public_root_unhealthy"

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then PRODUCT_BASELINE_PRESERVED="YES"; else fail_now "product_baseline_changed"; fi

{
  echo "checked_at=$(date -Is)"
  echo "task_id=$TASK_ID"
  echo "auth_mode=$AUTH_MODE"
  echo "device_pairing_bypass=$DEVICE_PAIRING_BYPASS"
  echo "auth_secret_unchanged=YES"
  echo "service_state=$SERVICE_STATE"
  echo "direct_root_status=$DIRECT_ROOT_STATUS"
  echo "public_root_status=$PUBLIC_ROOT_STATUS"
  echo "product_baseline_preserved=$PRODUCT_BASELINE_PRESERVED"
  echo "secret_values_recorded=NO"
} >> "$LOG_FILE"

git -C "$ORIS_REPO" add -- "$LOG_FILE" || fail_now "evidence_git_add_failed"
git -C "$ORIS_REPO" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed"
git -C "$ORIS_REPO" commit -m "chore(dev-employee): record Control UI pairing bypass $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed"
git -C "$ORIS_REPO" pull --rebase origin main >/dev/null 2>&1 || fail_now "evidence_rebase_failed"
git -C "$ORIS_REPO" push origin main >/dev/null 2>&1 || fail_now "evidence_push_failed"

RESULT="CHANGED"
summary
exit 0
