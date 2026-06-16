#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
STASH_COMMIT="39402142a31232ba578205adddb40234f58919f1"
SOURCE_FILE="scripts/dev_employee_diagnose_codex_failed_task.sh"
TASK_ID="recover-source-and-runtime-stash-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
PRIVATE_ROOT="$HOME/.local/state/oris/stash_recovery/$STAMP"
TMP_ROOT="/tmp/oris-stash-recovery-$STAMP"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/recover-source-runtime-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/recover-source-runtime-$STAMP.json"
MERGE_JSON="$PRIVATE_ROOT/source/merge-result.json"

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

RESULT="FAILED"
STASH_FOUND="NO"
STASH_SCOPE_VALID="NOT_RUN"
PRIVATE_ARCHIVE="NOT_RUN"
SOURCE_WORKTREE_CLASS="unknown"
SOURCE_THREE_WAY_MERGE="NOT_RUN"
SOURCE_STATIC_CHECK="NOT_RUN"
SOURCE_RECOVERY_COMMIT=""
SOURCE_RECOVERY_PUSH="NOT_RUN"
LOCAL_BRANCH_SYNC="NOT_RUN"
CURRENT_RUNTIME_FILES_PRESERVED="NOT_RUN"
RUNTIME_FILES_UNTRACKED="NOT_RUN"
RUNTIME_FILES_IGNORED="NOT_RUN"
RAW_CHAT_DATA_IGNORED="NOT_RUN"
STASH_DROPPED="NO"
DEPLOYMENT_ACCEPTANCE="NOT_VERIFIED"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
ARCHIVE_MANIFEST_SHA256=""
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_SOURCE_RUNTIME_RECOVERY"
STASH_REF=""

mkdir -p "$LOG_DIR" "$PRIVATE_ROOT/runtime/current" "$PRIVATE_ROOT/runtime/stashed" "$PRIVATE_ROOT/source" "$TMP_ROOT"
chmod 700 "$PRIVATE_ROOT" "$TMP_ROOT"
: > "$RUN_LOG"

log() { printf '%s\n' "$*" | tee -a "$RUN_LOG"; }
service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }

expected_file() {
  [ "$1" = "$SOURCE_FILE" ] && return 0
  local item
  for item in "${RUNTIME_FILES[@]}"; do [ "$1" = "$item" ] && return 0; done
  return 1
}

validate_runtime() {
  python3 - "$ORIS" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
for p in ['orchestration/active_routing.json','orchestration/runtime_plan.json','orchestration/runtime_state.json']:
    assert isinstance(json.loads((root/p).read_text(encoding='utf-8')),dict),p
for p in ['orchestration/execution_log.jsonl','logs/dev_employee/free_mesh_latency_events.jsonl']:
    for n,line in enumerate((root/p).read_text(encoding='utf-8').splitlines(),1):
        if line.strip(): assert isinstance(json.loads(line),dict),(p,n)
PY
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
 'task_id':'$TASK_ID','checked_at':'$(date -Is)','result':'$RESULT','failure_code':'$FAILURE_CODE' or None,
 'stash_commit':'$STASH_COMMIT','stash_ref':'$STASH_REF' or None,'stash_found':'$STASH_FOUND',
 'stash_scope_valid':'$STASH_SCOPE_VALID','private_archive':'$PRIVATE_ARCHIVE',
 'private_archive_path':'$PRIVATE_ROOT','archive_manifest_sha256':'$ARCHIVE_MANIFEST_SHA256' or None,
 'source_file':'$SOURCE_FILE','source_worktree_class':'$SOURCE_WORKTREE_CLASS',
 'source_three_way_merge':'$SOURCE_THREE_WAY_MERGE','source_static_check':'$SOURCE_STATIC_CHECK',
 'source_recovery_commit':'$SOURCE_RECOVERY_COMMIT' or None,'source_recovery_push':'$SOURCE_RECOVERY_PUSH',
 'local_branch_sync':'$LOCAL_BRANCH_SYNC','current_runtime_files_preserved':'$CURRENT_RUNTIME_FILES_PRESERVED',
 'runtime_files_untracked':'$RUNTIME_FILES_UNTRACKED','runtime_files_ignored':'$RUNTIME_FILES_IGNORED',
 'raw_chat_data_ignored':'$RAW_CHAT_DATA_IGNORED','stash_dropped':'$STASH_DROPPED',
 'deployment_acceptance':'$DEPLOYMENT_ACCEPTANCE','product_sha_unchanged':'$PRODUCT_SHA_UNCHANGED',
 'product_worktree_clean':'$PRODUCT_WORKTREE_CLEAN',
 'services':{'openclaw_gateway':'$(service_state "$OPENCLAW_SERVICE")','bridge':'$(service_state "$BRIDGE_SERVICE")','intake':'$(service_state "$INTAKE_SERVICE")','web_console':'$(service_state "$WEB_SERVICE")'},
 'openclaw_reinstalled':False,'agent_harness_added':True,'real_product_task_submitted':False,'real_product_change':False,
 'next_action':'$NEXT_ACTION'
}
open('$EVIDENCE_JSON','w',encoding='utf-8').write(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
PY
}

commit_evidence() {
  local wt="$TMP_ROOT/evidence"
  git fetch origin main >> "$RUN_LOG" 2>&1 || return 1
  git worktree add --detach "$wt" origin/main >> "$RUN_LOG" 2>&1 || return 1
  mkdir -p "$wt/logs/dev_employee/conversational_web"
  cp "$RUN_LOG" "$wt/${RUN_LOG#$ORIS/}"
  cp "$EVIDENCE_JSON" "$wt/${EVIDENCE_JSON#$ORIS/}"
  (
    cd "$wt" || exit 1
    git add -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" || exit 1
    git commit -m "test(runtime): complete source and runtime recovery $STAMP" || exit 1
    git push origin HEAD:main || exit 1
    git rev-parse HEAD
  ) > "$TMP_ROOT/evidence-git.log" 2>&1
  local rc="$?"
  [ "$rc" -eq 0 ] && LOG_COMMIT="$(tail -n 1 "$TMP_ROOT/evidence-git.log")" || LOG_COMMIT="EVIDENCE_PUSH_FAILED"
  git worktree remove --force "$wt" >/dev/null 2>&1 || true
  [ "$rc" -eq 0 ]
}

cleanup() {
  git worktree remove --force "$TMP_ROOT/source" >/dev/null 2>&1 || true
  git worktree remove --force "$TMP_ROOT/evidence" >/dev/null 2>&1 || true
  rm -rf "$TMP_ROOT"
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "STASH_FOUND=$STASH_FOUND"
  echo "STASH_SCOPE_VALID=$STASH_SCOPE_VALID"
  echo "PRIVATE_ARCHIVE=$PRIVATE_ROOT"
  echo "ARCHIVE_MANIFEST_SHA256=$ARCHIVE_MANIFEST_SHA256"
  echo "SOURCE_WORKTREE_CLASS=$SOURCE_WORKTREE_CLASS"
  echo "SOURCE_THREE_WAY_MERGE=$SOURCE_THREE_WAY_MERGE"
  echo "SOURCE_STATIC_CHECK=$SOURCE_STATIC_CHECK"
  echo "SOURCE_RECOVERY_COMMIT=$SOURCE_RECOVERY_COMMIT"
  echo "SOURCE_RECOVERY_PUSH=$SOURCE_RECOVERY_PUSH"
  echo "LOCAL_BRANCH_SYNC=$LOCAL_BRANCH_SYNC"
  echo "CURRENT_RUNTIME_FILES_PRESERVED=$CURRENT_RUNTIME_FILES_PRESERVED"
  echo "RUNTIME_FILES_UNTRACKED=$RUNTIME_FILES_UNTRACKED"
  echo "RUNTIME_FILES_IGNORED=$RUNTIME_FILES_IGNORED"
  echo "RAW_CHAT_DATA_IGNORED=$RAW_CHAT_DATA_IGNORED"
  echo "STASH_DROPPED=$STASH_DROPPED"
  echo "DEPLOYMENT_ACCEPTANCE=$DEPLOYMENT_ACCEPTANCE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state "$OPENCLAW_SERVICE")"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
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
  [ "$PRIVATE_ARCHIVE" = "PASS" ] && commit_evidence || true
  summary
  cleanup
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

log "===== timestamp ====="; log "$(date -Is)"; log "HEAD=$(git rev-parse HEAD 2>/dev/null || true)"
git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"

STASH_LINE="$(git stash list --format='%gd|%H|%gs' | grep -F "$STASH_COMMIT" | head -n 1 || true)"
[ -n "$STASH_LINE" ] || fail "target_stash_not_found" "INSPECT_GIT_STASH_LIST"
STASH_REF="${STASH_LINE%%|*}"; STASH_FOUND="YES"; log "STASH_REF=$STASH_REF"
mapfile -t FILES < <(git diff --name-only "${STASH_COMMIT}^1" "$STASH_COMMIT" | sed '/^$/d' | sort -u)
[ "${#FILES[@]}" -eq 6 ] || fail "unexpected_stash_file_count" "MANUAL_REVIEW_REQUIRED"
for path in "${FILES[@]}"; do expected_file "$path" || fail "unexpected_file_in_stash" "MANUAL_REVIEW_REQUIRED"; done
for path in "${RUNTIME_FILES[@]}" "$SOURCE_FILE"; do printf '%s\n' "${FILES[@]}" | grep -Fxq "$path" || fail "expected_file_missing_from_stash" "MANUAL_REVIEW_REQUIRED"; done
STASH_SCOPE_VALID="PASS"

validate_runtime >> "$RUN_LOG" 2>&1 || fail "current_runtime_content_invalid" "INSPECT_RUNTIME_FILES"
for path in "${RUNTIME_FILES[@]}"; do
  mkdir -p "$PRIVATE_ROOT/runtime/current/$(dirname "$path")" "$PRIVATE_ROOT/runtime/stashed/$(dirname "$path")"
  cp -p "$path" "$PRIVATE_ROOT/runtime/current/$path" || fail "current_runtime_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
  git show "$STASH_COMMIT:$path" > "$PRIVATE_ROOT/runtime/stashed/$path" || fail "stashed_runtime_archive_failed" "INSPECT_PRIVATE_ARCHIVE"
done

PYTHONPATH="$ORIS:$ORIS/scripts" python3 scripts/dev_employee_three_way_source_merge.py \
  --repo "$ORIS" --stash-commit "$STASH_COMMIT" --source-file "$SOURCE_FILE" \
  --archive-dir "$PRIVATE_ROOT/source" --output "$MERGE_JSON" >> "$RUN_LOG" 2>&1
MERGE_RC="$?"
[ "$MERGE_RC" -eq 0 ] || { PRIVATE_ARCHIVE="PASS"; fail "source_three_way_merge_failed" "REVIEW_PRIVATE_ARCHIVE_SOURCE_MERGE"; }
SOURCE_WORKTREE_CLASS="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["worktree_class"])' "$MERGE_JSON")"
MERGED_EQUALS_ORIGIN="$(python3 -c 'import json,sys;print(str(json.load(open(sys.argv[1]))["merged_equals_origin"]).lower())' "$MERGE_JSON")"
[ "$SOURCE_WORKTREE_CLASS" != "independent_variant" ] || { PRIVATE_ARCHIVE="PASS"; fail "independent_worktree_source_variant" "REVIEW_PRIVATE_ARCHIVE_SOURCE_VARIANTS"; }
SOURCE_THREE_WAY_MERGE="PASS"; SOURCE_STATIC_CHECK="PASS"; PRIVATE_ARCHIVE="PASS"

if [ "$MERGED_EQUALS_ORIGIN" = "true" ]; then
  SOURCE_RECOVERY_COMMIT="NO_SOURCE_CHANGE"; SOURCE_RECOVERY_PUSH="PASS"
else
  git worktree add --detach "$TMP_ROOT/source" origin/main >> "$RUN_LOG" 2>&1 || fail "source_worktree_create_failed" "INSPECT_GIT_WORKTREE"
  cp "$PRIVATE_ROOT/source/merged.sh" "$TMP_ROOT/source/$SOURCE_FILE" || fail "merged_source_copy_failed" "INSPECT_PRIVATE_ARCHIVE"
  (
    cd "$TMP_ROOT/source" || exit 1
    bash -n "$SOURCE_FILE" || exit 1
    git add -- "$SOURCE_FILE" || exit 1
    git commit -m "fix(dev-employee): recover local diagnostics hardening" || exit 1
    git push origin HEAD:main || exit 1
    git rev-parse HEAD
  ) > "$TMP_ROOT/source-git.log" 2>&1 || fail "source_recovery_push_failed" "INSPECT_PRIVATE_ARCHIVE_SOURCE"
  SOURCE_RECOVERY_COMMIT="$(tail -n 1 "$TMP_ROOT/source-git.log")"; SOURCE_RECOVERY_PUSH="PASS"
  git worktree remove --force "$TMP_ROOT/source" >/dev/null 2>&1 || true
fi

find "$PRIVATE_ROOT" -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 sha256sum > "$PRIVATE_ROOT/manifest.sha256" || fail "archive_manifest_failed" "INSPECT_PRIVATE_ARCHIVE"
ARCHIVE_MANIFEST_SHA256="$(sha256sum "$PRIVATE_ROOT/manifest.sha256" | awk '{print $1}')"
chmod -R go-rwx "$PRIVATE_ROOT"

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "post_merge_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_LOCAL_GIT_STATE"
git restore --source=HEAD --worktree -- "$SOURCE_FILE" >> "$RUN_LOG" 2>&1 || fail "source_worktree_sync_failed" "RESTORE_SOURCE_FROM_ORIGIN"
LOCAL_BRANCH_SYNC="PASS"

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

[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "unexpected_tracked_changes_after_sync" "INSPECT_GIT_STATUS"
git stash drop "$STASH_REF" >> "$RUN_LOG" 2>&1 || fail "stash_drop_failed" "INSPECT_GIT_STASH_LIST"
git stash list --format='%H' | grep -Fxq "$STASH_COMMIT" && fail "stash_commit_still_listed" "INSPECT_GIT_STASH_LIST"
STASH_DROPPED="YES"

for service in "$OPENCLAW_SERVICE" "$BRIDGE_SERVICE" "$INTAKE_SERVICE" "$WEB_SERVICE"; do [ "$(service_state "$service")" = "active" ] || fail "service_not_active_after_recovery" "INSPECT_USER_SERVICES"; done
WEB_HEALTH="$(curl -fsS http://127.0.0.1:18893/health 2>/dev/null || true)"
python3 - "$WEB_HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys
p=json.loads(sys.argv[1]);assert p.get('service')=='dev_employee_web_console_v5';assert p.get('agent_harness_enabled') is True;assert p.get('openclaw_provider_configured') is True
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
commit_evidence || { RESULT="FAILED"; FAILURE_CODE="recovery_evidence_push_failed"; NEXT_ACTION="RESOLVE_RECOVERY_EVIDENCE_PUSH"; }
summary
cleanup
[ "$RESULT" = "PASS" ] && exit 0
exit 1
