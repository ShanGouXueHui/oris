#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"

if [ -z "$REPO_ROOT" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=DIAGNOSTIC_BOOTSTRAP_FAILED"
  echo "FAILURE_CODE=repository_root_unresolved"
  echo "NEXT_ACTION=RESTORE_ORIS_REPOSITORY"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi

PYTHONPATH="$REPO_ROOT" python3 -m scripts.dev_employee_openclaw_enable.diagnostic_cli
exit "$?"
