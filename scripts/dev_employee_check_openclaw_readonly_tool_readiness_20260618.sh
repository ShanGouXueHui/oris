#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

REQUIRED_LIBS="
$LIB_DIR/dev_employee_openclaw_readonly_readiness_common_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_readiness_marker_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_readiness_policy_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_readiness_runtime_network_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_readiness_telemetry_invariants_20260618.sh
$LIB_DIR/dev_employee_openclaw_readonly_readiness_evidence_20260618.sh
"
for required in $REQUIRED_LIBS; do
  if [ ! -r "$required" ]; then
    echo "===== SUMMARY ====="
    echo "RESULT=FAILED"
    echo "TASK_ID=commercial-openclaw-readonly-tool-enable-20260618"
    echo "FAILURE_CODE=readiness_library_missing"
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

. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_common_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_marker_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_policy_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_runtime_network_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_telemetry_invariants_20260618.sh"
. "$LIB_DIR/dev_employee_openclaw_readonly_readiness_evidence_20260618.sh"
