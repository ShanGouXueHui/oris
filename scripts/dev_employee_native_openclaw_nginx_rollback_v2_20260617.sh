#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
EFFECTIVE_CONF="/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf"
BACKUP_ROOT="/etc/nginx/oris-backups"
OPENCLAW_DIRECT="http://127.0.0.1:18789/"
EXPECTED_PRODUCT_HEAD="927f1968cc86bfd5213670f4eaa171fc1a3be620"
EXPECTED_PRODUCT_STATUS=" M README.md"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-native-openclaw-rollback-v2-${STAMP}-XXXXXX)"
RUN_LOG="$TMP_ROOT/rollback.log"
RESULT_JSON="$TMP_ROOT/rollback.json"
WORKTREE="$TMP_ROOT/evidence-worktree"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_migration"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rollback-v2-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-rollback-v2-$STAMP.json"

RESULT="FAILED"
FAILURE_CODE=""
BACKUP_DIR=""
NGINX_TEST="NOT_RUN"
NGINX_RELOAD="NOT_RUN"
PUBLIC_ROOT_STATUS="000"
PUBLIC_ROOT_IS_OPENCLAW="unknown"
NGINX_CONFLICT_WARNING_COUNT="unknown"
PRODUCT_BASELINE_PRESERVED="NO"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_NATIVE_OPENCLAW_ROLLBACK_V2_FAILURE"

umask 077
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true; fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "BACKUP_DIR=$BACKUP_DIR"
  echo "NGINX_TEST=$NGINX_TEST"
  echo "NGINX_RELOAD=$NGINX_RELOAD"
  echo "PUBLIC_ROOT_STATUS=$PUBLIC_ROOT_STATUS"
  echo "PUBLIC_ROOT_IS_OPENCLAW=$PUBLIC_ROOT_IS_OPENCLAW"
  echo "NGINX_CONFLICT_WARNING_COUNT=$NGINX_CONFLICT_WARNING_COUNT"
  echo "PRODUCT_BASELINE_PRESERVED=$PRODUCT_BASELINE_PRESERVED"
  echo "LEGACY_DUPLICATE_RESTORED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() { FAILURE_CODE="$1"; NEXT_ACTION="$2"; RESULT="FAILED"; summary; exit 1; }
log() { printf '%s\n' "$*" >> "$RUN_LOG"; }

[ "$(id -un 2>/dev/null)" = "admin" ] || fail_now "wrong_linux_user" "RUN_AS_ADMIN"
for cmd in git curl python3 sha256sum sudo nginx systemctl grep find sort awk; do command -v "$cmd" >/dev/null 2>&1 || fail_now "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"; done
[ -d "$ORIS_REPO/.git" ] || fail_now "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"
[ -d "$PRODUCT_REPO/.git" ] || fail_now "product_repo_missing" "RESTORE_PRODUCT_REPOSITORY"

BACKUP_DIR="$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'native-openclaw-v2-*' -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR==1{$1=""; sub(/^ /,""); print; exit}')"
BACKUP_CONF="$BACKUP_DIR/oris-dev-employee-web-console.readonly.conf.bak"
[ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_CONF" ] || fail_now "native_openclaw_v2_backup_missing" "INSPECT_NGINX_BACKUPS"

PRODUCT_HEAD_BEFORE="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_BEFORE="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_BEFORE="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_BEFORE="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
[ "$PRODUCT_HEAD_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_head" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_REMOTE_BEFORE" = "$EXPECTED_PRODUCT_HEAD" ] || fail_now "unexpected_product_remote_main" "REVIEW_PRODUCT_BASELINE"
[ "$PRODUCT_STATUS_BEFORE" = "$EXPECTED_PRODUCT_STATUS" ] || fail_now "unexpected_product_status" "REVIEW_PRODUCT_BASELINE"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "BACKUP_DIR=$BACKUP_DIR"
log "LEGACY_DUPLICATE_RESTORED=NO"

sudo -n cp "$BACKUP_CONF" "$EFFECTIVE_CONF" >> "$RUN_LOG" 2>&1 || fail_now "backup_restore_failed" "CHECK_SUDO_PERMISSIONS"
if sudo -n nginx -t >> "$RUN_LOG" 2>&1; then NGINX_TEST="PASS"; else NGINX_TEST="FAILED"; fail_now "restored_nginx_test_failed" "INSPECT_RESTORED_CONFIG"; fi
if sudo -n systemctl reload nginx >> "$RUN_LOG" 2>&1; then NGINX_RELOAD="PASS"; else NGINX_RELOAD="FAILED"; fail_now "restored_nginx_reload_failed" "INSPECT_NGINX_SERVICE"; fi
sleep 2

PUBLIC_BODY="$TMP_ROOT/public.body"
DIRECT_BODY="$TMP_ROOT/direct.body"
PUBLIC_ROOT_STATUS="$(curl -sS -k --max-time 10 -H 'Cache-Control: no-cache' -o "$PUBLIC_BODY" -w '%{http_code}' "https://$DOMAIN/" 2>/dev/null || true)"
curl -sS --max-time 10 -H 'Cache-Control: no-cache' "$OPENCLAW_DIRECT" -o "$DIRECT_BODY" 2>/dev/null || true
PUBLIC_SHA="$(sha256sum "$PUBLIC_BODY" 2>/dev/null | awk '{print $1}')"
DIRECT_SHA="$(sha256sum "$DIRECT_BODY" 2>/dev/null | awk '{print $1}')"
if [ -n "$PUBLIC_SHA" ] && [ "$PUBLIC_SHA" = "$DIRECT_SHA" ]; then PUBLIC_ROOT_IS_OPENCLAW="YES"; else PUBLIC_ROOT_IS_OPENCLAW="NO"; fi
[ "$PUBLIC_ROOT_IS_OPENCLAW" = "NO" ] || fail_now "rollback_root_still_openclaw" "INSPECT_EFFECTIVE_NGINX_CONFIG"
case "$PUBLIC_ROOT_STATUS" in 200|301|302|401|403) ;; *) fail_now "public_root_unhealthy_after_rollback" "INSPECT_PUBLIC_ROUTE" ;; esac

NGINX_DUMP="$TMP_ROOT/nginx-T.txt"
sudo -n nginx -T > "$NGINX_DUMP" 2>&1 || fail_now "nginx_dump_failed" "INSPECT_EFFECTIVE_NGINX_CONFIG"
NGINX_CONFLICT_WARNING_COUNT="$(grep -Eic 'conflicting server name.*control\.orisfy\.com' "$NGINX_DUMP" || true)"
[ "$NGINX_CONFLICT_WARNING_COUNT" = "0" ] || fail_now "nginx_conflict_returned_after_rollback" "INSPECT_LOADED_NGINX_FILES"

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER="$(git -C "$PRODUCT_REPO" status --porcelain=v1 --untracked-files=all 2>/dev/null || true)"
README_HASH_AFTER="$(sha256sum "$PRODUCT_REPO/README.md" 2>/dev/null | awk '{print $1}')"
if [ "$PRODUCT_HEAD_AFTER" = "$PRODUCT_HEAD_BEFORE" ] && [ "$PRODUCT_REMOTE_AFTER" = "$PRODUCT_REMOTE_BEFORE" ] && [ "$PRODUCT_STATUS_AFTER" = "$PRODUCT_STATUS_BEFORE" ] && [ "$README_HASH_AFTER" = "$README_HASH_BEFORE" ]; then PRODUCT_BASELINE_PRESERVED="YES"; else fail_now "product_baseline_changed_during_rollback" "RESTORE_PRODUCT_BASELINE"; fi

RESULT="ROLLED_BACK_V2"
NEXT_ACTION="INSPECT_BROWSER_ACCEPTANCE_V2_FAILURES_BEFORE_RETRY"

export TASK_ID STAMP RESULT FAILURE_CODE BACKUP_DIR NGINX_TEST NGINX_RELOAD PUBLIC_ROOT_STATUS PUBLIC_ROOT_IS_OPENCLAW NGINX_CONFLICT_WARNING_COUNT PRODUCT_BASELINE_PRESERVED NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" <<'PY_RESULT'
import json,os,sys
from pathlib import Path
payload={"task_id":os.environ.get("TASK_ID"),"checked_at":os.environ.get("STAMP"),"result":os.environ.get("RESULT"),"failure_code":os.environ.get("FAILURE_CODE"),"backup_dir":os.environ.get("BACKUP_DIR"),"nginx_test":os.environ.get("NGINX_TEST"),"nginx_reload":os.environ.get("NGINX_RELOAD"),"public_root_status":os.environ.get("PUBLIC_ROOT_STATUS"),"public_root_is_openclaw":os.environ.get("PUBLIC_ROOT_IS_OPENCLAW")=="YES","nginx_conflict_warning_count":int(os.environ.get("NGINX_CONFLICT_WARNING_COUNT","-1")),"safety":{"product_baseline_preserved":os.environ.get("PRODUCT_BASELINE_PRESERVED")=="YES","legacy_duplicate_restored":False,"product_repository_mutated":False,"openclaw_config_mutated":False,"secret_values_recorded":False},"next_action":os.environ.get("NEXT_ACTION"),"evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True}}
Path(sys.argv[1]).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_RESULT

git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1 || fail_now "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1 || fail_now "evidence_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
python3 - "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL" "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL" <<'PY_NORMALIZE'
import json,sys
from pathlib import Path
sl,dl,sj,dj=map(Path,sys.argv[1:])
dl.write_text("\n".join(line.rstrip(" \t\r") for line in sl.read_text(encoding="utf-8",errors="replace").splitlines())+"\n",encoding="utf-8")
dj.write_text(json.dumps(json.loads(sj.read_text(encoding="utf-8")),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY_NORMALIZE
git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL" || fail_now "evidence_git_add_failed" "INSPECT_EVIDENCE_WORKTREE"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail_now "evidence_diff_check_failed" "INSPECT_EVIDENCE_FORMAT"
git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw rollback v2 $STAMP" >/dev/null 2>&1 || fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] && [ -n "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi
summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
