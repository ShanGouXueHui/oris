#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
EFFECTIVE_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
BACKUP_DIR="/etc/nginx/oris-backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-rollback-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/rollback.log"
RESULT_JSON="$TMP_ROOT/rollback.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_migration"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rollback-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rollback-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
BACKUP_FILE=""
NGINX_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_ROLLBACK_FAILURE"

umask 077
: > "$RUN_LOG"
cleanup() {
  if [ -d "$WORKTREE" ]; then git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true; fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT
log() { printf '%s\n' "$*" >> "$RUN_LOG"; }
summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BACKUP_FILE=$BACKUP_FILE"
  echo "NGINX_TEST=$NGINX_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}
fail_now() { FAILURE_CODE="$1"; NEXT_ACTION="$2"; RESULT="FAILED"; summary; exit 1; }

[ "$(id -un 2>/dev/null)" = "admin" ] || fail_now "wrong_linux_user" "RUN_AS_ADMIN"
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$BACKUP_DIR" ] || fail_now "backup_directory_missing" "INSPECT_NGINX_BACKUPS"

BACKUP_FILE="$(find "$BACKUP_DIR" -maxdepth 1 -type f -name 'oris-dev-employee-web-console.readonly.conf.*.bak' -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1{$1=""; sub(/^ /,""); print; exit}')"
[ -n "$BACKUP_FILE" ] && [ -f "$BACKUP_FILE" ] || fail_now "migration_backup_missing" "INSPECT_NGINX_BACKUPS"
log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "BACKUP_FILE=$BACKUP_FILE"

sudo -n cp "$BACKUP_FILE" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || fail_now "backup_restore_failed" "CHECK_SUDO_PERMISSIONS"
if sudo -n nginx -t >> "$RUN_LOG" 2>&1; then NGINX_TEST="PASS"; else NGINX_TEST="FAILED"; fail_now "restored_nginx_test_failed" "INSPECT_RESTORED_CONFIG"; fi
if sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1; then NGINX_RELOAD="PASS"; else NGINX_RELOAD="FAILED"; fail_now "restored_nginx_reload_failed" "INSPECT_NGINX_SERVICE"; fi
sleep 2
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -o /dev/null -w '%{http_code}' https://control.orisfy.com/ 2>/dev/null || true)"
case "$PUBLIC_ROOT_STATUS" in 200|301|302|401|403) ;; *) fail_now "public_root_unhealthy_after_rollback" "INSPECT_PUBLIC_ROUTE" ;; esac
RESULT="ROLLED_BACK"
NEXT_ACTION="VERIFY_CUSTOM_CONSOLE_AND_REDESIGN_MIGRATION"

python3 - "$RESULT_JSON" <<PY
import json
from pathlib import Path
Path("$RESULT_JSON").write_text(json.dumps({"task_id":"$TASK_ID","checked_at":"$STAMP","result":"$RESULT","backup_file":"$BACKUP_FILE","nginx_test":"$NGINX_TEST","nginx_reload":"$NGINX_RELOAD","public_root_status":"$PUBLIC_ROOT_STATUS","product_repository_changed":False,"next_action":"$NEXT_ACTION"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text("\n".join(x.rstrip(" \t\r") for x in sl.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
dj.write_text(json.dumps(json.loads(sj.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw rollback $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
[ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && EVIDENCE_REMOTE_VERIFIED="YES" || fail_now "evidence_remote_sha_mismatch" "VERIFY_ORIS_REMOTE_MAIN"
summary
exit 0
