#!/usr/bin/env bash

# Read-only native OpenClaw discovery entrypoint.
# Intentionally no `set -e`: every failure path emits the required SUMMARY block.

ORIS_ROOT="${ORIS_ROOT:-/home/admin/projects/oris}"
PAYLOAD="${ORIS_ROOT}/scripts/dev_employee_native_openclaw_readonly_discovery.py.gz.b64"
STATE_ROOT="${HOME}/.local/state/oris/dev_employee_discovery_runner"
EXPECTED_SHA256="fe706dd5b0b119902db4f4e90dc4059359330647188cf685b769bef2018c16a3"

summary_failed() {
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "REASON=$1"
  echo "CONFIG_MUTATED=NO"
  echo "SERVICE_RELOADED_OR_RESTARTED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

if [ ! -f "$PAYLOAD" ]; then
  summary_failed "discovery_runner_payload_not_found"
  exit 1
fi

if ! command -v base64 >/dev/null 2>&1 || ! command -v gzip >/dev/null 2>&1 || ! command -v sha256sum >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  summary_failed "required_local_tool_missing"
  exit 1
fi

umask 077
mkdir -p "$STATE_ROOT"
if [ $? -ne 0 ]; then
  summary_failed "cannot_create_private_runner_state"
  exit 1
fi

RUN_DIR="$(mktemp -d "${STATE_ROOT}/run.XXXXXX")"
if [ -z "$RUN_DIR" ] || [ ! -d "$RUN_DIR" ]; then
  summary_failed "cannot_create_private_runner_directory"
  exit 1
fi

RUNNER="${RUN_DIR}/dev_employee_native_openclaw_readonly_discovery.py"
base64 -d "$PAYLOAD" 2>/dev/null | gzip -d > "$RUNNER" 2>/dev/null
DECODE_RC=$?
if [ $DECODE_RC -ne 0 ] || [ ! -s "$RUNNER" ]; then
  rm -rf "$RUN_DIR"
  summary_failed "discovery_runner_decode_failed"
  exit 1
fi

ACTUAL_SHA256="$(sha256sum "$RUNNER" | awk '{print $1}')"
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
  rm -rf "$RUN_DIR"
  summary_failed "discovery_runner_sha256_mismatch"
  exit 1
fi

python3 -m py_compile "$RUNNER" >/dev/null 2>&1
COMPILE_RC=$?
if [ $COMPILE_RC -ne 0 ]; then
  rm -rf "$RUN_DIR"
  summary_failed "discovery_runner_compile_failed"
  exit 1
fi

python3 "$RUNNER"
RUN_RC=$?
rm -rf "$RUN_DIR"
exit $RUN_RC
