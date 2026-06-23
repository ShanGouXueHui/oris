#!/usr/bin/env bash

# ORIS Runtime v2 Module G official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-g-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_G_COMMIT_AND_PUSH:-1}"
MODULE_F_FINAL_SHA="3e0aa696b7866aa368fd1e2020a7a9cf1b3f174a"
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
    docs/runtime_v2/END_TO_END_RUNTIME_HARNESS_AND_ACCEPTANCE_RUNNER_MODULE_G.md \
    schemas/runtime_v2/acceptance_scenario.schema.json \
    schemas/runtime_v2/acceptance_summary.schema.json \
    scripts/lib/runtime_v2_acceptance_harness.py \
    tests/runtime_v2/test_acceptance_harness.py \
    docs/testing/MODULE_G_TEST_PLAN.md \
    reports/testing/module_G_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_G_execution_report.md \
    reports/execution/module_G_bootstrap_latest.log >> "$LOG_FILE" 2>&1
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
p = Path("reports/execution/module_G_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY
  git add reports/execution/module_G_execution_report.md reports/execution/module_G_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-g): record evidence commit sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_G_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module G official bootstrap $VERSION starting..."
TEMP_LOG="/tmp/oris_module_G_bootstrap_$$.log"
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
LOG_FILE="$ORIS_DIR/reports/execution/module_G_bootstrap_latest.log"
{
  echo "# Module G bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_g*.sh' ! -name 'bootstrap_runtime_v2_module_g.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_g_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module G bootstrap entrypoints found; keep one official entry only"
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
  echo "module_F_expected_final_sha=$MODULE_F_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_G_TEST_PLAN.md <<'EOF'
# Module G Test Plan - End-to-End Runtime Harness and Acceptance Runner

## Scope

Validate deterministic end-to-end Runtime v2 scenarios that combine persistent run store, worker loop, executor adapter, evidence publisher, and approval gate.

## Test Targets

1. Success scenario completes and creates an evidence index.
2. Repair scenario handles retryable failure and completes.
3. Approval scenario enters approval, receives approval, resumes, and completes.
4. Blocked scenario enters approval, receives rejection, and becomes blocked.
5. Acceptance summary aggregates all scenario results.
6. Evidence index integrity includes artifact hashes.

## Acceptance

Module G passes only when tests pass and evidence is written to:

- `reports/testing/module_G_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_G_execution_report.md`
EOF

cat > schemas/runtime_v2/acceptance_scenario.schema.json <<'EOF'
{
  "version": "runtime_v2_module_G",
  "type": "object",
  "required": ["scenario_id", "scenario_type", "status", "run_id", "evidence_index_id"],
  "properties": {
    "scenario_id": {"type": "string"},
    "scenario_type": {"enum": ["success", "repair", "approval", "blocked"]},
    "status": {"enum": ["passed", "failed"]},
    "run_id": {"type": "string"},
    "final_state": {"type": "string"},
    "evidence_index_id": {"type": ["string", "null"]}
  }
}
EOF

cat > schemas/runtime_v2/acceptance_summary.schema.json <<'EOF'
{
  "version": "runtime_v2_module_G",
  "type": "object",
  "required": ["module", "status", "scenarios"],
  "properties": {
    "module": {"type": "string"},
    "status": {"enum": ["passed", "failed"]},
    "scenarios": {"type": "array"},
    "created_at": {"type": "string"}
  }
}
EOF

cat > scripts/lib/runtime_v2_acceptance_harness.py <<'EOF'
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from runtime_v2_approval_gate import ApprovalGateStore
from runtime_v2_evidence_publisher import RuntimeV2EvidencePublisher
from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore, utc_now
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2AcceptanceHarness:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.store = RuntimeV2RunStore(self.root / "runtime_store.json")
        self.executor = RuntimeV2Executor(self.root / "executor_evidence")
        self.publisher = RuntimeV2EvidencePublisher(self.root)
        self.approvals = ApprovalGateStore(self.root / "approval_store.json", self.store)
        self.worker = RuntimeV2Worker(self.store, "acceptance-worker", max_repair_attempts=1)
        (self.root / "summaries").mkdir(parents=True, exist_ok=True)

    def run_success_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance success", "Module G")
        self.store.enqueue(run["run_id"])
        result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "noop", "payload": {}, "risk_level": "LOW"}))
        return self._scenario_result("success", run["run_id"], result["status"] == "COMPLETED")

    def run_repair_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance repair", "Module G")
        self.store.enqueue(run["run_id"])
        def executor(run_record: Dict[str, Any], attempt: int) -> Dict[str, Any]:
            if attempt == 0:
                self.executor.execute({"action_type": "fail_retryable", "payload": {"reason": "synthetic"}, "risk_level": "LOW"})
                return {"type": "retryable", "reason": "synthetic"}
            self.executor.execute({"action_type": "write_evidence", "payload": {"repaired": True}, "risk_level": "LOW"})
            return {"type": "success"}
        result = self.worker.run_once(executor)
        return self._scenario_result("repair", run["run_id"], result["status"] == "REPAIRED")

    def run_approval_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance approval", "Module G")
        self.store.enqueue(run["run_id"])
        wait_result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "require_approval", "payload": {"reason": "manual gate"}, "risk_level": "HIGH"}))
        approval = self.approvals.create_request_from_worker_result(run["run_id"], wait_result, "require_approval")
        self.approvals.decide(approval["approval_id"], "APPROVE", "control-plane")
        self.store.enqueue(run["run_id"])
        done = self.worker.run_once(self.executor.as_worker_executor({"action_type": "noop", "payload": {}, "risk_level": "LOW"}))
        return self._scenario_result("approval", run["run_id"], done["status"] == "COMPLETED")

    def run_blocked_scenario(self) -> Dict[str, Any]:
        run = self.store.create_run("acceptance blocked", "Module G")
        self.store.enqueue(run["run_id"])
        wait_result = self.worker.run_once(self.executor.as_worker_executor({"action_type": "require_approval", "payload": {"reason": "manual gate"}, "risk_level": "HIGH"}))
        approval = self.approvals.create_request_from_worker_result(run["run_id"], wait_result, "require_approval")
        self.approvals.decide(approval["approval_id"], "REJECT", "control-plane")
        return self._scenario_result("blocked", run["run_id"], self.store.get_run(run["run_id"])["state"] == "FAILED_BLOCKED")

    def run_all(self) -> Dict[str, Any]:
        scenarios = [
            self.run_success_scenario(),
            self.run_repair_scenario(),
            self.run_approval_scenario(),
            self.run_blocked_scenario(),
        ]
        status = "passed" if all(item["status"] == "passed" for item in scenarios) else "failed"
        summary = {"module": "Runtime v2 Module G", "status": status, "scenarios": scenarios, "created_at": utc_now()}
        (self.root / "summaries" / "acceptance_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return summary

    def _scenario_result(self, scenario_type: str, run_id: str, ok: bool) -> Dict[str, Any]:
        final_state = self.store.get_run(run_id)["state"]
        summary_path = self.root / "summaries" / f"{scenario_type}_{run_id}.json"
        payload = {"scenario_type": scenario_type, "run_id": run_id, "final_state": final_state, "ok": ok}
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        artifact_paths = [str(path.relative_to(self.root)) for path in (self.root / "executor_evidence").glob("*.json")]
        artifact_paths.append(str(summary_path.relative_to(self.root)))
        index = self.publisher.build_index(f"Module G {scenario_type}", "passed" if ok else "failed", artifact_paths)
        return {
            "scenario_id": f"{scenario_type}:{run_id}",
            "scenario_type": scenario_type,
            "status": "passed" if ok else "failed",
            "run_id": run_id,
            "final_state": final_state,
            "evidence_index_id": index["index_id"],
        }
EOF

cat > tests/runtime_v2/test_acceptance_harness.py <<'EOF'
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_acceptance_harness import RuntimeV2AcceptanceHarness


class RuntimeV2AcceptanceHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.harness = RuntimeV2AcceptanceHarness(Path(self.tmpdir.name))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_success_scenario_completes_with_evidence_index(self):
        result = self.harness.run_success_scenario()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["final_state"], "COMPLETED")
        self.assertIsNotNone(result["evidence_index_id"])

    def test_repair_scenario_completes(self):
        result = self.harness.run_repair_scenario()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["final_state"], "COMPLETED")

    def test_approval_scenario_resumes_and_completes(self):
        result = self.harness.run_approval_scenario()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["final_state"], "COMPLETED")

    def test_blocked_scenario_reaches_failed_blocked(self):
        result = self.harness.run_blocked_scenario()
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["final_state"], "FAILED_BLOCKED")

    def test_acceptance_summary_generation(self):
        summary = self.harness.run_all()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(len(summary["scenarios"]), 4)

    def test_evidence_index_integrity(self):
        result = self.harness.run_success_scenario()
        self.assertEqual(len(result["evidence_index_id"]), 24)


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/END_TO_END_RUNTIME_HARNESS_AND_ACCEPTANCE_RUNNER_MODULE_G.md <<'EOF'
# Runtime v2 Module G - End-to-End Runtime Harness and Acceptance Runner

## Objective

Module G combines Modules B-F into deterministic acceptance scenarios that validate the runtime substrate as an integrated system.

## Scenarios

1. Success: run creation, queueing, worker execution, executor success, completion, evidence indexing.
2. Repair: retryable failure, repair path, completion.
3. Approval: high-risk action, approval request, approve decision, resumed execution, completion.
4. Blocked: high-risk action, reject decision, blocked state.

## Evidence

Each scenario writes a scenario summary and creates an evidence index using the Module E publisher.

## Boundary

Module G is still a deterministic local harness. It does not mutate product repositories, perform deployment, or call external services.
EOF

summary "Generated Module G files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_F_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path
result = {
    "module": "Runtime v2 Module G",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_F_final_sha": os.environ.get("MODULE_F_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": ["success_scenario", "repair_scenario", "approval_scenario", "blocked_scenario", "acceptance_summary", "evidence_index_integrity"],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_G_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_G_execution_report.md <<EOF
# Runtime v2 Module G Execution Report

## Module

End-to-End Runtime Harness and Acceptance Runner

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module F Baseline

$MODULE_F_FINAL_SHA

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

- \`docs/runtime_v2/END_TO_END_RUNTIME_HARNESS_AND_ACCEPTANCE_RUNNER_MODULE_G.md\`
- \`schemas/runtime_v2/acceptance_scenario.schema.json\`
- \`schemas/runtime_v2/acceptance_summary.schema.json\`
- \`scripts/lib/runtime_v2_acceptance_harness.py\`
- \`tests/runtime_v2/test_acceptance_harness.py\`
- \`docs/testing/MODULE_G_TEST_PLAN.md\`
- \`reports/testing/module_G_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_G_bootstrap_latest.log\`

## Module G Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_G_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module G tests passed" "runtime-v2(module-g): add end-to-end acceptance harness"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module G tests failed" "runtime-v2(module-g): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
