#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

if [ -z "$REPO_ROOT" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=MODEL_TOOL_DIAGNOSTIC_FAILED"
  echo "FAILURE_CODE=repository_root_unresolved"
  echo "OPENCLAW_ACCESSED=NO"
  echo "GATEWAY_RESTARTED=NO"
  echo "TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=RESTORE_ORIS_REPOSITORY"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi

CACHE_DIR="$(mktemp -d 2>/dev/null || true)"
if [ -z "$CACHE_DIR" ] || [ ! -d "$CACHE_DIR" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=MODEL_TOOL_DIAGNOSTIC_FAILED"
  echo "FAILURE_CODE=compile_cache_creation_failed"
  echo "OPENCLAW_ACCESSED=NO"
  echo "GATEWAY_RESTARTED=NO"
  echo "TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=RESTORE_PRIVATE_TEMPORARY_DIRECTORY_ACCESS"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$CACHE_DIR" \
  python3 -m compileall -q \
  "$REPO_ROOT/scripts/dev_employee_openclaw_enable" \
  "$REPO_ROOT/scripts/dev_employee_quality"
COMPILE_RC=$?
rm -rf -- "$CACHE_DIR"

if [ "$COMPILE_RC" -ne 0 ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=MODEL_TOOL_DIAGNOSTIC_FAILED"
  echo "FAILURE_CODE=python_compile_failed"
  echo "OPENCLAW_ACCESSED=NO"
  echo "GATEWAY_RESTARTED=NO"
  echo "TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=FIX_COMPILE_FAILURE"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit "$COMPILE_RC"
fi

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO_ROOT" \
  python3 -m scripts.dev_employee_openclaw_enable.code_audit_cli --quiet
AUDIT_RC=$?
if [ "$AUDIT_RC" -ne 0 ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=MODEL_TOOL_DIAGNOSTIC_BLOCKED"
  echo "FAILURE_CODE=code_audit_gate_failed"
  echo "OPENCLAW_ACCESSED=NO"
  echo "GATEWAY_RESTARTED=NO"
  echo "TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=FIX_ALL_CODE_AUDIT_FINDINGS"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit "$AUDIT_RC"
fi

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$REPO_ROOT" \
  python3 -m scripts.dev_employee_openclaw_enable.model_tool_diagnostic_cli
exit "$?"
