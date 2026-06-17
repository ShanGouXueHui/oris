#!/usr/bin/env bash

TASK_ID="commercial-native-openclaw-ui-20260617"
TARGET="/home/admin/projects/oris/scripts/dev_employee_native_openclaw_reject_rollback_and_diagnose_v2_20260617.sh"

summary_failed() {
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$1"
  echo "CURRENT_TASK_UPDATED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "PRODUCT_REPOSITORY_MUTATED=NO"
  echo "OPENCLAW_CONFIG_MUTATED=NO"
  echo "NEXT_ACTION=$2"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_failed "wrong_linux_user" "RUN_AS_ADMIN"
  exit 1
fi

if [ ! -f "$TARGET" ]; then
  summary_failed "diagnosis_v2_missing" "PULL_ORIS_MAIN_AND_RETRY"
  exit 1
fi

if ! bash -n "$TARGET" >/dev/null 2>&1; then
  summary_failed "diagnosis_v2_syntax_invalid" "REPAIR_DIAGNOSIS_V2"
  exit 1
fi

bash "$TARGET"
exit "$?"
