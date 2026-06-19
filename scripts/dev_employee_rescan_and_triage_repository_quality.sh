#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-quality-rescan-${STAMP}-XXXXXX)"
SCAN_OUTPUT="$TMP_ROOT/scan.out"
TRIAGE_OUTPUT="$TMP_ROOT/triage.out"
RESULT="FAILED"
FAILURE_CODE=""
SCAN_RC=""
TRIAGE_RC=""

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary_value() {
  local source_file="$1" key="$2" default_value="$3"
  awk -F= -v target="$key" '$1 == target {value=substr($0,index($0,"=")+1)} END {if (value != "") print value; else print default_value}' default_value="$default_value" "$source_file" 2>/dev/null
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "SCAN_RESULT=$(summary_value "$SCAN_OUTPUT" RESULT UNKNOWN)"
  echo "SCAN_FINDING_COUNT=$(summary_value "$SCAN_OUTPUT" FINDING_COUNT 0)"
  echo "SCAN_EVIDENCE_COMMIT=$(summary_value "$SCAN_OUTPUT" EVIDENCE_COMMIT '')"
  echo "SCAN_EVIDENCE_REMOTE_VERIFIED=$(summary_value "$SCAN_OUTPUT" EVIDENCE_REMOTE_VERIFIED NO)"
  echo "TRIAGE_RESULT=$(summary_value "$TRIAGE_OUTPUT" RESULT UNKNOWN)"
  echo "GENERATED_RUNTIME_ARTIFACT_FINDINGS=$(summary_value "$TRIAGE_OUTPUT" GENERATED_RUNTIME_ARTIFACT_FINDINGS 0)"
  echo "LEGACY_OPERATIONAL_SCRIPT_FINDINGS=$(summary_value "$TRIAGE_OUTPUT" LEGACY_OPERATIONAL_SCRIPT_FINDINGS 0)"
  echo "ACTIONABLE_ENGINEERING_FINDINGS=$(summary_value "$TRIAGE_OUTPUT" ACTIONABLE_ENGINEERING_FINDINGS 0)"
  echo "TRIAGE_EVIDENCE_COMMIT=$(summary_value "$TRIAGE_OUTPUT" EVIDENCE_COMMIT '')"
  echo "TRIAGE_EVIDENCE_REMOTE_VERIFIED=$(summary_value "$TRIAGE_OUTPUT" EVIDENCE_REMOTE_VERIFIED NO)"
  echo "FILES_MODIFIED=NO"
  echo "NEXT_ACTION=READ_GITHUB_TRIAGE_AND_FIX_ACTIONABLE_FINDINGS"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

[ -n "$REPO_ROOT" ] || { FAILURE_CODE="repository_root_unresolved"; summary; exit 1; }
for command_name in git bash awk date mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || { FAILURE_CODE="required_command_missing_$command_name"; summary; exit 1; }
done

bash "$REPO_ROOT/scripts/dev_employee_scan_repository_quality.sh" > "$SCAN_OUTPUT" 2>&1
SCAN_RC="$?"
if [ "$SCAN_RC" != "0" ] && [ "$SCAN_RC" != "2" ]; then
  FAILURE_CODE="repository_quality_scan_failed"
  summary
  exit 1
fi

SCAN_REMOTE_VERIFIED="$(summary_value "$SCAN_OUTPUT" EVIDENCE_REMOTE_VERIFIED NO)"
[ "$SCAN_REMOTE_VERIFIED" = "YES" ] || { FAILURE_CODE="scan_evidence_not_remote_verified"; summary; exit 1; }

git -C "$REPO_ROOT" pull --ff-only origin main >/dev/null 2>&1 || { FAILURE_CODE="pull_scan_evidence_failed"; summary; exit 1; }
git -C "$REPO_ROOT" worktree prune >/dev/null 2>&1 || true

bash "$REPO_ROOT/scripts/dev_employee_triage_repository_quality.sh" > "$TRIAGE_OUTPUT" 2>&1
TRIAGE_RC="$?"
if [ "$TRIAGE_RC" != "0" ]; then
  FAILURE_CODE="repository_quality_triage_failed"
  summary
  exit 1
fi

TRIAGE_REMOTE_VERIFIED="$(summary_value "$TRIAGE_OUTPUT" EVIDENCE_REMOTE_VERIFIED NO)"
[ "$TRIAGE_REMOTE_VERIFIED" = "YES" ] || { FAILURE_CODE="triage_evidence_not_remote_verified"; summary; exit 1; }

RESULT="RESCANNED_AND_TRIAGED"
summary
exit 0
