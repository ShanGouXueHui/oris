#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
EFFECTIVE_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
LEGACY_DUPLICATE="/etc/nginx/sites-enabled/control.orisfy.com.conf.disabled_20260601011754"
HTPASSWD_FILE="/etc/nginx/oris-dev-employee.htpasswd"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
PRIVATE_TOKEN_FILE="$HOME/.openclaw/private/control-orisfy-gateway-token-current.txt"
PRIVATE_DASHBOARD_URL_FILE="$HOME/.openclaw/private/control-orisfy-dashboard-url-current.txt"
OPENCLAW_UPSTREAM="http://127.0.0.1:18789"
CONSOLE_UPSTREAM="http://127.0.0.1:18893"
INTAKE_PORT="18892"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/etc/nginx/oris-backups/native-openclaw-v2-$STAMP"
BACKUP_CONF="$BACKUP_DIR/oris-dev-employee-web-console.readonly.conf.bak"
BACKUP_LEGACY="$BACKUP_DIR/control.orisfy.com.legacy-duplicate.bak"
CANDIDATE="$(mktemp /tmp/oris-native-openclaw-v2-${STAMP}-XXXXXX.conf)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-v2-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/migration.log"
RESULT_JSON="$TMP_ROOT/migration.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_migration"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-migration-v2-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-migration-v2-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
MIGRATION_APPLIED="NO"
ROLLBACK_PERFORMED="NO"
LEGACY_DUPLICATE_REMOVED="NO"
NGINX_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
NGINX_CONFLICT_WARNING_COUNT="unknown"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_MATCHES_OPENCLAW="NO"
PUBLIC_ADMIN_STATUS="000"
PUBLIC_ROLLBACK_STATUS="000"
PUBLIC_BOOTSTRAP_STATUS="000"
PUBLIC_SESSION_STATUS="000"
PUBLIC_MESSAGES_STATUS="000"
INTAKE_LOOPBACK_ONLY="unknown"
TOKEN_PRIVATE_ARTIFACT_VALID="NO"
PRODUCT_BASELINE_PRESERVED="NO"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_NATIVE_OPENCLAW_MIGRATION_V2_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  rm -f "$CANDIDATE"
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
  echo "MIGRATION_APPLIED=$MIGRATION_APPLIED"
  echo "ROLLBACK_PERFORMED=$ROLLBACK_PERFORMED"
  echo "LEGACY_DUPLICATE_REMOVED=$LEGACY_DUPLICATE_REMOVED"
  echo "NGINX_TEST=$NGINX_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "NGINX_CONFLICT_WARNING_COUNT=$NGINX_CONFLICT_WARNING_COUNT"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_MATCHES_OPENCLAW=$PUBLIC_ROOT_MATCHES_OPENCLAW"
  echo "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
  echo "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
  echo "PUBLIC_BOOTSTRAP_STATUS=$PUBLIC_BOOTSTRAP_STATUS"
  echo "PUBLIC_SESSION_STATUS=$PUBLIC_SESSION_STATUS"
  echo "PUBLIC_MESSAGES_STATUS=$PUBLIC_MESSAGES_STATUS"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "TOKEN_PRIVATE_ARTIFACT_VALID=$TOKEN_PRIVATE_ARTIFACT_VALID"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "BACKUP_DIR=$BACKUP_DIR"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "OPENCLAW_SERVICE_RESTARTED=NO"
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

rollback_nginx() {
  local ok="YES"
  if [ -f "$BACKUP_CONF" ]; then
    sudo -n cp "$BACKUP_CONF" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || ok="NO"
  else
    ok="NO"
  fi
  if [ -f "$BACKUP_LEGACY" ] && [ ! -e "$LEGACY_DUPLICATE" ]; then
    sudo -n cp -a "$BACKUP_LEGACY" "$LEGACY_DUPLICATE" >> "$RUN_LOG" 2>&1 || ok="NO"
  fi
  if [ "$ok" = "YES" ]; then
    sudo -n nginx -t >> "$RUN_LOG" 2>&1 || ok="NO"
  fi
  if [ "$ok" = "YES" ]; then
    sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1 || ok="NO"
  fi
  if [ "$ok" = "YES" ]; then
    ROLLBACK_PERFORMED="YES"
    MIGRATION_APPLIED="NO"
    return 0
  fi
  return 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then fail_now "wrong_linux_user" "RUN_AS_ADMIN"; fi
for cmd in git curl python3 sha256sum sudo nginx systemctl ss stat grep; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$EFFECTIVE_CONF" ] || fail_now "effective_nginx_config_missing" "RESTORE_EFFECTIVE_NGINX_CONFIG"
[ -f "$HTPASSWD_FILE" ] || fail_now "admin_htpasswd_missing" "RESTORE_CURRENT_ADMIN_HTPASSWD"
[ -f "$OPENCLAW_CONFIG" ] || fail_now "openclaw_config_missing" "RESTORE_OPENCLAW_CONFIG"
[ -f "$PRIVATE_TOKEN_FILE" ] || fail_now "private_token_file_missing" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
[ -f "$PRIVATE_DASHBOARD_URL_FILE" ] || fail_now "private_dashboard_url_file_missing" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
[ "$(stat -c '%a' "$PRIVATE_TOKEN_FILE" 2>/dev/null)" = "600" ] || fail_now "private_token_file_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"
[ "$(stat -c '%a' "$PRIVATE_DASHBOARD_URL_FILE" 2>/dev/null)" = "600" ] || fail_now "private_dashboard_url_file_not_0600" "RESTORE_PRIVATE_FILE_PERMISSIONS"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=REVERSIBLE_NATIVE_OPENCLAW_NGINX_MIGRATION_V2"
log "SECRET_VALUES_RECORDED=NO"
log "OPENCLAW_CONFIG_MUTATED=NO"
log "OPENCLAW_SERVICE_RESTARTED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "PRODUCT_REPOSITORY_MUTATED=NO"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
log "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status" "REVIEW_PRODUCT_BASELINE"

python3 - "$OPENCLAW_CONFIG" "$PRIVATE_TOKEN_FILE" "$PRIVATE_DASHBOARD_URL_FILE" "$DOMAIN" "$TMP_ROOT/private-artifacts-safe.json" <<'PY_PRIVATE_ARTIFACTS'
import json,sys
from pathlib import Path
from urllib.parse import urlsplit
config_path=Path(sys.argv[1]); token_path=Path(sys.argv[2]); url_path=Path(sys.argv[3]); domain=sys.argv[4]; out=Path(sys.argv[5])
config=json.loads(config_path.read_text(encoding="utf-8"))
config_token=config.get("gateway",{}).get("auth",{}).get("token")
private_token=token_path.read_text(encoding="utf-8").strip()
private_url=url_path.read_text(encoding="utf-8").strip()
parsed=urlsplit(private_url)
valid=(config.get("gateway",{}).get("auth",{}).get("mode")=="token" and isinstance(config_token,str) and config_token and private_token==config_token and parsed.scheme=="https" and parsed.hostname==domain)
out.write_text(json.dumps({"valid":bool(valid),"dashboard_path":parsed.path or "/","dashboard_has_query":bool(parsed.query),"dashboard_has_fragment":bool(parsed.fragment),"secret_values_recorded":False},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_PRIVATE_ARTIFACTS
[ "$?" -eq 0 ] || fail_now "private_artifact_validation_failed" "FINALIZE_OPENCLAW_TOKEN_ROTATION"
TOKEN_PRIVATE_ARTIFACT_VALID="$(python3 -c 'import json,sys; print("YES" if json.load(open(sys.argv[1]))["valid"] else "NO")' "$TMP_ROOT/private-artifacts-safe.json")"
[ "$TOKEN_PRIVATE_ARTIFACT_VALID" = "YES" ] || fail_now "private_token_does_not_match_openclaw_config" "FINALIZE_OPENCLAW_TOKEN_ROTATION"

OPENCLAW_STATE="$(systemctl --user is-active openclaw-gateway.service 2>/dev/null || true)"
OPENCLAW_STATUS="$(curl -sS --max-time 8 -o "$TMP_ROOT/openclaw-root.body" -w '%{http_code}' "$OPENCLAW_UPSTREAM/" 2>/dev/null || true)"
CONSOLE_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$CONSOLE_UPSTREAM/" 2>/dev/null || true)"
BOOTSTRAP_DIRECT="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$CONSOLE_UPSTREAM/api/chat/bootstrap" 2>/dev/null || true)"
SESSION_DIRECT="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$CONSOLE_UPSTREAM/api/chat/session" 2>/dev/null || true)"
MESSAGES_DIRECT="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$CONSOLE_UPSTREAM/api/chat/messages" 2>/dev/null || true)"
log "OPENCLAW_STATE=$OPENCLAW_STATE"
log "OPENCLAW_DIRECT_STATUS=$OPENCLAW_STATUS"
log "CONSOLE_DIRECT_STATUS=$CONSOLE_STATUS"
log "CONSOLE_BOOTSTRAP_DIRECT_STATUS=$BOOTSTRAP_DIRECT"
log "CONSOLE_SESSION_DIRECT_STATUS=$SESSION_DIRECT"
log "CONSOLE_MESSAGES_DIRECT_GET_STATUS=$MESSAGES_DIRECT"
[ "$OPENCLAW_STATE" = "active" ] || fail_now "openclaw_gateway_not_active" "RESTORE_OPENCLAW_GATEWAY"
[ "$OPENCLAW_STATUS" = "200" ] || fail_now "openclaw_direct_root_unhealthy" "RESTORE_OPENCLAW_GATEWAY"
case "$CONSOLE_STATUS" in 200|301|302|401|403) ;; *) fail_now "console_direct_root_unhealthy" "RESTORE_CONSOLE_SERVICE" ;; esac
[ "$BOOTSTRAP_DIRECT" = "200" ] || fail_now "console_bootstrap_direct_unhealthy" "RESTORE_CONSOLE_BOOTSTRAP"
case "$SESSION_DIRECT" in 200|400|401|404) ;; *) fail_now "console_session_direct_unexpected" "INSPECT_CONSOLE_SESSION_API" ;; esac
case "$MESSAGES_DIRECT" in 200|400|401|404|405) ;; *) fail_now "console_messages_direct_unexpected" "INSPECT_CONSOLE_MESSAGES_API" ;; esac

PUBLIC_BEFORE="$TMP_ROOT/public-before.body"
PUBLIC_BEFORE_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_BEFORE" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
PUBLIC_BEFORE_SHA="$(sha256sum "$PUBLIC_BEFORE" 2>/dev/null | awk '{print $1}')"
OPENCLAW_SHA="$(sha256sum "$TMP_ROOT/openclaw-root.body" 2>/dev/null | awk '{print $1}')"
if [ "$PUBLIC_BEFORE_STATUS" = "200" ] && [ -n "$PUBLIC_BEFORE_SHA" ] && [ "$PUBLIC_BEFORE_SHA" = "$OPENCLAW_SHA" ]; then
  fail_now "public_root_already_openclaw_before_v2" "RUN_BROWSER_ACCEPTANCE_OR_ROLLBACK"
fi

INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
case "$INTAKE_LISTENER" in 127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;; *) INTAKE_LOOPBACK_ONLY="NO" ;; esac
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || fail_now "intake_not_loopback_only" "RESTORE_INTAKE_PRIVATE_BINDING"

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"

cat > "$CANDIDATE" <<'NGINX_V2'
server {
    listen 443 ssl http2;
    server_name control.orisfy.com;

    ssl_certificate /etc/letsencrypt/live/control.orisfy.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/control.orisfy.com/privkey.pem;

    access_log /var/log/nginx/oris-dev-employee-console.access.log;
    error_log /var/log/nginx/oris-dev-employee-console.error.log warn;
    client_max_body_size 16m;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header X-Frame-Options "DENY" always;
    add_header Cache-Control "no-cache" always;

    location = /admin {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /admin;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location ^~ /admin/ {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        rewrite ^/admin/?(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:18893;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /admin;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location = /_oris-chat-shell {
        auth_basic "ORIS Diagnostic";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /_oris-chat-shell;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location ^~ /_oris-chat-shell/ {
        auth_basic "ORIS Diagnostic";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        rewrite ^/_oris-chat-shell/?(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:18893;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Prefix /_oris-chat-shell;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location = /api/chat/bootstrap {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/api/chat/bootstrap;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
    }

    location = /api/chat/session {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/api/chat/session;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
    }

    location = /api/chat/messages {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/api/chat/messages;
        proxy_http_version 1.1;
        proxy_pass_request_headers on;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
        proxy_set_header X-ORIS-Chat-CSRF $http_x_oris_chat_csrf;
        proxy_connect_timeout 10s;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
        proxy_buffering off;
    }

    location = /api/goals {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/api/goals;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
    }

    location ^~ /api/goals/ {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
    }

    location = /api/projects {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/oris-dev-employee.htpasswd;
        proxy_pass http://127.0.0.1:18893/api/projects;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-User $remote_user;
    }

    location / {
        proxy_pass http://127.0.0.1:18789;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
    }
}

server {
    listen 80;
    server_name control.orisfy.com;
    return 301 https://$host$request_uri;
}
NGINX_V2

sudo -n mkdir -p "$BACKUP_DIR" >> "$RUN_LOG" 2>&1 || fail_now "backup_directory_create_failed" "CHECK_SUDO_PERMISSIONS"
sudo -n cp -a "$EFFECTIVE_CONF" "$BACKUP_CONF" >> "$RUN_LOG" 2>&1 || fail_now "effective_config_backup_failed" "CHECK_SUDO_PERMISSIONS"
if [ -e "$LEGACY_DUPLICATE" ]; then
  sudo -n cp -a "$LEGACY_DUPLICATE" "$BACKUP_LEGACY" >> "$RUN_LOG" 2>&1 || fail_now "legacy_duplicate_backup_failed" "CHECK_SUDO_PERMISSIONS"
  sudo -n rm -f "$LEGACY_DUPLICATE" >> "$RUN_LOG" 2>&1 || fail_now "legacy_duplicate_remove_failed" "CHECK_SUDO_PERMISSIONS"
  LEGACY_DUPLICATE_REMOVED="YES"
else
  LEGACY_DUPLICATE_REMOVED="ALREADY_ABSENT"
fi
sudo -n cp "$CANDIDATE" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || { rollback_nginx || true; fail_now "candidate_install_failed" "CHECK_SUDO_PERMISSIONS"; }

if sudo -n nginx -t >> "$RUN_LOG" 2>&1; then NGINX_TEST="PASS"; else NGINX_TEST="FAILED"; rollback_nginx || true; fail_now "nginx_test_failed" "READ_MIGRATION_V2_EVIDENCE"; fi
NGINX_DUMP="$TMP_ROOT/nginx-T.txt"
sudo -n nginx -T > "$NGINX_DUMP" 2>&1 || { rollback_nginx || true; fail_now "nginx_dump_failed" "READ_MIGRATION_V2_EVIDENCE"; }
NGINX_CONFLICT_WARNING_COUNT="$(grep -Eic 'conflicting server name.*control\.orisfy\.com' "$NGINX_DUMP" || true)"
[ "$NGINX_CONFLICT_WARNING_COUNT" = "0" ] || { rollback_nginx || true; fail_now "nginx_duplicate_server_block_remains" "READ_MIGRATION_V2_EVIDENCE"; }

if sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1; then NGINX_RELOAD="PASS"; MIGRATION_APPLIED="YES"; else NGINX_RELOAD="FAILED"; rollback_nginx || true; fail_now "nginx_reload_failed" "READ_MIGRATION_V2_EVIDENCE"; fi
sleep 2

PUBLIC_ROOT_BODY="$TMP_ROOT/public-root.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_ROOT_BODY" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
PUBLIC_ROOT_SHA="$(sha256sum "$PUBLIC_ROOT_BODY" 2>/dev/null | awk '{print $1}')"
OPENCLAW_DIRECT_SHA="$(curl -sS --max-time 10 -H 'Cache-Control: no-cache' "$OPENCLAW_UPSTREAM/" 2>/dev/null | sha256sum | awk '{print $1}')"
if [ "$PUBLIC_ROOT_STATUS" = "200" ] && [ -n "$PUBLIC_ROOT_SHA" ] && [ "$PUBLIC_ROOT_SHA" = "$OPENCLAW_DIRECT_SHA" ]; then PUBLIC_ROOT_MATCHES_OPENCLAW="YES"; fi
PUBLIC_ADMIN_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/admin" 2>/dev/null || true)"
PUBLIC_ROLLBACK_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/_oris-chat-shell" 2>/dev/null || true)"
PUBLIC_BOOTSTRAP_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/bootstrap" 2>/dev/null || true)"
PUBLIC_SESSION_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/session" 2>/dev/null || true)"
PUBLIC_MESSAGES_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN/api/chat/messages" 2>/dev/null || true)"
log "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
log "PUBLIC_ROOT_MATCHES_OPENCLAW=$PUBLIC_ROOT_MATCHES_OPENCLAW"
log "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
log "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
log "PUBLIC_BOOTSTRAP_STATUS=$PUBLIC_BOOTSTRAP_STATUS"
log "PUBLIC_SESSION_STATUS=$PUBLIC_SESSION_STATUS"
log "PUBLIC_MESSAGES_STATUS=$PUBLIC_MESSAGES_STATUS"

[ "$PUBLIC_ROOT_MATCHES_OPENCLAW" = "YES" ] || { rollback_nginx || true; fail_now "public_root_not_native_openclaw" "READ_MIGRATION_V2_EVIDENCE"; }
for restricted_status in "$PUBLIC_ADMIN_STATUS" "$PUBLIC_ROLLBACK_STATUS" "$PUBLIC_BOOTSTRAP_STATUS" "$PUBLIC_SESSION_STATUS" "$PUBLIC_MESSAGES_STATUS"; do
  case "$restricted_status" in 401|403) ;; *) rollback_nginx || true; fail_now "restricted_console_route_not_protected" "READ_MIGRATION_V2_EVIDENCE" ;; esac
done

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then PRODUCT_BASELINE_PRESERVED="YES"; else rollback_nginx || true; fail_now "product_baseline_changed_during_migration_v2" "RESTORE_PRODUCT_BASELINE"; fi

RESULT="MIGRATED_V2"
NEXT_ACTION="OPEN_PRIVATE_DASHBOARD_URL_ENTER_PRIVATE_TOKEN_AND_RUN_BROWSER_ACCEPTANCE_V2"

export TASK_ID STAMP RESULT FAILURE_CODE MIGRATION_APPLIED ROLLBACK_PERFORMED LEGACY_DUPLICATE_REMOVED NGINX_TEST NGINX_RELOAD NGINX_CONFLICT_WARNING_COUNT PUBLIC_ROOT_STATUS PUBLIC_ROOT_MATCHES_OPENCLAW PUBLIC_ADMIN_STATUS PUBLIC_ROLLBACK_STATUS PUBLIC_BOOTSTRAP_STATUS PUBLIC_SESSION_STATUS PUBLIC_MESSAGES_STATUS INTAKE_LOOPBACK_ONLY TOKEN_PRIVATE_ARTIFACT_VALID PRODUCT_BASELINE_PRESERVED BACKUP_DIR NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={
 "task_id":os.environ.get("TASK_ID"),"checked_at":os.environ.get("STAMP"),"result":os.environ.get("RESULT"),"failure_code":os.environ.get("FAILURE_CODE"),
 "migration":{"applied":os.environ.get("MIGRATION_APPLIED")=="YES","rollback_performed":os.environ.get("ROLLBACK_PERFORMED")=="YES","legacy_duplicate_removed":os.environ.get("LEGACY_DUPLICATE_REMOVED"),"nginx_test":os.environ.get("NGINX_TEST"),"nginx_reload":os.environ.get("NGINX_RELOAD"),"conflict_warning_count":int(os.environ.get("NGINX_CONFLICT_WARNING_COUNT","-1")),"backup_dir":os.environ.get("BACKUP_DIR")},
 "public":{"root_status":os.environ.get("PUBLIC_ROOT_STATUS"),"root_matches_openclaw":os.environ.get("PUBLIC_ROOT_MATCHES_OPENCLAW")=="YES","admin_without_credentials":os.environ.get("PUBLIC_ADMIN_STATUS"),"rollback_without_credentials":os.environ.get("PUBLIC_ROLLBACK_STATUS"),"bootstrap_without_credentials":os.environ.get("PUBLIC_BOOTSTRAP_STATUS"),"session_without_credentials":os.environ.get("PUBLIC_SESSION_STATUS"),"messages_without_credentials":os.environ.get("PUBLIC_MESSAGES_STATUS")},
 "safety":{"intake_loopback_only":os.environ.get("INTAKE_LOOPBACK_ONLY")=="YES","private_token_artifact_valid":os.environ.get("TOKEN_PRIVATE_ARTIFACT_VALID")=="YES","product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES","openclaw_config_mutated":False,"openclaw_service_restarted":False,"product_task_submitted":False,"product_repository_mutated":False,"secret_values_recorded":False},
 "next_action":os.environ.get("NEXT_ACTION"),"evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True}
}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY_SECRET_SCAN'
import re,sys
from pathlib import Path
patterns=[re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),re.compile(r"(?i)(gateway[_ -]?token|password|authorization|credential)(\s*[=:]\s*|\s+)(?!<redacted>|true\b|false\b|yes\b|no\b|null\b)[A-Za-z0-9._~+/-]{20,}")]
for filename in sys.argv[1:]:
 text=Path(filename).read_text(encoding="utf-8",errors="replace")
 if any(pattern.search(text) for pattern in patterns): raise SystemExit(1)
PY_SECRET_SCAN
if [ "$?" -eq 0 ]; then SECRET_SCAN="PASS"; else fail_now "migration_v2_evidence_secret_scan_failed" "REPAIR_MIGRATION_V2_REDACTION"; fi

git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text("\n".join(line.rstrip(" \t\r") for line in sl.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
dj.write_text(json.dumps(json.loads(sj.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_NORMALIZE
[ "$?" -eq 0 ] || fail_now "evidence_normalization_failed" "INSPECT_MIGRATION_V2_EVIDENCE"
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw migration v2 $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
