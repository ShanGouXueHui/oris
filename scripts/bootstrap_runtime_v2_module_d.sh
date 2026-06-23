#!/usr/bin/env bash

# ORIS Runtime v2 Module D official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-d-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_D_COMMIT_AND_PUSH:-1}"
MODULE_C_FINAL_SHA="83358d791f643fb3f734eec1af5351c65947be78"
MODULE0_SHA="7d1d604b92b21f1213f990140b3345b4be2163ca"
LOG_FILE=""
PYTHON_BIN="${PYTHON_BIN:-python3}"

summary() { printf '%s\n' "$1"; }

fail_short() {
  summary "FAILED: $1"
  if [ -n "$LOG_FILE" ]; then summary "Log: $LOG_FILE"; fi
  exit 1
}

ensure_git_identity() {
  name="$(git config user.name 2>/dev/null)"
  email="$(git config user.email 2>/dev/null)"
  if [ -z "$name" ]; then git config user.name "oris-runtime-bot" >> "$LOG_FILE" 2>&1; fi
  if [ -z "$email" ]; then git config user.email "oris-runtime-bot@example.local" >> "$LOG_FILE" 2>&1; fi
}

commit_and_push_evidence() {
  status_label="$1"
  commit_message="$2"

  cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo for evidence commit"
  ensure_git_identity

  git add \
    docs/runtime_v2/TOOL_EXECUTOR_ADAPTER_AND_EVIDENCE_CONTRACT_MODULE_D.md \
    schemas/runtime_v2/executor_action.schema.json \
    schemas/runtime_v2/executor_result.schema.json \
    schemas/runtime_v2/evidence_artifact.schema.json \
    scripts/lib/runtime_v2_executor.py \
    tests/runtime_v2/test_executor_adapter.py \
    docs/testing/MODULE_D_TEST_PLAN.md \
    reports/testing/module_D_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_D_execution_report.md \
    reports/execution/module_D_bootstrap_latest.log >> "$LOG_FILE" 2>&1

  if git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    summary "$status_label. No file changes to commit."
    summary "Log: $LOG_FILE"
    return 0
  fi

  git commit -m "$commit_message" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    summary "$status_label, but git commit failed."
    summary "Log: $LOG_FILE"
    return "$rc"
  fi

  evidence_sha="$(git rev-parse HEAD 2>> "$LOG_FILE")"
  "$PYTHON_BIN" - <<PY >> "$LOG_FILE" 2>&1
from pathlib import Path
p = Path("reports/execution/module_D_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_D_execution_report.md reports/execution/module_D_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-d): record evidence commit sha" >> "$LOG_FILE" 2>&1
  fi

  final_sha="$(git rev-parse HEAD 2>> "$LOG_FILE")"
  git push origin "$BRANCH" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    summary "$status_label, local evidence committed but push failed."
    summary "Local commit: $final_sha"
    summary "Log: $LOG_FILE"
    return "$rc"
  fi

  summary "$status_label. Evidence pushed."
  summary "Commit: $final_sha"
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_D_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module D official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_D_bootstrap_$$.log"
LOG_FILE="$TEMP_LOG"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then PYTHON_BIN="python"; fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then fail_short "python3/python not found"; fi

if [ ! -d "$ORIS_DIR/.git" ]; then
  git clone "$ORIS_REPO_URL" "$ORIS_DIR" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then fail_short "cannot clone ORIS repo"; fi
else
  cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo"
  git fetch origin >> "$LOG_FILE" 2>&1
  git checkout "$BRANCH" >> "$LOG_FILE" 2>&1
  git pull --ff-only origin "$BRANCH" >> "$LOG_FILE" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then fail_short "cannot fast-forward ORIS repo; inspect local changes in $ORIS_DIR"; fi
fi

cd "$ORIS_DIR" || fail_short "cannot enter ORIS repo after clone/update"
mkdir -p reports/execution
LOG_FILE="$ORIS_DIR/reports/execution/module_D_bootstrap_latest.log"
{
  echo "# Module D bootstrap log"
  echo "version=$VERSION"
  echo "started_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "oris_dir=$ORIS_DIR"
  echo "branch=$BRANCH"
  echo "python_bin=$PYTHON_BIN"
  echo ""
  echo "# pre-log bootstrap output"
  if [ -f "$TEMP_LOG" ]; then cat "$TEMP_LOG"; fi
} > "$LOG_FILE" 2>&1
rm -f "$TEMP_LOG"

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_d*.sh' ! -name 'bootstrap_runtime_v2_module_d.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_d_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module D bootstrap entrypoints found; keep one official entry only"
fi

summary "Checking product repo state via git ls-remote..."
PRODUCT_CHECK_STATUS="ls_remote_unknown"
PRODUCT_HEAD="$(git ls-remote "$PRODUCT_REPO_URL" "refs/heads/$BRANCH" 2>> "$LOG_FILE" | awk '{print $1}')"
if [ -n "$PRODUCT_HEAD" ]; then PRODUCT_CHECK_STATUS="ls_remote_ok"; else PRODUCT_HEAD="UNKNOWN"; PRODUCT_CHECK_STATUS="ls_remote_failed_non_blocking"; fi

BASE_SHA="$(git rev-parse HEAD 2>> "$LOG_FILE")"
{
  echo ""
  echo "# repository state"
  echo "base_sha=$BASE_SHA"
  echo "module_C_expected_final_sha=$MODULE_C_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  echo ""
  echo "# module C evidence check"
  if [ -f reports/testing/latest_test_result.json ]; then cat reports/testing/latest_test_result.json; else echo "missing reports/testing/latest_test_result.json"; fi
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_D_TEST_PLAN.md <<'EOF'
# Module D Test Plan - Tool Executor Adapter and Evidence Contract

## Scope

Validate a safe executor abstraction that Module C worker logic can call without enabling unbounded generic execution.

## Test Targets

1. Allowed actions execute through a deterministic local test executor.
2. Denied actions are blocked before execution.
3. Evidence artifacts are created for executed allowed actions.
4. Retryable executor failures map to worker-compatible retryable outcomes.
5. Fatal executor failures map to worker-compatible fatal outcomes.
6. Approval-required actions map to worker-compatible approval outcomes.
7. Worker integration completes a run through the executor adapter.

## Acceptance

Module D passes only when tests pass and evidence is written to:

- `reports/testing/module_D_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_D_execution_report.md`
EOF

cat > schemas/runtime_v2/executor_action.schema.json <<'EOF'
{
  "version": "runtime_v2_module_D",
  "type": "object",
  "required": ["action_type", "payload"],
  "properties": {
    "action_type": {"type": "string"},
    "payload": {"type": "object"},
    "risk_level": {"enum": ["LOW", "MEDIUM", "HIGH"]},
    "idempotency_key": {"type": ["string", "null"]}
  }
}
EOF

cat > schemas/runtime_v2/executor_result.schema.json <<'EOF'
{
  "version": "runtime_v2_module_D",
  "type": "object",
  "required": ["status", "outcome_type", "evidence_ref"],
  "properties": {
    "status": {"enum": ["SUCCEEDED", "DENIED", "RETRYABLE_FAILED", "FATAL_FAILED", "APPROVAL_REQUIRED"]},
    "outcome_type": {"enum": ["success", "denied", "retryable", "fatal", "approval_required"]},
    "evidence_ref": {"type": ["string", "null"]},
    "message": {"type": "string"}
  }
}
EOF

cat > schemas/runtime_v2/evidence_artifact.schema.json <<'EOF'
{
  "version": "runtime_v2_module_D",
  "type": "object",
  "required": ["artifact_id", "action_type", "status", "created_at"],
  "properties": {
    "artifact_id": {"type": "string"},
    "action_type": {"type": "string"},
    "status": {"type": "string"},
    "created_at": {"type": "string"},
    "payload_summary": {"type": "object"}
  }
}
EOF

cat > scripts/lib/runtime_v2_executor.py <<'EOF'
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from runtime_v2_run_store import utc_now


class ExecutorPolicyError(Exception):
    pass


class DeniedActionError(ExecutorPolicyError):
    pass


DEFAULT_ALLOWED_ACTIONS = {
    "noop",
    "write_evidence",
    "fail_retryable",
    "fail_fatal",
    "require_approval",
}


class RuntimeV2Executor:
    def __init__(self, evidence_dir: Path | str, allowed_actions: Optional[Iterable[str]] = None) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_actions = set(allowed_actions or DEFAULT_ALLOWED_ACTIONS)

    def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("action_type", "")
        payload = action.get("payload", {})
        risk_level = action.get("risk_level", "LOW")

        if action_type not in self.allowed_actions:
            artifact_ref = self._write_artifact(action_type or "unknown", "DENIED", {"reason": "action_not_allowed"})
            return {
                "status": "DENIED",
                "outcome_type": "denied",
                "evidence_ref": artifact_ref,
                "message": f"action denied: {action_type}",
            }

        if risk_level == "HIGH" and action_type != "require_approval":
            artifact_ref = self._write_artifact(action_type, "APPROVAL_REQUIRED", {"reason": "high_risk_action"})
            return {
                "status": "APPROVAL_REQUIRED",
                "outcome_type": "approval_required",
                "evidence_ref": artifact_ref,
                "message": "high-risk action requires approval",
            }

        if action_type == "noop":
            artifact_ref = self._write_artifact(action_type, "SUCCEEDED", {"payload": payload})
            return {"status": "SUCCEEDED", "outcome_type": "success", "evidence_ref": artifact_ref, "message": "noop completed"}

        if action_type == "write_evidence":
            artifact_ref = self._write_artifact(action_type, "SUCCEEDED", {"payload": payload})
            return {"status": "SUCCEEDED", "outcome_type": "success", "evidence_ref": artifact_ref, "message": "evidence written"}

        if action_type == "fail_retryable":
            artifact_ref = self._write_artifact(action_type, "RETRYABLE_FAILED", {"reason": payload.get("reason", "retryable_failure")})
            return {"status": "RETRYABLE_FAILED", "outcome_type": "retryable", "evidence_ref": artifact_ref, "message": "retryable failure"}

        if action_type == "fail_fatal":
            artifact_ref = self._write_artifact(action_type, "FATAL_FAILED", {"reason": payload.get("reason", "fatal_failure")})
            return {"status": "FATAL_FAILED", "outcome_type": "fatal", "evidence_ref": artifact_ref, "message": "fatal failure"}

        if action_type == "require_approval":
            artifact_ref = self._write_artifact(action_type, "APPROVAL_REQUIRED", {"reason": payload.get("reason", "approval_required")})
            return {"status": "APPROVAL_REQUIRED", "outcome_type": "approval_required", "evidence_ref": artifact_ref, "message": "approval required"}

        artifact_ref = self._write_artifact(action_type, "FATAL_FAILED", {"reason": "unhandled_allowed_action"})
        return {"status": "FATAL_FAILED", "outcome_type": "fatal", "evidence_ref": artifact_ref, "message": "unhandled allowed action"}

    def as_worker_executor(self, action: Dict[str, Any]):
        def _executor(run: Dict[str, Any], attempt: int) -> Dict[str, Any]:
            result = self.execute(action)
            outcome_type = result["outcome_type"]
            if outcome_type == "denied":
                return {"type": "fatal", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "approval_required":
                return {"type": "approval_required", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "retryable":
                return {"type": "retryable", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            if outcome_type == "fatal":
                return {"type": "fatal", "reason": result["message"], "evidence_ref": result["evidence_ref"]}
            return {"type": "success", "evidence_ref": result["evidence_ref"]}
        return _executor

    def _write_artifact(self, action_type: str, status: str, payload_summary: Dict[str, Any]) -> str:
        artifact_id = str(uuid.uuid4())
        artifact = {
            "artifact_id": artifact_id,
            "action_type": action_type,
            "status": status,
            "created_at": utc_now(),
            "payload_summary": payload_summary,
        }
        path = self.evidence_dir / f"{artifact_id}.json"
        path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return str(path)
EOF

cat > tests/runtime_v2/test_executor_adapter.py <<'EOF'
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2ExecutorTests(unittest.TestCase):
    def make_executor(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        evidence_dir = Path(self.tmpdir.name) / "evidence"
        return RuntimeV2Executor(evidence_dir)

    def tearDown(self):
        tmpdir = getattr(self, "tmpdir", None)
        if tmpdir is not None:
            tmpdir.cleanup()

    def test_allowed_action_execution(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "noop", "payload": {"x": 1}, "risk_level": "LOW"})
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["outcome_type"], "success")

    def test_denied_action_protection(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "shell_exec", "payload": {"cmd": "rm -rf /"}, "risk_level": "HIGH"})
        self.assertEqual(result["status"], "DENIED")
        self.assertEqual(result["outcome_type"], "denied")

    def test_evidence_capture(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "write_evidence", "payload": {"note": "ok"}, "risk_level": "LOW"})
        evidence_path = Path(result["evidence_ref"])
        self.assertTrue(evidence_path.exists())
        artifact = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact["action_type"], "write_evidence")
        self.assertEqual(artifact["status"], "SUCCEEDED")

    def test_retryable_executor_failure_mapping(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "fail_retryable", "payload": {"reason": "network"}, "risk_level": "LOW"})
        self.assertEqual(result["outcome_type"], "retryable")

    def test_fatal_executor_failure_mapping(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "fail_fatal", "payload": {"reason": "policy"}, "risk_level": "LOW"})
        self.assertEqual(result["outcome_type"], "fatal")

    def test_approval_required_mapping(self):
        executor = self.make_executor()
        result = executor.execute({"action_type": "require_approval", "payload": {"reason": "high_risk"}, "risk_level": "HIGH"})
        self.assertEqual(result["outcome_type"], "approval_required")

    def test_worker_integration_with_executor_adapter(self):
        executor = self.make_executor()
        store = RuntimeV2RunStore(Path(self.tmpdir.name) / "runtime_store.json")
        worker = RuntimeV2Worker(store, "worker-d")
        run = store.create_run("module d worker integration", "Module D")
        store.enqueue(run["run_id"])
        result = worker.run_once(executor.as_worker_executor({"action_type": "noop", "payload": {}, "risk_level": "LOW"}))
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(store.get_run(run["run_id"])["state"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/TOOL_EXECUTOR_ADAPTER_AND_EVIDENCE_CONTRACT_MODULE_D.md <<'EOF'
# Runtime v2 Module D - Tool Executor Adapter and Evidence Contract

## Objective

Module D connects the Module C worker loop to a safe executor abstraction without enabling unbounded generic execution.

## Executor Boundary

The executor accepts structured actions rather than arbitrary shell commands. Actions are checked against an allowlist before execution.

Default allowed actions for Module D validation are deterministic local test actions:

- `noop`
- `write_evidence`
- `fail_retryable`
- `fail_fatal`
- `require_approval`

Denied actions produce a structured denied result and evidence artifact. They are not executed.

## Evidence Contract

Every executor decision writes an evidence artifact with:

- artifact id;
- action type;
- status;
- creation timestamp;
- payload summary.

The artifact schema is stored in `schemas/runtime_v2/evidence_artifact.schema.json`.

## Result Mapping

Executor results are mapped to worker-compatible outcomes:

- `success`
- `retryable`
- `fatal`
- `approval_required`
- `denied` as fatal policy stop for the worker

## Sandbox Policy

Module D intentionally does not expose arbitrary command execution. Real Codex/tool integration must be added behind this adapter with explicit action contracts, risk classification, evidence writing, and approval gates.

## Non-Goals

- No unrestricted shell execution.
- No production deployment.
- No product repository mutation.
- No credential handling.
EOF

summary "Generated Module D files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_C_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module D",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_C_final_sha": os.environ.get("MODULE_C_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "allowed_action_execution",
        "denied_action_protection",
        "evidence_capture",
        "retryable_executor_failure_mapping",
        "fatal_executor_failure_mapping",
        "approval_required_mapping",
        "worker_integration_with_executor_adapter",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_D_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_D_execution_report.md <<EOF
# Runtime v2 Module D Execution Report

## Module

Tool Executor Adapter and Evidence Contract

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module C Baseline

$MODULE_C_FINAL_SHA

## Product Repository Check

- Product repo check status: $PRODUCT_CHECK_STATUS
- Product repo head: $PRODUCT_HEAD
- Module 0 expected commit: $MODULE0_SHA
- Old interactive insight product continued: no

## Test Command

\`$TEST_COMMAND\`

## Test Result

- test exit code: $TEST_RC
- status: $TEST_STATUS

## Evidence Files

- \`docs/runtime_v2/TOOL_EXECUTOR_ADAPTER_AND_EVIDENCE_CONTRACT_MODULE_D.md\`
- \`schemas/runtime_v2/executor_action.schema.json\`
- \`schemas/runtime_v2/executor_result.schema.json\`
- \`schemas/runtime_v2/evidence_artifact.schema.json\`
- \`scripts/lib/runtime_v2_executor.py\`
- \`tests/runtime_v2/test_executor_adapter.py\`
- \`docs/testing/MODULE_D_TEST_PLAN.md\`
- \`reports/testing/module_D_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_D_bootstrap_latest.log\`

## Module D Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_D_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module D tests passed" "runtime-v2(module-d): add tool executor adapter and evidence contract"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module D tests failed" "runtime-v2(module-d): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
