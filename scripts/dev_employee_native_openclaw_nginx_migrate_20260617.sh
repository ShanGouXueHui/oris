#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
EFFECTIVE_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
OPENCLAW_UPSTREAM="http://127.0.0.1:18789"
CONSOLE_UPSTREAM="http://127.0.0.1:18893"
INTAKE_PORT="18892"
ADMIN_PREFIX="/admin"
ROLLBACK_PREFIX="/_oris-chat-shell"
HTPASSWD_FILE="/etc/nginx/.htpasswd-openclaw"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="/etc/nginx/oris-backups"
BACKUP_FILE="$BACKUP_DIR/oris-dev-employee-web-console.readonly.conf.$STAMP.bak"
CANDIDATE="$(mktemp /tmp/oris-native-openclaw-nginx-${STAMP}-XXXXXX.conf)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-migration-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/migration.log"
RESULT_JSON="$TMP_ROOT/migration.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_migration"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-migration-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-migration-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
MIGRATION_APPLIED="NO"
ROLLBACK_PERFORMED="NO"
NGINX_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ADMIN_STATUS="000"
PUBLIC_ROLLBACK_STATUS="000"
INTAKE_LOOPBACK_ONLY="unknown"
PRODUCT_README_PRESERVED="unknown"
PRODUCT_HEAD="unknown"
PRODUCT_REMOTE_MAIN="unknown"
PRODUCT_STATUS="unknown"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_MIGRATION_FAILURE"

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
  echo "NGINX_TEST=$NGINX_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
  echo "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "PRODUCT_HEAD=$PRODUCT_HEAD"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_STATUS=$PRODUCT_STATUS"
  echo "PRODUCT_README_PRESERVED=$PRODUCT_README_PRESERVED"
  echo "BACKUP_FILE=$BACKUP_FILE"
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
  if [ -f "$BACKUP_FILE" ]; then
    sudo -n cp "$BACKUP_FILE" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || return 1
    sudo -n nginx -t >> "$RUN_LOG" 2>&1 || return 1
    sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1 || return 1
    ROLLBACK_PERFORMED="YES"
    MIGRATION_APPLIED="NO"
    return 0
  fi
  return 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

for cmd in git curl python3 sha256sum sudo nginx systemctl ss; do
  command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done

[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"
[ -f "$EFFECTIVE_CONF" ] || fail_now "effective_nginx_config_missing" "RESTORE_EFFECTIVE_NGINX_CONFIG"
[ -f "$HTPASSWD_FILE" ] || fail_now "admin_htpasswd_missing" "RESTORE_EXISTING_ADMIN_HTPASSWD"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=REVERSIBLE_NATIVE_OPENCLAW_NGINX_MIGRATION"
log "EFFECTIVE_CONF=$EFFECTIVE_CONF"
log "PRODUCT_MUTATION_ALLOWED=NO"

ACTIVE_QUEUE_COUNT="$(find "$ORIS_REPO/orchestration/dev_employee_queue" -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' -o -name '*.claimed.json' -o -name '*.planning.json' -o -name '*.executing.json' -o -name '*.committing.json' -o -name '*.pushing.json' -o -name '*.cancelling.json' \) 2>/dev/null | wc -l | tr -d ' ')"
log "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
[ "$ACTIVE_QUEUE_COUNT" = "0" ] || fail_now "active_queue_present" "WAIT_FOR_QUEUE_TO_DRAIN"

PRODUCT_HEAD="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_MAIN="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_RAW="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
PRODUCT_STATUS="$(printf '%s\n' "$PRODUCT_STATUS_RAW" | tr '\n' ';' | sed 's/;$//')"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
log "PRODUCT_HEAD=$PRODUCT_HEAD"
log "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
log "PRODUCT_STATUS=$PRODUCT_STATUS"
log "README_HASH_BEFORE=$README_HASH_BEFORE"
[ "$PRODUCT_HEAD" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_MAIN" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_RAW" = " M README.md" ] || fail_now "unexpected_product_worktree_state" "REVIEW_PRODUCT_BASELINE"

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"

OPENCLAW_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$OPENCLAW_UPSTREAM/" 2>/dev/null || true)"
CONSOLE_STATUS="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "$CONSOLE_UPSTREAM/" 2>/dev/null || true)"
log "OPENCLAW_DIRECT_STATUS=$OPENCLAW_STATUS"
log "CONSOLE_DIRECT_STATUS=$CONSOLE_STATUS"
[ "$OPENCLAW_STATUS" = "200" ] || fail_now "openclaw_direct_root_unhealthy" "REPAIR_OPENCLAW_BEFORE_MIGRATION"
case "$CONSOLE_STATUS" in 200|301|302|401|403) ;; *) fail_now "console_direct_root_unhealthy" "REPAIR_CONSOLE_BEFORE_MIGRATION" ;; esac

INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
case "$INTAKE_LISTENER" in
  127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;;
  *) INTAKE_LOOPBACK_ONLY="NO" ;;
esac
log "INTAKE_LISTENER=$INTAKE_LISTENER"
log "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || fail_now "intake_not_loopback_only" "RESTORE_INTAKE_PRIVATE_BINDING"

cat > "$CANDIDATE" <<'NGINX'
server {
    listen 443 ssl http2;
    server_name control.orisfy.com;

    ssl_certificate /etc/letsencrypt/live/control.orisfy.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/control.orisfy.com/privkey.pem;

    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy no-referrer always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header X-Frame-Options DENY always;
    add_header Cache-Control no-cache always;

    location = /admin {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
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
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
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
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
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
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
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

    location = /api/goals {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
        proxy_pass http://127.0.0.1:18893/api/goals;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location ^~ /api/goals/ {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
        proxy_pass http://127.0.0.1:18893;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /api/projects {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
        proxy_pass http://127.0.0.1:18893/api/projects;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location = /api/chat/messages {
        auth_basic "ORIS Admin";
        auth_basic_user_file /etc/nginx/.htpasswd-openclaw;
        proxy_pass http://127.0.0.1:18893/api/chat/messages;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
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
    }
}

server {
    listen 80;
    server_name control.orisfy.com;
    return 301 https://$host$request_uri;
}
NGINX

sudo -n mkdir -p "$BACKUP_DIR" >> "$RUN_LOG" 2>&1 || fail_now "backup_directory_create_failed" "CHECK_SUDO_PERMISSIONS"
sudo -n cp "$EFFECTIVE_CONF" "$BACKUP_FILE" >> "$RUN_LOG" 2>&1 || fail_now "nginx_backup_failed" "CHECK_SUDO_PERMISSIONS"
log "BACKUP_FILE=$BACKUP_FILE"

sudo -n cp "$CANDIDATE" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || fail_now "candidate_install_failed" "CHECK_SUDO_PERMISSIONS"
if sudo -n nginx -t >> "$RUN_LOG" 2>&1; then
  NGINX_TEST="PASS"
else
  NGINX_TEST="FAILED"
  rollback_nginx || true
  fail_now "nginx_test_failed" "READ_MIGRATION_EVIDENCE"
fi

if sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1; then
  NGINX_RELOAD="PASS"
  MIGRATION_APPLIED="YES"
else
  NGINX_RELOAD="FAILED"
  rollback_nginx || true
  fail_now "nginx_reload_failed" "READ_MIGRATION_EVIDENCE"
fi

sleep 2
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -o "$TMP_ROOT/public-root.body" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
PUBLIC_ADMIN_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN$ADMIN_PREFIX" 2>/dev/null || true)"
PUBLIC_ROLLBACK_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' "https://$DOMAIN$ROLLBACK_PREFIX" 2>/dev/null || true)"
ROOT_BODY_SHA="$(sha256sum "$TMP_ROOT/public-root.body" 2>/dev/null | awk '{print $1}')"
DIRECT_BODY_SHA="$(curl -sS --max-time 10 "$OPENCLAW_UPSTREAM/" 2>/dev/null | sha256sum | awk '{print $1}')"
log "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
log "PUBLIC_ADMIN_STATUS=$PUBLIC_ADMIN_STATUS"
log "PUBLIC_ROLLBACK_STATUS=$PUBLIC_ROLLBACK_STATUS"
log "PUBLIC_ROOT_BODY_SHA256=$ROOT_BODY_SHA"
log "DIRECT_OPENCLAW_BODY_SHA256=$DIRECT_BODY_SHA"

if [ "$PUBLIC_ROOT_STATUS" != "200" ] || [ -z "$ROOT_BODY_SHA" ] || [ "$ROOT_BODY_SHA" != "$DIRECT_BODY_SHA" ]; then
  rollback_nginx || true
  fail_now "public_root_not_native_openclaw" "READ_MIGRATION_EVIDENCE"
fi
case "$PUBLIC_ADMIN_STATUS" in 401|403) ;; *) rollback_nginx || true; fail_now "admin_route_not_restricted" "READ_MIGRATION_EVIDENCE" ;; esac
case "$PUBLIC_ROLLBACK_STATUS" in 401|403) ;; *) rollback_nginx || true; fail_now "rollback_route_not_restricted" "READ_MIGRATION_EVIDENCE" ;; esac

README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
if [ "$README_HASH_BEFORE" = "$README_HASH_AFTER" ] && [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_MAIN" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_RAW" ]; then
  PRODUCT_README_PRESERVED="YES"
else
  PRODUCT_README_PRESERVED="NO"
  rollback_nginx || true
  fail_now "product_repository_changed_during_migration" "RESTORE_PRODUCT_BASELINE"
fi

RESULT="MIGRATED"
NEXT_ACTION="BROWSER_ACCEPT_NATIVE_OPENCLAW_NEW_HISTORY_SWITCH_CLEAR_AND_ADMIN"

python3 - "$RESULT_JSON" <<PY
import json
from pathlib import Path
payload = {
  "task_id": "$TASK_ID",
  "checked_at": "$STAMP",
  "result": "$RESULT",
  "failure_code": "$FAILURE_CODE",
  "migration_applied": "$MIGRATION_APPLIED" == "YES",
  "rollback_performed": "$ROLLBACK_PERFORMED" == "YES",
  "nginx_test": "$NGINX_TEST",
  "nginx_reload": "$NGINX_RELOAD",
  "public": {
    "root_status": "$PUBLIC_ROOT_STATUS",
    "admin_status_without_credentials": "$PUBLIC_ADMIN_STATUS",
    "rollback_status_without_credentials": "$PUBLIC_ROLLBACK_STATUS",
    "root_matches_direct_openclaw": "$ROOT_BODY_SHA" == "$DIRECT_BODY_SHA"
  },
  "routing": {
    "root_upstream": "$OPENCLAW_UPSTREAM",
    "admin_upstream": "$CONSOLE_UPSTREAM",
    "rollback_upstream": "$CONSOLE_UPSTREAM",
    "intake_publicly_exposed": False
  },
  "safety": {
    "backup_file": "$BACKUP_FILE",
    "product_readme_preserved": "$PRODUCT_README_PRESERVED" == "YES",
    "product_task_submitted": False,
    "openclaw_reinstalled_or_upgraded": False
  },
  "next_action": "$NEXT_ACTION"
}
Path("$RESULT_JSON").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

if ! git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1; then
  fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
fi
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY'
import json, sys
from pathlib import Path
src_log, dst_log, src_json, dst_json = map(Path, sys.argv[1:])
lines = [line.rstrip(" \t\r") for line in src_log.read_text(encoding="utf-8", errors="replace").splitlines()]
dst_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
payload = json.loads(src_json.read_text(encoding="utf-8"))
dst_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw migration $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
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
