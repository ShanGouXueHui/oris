#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-quality-scan-${STAMP}-XXXXXX)"
WORKTREE="$TMP_ROOT/worktree"
REPORT_NAME="repository-quality-scan-$STAMP.json"
REPORT_REL="logs/dev_employee/repository_quality_scan/$REPORT_NAME"
REPORT_TMP="$TMP_ROOT/$REPORT_NAME"
SCAN_OUTPUT="$TMP_ROOT/scan-output.txt"
RESULT="FAILED"
FAILURE_CODE=""
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"

cleanup() {
  if [ -n "$REPO_ROOT" ] && [ -d "$WORKTREE" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary() {
  local files_scanned finding_count next_action
  files_scanned="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["files_scanned"])' "$REPORT_TMP" 2>/dev/null || echo 0)"
  finding_count="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["finding_count"])' "$REPORT_TMP" 2>/dev/null || echo 0)"
  next_action="FIX_ALL_REPORTED_FINDINGS"
  [ "$finding_count" = "0" ] && next_action="QUALITY_GATE_READY"
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "FILES_SCANNED=$files_scanned"
  echo "FINDING_COUNT=$finding_count"
  echo "FILES_MODIFIED=NO"
  echo "REPORT=$REPORT_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$next_action"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  [ -f "$REPORT_TMP" ] || printf '{"files_scanned":0,"finding_count":0}\n' > "$REPORT_TMP"
  summary
  exit 1
}

[ -n "$REPO_ROOT" ] || fail "repository_root_unresolved"
for command_name in git python3 date mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required_command_missing_$command_name"
done

PYTHONPATH="$REPO_ROOT" python3 -m scripts.dev_employee_quality.cli "$REPO_ROOT" "$REPORT_TMP" > "$SCAN_OUTPUT" 2>&1
SCAN_RC="$?"
[ "$SCAN_RC" = "0" ] || [ "$SCAN_RC" = "2" ] || fail "quality_scanner_execution_failed"
[ -f "$REPORT_TMP" ] || fail "quality_report_missing"

git -C "$REPO_ROOT" fetch origin main >/dev/null 2>&1 || fail "git_fetch_failed"
git -C "$REPO_ROOT" worktree add --detach "$WORKTREE" origin/main >/dev/null 2>&1 || fail "detached_worktree_create_failed"
mkdir -p "$WORKTREE/$(dirname "$REPORT_REL")" || fail "evidence_directory_create_failed"
cp "$REPORT_TMP" "$WORKTREE/$REPORT_REL" || fail "evidence_copy_failed"
git -C "$WORKTREE" add -- "$REPORT_REL" || fail "evidence_add_failed"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail "evidence_diff_check_failed"
git -C "$WORKTREE" commit -m "chore(dev-employee): record repository quality scan $STAMP" >/dev/null 2>&1 || fail "evidence_commit_failed"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail "evidence_refetch_failed"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail "evidence_rebase_failed"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail "evidence_push_failed"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
[ -n "$EVIDENCE_COMMIT" ] && [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] || fail "evidence_remote_sha_mismatch"
EVIDENCE_REMOTE_VERIFIED="YES"
RESULT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["result"])' "$REPORT_TMP" 2>/dev/null || echo FAILED)"
summary
[ "$SCAN_RC" = "0" ] && exit 0
exit 2
