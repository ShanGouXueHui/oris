#!/usr/bin/env bash

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-remediate-enable-${STAMP}-XXXXXX)"
QUALITY_OUT="$TMP_ROOT/quality.out"
TARGET_GATE_JSON="$TMP_ROOT/target-gate.json"
PREFLIGHT_JSON="$TMP_ROOT/preflight.json"
ROTATION_OUT="$TMP_ROOT/rotation.out"
ENABLEMENT_OUT="$TMP_ROOT/enablement.out"
RESULT="FAILED"
FAILURE_CODE=""

export PYTHONDONTWRITEBYTECODE=1

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary_value() {
  local source_file="$1" key="$2" default_value="$3"
  awk -F= -v target="$key" -v fallback="$default_value" '
    $1 == target {value=substr($0,index($0,"=")+1)}
    END {if (value != "") print value; else print fallback}
  ' "$source_file" 2>/dev/null
}

json_value() {
  local source_file="$1" key="$2" default_value="$3"
  python3 - "$source_file" "$key" "$default_value" <<'PY'
import json,sys
from pathlib import Path
try:
 value=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
 for part in sys.argv[2].split('.'):
  value=value[part]
 print(value)
except Exception:
 print(sys.argv[3])
PY
}

summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "QUALITY_SCAN_RESULT=$(summary_value "$QUALITY_OUT" SCAN_RESULT UNKNOWN)"
  echo "QUALITY_SCAN_FINDINGS=$(summary_value "$QUALITY_OUT" SCAN_FINDING_COUNT 0)"
  echo "TARGET_QUALITY_GATE=$(json_value "$TARGET_GATE_JSON" result NOT_RUN)"
  echo "TARGET_QUALITY_FINDINGS=$(json_value "$TARGET_GATE_JSON" target_finding_count 0)"
  echo "OPENCLAW_PREFLIGHT=$(json_value "$PREFLIGHT_JSON" result NOT_RUN)"
  echo "PREFLIGHT_FAILURE_STAGE=$(json_value "$PREFLIGHT_JSON" failure_stage '')"
  echo "PREFLIGHT_FAILURE_TYPE=$(json_value "$PREFLIGHT_JSON" failure_type '')"
  echo "PREFLIGHT_CONTEXT_LOADED=$(json_value "$PREFLIGHT_JSON" context_loaded NOT_RUN)"
  echo "PREFLIGHT_PYTHON_COMPILED=$(json_value "$PREFLIGHT_JSON" python_compiled NOT_RUN)"
  echo "PREFLIGHT_READINESS_READY=$(json_value "$PREFLIGHT_JSON" readiness_evidence_ready NOT_RUN)"
  echo "PREFLIGHT_TOOLS_DENIED=$(json_value "$PREFLIGHT_JSON" tools_denied_baseline NOT_RUN)"
  echo "PREFLIGHT_AGENT_CLI=$(json_value "$PREFLIGHT_JSON" agent_cli_supported NOT_RUN)"
  echo "PREFLIGHT_GATEWAY_TRANSPORT=$(json_value "$PREFLIGHT_JSON" gateway_transport_supported NOT_RUN)"
  echo "PREFLIGHT_SKILL_TARGET=$(json_value "$PREFLIGHT_JSON" skill_install_target_ready NOT_RUN)"
  echo "PREFLIGHT_PLUGIN_RUNTIME=$(json_value "$PREFLIGHT_JSON" plugin_runtime_ok NOT_RUN)"
  echo "PREFLIGHT_PUBLIC_ROUTES=$(json_value "$PREFLIGHT_JSON" public_routes_ok NOT_RUN)"
  echo "PREFLIGHT_PRIVATE_LISTENERS=$(json_value "$PREFLIGHT_JSON" internal_listeners_private NOT_RUN)"
  echo "PREFLIGHT_SOURCE_WORKTREE=$(json_value "$PREFLIGHT_JSON" source_worktree_ready NOT_RUN)"
  echo "PREFLIGHT_SOURCE_HEAD_SYNCED=$(json_value "$PREFLIGHT_JSON" source_worktree_head_synced NOT_RUN)"
  echo "PREFLIGHT_SOURCE_DIRTY_COUNT=$(json_value "$PREFLIGHT_JSON" source_worktree_dirty_count NOT_RUN)"
  echo "PREFLIGHT_SOURCE_DIRTY_PATHS=$(json_value "$PREFLIGHT_JSON" source_worktree_dirty_paths '[]')"
  echo "PREFLIGHT_SOURCE_DIRTY_PATHS_TRUNCATED=$(json_value "$PREFLIGHT_JSON" source_worktree_dirty_paths_truncated NOT_RUN)"
  echo "DATABASE_ROTATION_RESULT=$(summary_value "$ROTATION_OUT" RESULT NOT_RUN)"
  echo "DATABASE_CREDENTIAL_ROTATED=$(summary_value "$ROTATION_OUT" DATABASE_CREDENTIAL_ROTATED NO)"
  echo "DATABASE_ROTATION_EVIDENCE_COMMIT=$(summary_value "$ROTATION_OUT" EVIDENCE_COMMIT '')"
  echo "ENABLEMENT_RESULT=$(summary_value "$ENABLEMENT_OUT" RESULT NOT_RUN)"
  echo "ENABLEMENT_FAILURE_CODE=$(summary_value "$ENABLEMENT_OUT" FAILURE_CODE '')"
  echo "ROUTING_SKILL_INSTALLED=$(summary_value "$ENABLEMENT_OUT" ROUTING_SKILL_INSTALLED NO)"
  echo "NATIVE_AGENT_ACCEPTANCE_PASS=$(summary_value "$ENABLEMENT_OUT" NATIVE_AGENT_ACCEPTANCE_PASS NO)"
  echo "TELEMETRY_PRIVACY_PASS=$(summary_value "$ENABLEMENT_OUT" TELEMETRY_PRIVACY_PASS NO)"
  echo "ENABLEMENT_ROLLBACK_COUNT=$(summary_value "$ENABLEMENT_OUT" ROLLBACK_COUNT 0)"
  echo "ENABLEMENT_ROLLBACK_HEALTHY=$(summary_value "$ENABLEMENT_OUT" ROLLBACK_HEALTHY NOT_RUN)"
  echo "ENABLEMENT_EVIDENCE_COMMIT=$(summary_value "$ENABLEMENT_OUT" EVIDENCE_COMMIT '')"
  echo "ENABLEMENT_EVIDENCE_REMOTE_VERIFIED=$(summary_value "$ENABLEMENT_OUT" EVIDENCE_REMOTE_VERIFIED NO)"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "WRITE_TOOLS_ADDED=NO"
  echo "SECRET_VALUES_PRINTED=NO"
  echo "NEXT_ACTION=$([ "$RESULT" = "COMPLETED" ] && echo PERSIST_COMPLETION_AND_BEGIN_P1_TYPED_WRITE_ACTION_DESIGN || echo INSPECT_FAILED_STAGE_EVIDENCE)"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  summary
  exit 1
}

[ -n "$REPO_ROOT" ] || fail "repository_root_unresolved"
for command_name in git python3 bash awk date mktemp sort tail; do
  command -v "$command_name" >/dev/null 2>&1 || fail "required_command_missing_$command_name"
done

bash "$REPO_ROOT/scripts/dev_employee_rescan_and_triage_repository_quality.sh" > "$QUALITY_OUT" 2>&1
[ "$?" = "0" ] || fail "post_edit_quality_scan_failed"
git -C "$REPO_ROOT" pull --ff-only origin main >/dev/null 2>&1 || fail "pull_quality_evidence_failed"
git -C "$REPO_ROOT" worktree prune >/dev/null 2>&1 || true

LATEST_SCAN="$(git -C "$REPO_ROOT" ls-files 'logs/dev_employee/repository_quality_scan/repository-quality-scan-*.json' | sort | tail -n 1)"
[ -n "$LATEST_SCAN" ] || fail "latest_quality_scan_missing"
PYTHONPATH="$REPO_ROOT" python3 -m scripts.dev_employee_quality.target_gate \
  "$REPO_ROOT/$LATEST_SCAN" "$TARGET_GATE_JSON" >/dev/null 2>&1
[ "$?" = "0" ] || fail "active_remediation_target_quality_gate_failed"

PYTHONPATH="$REPO_ROOT" python3 -m scripts.dev_employee_openclaw_enable.preflight \
  "$PREFLIGHT_JSON" >/dev/null 2>&1
[ "$?" = "0" ] || fail "automatic_openclaw_preflight_failed"

bash "$REPO_ROOT/scripts/dev_employee_rotate_insight_db_credential.sh" > "$ROTATION_OUT" 2>&1
[ "$?" = "0" ] || fail "database_credential_rotation_workflow_failed"
git -C "$REPO_ROOT" pull --ff-only origin main >/dev/null 2>&1 || fail "pull_security_evidence_failed"
git -C "$REPO_ROOT" worktree prune >/dev/null 2>&1 || true

bash "$REPO_ROOT/scripts/dev_employee_enable_openclaw_readonly_tools.sh" > "$ENABLEMENT_OUT" 2>&1
[ "$?" = "0" ] || fail "automatic_openclaw_enablement_failed"

if [ "$(summary_value "$ENABLEMENT_OUT" RESULT UNKNOWN)" != "ENABLED_READONLY_AUTOMATIC_ACCEPTED" ]; then
  fail "automatic_openclaw_acceptance_result_invalid"
fi
if [ "$(summary_value "$ENABLEMENT_OUT" ROUTING_SKILL_INSTALLED NO)" != "YES" ]; then
  fail "automatic_routing_skill_result_invalid"
fi
if [ "$(summary_value "$ENABLEMENT_OUT" EVIDENCE_REMOTE_VERIFIED NO)" != "YES" ]; then
  fail "automatic_openclaw_evidence_not_remote_verified"
fi

RESULT="COMPLETED"
summary
exit 0
