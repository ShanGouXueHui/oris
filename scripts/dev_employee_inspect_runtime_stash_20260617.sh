#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
TASK_ID="inspect-runtime-stash-after-agent-harness-web-20260617"
TARGET_STASH_MESSAGE="temp-before-agent-harness-web-20260617022706"
STAMP="$(date +%Y%m%d%H%M%S)"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/inspect-runtime-stash-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/inspect-runtime-stash-$STAMP.json"
GIT_OUTPUT="/tmp/oris-inspect-runtime-stash-git-$STAMP.log"
TMP_WORKTREE="/tmp/oris-inspect-runtime-stash-worktree-$STAMP"

EXPECTED_RUNTIME_FILES=(
  "logs/dev_employee/free_mesh_latency_events.jsonl"
  "orchestration/active_routing.json"
  "orchestration/execution_log.jsonl"
  "orchestration/runtime_plan.json"
  "orchestration/runtime_state.json"
)

RESULT="FAILED"
STASH_FOUND="NO"
STASH_FILE_COUNT="0"
EXPECTED_RUNTIME_COUNT="0"
EXTRA_FILE_COUNT="0"
EXTRA_SOURCE_COUNT="0"
EXTRA_RUNTIME_COUNT="0"
STASH_HAS_UNTRACKED_PARENT="NO"
STASH_MUTATED="NO"
SERVICES_CHANGED="NO"
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_STASH_EVIDENCE"
STASH_REF=""
STASH_COMMIT=""
EXTRA_FILES_CSV=""

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

log() {
  printf '%s\n' "$*" | tee -a "$RUN_LOG"
}

is_expected_runtime_file() {
  local candidate="$1"
  local expected
  for expected in "${EXPECTED_RUNTIME_FILES[@]}"; do
    [ "$candidate" = "$expected" ] && return 0
  done
  return 1
}

is_runtime_like_file() {
  case "$1" in
    orchestration/*.jsonl|orchestration/*_state.json|orchestration/runtime_*.json|orchestration/active_routing.json|logs/dev_employee/*latency*.jsonl|logs/dev_employee/agent_harness/*.jsonl|orchestration/dev_employee_chat_sessions/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

write_evidence() {
  python3 - "$EVIDENCE_JSON" "$RUN_LOG" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

out = Path(sys.argv[1])
text = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")

def last(name, default=""):
    values = re.findall(rf"^{re.escape(name)}=(.*)$", text, re.M)
    return values[-1].strip() if values else default

files = []
for line in text.splitlines():
    if line.startswith("STASH_FILE="):
        _, rest = line.split("=", 1)
        status, path, category = rest.split("|", 2)
        files.append({"status": status, "path": path, "category": category})

payload = {
    "task_id": last("TASK_ID"),
    "checked_at": last("CHECKED_AT"),
    "result": last("RESULT", "FAILED"),
    "failure_code": last("FAILURE_CODE") or None,
    "stash_found": last("STASH_FOUND") == "YES",
    "stash_ref": last("STASH_REF") or None,
    "stash_commit": last("STASH_COMMIT") or None,
    "stash_file_count": int(last("STASH_FILE_COUNT", "0")),
    "expected_runtime_count": int(last("EXPECTED_RUNTIME_COUNT", "0")),
    "extra_file_count": int(last("EXTRA_FILE_COUNT", "0")),
    "extra_runtime_count": int(last("EXTRA_RUNTIME_COUNT", "0")),
    "extra_source_count": int(last("EXTRA_SOURCE_COUNT", "0")),
    "stash_has_untracked_parent": last("STASH_HAS_UNTRACKED_PARENT") == "YES",
    "files": files,
    "stash_mutated": False,
    "services_changed": False,
    "real_product_task_submitted": False,
    "real_product_change": False,
    "next_action": last("NEXT_ACTION"),
}
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

commit_logs() {
  rm -rf "$TMP_WORKTREE"
  git worktree add --detach "$TMP_WORKTREE" origin/main > "$GIT_OUTPUT" 2>&1 || {
    LOG_COMMIT="WORKTREE_ADD_FAILED"
    return 1
  }
  mkdir -p "$TMP_WORKTREE/logs/dev_employee/conversational_web"
  cp "$RUN_LOG" "$TMP_WORKTREE/${RUN_LOG#$ORIS/}"
  cp "$EVIDENCE_JSON" "$TMP_WORKTREE/${EVIDENCE_JSON#$ORIS/}"
  (
    cd "$TMP_WORKTREE" || exit 1
    git add -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" || exit 1
    git commit -m "chore(runtime): record stash inspection $STAMP" || exit 1
    git push origin HEAD:main || exit 1
    git rev-parse HEAD
  ) > "$GIT_OUTPUT" 2>&1
  local rc="$?"
  if [ "$rc" -eq 0 ]; then
    LOG_COMMIT="$(tail -n 1 "$GIT_OUTPUT" | tr -d '\r\n')"
  else
    LOG_COMMIT="LOG_PUSH_FAILED"
  fi
  git worktree remove --force "$TMP_WORKTREE" >/dev/null 2>&1 || true
  rm -rf "$TMP_WORKTREE"
  [ "$rc" -eq 0 ]
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "STASH_FOUND=$STASH_FOUND"
  echo "STASH_FILE_COUNT=$STASH_FILE_COUNT"
  echo "EXPECTED_RUNTIME_COUNT=$EXPECTED_RUNTIME_COUNT"
  echo "EXTRA_FILE_COUNT=$EXTRA_FILE_COUNT"
  echo "EXTRA_RUNTIME_COUNT=$EXTRA_RUNTIME_COUNT"
  echo "EXTRA_SOURCE_COUNT=$EXTRA_SOURCE_COUNT"
  echo "STASH_HAS_UNTRACKED_PARENT=$STASH_HAS_UNTRACKED_PARENT"
  echo "STASH_MUTATED=$STASH_MUTATED"
  echo "SERVICES_CHANGED=$SERVICES_CHANGED"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "LOG_COMMIT=$LOG_COMMIT"
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
  log "CHECKED_AT=$(date -Is)"
  log "TASK_ID=$TASK_ID"
  log "RESULT=$RESULT"
  log "FAILURE_CODE=$FAILURE_CODE"
  log "NEXT_ACTION=$NEXT_ACTION"
  write_evidence
  commit_logs || true
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

git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"

STASH_LINE="$(git stash list --format='%gd|%H|%gs' | grep -F "$TARGET_STASH_MESSAGE" | head -n 1 || true)"
[ -n "$STASH_LINE" ] || fail "target_stash_not_found" "INSPECT_GIT_STASH_LIST"
STASH_REF="${STASH_LINE%%|*}"
REST="${STASH_LINE#*|}"
STASH_COMMIT="${REST%%|*}"
STASH_FOUND="YES"

PARENT_COUNT="$(git cat-file -p "$STASH_COMMIT" | grep -c '^parent ' || true)"
[ "$PARENT_COUNT" -ge 3 ] && STASH_HAS_UNTRACKED_PARENT="YES"

mapfile -t CHANGED_ROWS < <(git diff --name-status "${STASH_COMMIT}^1" "$STASH_COMMIT" | sed '/^$/d')
STASH_FILE_COUNT="${#CHANGED_ROWS[@]}"
[ "$STASH_FILE_COUNT" -gt 0 ] || fail "stash_has_no_tracked_changes" "INSPECT_TARGET_STASH"

for row in "${CHANGED_ROWS[@]}"; do
  status="${row%%$'\t'*}"
  path="${row#*$'\t'}"
  category="extra_source"
  if is_expected_runtime_file "$path"; then
    category="expected_runtime"
    EXPECTED_RUNTIME_COUNT="$((EXPECTED_RUNTIME_COUNT + 1))"
  elif is_runtime_like_file "$path"; then
    category="extra_runtime"
    EXTRA_RUNTIME_COUNT="$((EXTRA_RUNTIME_COUNT + 1))"
    EXTRA_FILE_COUNT="$((EXTRA_FILE_COUNT + 1))"
  else
    EXTRA_SOURCE_COUNT="$((EXTRA_SOURCE_COUNT + 1))"
    EXTRA_FILE_COUNT="$((EXTRA_FILE_COUNT + 1))"
  fi
  log "STASH_FILE=$status|$path|$category"
done

if [ "$EXTRA_SOURCE_COUNT" -gt 0 ]; then
  NEXT_ACTION="BUILD_THREE_WAY_SOURCE_AND_RUNTIME_RECOVERY"
elif [ "$EXTRA_RUNTIME_COUNT" -gt 0 ]; then
  NEXT_ACTION="EXTEND_RUNTIME_BOUNDARY_AND_RECONCILE"
else
  NEXT_ACTION="RECONCILE_EXPECTED_RUNTIME_STASH"
fi
RESULT="PASS"

log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "STASH_REF=$STASH_REF"
log "STASH_COMMIT=$STASH_COMMIT"
log "STASH_FOUND=$STASH_FOUND"
log "STASH_FILE_COUNT=$STASH_FILE_COUNT"
log "EXPECTED_RUNTIME_COUNT=$EXPECTED_RUNTIME_COUNT"
log "EXTRA_FILE_COUNT=$EXTRA_FILE_COUNT"
log "EXTRA_RUNTIME_COUNT=$EXTRA_RUNTIME_COUNT"
log "EXTRA_SOURCE_COUNT=$EXTRA_SOURCE_COUNT"
log "STASH_HAS_UNTRACKED_PARENT=$STASH_HAS_UNTRACKED_PARENT"
log "RESULT=$RESULT"
log "FAILURE_CODE=$FAILURE_CODE"
log "NEXT_ACTION=$NEXT_ACTION"
write_evidence
commit_logs || {
  RESULT="FAILED"
  FAILURE_CODE="inspection_evidence_push_failed"
  NEXT_ACTION="RESOLVE_INSPECTION_EVIDENCE_PUSH"
}
summary
rm -f "$GIT_OUTPUT"

if [ "$RESULT" = "PASS" ]; then
  exit 0
fi
exit 1
