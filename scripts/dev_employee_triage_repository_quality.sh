#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-quality-triage-${STAMP}-XXXXXX)"
WORKTREE="$TMP_ROOT/worktree"
TRIAGE_NAME="repository-quality-triage-$STAMP.json"
TRIAGE_REL="logs/dev_employee/repository_quality_triage/$TRIAGE_NAME"
TRIAGE_TMP="$TMP_ROOT/$TRIAGE_NAME"
RESULT="FAILED"
FAILURE_CODE=""
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
SOURCE_REPORT=""

cleanup() {
  if [ -n "$REPO_ROOT" ] && [ -d "$WORKTREE" ]; then
    git -C "$REPO_ROOT" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

json_value() {
  local key="$1" default_value="$2"
  python3 - "$TRIAGE_TMP" "$key" "$default_value" <<'PY'
import json,sys
from pathlib import Path
path=Path(sys.argv[1]); key=sys.argv[2]; default=sys.argv[3]
try:
 data=json.loads(path.read_text(encoding='utf-8'))
 value=data
 for part in key.split('.'):
  value=value[part]
 print(value)
except Exception:
 print(default)
PY
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "SOURCE_REPORT=$SOURCE_REPORT"
  echo "REPORTED_FINDINGS=$(json_value source_report.reported_findings 0)"
  echo "DEDUPLICATED_FINDINGS=$(json_value deduplicated_findings 0)"
  echo "GENERATED_RUNTIME_ARTIFACT_FINDINGS=$(json_value generated_runtime_artifact_findings 0)"
  echo "ACTIONABLE_ENGINEERING_FINDINGS=$(json_value actionable_engineering_findings 0)"
  echo "TRIAGE_REPORT=$TRIAGE_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "FILES_MODIFIED=NO"
  echo "NEXT_ACTION=READ_GITHUB_TRIAGE_AND_FIX_SCANNER_POLICY_FIRST"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  [ -f "$TRIAGE_TMP" ] || printf '{}\n' > "$TRIAGE_TMP"
  summary
  exit 1
}

[ -n "$REPO_ROOT" ] || fail "repository_root_unresolved"
for command_name in git python3 date mktemp sort tail; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required_command_missing_$command_name"
done

SOURCE_REPORT="$(git -C "$REPO_ROOT" ls-files 'logs/dev_employee/repository_quality_scan/repository-quality-scan-*.json' | sort | tail -n 1)"
[ -n "$SOURCE_REPORT" ] || fail "quality_scan_report_not_found"
[ -f "$REPO_ROOT/$SOURCE_REPORT" ] || fail "quality_scan_report_missing_from_worktree"

PYTHONPATH="$REPO_ROOT" python3 -m scripts.dev_employee_quality.triage "$REPO_ROOT/$SOURCE_REPORT" "$TRIAGE_TMP" >/dev/null 2>&1
[ "$?" = "0" ] || fail "quality_triage_execution_failed"
[ -f "$TRIAGE_TMP" ] || fail "quality_triage_report_missing"

git -C "$REPO_ROOT" fetch origin main >/dev/null 2>&1 || fail "git_fetch_failed"
git -C "$REPO_ROOT" worktree add --detach "$WORKTREE" origin/main >/dev/null 2>&1 || fail "detached_worktree_create_failed"
mkdir -p "$WORKTREE/$(dirname "$TRIAGE_REL")" || fail "triage_evidence_directory_create_failed"
cp "$TRIAGE_TMP" "$WORKTREE/$TRIAGE_REL" || fail "triage_evidence_copy_failed"
git -C "$WORKTREE" add -- "$TRIAGE_REL" || fail "triage_evidence_add_failed"
git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1 || fail "triage_evidence_diff_check_failed"
git -C "$WORKTREE" commit -m "chore(dev-employee): record repository quality triage $STAMP" >/dev/null 2>&1 || fail "triage_evidence_commit_failed"
git -C "$WORKTREE" fetch origin main >/dev/null 2>&1 || fail "triage_evidence_refetch_failed"
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1 || fail "triage_evidence_rebase_failed"
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1 || fail "triage_evidence_push_failed"
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
[ -n "$EVIDENCE_COMMIT" ] && [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ] || fail "triage_evidence_remote_sha_mismatch"
EVIDENCE_REMOTE_VERIFIED="YES"
RESULT="TRIAGED"
summary
exit 0
