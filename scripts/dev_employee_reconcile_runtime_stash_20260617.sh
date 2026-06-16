#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="reconcile-runtime-stash-after-agent-harness-web-20260617"
TARGET_STASH_MESSAGE="temp-before-agent-harness-web-20260617022706"
STAMP="$(date +%Y%m%d%H%M%S)"
PRIVATE_ROOT="$HOME/.local/state/oris/stash_recovery/$STAMP"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/reconcile-runtime-stash-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/reconcile-runtime-stash-$STAMP.json"
GIT_OUTPUT="/tmp/oris-reconcile-runtime-stash-git-$STAMP.log"
WEB_SERVICE="oris-dev-employee-web-console.service"
INTAKE_SERVICE="oris-dev-employee-intake.service"
BRIDGE_SERVICE="oris-dev-employee-bridge.service"
OPENCLAW_SERVICE="openclaw-gateway.service"

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
STASH_ARCHIVE="NOT_RUN"
STASH_DROPPED="NO"
CURRENT_RUNTIME_FILES_PRESERVED="NOT_RUN"
RUNTIME_FILES_UNTRACKED="NOT_RUN"
RUNTIME_FILES_IGNORED="NOT_RUN"
RAW_CHAT_DATA_IGNORED="NOT_RUN"
LOCAL_BRANCH_SYNC="NOT_RUN"
DEPLOYMENT_ACCEPTANCE="NOT_VERIFIED"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_RUNTIME_STASH_RECOVERY"
STASH_REF=""
STASH_COMMIT=""
ARCHIVE_MANIFEST_SHA256=""

mkdir -p "$LOG_DIR" "$PRIVATE_ROOT/stashed" "$PRIVATE_ROOT/current"
chmod 700 "$PRIVATE_ROOT"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

service_state() {
  systemctl --user is-active "$1" 2>/dev/null || true
}

is_expected_runtime_file() {
  local candidate="$1"
  local expected
  for expected in "${RUNTIME_FILES[@]}"; do
    if [ "$candidate" = "$expected" ]; then
      return 0
    fi
  done
  return 1
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload = {
  "task_id": "$TASK_ID",
  "checked_at": "$(date -Is)",
  "result": "$RESULT",
  "failure_code": "$FAILURE_CODE",
  "stash_found": "$STASH_FOUND",
  "stash_scope_valid": "$STASH_SCOPE_VALID",
  "stash_archive": "$STASH_ARCHIVE",
  "stash_dropped": "$STASH_DROPPED",
  "current_runtime_files_preserved": "$CURRENT_RUNTIME_FILES_PRESERVED",
  "runtime_files_untracked": "$RUNTIME_FILES_UNTRACKED",
  "runtime_files_ignored": "$RUNTIME_FILES_IGNORED",
  "raw_chat_data_ignored": "$RAW_CHAT_DATA_IGNORED",
  "local_branch_sync": "$LOCAL_BRANCH_SYNC",
  "deployment_acceptance": "$DEPLOYMENT_ACCEPTANCE",
  "product_sha_unchanged": "$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean": "$PRODUCT_WORKTREE_CLEAN",
  "stash_commit": "$STASH_COMMIT" or None,
  "private_archive_path": "$PRIVATE_ROOT",
  "archive_manifest_sha256": "$ARCHIVE_MANIFEST_SHA256" or None,
  "services": {
    "openclaw_gateway": "$(service_state "$OPENCLAW_SERVICE")",
    "bridge": "$(service_state "$BRIDGE_SERVICE")",
    "intake": "$(service_state "$INTAKE_SERVICE")",
    "web_console": "$(service_state "$WEB_SERVICE")"
  },
  "openclaw_reinstalled": False,
  "agent_harness_added": True,
  "real_product_task_submitted": False,
  "real_product_change": False,
  "next_action": "$NEXT_ACTION"
}
open("$EVIDENCE_JSON", "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
PY
}

commit_logs() {
  local files=("${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}")
  git add -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_ADD_FAILED"
    return 1
  }
  git diff --cached --quiet -- "${files[@]}"
  local rc="$?"
  if [ "$rc" -eq 0 ]; then
    LOG_COMMIT="NO_LOG_CHANGES"
    return 0
  fi
  if [ "$rc" -ne 1 ]; then
    LOG_COMMIT="LOG_DIFF_FAILED"
    return 1
  fi
  git commit --only -m "test(runtime): reconcile generated state stash $STAMP" -- "${files[@]}" > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_COMMIT_FAILED"
    return 1
  }
  git push origin main > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="LOG_PUSH_FAILED"
    return 1
  }
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
  return 0
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "STASH_FOUND=$STASH_FOUND"
  echo "STASH_SCOPE_VALID=$STASH_SCOPE_VALID"
  echo "STASH_ARCHIVE=$STASH_ARCHIVE"
  echo "STASH_DROPPED=$STASH_DROPPED"
  echo "CURRENT_RUNTIME_FILES_PRESERVED=$CURRENT_RUNTIME_FILES_PRESERVED"
  echo "RUNTIME_FILES_UNTRACKED=$RUNTIME_FILES_UNTRACKED"
  echo "RUNTIME_FILES_IGNORED=$RUNTIME_FILES_IGNORED"
  echo "RAW_CHAT_DATA_IGNORED=$RAW_CHAT_DATA_IGNORED"
  echo "LOCAL_BRANCH_SYNC=$LOCAL_BRANCH_SYNC"
  echo "DEPLOYMENT_ACCEPTANCE=$DEPLOYMENT_ACCEPTANCE"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state "$OPENCLAW_SERVICE")"
  echo "BRIDGE_SERVICE=$(service_state "$BRIDGE_SERVICE")"
  echo "INTAKE_SERVICE=$(service_state "$INTAKE_SERVICE")"
  echo "WEB_CONSOLE_SERVICE=$(service_state "$WEB_SERVICE")"
  echo "PRIVATE_ARCHIVE=$PRIVATE_ROOT"
  echo "ARCHIVE_MANIFEST_SHA256=$ARCHIVE_MANIFEST_SHA256"
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
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  log "FAILURE_CODE=$FAILURE_CODE"
  write_evidence
  if [ "$LOCAL_BRANCH_SYNC" = "PASS" ]; then
    commit_logs || true
  fi
  summary
  rm -f "$GIT_OUTPUT"
  exit 1
}

if [ "$(id -un)" != "admin" ]; then
  FAILURE_CODE="wrong_linux_user"
  NEXT_ACTION="RUN_AS_ADMIN"
  write_evidence
  summary
  exit 1
fi

cd "$ORIS" || {
  FAILURE_CODE="oris_directory_missing"
  NEXT_ACTION="RESTORE_ORIS_REPOSITORY"
  write_evidence
  summary
  exit 1
}

log "===== timestamp ====="
log "$(date -Is)"
log "===== current revision ====="
log "HEAD=$(git rev-parse HEAD 2>/dev/null || true)"

STASH_LINE="$(git stash list --format='%gd|%H|%gs' | grep -F "$TARGET_STASH_MESSAGE" | head -n 1 || true)"
if [ -z "$STASH_LINE" ]; then
  fail "target_stash_not_found" "INSPECT_GIT_STASH_LIST"
fi
STASH_REF="${STASH_LINE%%|*}"
REST="${STASH_LINE#*|}"
STASH_COMMIT="${REST%%|*}"
STASH_FOUND="YES"
log "STASH_REF=$STASH_REF"
log "STASH_COMMIT=$STASH_COMMIT"

mapfile -t STASH_FILES < <(git diff --name-only "${STASH_COMMIT}^1" "$STASH_COMMIT" | sed '/^$/d' | sort -u)
if [ "${#STASH_FILES[@]}" -eq 0 ]; then
  fail "target_stash_has_no_tracked_files" "INSPECT_TARGET_STASH"
fi
for path in "${STASH_FILES[@]}"; do
  log "STASH_FILE=$path"
  if ! is_expected_runtime_file "$path"; then
    fail "non_runtime_file_present_in_stash" "MANUAL_REVIEW_REQUIRED"
  fi
done
for expected in "${RUNTIME_FILES[@]}"; do
  found="NO"
  for path in "${STASH_FILES[@]}"; do
    [ "$path" = "$expected" ] && found="YES"
  done
  if [ "$found" != "YES" ]; then
    fail "expected_runtime_file_missing_from_stash" "INSPECT_TARGET_STASH"
  fi
done
STASH_SCOPE_VALID="PASS"

CURRENT_BEFORE="$PRIVATE_ROOT/current-before.sha256"
: > "$CURRENT_BEFORE"
for path in "${RUNTIME_FILES[@]}"; do
  if [ ! -f "$ORIS/$path" ]; then
    fail "current_runtime_file_missing" "RESTORE_RUNTIME_FILE"
  fi
  mkdir -p "$PRIVATE_ROOT/current/$(dirname "$path")" "$PRIVATE_ROOT/stashed/$(dirname "$path")"
  cp -p "$ORIS/$path" "$PRIVATE_ROOT/current/$path" || fail "current_runtime_backup_failed" "INSPECT_PRIVATE_ARCHIVE"
  git show "$STASH_COMMIT:$path" > "$PRIVATE_ROOT/stashed/$path" || fail "stashed_runtime_export_failed" "INSPECT_TARGET_STASH"
  sha256sum "$ORIS/$path" >> "$CURRENT_BEFORE" || fail "current_runtime_checksum_failed" "INSPECT_RUNTIME_FILES"
done

git diff --binary "${STASH_COMMIT}^1" "$STASH_COMMIT" > "$PRIVATE_ROOT/stash.patch" || fail "stash_patch_export_failed" "INSPECT_TARGET_STASH"
printf '%s\n' \
  "created_at=$(date -Is)" \
  "repository=$ORIS" \
  "stash_ref=$STASH_REF" \
  "stash_commit=$STASH_COMMIT" \
  "policy=current_runtime_authoritative_stash_privately_archived" > "$PRIVATE_ROOT/metadata.txt"
find "$PRIVATE_ROOT" -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 sha256sum > "$PRIVATE_ROOT/manifest.sha256" || fail "archive_manifest_failed" "INSPECT_PRIVATE_ARCHIVE"
ARCHIVE_MANIFEST_SHA256="$(sha256sum "$PRIVATE_ROOT/manifest.sha256" | awk '{print $1}')"
[ -n "$ARCHIVE_MANIFEST_SHA256" ] || fail "archive_manifest_empty" "INSPECT_PRIVATE_ARCHIVE"
chmod -R go-rwx "$PRIVATE_ROOT"
STASH_ARCHIVE="PASS"

python3 - "$ORIS" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
from pathlib import Path
root=Path(sys.argv[1])
for relative in [
    'orchestration/active_routing.json',
    'orchestration/runtime_plan.json',
    'orchestration/runtime_state.json',
]:
    payload=json.loads((root/relative).read_text(encoding='utf-8'))
    assert isinstance(payload, dict)
for relative in [
    'orchestration/execution_log.jsonl',
    'logs/dev_employee/free_mesh_latency_events.jsonl',
]:
    for number, line in enumerate((root/relative).read_text(encoding='utf-8').splitlines(), start=1):
        if line.strip():
            payload=json.loads(line)
            assert isinstance(payload, dict), (relative, number)
PY
[ "$?" -eq 0 ] || fail "current_runtime_content_invalid" "INSPECT_RUNTIME_FILES"

CURRENT_HEAD="$(git rev-parse HEAD)"
git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git merge-base --is-ancestor "$CURRENT_HEAD" origin/main
[ "$?" -eq 0 ] || fail "local_head_not_ancestor_of_origin" "MANUAL_GIT_REVIEW_REQUIRED"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_GIT_RESET"
LOCAL_BRANCH_SYNC="PASS"

for path in "${RUNTIME_FILES[@]}"; do
  if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    fail "runtime_file_still_tracked" "FIX_RUNTIME_GIT_BOUNDARY"
  fi
  git check-ignore -q "$path"
  [ "$?" -eq 0 ] || fail "runtime_file_not_ignored" "FIX_RUNTIME_GIT_BOUNDARY"
  [ -f "$ORIS/$path" ] || fail "runtime_file_removed_from_worktree" "RESTORE_FROM_PRIVATE_ARCHIVE"
done
RUNTIME_FILES_UNTRACKED="PASS"
RUNTIME_FILES_IGNORED="PASS"

git check-ignore -q orchestration/dev_employee_chat_sessions/example.json
[ "$?" -eq 0 ] || fail "chat_sessions_not_ignored" "FIX_CONVERSATION_DATA_GIT_BOUNDARY"
git check-ignore -q logs/dev_employee/agent_harness/example.jsonl
[ "$?" -eq 0 ] || fail "harness_trace_not_ignored" "FIX_CONVERSATION_DATA_GIT_BOUNDARY"
RAW_CHAT_DATA_IGNORED="PASS"

CURRENT_AFTER="$PRIVATE_ROOT/current-after.sha256"
: > "$CURRENT_AFTER"
for path in "${RUNTIME_FILES[@]}"; do
  sha256sum "$ORIS/$path" >> "$CURRENT_AFTER" || fail "post_sync_runtime_checksum_failed" "INSPECT_RUNTIME_FILES"
done
python3 - "$CURRENT_BEFORE" "$CURRENT_AFTER" <<'PY' >> "$RUN_LOG" 2>&1
import sys

def normalized(path):
    rows=[]
    for line in open(path, encoding='utf-8'):
        digest, filename=line.strip().split(None,1)
        rows.append((digest, filename))
    return rows
assert normalized(sys.argv[1]) == normalized(sys.argv[2])
PY
[ "$?" -eq 0 ] || fail "current_runtime_files_changed_during_migration" "RESTORE_FROM_PRIVATE_ARCHIVE"
CURRENT_RUNTIME_FILES_PRESERVED="PASS"

git stash drop "$STASH_REF" >> "$RUN_LOG" 2>&1 || fail "stash_drop_failed" "INSPECT_GIT_STASH_LIST"
if git stash list --format='%H' | grep -Fxq "$STASH_COMMIT"; then
  fail "stash_commit_still_listed" "INSPECT_GIT_STASH_LIST"
fi
STASH_DROPPED="YES"

TRACKED_DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$TRACKED_DIRTY" ]; then
  log "===== unexpected tracked changes ====="
  log "$TRACKED_DIRTY"
  fail "unexpected_tracked_changes_after_migration" "INSPECT_GIT_STATUS"
fi

[ "$(service_state "$OPENCLAW_SERVICE")" = "active" ] || fail "openclaw_service_not_active" "INSPECT_OPENCLAW_SERVICE"
[ "$(service_state "$BRIDGE_SERVICE")" = "active" ] || fail "bridge_service_not_active" "INSPECT_BRIDGE_SERVICE"
[ "$(service_state "$INTAKE_SERVICE")" = "active" ] || fail "intake_service_not_active" "INSPECT_INTAKE_SERVICE"
[ "$(service_state "$WEB_SERVICE")" = "active" ] || fail "web_service_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
WEB_HEALTH="$(curl -fsS http://127.0.0.1:18893/health 2>/dev/null || true)"
python3 - "$WEB_HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json
import sys
payload=json.loads(sys.argv[1])
assert payload.get('service') == 'dev_employee_web_console_v5'
assert payload.get('agent_harness_enabled') is True
assert payload.get('openclaw_provider_configured') is True
PY
[ "$?" -eq 0 ] || fail "agent_harness_web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
DEPLOYMENT_ACCEPTANCE="PASS"

PRODUCT_LOCAL_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_SHA="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n 1)"
PRODUCT_DIRTY="$(git -C "$PRODUCT" status --porcelain --untracked-files=no)"
if [ -n "$PRODUCT_LOCAL_SHA" ] && [ "$PRODUCT_LOCAL_SHA" = "$PRODUCT_REMOTE_SHA" ]; then
  PRODUCT_SHA_UNCHANGED="PASS"
else
  fail "product_sha_mismatch" "INSPECT_PRODUCT_REPOSITORY"
fi
if [ -z "$PRODUCT_DIRTY" ]; then
  PRODUCT_WORKTREE_CLEAN="PASS"
else
  fail "product_worktree_dirty" "INSPECT_PRODUCT_REPOSITORY"
fi

RESULT="PASS"
NEXT_ACTION="REQUEST_CONVERSATIONAL_BROWSER_TEST"
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="recovery_evidence_push_failed"
  NEXT_ACTION="RESOLVE_ORIS_EVIDENCE_PUSH"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
