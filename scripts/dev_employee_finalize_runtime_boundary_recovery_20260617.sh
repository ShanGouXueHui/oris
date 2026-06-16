#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="finalize-runtime-boundary-recovery-20260617"
STASH_COMMIT="39402142a31232ba578205adddb40234f58919f1"
ARCHIVE_ROOT="/home/admin/.local/state/oris/stash_recovery/20260617025439"
EXPECTED_ARCHIVE_MANIFEST="e80cbc3b0bb473cfd6b0c8d013cc6979ba8d7274684c1f24ce3ce5ef90baca5e"
STAMP="$(date +%Y%m%d%H%M%S)"
FINAL_ARCHIVE="$ARCHIVE_ROOT/finalize-$STAMP"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/finalize-runtime-boundary-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/finalize-runtime-boundary-$STAMP.json"

OPENCLAW_SERVICE="openclaw-gateway.service"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
WEB_SERVICE="oris-dev-employee-web-console.service"

RUNTIME_FILES=(
  "logs/dev_employee/free_mesh_latency_events.jsonl"
  "orchestration/active_routing.json"
  "orchestration/execution_log.jsonl"
  "orchestration/runtime_plan.json"
  "orchestration/runtime_state.json"
)

ALLOWED_TRACKED_DRIFT=(
  ".gitignore"
  "docs/RUNTIME_STATE_GIT_BOUNDARY_2026-06-17.md"
  "scripts/dev_employee_apply_source_runtime_recovery_20260617.sh"
  "scripts/dev_employee_inspect_runtime_stash_20260617.sh"
  "scripts/dev_employee_reconcile_runtime_stash_20260617.sh"
  "scripts/dev_employee_reconcile_runtime_stash_v2_20260617.sh"
  "scripts/dev_employee_resume_source_runtime_recovery_20260617.sh"
  "scripts/dev_employee_resume_source_runtime_recovery_v2_20260617.sh"
  "scripts/dev_employee_three_way_source_merge.py"
  "scripts/dev_employee_three_way_source_merge_v2.py"
)

RESULT="FAILED"
ARCHIVE_VERIFIED="NOT_RUN"
TRACKED_DRIFT_GUARD="NOT_RUN"
TRACKED_STATE_ARCHIVED="NOT_RUN"
TRACKED_WORKTREE_SYNC="NOT_RUN"
LOCAL_BRANCH_SYNC="NOT_RUN"
CURRENT_RUNTIME_FILES_PRESERVED="NOT_RUN"
RUNTIME_FILES_UNTRACKED="NOT_RUN"
RUNTIME_FILES_IGNORED="NOT_RUN"
RAW_CHAT_DATA_IGNORED="NOT_RUN"
STASH_FOUND="NO"
STASH_DROPPED="NO"
DEPLOYMENT_ACCEPTANCE="NOT_VERIFIED"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
FINAL_ARCHIVE_MANIFEST_SHA256=""
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_RUNTIME_BOUNDARY_FINALIZATION"
STASH_REF=""

mkdir -p "$LOG_DIR" "$FINAL_ARCHIVE"
chmod 700 "$FINAL_ARCHIVE"
: > "$RUN_LOG"

log() { printf '%s\n' "$*" | tee -a "$RUN_LOG"; }
service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }

is_allowed_drift() {
  local candidate="$1"
  local allowed
  for allowed in "${ALLOWED_TRACKED_DRIFT[@]}"; do
    [ "$candidate" = "$allowed" ] && return 0
  done
  return 1
}

validate_runtime() {
  python3 - "$ORIS" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
for p in ['orchestration/active_routing.json','orchestration/runtime_plan.json','orchestration/runtime_state.json']:
    path=root/p
    assert path.is_file(),p
    assert isinstance(json.loads(path.read_text(encoding='utf-8')),dict),p
for p in ['orchestration/execution_log.jsonl','logs/dev_employee/free_mesh_latency_events.jsonl']:
    path=root/p
    assert path.is_file(),p
    for n,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        if line.strip(): assert isinstance(json.loads(line),dict),(p,n)
PY
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
 'task_id':'$TASK_ID','checked_at':'$(date -Is)','result':'$RESULT','failure_code':'$FAILURE_CODE' or None,
 'archive_verified':'$ARCHIVE_VERIFIED','tracked_drift_guard':'$TRACKED_DRIFT_GUARD',
 'tracked_state_archived':'$TRACKED_STATE_ARCHIVED','tracked_worktree_sync':'$TRACKED_WORKTREE_SYNC',
 'local_branch_sync':'$LOCAL_BRANCH_SYNC','current_runtime_files_preserved':'$CURRENT_RUNTIME_FILES_PRESERVED',
 'runtime_files_untracked':'$RUNTIME_FILES_UNTRACKED','runtime_files_ignored':'$RUNTIME_FILES_IGNORED',
 'raw_chat_data_ignored':'$RAW_CHAT_DATA_IGNORED','stash_found':'$STASH_FOUND','stash_dropped':'$STASH_DROPPED',
 'deployment_acceptance':'$DEPLOYMENT_ACCEPTANCE','product_sha_unchanged':'$PRODUCT_SHA_UNCHANGED',
 'product_worktree_clean':'$PRODUCT_WORKTREE_CLEAN','private_archive_path':'$FINAL_ARCHIVE',
 'final_archive_manifest_sha256':'$FINAL_ARCHIVE_MANIFEST_SHA256' or None,
 'services':{'openclaw_gateway':'$(service_state "$OPENCLAW_SERVICE")','bridge':'$(service_state "$BRIDGE_SERVICE")','intake':'$(service_state "$INTAKE_SERVICE")','web_console':'$(service_state "$WEB_SERVICE")'},
 'openclaw_reinstalled':False,'agent_harness_added':True,'real_product_task_submitted':False,'real_product_change':False,
 'next_action':'$NEXT_ACTION'
}
open('$EVIDENCE_JSON','w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
}

commit_evidence() {
  git add -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" >/tmp/oris-finalize-runtime-add-$STAMP.log 2>&1 || return 1
  git commit --only -m "test(runtime): finalize runtime boundary recovery $STAMP" -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" >/tmp/oris-finalize-runtime-commit-$STAMP.log 2>&1 || return 1
  git push origin main >/tmp/oris-finalize-runtime-push-$STAMP.log 2>&1 || return 1
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "ARCHIVE_VERIFIED=$ARCHIVE_VERIFIED"
  echo "TRACKED_DRIFT_GUARD=$TRACKED_DRIFT_GUARD"
  echo "TRACKED_STATE_ARCHIVED=$TRACKED_STATE_ARCHIVED"
  echo "TRACKED_WORKTREE_SYNC=$TRACKED_WORKTREE_SYNC"
  echo "LOCAL_BRANCH_SYNC=$LOCAL_BRANCH_SYNC"
  echo "CURRENT_RUNTIME_FILES_PRESERVED=$CURRENT_RUNTIME_FILES_PRESERVED"
  echo "RUNTIME_FILES_UNTRACKED=$RUNTIME_FILES_UNTRACKED"
  echo "RUNTIME_FILES_IGNORED=$RUNTIME_FILES_IGNORED"
  echo "RAW_CHAT_DATA_IGNORED=$RAW_CHAT_DATA_IGNORED"
  echo "STASH_FOUND=$STASH_FOUND"
  echo "STASH_DROPPED=$STASH_DROPPED"
  echo "DEPLOYMENT_ACCEPTANCE=$DEPLOYMENT_ACCEPTANCE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state "$OPENCLAW_SERVICE")"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "PRIVATE_ARCHIVE=$FINAL_ARCHIVE"
  echo "FINAL_ARCHIVE_MANIFEST_SHA256=$FINAL_ARCHIVE_MANIFEST_SHA256"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "OPENCLAW_REINSTALLED=NO"
  echo "AGENT_HARNESS_ADDED=YES"
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
  summary
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

log "===== timestamp ====="; log "$(date -Is)"; log "HEAD=$(git rev-parse HEAD 2>/dev/null || true)"

[ -f "$ARCHIVE_ROOT/manifest.sha256" ] || fail "source_runtime_archive_manifest_missing" "INSPECT_PRIVATE_ARCHIVE"
ACTUAL_ARCHIVE_MANIFEST="$(sha256sum "$ARCHIVE_ROOT/manifest.sha256" | awk '{print $1}')"
[ "$ACTUAL_ARCHIVE_MANIFEST" = "$EXPECTED_ARCHIVE_MANIFEST" ] || fail "source_runtime_archive_manifest_mismatch" "INSPECT_PRIVATE_ARCHIVE"
ARCHIVE_VERIFIED="PASS"

STASH_LINE="$(git stash list --format='%gd|%H|%gs' | grep -F "$STASH_COMMIT" | head -n 1 || true)"
[ -n "$STASH_LINE" ] || fail "target_stash_not_found" "INSPECT_GIT_STASH_LIST"
STASH_REF="${STASH_LINE%%|*}"; STASH_FOUND="YES"

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"

mapfile -t DIRTY_PATHS < <({ git diff --name-only; git diff --cached --name-only; } | sed '/^$/d' | sort -u)
for path in "${DIRTY_PATHS[@]}"; do
  log "TRACKED_DRIFT=$path"
  is_allowed_drift "$path" || fail "unexpected_tracked_drift" "MANUAL_REVIEW_REQUIRED"
done
TRACKED_DRIFT_GUARD="PASS"

git diff --binary > "$FINAL_ARCHIVE/unstaged.patch" || fail "unstaged_patch_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
git diff --cached --binary > "$FINAL_ARCHIVE/staged.patch" || fail "staged_patch_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
git status --porcelain=v1 --untracked-files=no > "$FINAL_ARCHIVE/status.txt" || fail "status_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
printf '%s\n' "created_at=$(date -Is)" "head=$(git rev-parse HEAD)" "origin_main=$(git rev-parse origin/main)" "stash_commit=$STASH_COMMIT" > "$FINAL_ARCHIVE/metadata.txt"
chmod -R go-rwx "$FINAL_ARCHIVE"
TRACKED_STATE_ARCHIVED="PASS"

validate_runtime >> "$RUN_LOG" 2>&1 || fail "runtime_content_invalid_before_sync" "INSPECT_RUNTIME_FILES"

# Restore only Git-tracked content from origin/main. Runtime files are already absent
# from the origin index and therefore remain as untracked local operational state.
git restore --source=origin/main --staged --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_worktree_restore_failed" "INSPECT_GIT_RESTORE"
TRACKED_WORKTREE_SYNC="PASS"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_LOCAL_GIT_STATE"
LOCAL_BRANCH_SYNC="PASS"

[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "tracked_worktree_not_clean_after_sync" "INSPECT_GIT_STATUS"

for path in "${RUNTIME_FILES[@]}"; do
  git ls-files --error-unmatch "$path" >/dev/null 2>&1 && fail "runtime_file_still_tracked" "FIX_RUNTIME_GIT_BOUNDARY"
  git check-ignore -q "$path" || fail "runtime_file_not_ignored" "FIX_RUNTIME_GIT_BOUNDARY"
  [ -f "$path" ] || fail "runtime_file_missing_after_sync" "RESTORE_RUNTIME_FROM_PRIVATE_ARCHIVE"
done
RUNTIME_FILES_UNTRACKED="PASS"; RUNTIME_FILES_IGNORED="PASS"
validate_runtime >> "$RUN_LOG" 2>&1 || fail "runtime_content_invalid_after_sync" "RESTORE_RUNTIME_FROM_PRIVATE_ARCHIVE"
CURRENT_RUNTIME_FILES_PRESERVED="PASS"

git check-ignore -q orchestration/dev_employee_chat_sessions/example.json || fail "chat_sessions_not_ignored" "FIX_CONVERSATION_DATA_GIT_BOUNDARY"
git check-ignore -q logs/dev_employee/agent_harness/example.jsonl || fail "harness_trace_not_ignored" "FIX_CONVERSATION_DATA_GIT_BOUNDARY"
RAW_CHAT_DATA_IGNORED="PASS"

find "$FINAL_ARCHIVE" -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 sha256sum > "$FINAL_ARCHIVE/manifest.sha256" || fail "final_archive_manifest_failed" "INSPECT_PRIVATE_ARCHIVE"
FINAL_ARCHIVE_MANIFEST_SHA256="$(sha256sum "$FINAL_ARCHIVE/manifest.sha256" | awk '{print $1}')"
[ -n "$FINAL_ARCHIVE_MANIFEST_SHA256" ] || fail "final_archive_manifest_empty" "INSPECT_PRIVATE_ARCHIVE"
chmod -R go-rwx "$FINAL_ARCHIVE"

git stash drop "$STASH_REF" >> "$RUN_LOG" 2>&1 || fail "stash_drop_failed" "INSPECT_GIT_STASH_LIST"
git stash list --format='%H' | grep -Fxq "$STASH_COMMIT" && fail "stash_commit_still_listed" "INSPECT_GIT_STASH_LIST"
STASH_DROPPED="YES"

for service in "$OPENCLAW_SERVICE" "$BRIDGE_SERVICE" "$INTAKE_SERVICE" "$WEB_SERVICE"; do
  [ "$(service_state "$service")" = "active" ] || fail "service_not_active_after_finalization" "INSPECT_USER_SERVICES"
done
WEB_HEALTH="$(curl -fsS http://127.0.0.1:18893/health 2>/dev/null || true)"
python3 - "$WEB_HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys
p=json.loads(sys.argv[1]);assert p.get('service')=='dev_employee_web_console_v5';assert p.get('default_experience')=='conversation';assert p.get('agent_harness_enabled') is True;assert p.get('openclaw_provider_configured') is True
PY
[ "$?" -eq 0 ] || fail "agent_harness_web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
DEPLOYMENT_ACCEPTANCE="PASS"

LOCAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"; REMOTE_SHA="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"; DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
[ -n "$LOCAL_SHA" ] && [ "$LOCAL_SHA" = "$REMOTE_SHA" ] || fail "product_sha_mismatch" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_SHA_UNCHANGED="PASS"
[ -z "$DIRTY" ] || fail "product_worktree_dirty" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_WORKTREE_CLEAN="PASS"

RESULT="PASS"; NEXT_ACTION="REQUEST_CONVERSATIONAL_BROWSER_TEST"
write_evidence
commit_evidence || { RESULT="FAILED"; FAILURE_CODE="finalization_evidence_push_failed"; NEXT_ACTION="RESOLVE_FINALIZATION_EVIDENCE_PUSH"; }
summary
[ "$RESULT" = "PASS" ] && exit 0
exit 1
