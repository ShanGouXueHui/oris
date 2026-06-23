#!/usr/bin/env bash

# ORIS Runtime v2 Module F official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-f-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_F_COMMIT_AND_PUSH:-1}"
MODULE_E_FINAL_SHA="b8b168051ed3a3cd67ddea8798ec2f1983cd5a40"
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
    docs/runtime_v2/APPROVAL_GATE_AND_CONTROL_PLANE_CONTRACT_MODULE_F.md \
    schemas/runtime_v2/approval_request.schema.json \
    schemas/runtime_v2/approval_decision.schema.json \
    scripts/lib/runtime_v2_approval_gate.py \
    tests/runtime_v2/test_approval_gate.py \
    docs/testing/MODULE_F_TEST_PLAN.md \
    reports/testing/module_F_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_F_execution_report.md \
    reports/execution/module_F_bootstrap_latest.log >> "$LOG_FILE" 2>&1

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
p = Path("reports/execution/module_F_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_F_execution_report.md reports/execution/module_F_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-f): record evidence commit sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_F_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module F official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_F_bootstrap_$$.log"
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
LOG_FILE="$ORIS_DIR/reports/execution/module_F_bootstrap_latest.log"
{
  echo "# Module F bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_f*.sh' ! -name 'bootstrap_runtime_v2_module_f.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_f_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module F bootstrap entrypoints found; keep one official entry only"
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
  echo "module_E_expected_final_sha=$MODULE_E_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  echo ""
  echo "# module E evidence check"
  if [ -f reports/testing/latest_test_result.json ]; then cat reports/testing/latest_test_result.json; else echo "missing reports/testing/latest_test_result.json"; fi
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_F_TEST_PLAN.md <<'EOF'
# Module F Test Plan - Approval Gate and Control Plane Contract

## Scope

Validate the control-plane approval boundary for high-risk runtime actions while keeping OpenClaw Web outside the long-running execution path.

## Test Targets

1. Approval requests are created from runs and high-risk action metadata.
2. Approve decisions transition runs from `WAITING_APPROVAL` back to `RUNNING`.
3. Reject decisions transition runs to `FAILED_BLOCKED`.
4. Expired approvals transition runs to `FAILED_BLOCKED`.
5. Duplicate decisions are idempotent and do not mutate final decision state.
6. Approval issue payloads summarize requested action and evidence reference.
7. Worker/executor approval outcome can be converted into a pending approval request.

## Acceptance

Module F passes only when tests pass and evidence is written to:

- `reports/testing/module_F_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_F_execution_report.md`
EOF

cat > schemas/runtime_v2/approval_request.schema.json <<'EOF'
{
  "version": "runtime_v2_module_F",
  "type": "object",
  "required": ["approval_id", "run_id", "status", "risk_level", "action_type", "created_at"],
  "properties": {
    "approval_id": {"type": "string"},
    "run_id": {"type": "string"},
    "status": {"enum": ["PENDING", "APPROVED", "REJECTED", "EXPIRED"]},
    "risk_level": {"enum": ["MEDIUM", "HIGH"]},
    "action_type": {"type": "string"},
    "reason": {"type": "string"},
    "evidence_ref": {"type": ["string", "null"]},
    "created_at": {"type": "string"},
    "decided_at": {"type": ["string", "null"]}
  }
}
EOF

cat > schemas/runtime_v2/approval_decision.schema.json <<'EOF'
{
  "version": "runtime_v2_module_F",
  "type": "object",
  "required": ["approval_id", "decision", "actor", "decided_at"],
  "properties": {
    "approval_id": {"type": "string"},
    "decision": {"enum": ["APPROVE", "REJECT", "EXPIRE"]},
    "actor": {"type": "string"},
    "comment": {"type": "string"},
    "decided_at": {"type": "string"}
  }
}
EOF

cat > scripts/lib/runtime_v2_approval_gate.py <<'EOF'
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from runtime_v2_run_store import RuntimeV2RunStore, utc_now


class ApprovalGateError(Exception):
    pass


class ApprovalNotFoundError(ApprovalGateError):
    pass


class ApprovalGateStore:
    def __init__(self, path: Path | str, run_store: RuntimeV2RunStore) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_store = run_store
        if not self.path.exists():
            self._write({"approvals": {}, "decisions": []})

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def create_request(self, run_id: str, action_type: str, risk_level: str, reason: str, evidence_ref: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if idempotency_key:
            for approval in data["approvals"].values():
                if approval.get("idempotency_key") == idempotency_key:
                    return approval
        approval_id = str(uuid.uuid4())
        approval = {
            "approval_id": approval_id,
            "run_id": run_id,
            "status": "PENDING",
            "risk_level": risk_level,
            "action_type": action_type,
            "reason": reason,
            "evidence_ref": evidence_ref,
            "idempotency_key": idempotency_key,
            "created_at": utc_now(),
            "decided_at": None,
        }
        data["approvals"][approval_id] = approval
        data["decisions"].append({"approval_id": approval_id, "decision": "REQUESTED", "actor": "runtime", "comment": reason, "decided_at": approval["created_at"]})
        self._write(data)
        return approval

    def get_request(self, approval_id: str) -> Dict[str, Any]:
        data = self._read()
        if approval_id not in data["approvals"]:
            raise ApprovalNotFoundError(approval_id)
        return data["approvals"][approval_id]

    def decide(self, approval_id: str, decision: str, actor: str, comment: str = "") -> Dict[str, Any]:
        data = self._read()
        if approval_id not in data["approvals"]:
            raise ApprovalNotFoundError(approval_id)
        approval = data["approvals"][approval_id]
        if approval["status"] != "PENDING":
            return approval
        now = utc_now()
        approval["decided_at"] = now
        normalized = decision.upper()
        if normalized == "APPROVE":
            approval["status"] = "APPROVED"
            self.run_store.transition_run(approval["run_id"], "RUNNING", actor=actor, reason="approval_approved")
        elif normalized == "REJECT":
            approval["status"] = "REJECTED"
            self.run_store.transition_run(approval["run_id"], "FAILED_BLOCKED", actor=actor, reason="approval_rejected")
        elif normalized == "EXPIRE":
            approval["status"] = "EXPIRED"
            self.run_store.transition_run(approval["run_id"], "FAILED_BLOCKED", actor=actor, reason="approval_expired")
        else:
            raise ApprovalGateError(f"unknown decision: {decision}")
        data["decisions"].append({"approval_id": approval_id, "decision": normalized, "actor": actor, "comment": comment, "decided_at": now})
        self._write(data)
        return approval

    def create_issue_payload(self, approval_id: str) -> Dict[str, Any]:
        approval = self.get_request(approval_id)
        title = f"Approval required: {approval['action_type']} for run {approval['run_id']}"
        body = (
            f"Risk level: {approval['risk_level']}\n\n"
            f"Reason: {approval['reason']}\n\n"
            f"Evidence: `{approval.get('evidence_ref')}`\n\n"
            "Decision options: APPROVE, REJECT, EXPIRE"
        )
        return {"title": title, "body": body, "approval_id": approval_id, "run_id": approval["run_id"]}

    def create_request_from_worker_result(self, run_id: str, worker_result: Dict[str, Any], action_type: str = "unknown_high_risk_action") -> Dict[str, Any]:
        if worker_result.get("status") != "WAITING_APPROVAL":
            raise ApprovalGateError("worker result is not waiting for approval")
        return self.create_request(
            run_id=run_id,
            action_type=action_type,
            risk_level="HIGH",
            reason=worker_result.get("decision", "approval_required"),
            evidence_ref=worker_result.get("evidence_ref"),
            idempotency_key=f"approval:{run_id}:{action_type}",
        )
EOF

cat > tests/runtime_v2/test_approval_gate.py <<'EOF'
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_approval_gate import ApprovalGateStore
from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore
from runtime_v2_worker import RuntimeV2Worker


class ApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.run_store = RuntimeV2RunStore(self.root / "runtime_store.json")
        self.gate = ApprovalGateStore(self.root / "approval_store.json", self.run_store)

    def tearDown(self):
        self.tmpdir.cleanup()

    def create_waiting_run(self):
        run = self.run_store.create_run("approval", "Module F")
        for state in ["PLANNED", "READY", "RUNNING", "WAITING_APPROVAL"]:
            run = self.run_store.transition_run(run["run_id"], state)
        return run

    def test_request_creation(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "production deploy", "evidence.json")
        self.assertEqual(approval["status"], "PENDING")
        self.assertEqual(approval["run_id"], run["run_id"])

    def test_approve_path(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "ok")
        decided = self.gate.decide(approval["approval_id"], "APPROVE", "human")
        self.assertEqual(decided["status"], "APPROVED")
        self.assertEqual(self.run_store.get_run(run["run_id"])["state"], "RUNNING")

    def test_reject_path(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "not ok")
        decided = self.gate.decide(approval["approval_id"], "REJECT", "human")
        self.assertEqual(decided["status"], "REJECTED")
        self.assertEqual(self.run_store.get_run(run["run_id"])["state"], "FAILED_BLOCKED")

    def test_expire_path(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "timeout")
        decided = self.gate.decide(approval["approval_id"], "EXPIRE", "runtime")
        self.assertEqual(decided["status"], "EXPIRED")
        self.assertEqual(self.run_store.get_run(run["run_id"])["state"], "FAILED_BLOCKED")

    def test_idempotent_decision_handling(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "ok")
        first = self.gate.decide(approval["approval_id"], "APPROVE", "human")
        second = self.gate.decide(approval["approval_id"], "REJECT", "human")
        self.assertEqual(first["status"], "APPROVED")
        self.assertEqual(second["status"], "APPROVED")

    def test_issue_payload_generation(self):
        run = self.create_waiting_run()
        approval = self.gate.create_request(run["run_id"], "deploy", "HIGH", "production deploy", "evidence.json")
        payload = self.gate.create_issue_payload(approval["approval_id"])
        self.assertIn("Approval required", payload["title"])
        self.assertIn("production deploy", payload["body"])
        self.assertIn("evidence.json", payload["body"])

    def test_worker_executor_approval_integration(self):
        executor = RuntimeV2Executor(self.root / "executor_evidence")
        worker = RuntimeV2Worker(self.run_store, "worker-f")
        run = self.run_store.create_run("approval integration", "Module F")
        self.run_store.enqueue(run["run_id"])
        result = worker.run_once(executor.as_worker_executor({"action_type": "require_approval", "payload": {"reason": "manual gate"}, "risk_level": "HIGH"}))
        self.assertEqual(result["status"], "WAITING_APPROVAL")
        approval = self.gate.create_request_from_worker_result(run["run_id"], result, "require_approval")
        self.assertEqual(approval["status"], "PENDING")


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/APPROVAL_GATE_AND_CONTROL_PLANE_CONTRACT_MODULE_F.md <<'EOF'
# Runtime v2 Module F - Approval Gate and Control Plane Contract

## Objective

Module F formalizes the OpenClaw Web control-plane boundary for high-risk actions while keeping the autonomous worker as the execution runtime.

## Approval Request Contract

Approval requests capture:

- approval id;
- run id;
- status;
- risk level;
- action type;
- reason;
- evidence reference;
- timestamps.

The schema is stored in `schemas/runtime_v2/approval_request.schema.json`.

## Approval Decision Contract

Decisions are explicit and auditable:

- `APPROVE`
- `REJECT`
- `EXPIRE`

The schema is stored in `schemas/runtime_v2/approval_decision.schema.json`.

## State Mapping

- `APPROVE`: `WAITING_APPROVAL -> RUNNING`
- `REJECT`: `WAITING_APPROVAL -> FAILED_BLOCKED`
- `EXPIRE`: `WAITING_APPROVAL -> FAILED_BLOCKED`

Duplicate decisions are idempotent: once a request is no longer pending, later decisions return the existing state without mutating it.

## Control Plane Boundary

OpenClaw Web may create or resolve approval decisions. It does not become the long-running execution runtime.

## Non-Goals

- No web UI implementation.
- No production auth/RBAC.
- No product repository mutation.
- No deployment workflow.
EOF

summary "Generated Module F files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_E_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module F",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_E_final_sha": os.environ.get("MODULE_E_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "request_creation",
        "approve_path",
        "reject_path",
        "expire_path",
        "idempotent_decision_handling",
        "issue_payload_generation",
        "worker_executor_approval_integration",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_F_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_F_execution_report.md <<EOF
# Runtime v2 Module F Execution Report

## Module

Approval Gate and Control Plane Contract

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module E Baseline

$MODULE_E_FINAL_SHA

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

- \`docs/runtime_v2/APPROVAL_GATE_AND_CONTROL_PLANE_CONTRACT_MODULE_F.md\`
- \`schemas/runtime_v2/approval_request.schema.json\`
- \`schemas/runtime_v2/approval_decision.schema.json\`
- \`scripts/lib/runtime_v2_approval_gate.py\`
- \`tests/runtime_v2/test_approval_gate.py\`
- \`docs/testing/MODULE_F_TEST_PLAN.md\`
- \`reports/testing/module_F_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_F_bootstrap_latest.log\`

## Module F Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_F_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module F tests passed" "runtime-v2(module-f): add approval gate and control plane contract"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module F tests failed" "runtime-v2(module-f): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
