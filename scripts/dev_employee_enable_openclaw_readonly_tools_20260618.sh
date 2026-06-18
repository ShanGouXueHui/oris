#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
REQUIRED_LIBS="
$LIB_DIR/dev_employee_openclaw_readonly_enable_common_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_enable_preflight_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_enable_policy_direct_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_enable_browser_telemetry_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_enable_finalize_20260618.sh
"
for required in $REQUIRED_LIBS; do
  if [ ! -r "$required" ]; then
    echo "===== SUMMARY ====="
    echo "RESULT=FAILED"
    echo "TASK_ID=commercial-openclaw-readonly-tool-enable-20260618"
    echo "FAILURE_CODE=enablement_library_missing"
    echo "CONFIG_MUTATED=NO"
    echo "GATEWAY_RESTARTED_OR_RELOADED=NO"
    echo "TOOLS_ENABLED=NO"
    echo "PRODUCT_TASK_SUBMITTED=NO"
    echo "NEXT_ACTION=PULL_ORIS_MAIN_AND_RETRY"
    echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
    echo "===== END SUMMARY ====="
    exit 1
  fi
done

. "$LIB_DIR/dev_employee_openclaw_readonly_enable_common_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_enable_preflight_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_enable_policy_direct_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_enable_browser_telemetry_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_enable_finalize_20260618.sh"
