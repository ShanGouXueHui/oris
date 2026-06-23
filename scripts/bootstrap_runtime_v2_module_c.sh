#!/usr/bin/env bash

# ORIS Runtime v2 Module C official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-23-runtime-v2-module-c-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_C_COMMIT_AND_PUSH:-1}"
MODULE_B_FINAL_SHA="68a704da3f03bff31206f90cb5806f240c8ba9f6"
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
    docs/runtime_v2/AUTONOMOUS_WORKER_LOOP_AND_REPAIR_POLICY_MODULE_C.md \
    schemas/runtime_v2/worker_iteration.schema.json \
    scripts/lib/runtime_v2_worker.py \
    tests/runtime_v2/test_worker_loop.py \
    docs/testing/MODULE_C_TEST_PLAN.md \
    reports/testing/module_C_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_C_execution_report.md \
    reports/execution/module_C_bootstrap_latest.log >> "$LOG_FILE" 2>&1

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
p = Path("reports/execution/module_C_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_C_execution_report.md reports/execution/module_C_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-c): record evidence commit sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_C_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module C official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_C_bootstrap_$$.log"
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
LOG_FILE="$ORIS_DIR/reports/execution/module_C_bootstrap_latest.log"
{
  echo "# Module C bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_c*.sh' ! -name 'bootstrap_runtime_v2_module_c.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_c_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module C bootstrap entrypoints found; keep one official entry only"
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
  echo "module_B_expected_final_sha=$MODULE_B_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  echo ""
  echo "# module B evidence check"
  if [ -f reports/testing/latest_test_result.json ]; then cat reports/testing/latest_test_result.json; else echo "missing reports/testing/latest_test_result.json"; fi
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_C_TEST_PLAN.md <<'EOF'
# Module C Test Plan - Autonomous Worker Loop and Repair Policy

## Scope

Validate a bounded autonomous worker iteration that uses the Module B persistent run store and queue contract.

## Test Targets

1. A successful worker iteration claims one queued item and drives a run to `COMPLETED`.
2. A retryable task failure is repaired and then completed within retry budget.
3. An approval-required task enters `WAITING_APPROVAL` and leaves the queue item claimed for control-plane action.
4. A fatal task failure is recorded as `FAILED_FATAL`.
5. A terminal run is not mutated by a worker iteration.
6. Worker decisions are recorded in the append-only event log.

## Acceptance

Module C passes only when tests pass and evidence is written to:

- `reports/testing/module_C_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_C_execution_report.md`
EOF

cat > schemas/runtime_v2/worker_iteration.schema.json <<'EOF'
{
  "version": "runtime_v2_module_C",
  "type": "object",
  "required": ["worker_id", "status", "run_id", "queue_id", "decision"],
  "properties": {
    "worker_id": {"type": "string"},
    "status": {"enum": ["IDLE", "COMPLETED", "REPAIRED", "WAITING_APPROVAL", "FAILED_FATAL", "SKIPPED_TERMINAL"]},
    "run_id": {"type": ["string", "null"]},
    "queue_id": {"type": ["string", "null"]},
    "decision": {"type": "string"},
    "attempts": {"type": "integer"},
    "created_at": {"type": "string"}
  }
}
EOF

cat > scripts/lib/runtime_v2_worker.py <<'EOF'
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runtime_v2_run_store import InvalidTransitionError, RuntimeV2RunStore, utc_now

TaskExecutor = Callable[[Dict[str, Any], int], Dict[str, Any]]


class RuntimeV2Worker:
    def __init__(self, store: RuntimeV2RunStore, worker_id: str, max_repair_attempts: int = 1) -> None:
        self.store = store
        self.worker_id = worker_id
        self.max_repair_attempts = max_repair_attempts

    def run_once(self, executor: Optional[TaskExecutor] = None) -> Dict[str, Any]:
        item = self.store.claim_next(self.worker_id)
        if item is None:
            return self._iteration("IDLE", None, None, "no_queued_item", 0)

        run = self.store.get_run(item["run_id"])
        if run["state"] in {"COMPLETED", "FAILED_FATAL", "CANCELLED"}:
            self.store.ack_queue_item(item["queue_id"])
            return self._iteration("SKIPPED_TERMINAL", run["run_id"], item["queue_id"], "terminal_run_skipped", 0)

        self._drive_to_running(run["run_id"])
        run = self.store.get_run(run["run_id"])

        task_executor = executor or self._default_success_executor
        attempts = 0
        while True:
            outcome = task_executor(run, attempts)
            outcome_type = outcome.get("type", "success")

            if outcome_type == "success":
                self._complete_successfully(run["run_id"])
                self.store.ack_queue_item(item["queue_id"])
                self._record_worker_event(run["run_id"], "WORKER_ITERATION_COMPLETED", {"queue_id": item["queue_id"], "attempts": attempts})
                status = "REPAIRED" if attempts > 0 else "COMPLETED"
                return self._iteration(status, run["run_id"], item["queue_id"], "success", attempts)

            if outcome_type == "approval_required":
                self.store.transition_run(run["run_id"], "WAITING_APPROVAL", actor=self.worker_id, reason=outcome.get("reason", "approval_required"))
                self._record_worker_event(run["run_id"], "WORKER_WAITING_APPROVAL", {"queue_id": item["queue_id"], "reason": outcome.get("reason", "")})
                return self._iteration("WAITING_APPROVAL", run["run_id"], item["queue_id"], "approval_required", attempts)

            if outcome_type == "fatal":
                self._fail_fatally(run["run_id"], outcome.get("reason", "fatal"))
                self.store.ack_queue_item(item["queue_id"])
                self._record_worker_event(run["run_id"], "WORKER_FATAL_FAILURE", {"queue_id": item["queue_id"], "reason": outcome.get("reason", "")})
                return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "fatal", attempts)

            if outcome_type == "retryable":
                if attempts >= self.max_repair_attempts:
                    self._fail_fatally(run["run_id"], "retry_budget_exhausted")
                    self.store.ack_queue_item(item["queue_id"])
                    return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "retry_budget_exhausted", attempts)
                self.store.transition_run(run["run_id"], "FAILED_RETRYABLE", actor=self.worker_id, reason=outcome.get("reason", "retryable"))
                self.store.transition_run(run["run_id"], "REPAIRING", actor=self.worker_id, reason="auto_repair")
                self.store.transition_run(run["run_id"], "TESTING", actor=self.worker_id, reason="post_repair_test")
                self._record_worker_event(run["run_id"], "WORKER_REPAIR_ATTEMPTED", {"queue_id": item["queue_id"], "attempt": attempts + 1})
                attempts += 1
                run = self.store.get_run(run["run_id"])
                continue

            self._fail_fatally(run["run_id"], f"unknown_outcome:{outcome_type}")
            self.store.ack_queue_item(item["queue_id"])
            return self._iteration("FAILED_FATAL", run["run_id"], item["queue_id"], "unknown_outcome", attempts)

    def _drive_to_running(self, run_id: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RECEIVED":
            run = self.store.transition_run(run_id, "PLANNED", actor=self.worker_id, reason="worker_planned")
        if run["state"] == "PLANNED":
            run = self.store.transition_run(run_id, "READY", actor=self.worker_id, reason="worker_ready")
        if run["state"] == "READY":
            self.store.transition_run(run_id, "RUNNING", actor=self.worker_id, reason="worker_running")

    def _complete_successfully(self, run_id: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RUNNING":
            run = self.store.transition_run(run_id, "TESTING", actor=self.worker_id, reason="tests_started")
        if run["state"] == "TESTING":
            run = self.store.transition_run(run_id, "COMMITTING", actor=self.worker_id, reason="evidence_ready")
        if run["state"] == "COMMITTING":
            self.store.transition_run(run_id, "COMPLETED", actor=self.worker_id, reason="worker_completed")

    def _fail_fatally(self, run_id: str, reason: str) -> None:
        run = self.store.get_run(run_id)
        if run["state"] == "RUNNING":
            self.store.transition_run(run_id, "FAILED_RETRYABLE", actor=self.worker_id, reason=reason)
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason="fatal_terminal_stop")
            return
        if run["state"] in {"FAILED_RETRYABLE", "FAILED_BLOCKED"}:
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason=reason)
            return
        try:
            self.store.transition_run(run_id, "CANCELLED", actor=self.worker_id, reason=reason)
        except InvalidTransitionError:
            pass

    def _record_worker_event(self, run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        data = self.store._read()
        self.store._append_event(data, event_type, run_id, payload)
        self.store._write(data)

    def _iteration(self, status: str, run_id: Optional[str], queue_id: Optional[str], decision: str, attempts: int) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "status": status,
            "run_id": run_id,
            "queue_id": queue_id,
            "decision": decision,
            "attempts": attempts,
            "created_at": utc_now(),
        }

    @staticmethod
    def _default_success_executor(run: Dict[str, Any], attempt: int) -> Dict[str, Any]:
        return {"type": "success"}
EOF

cat > tests/runtime_v2/test_worker_loop.py <<'EOF'
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_run_store import InvalidTransitionError, RuntimeV2RunStore
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2WorkerTests(unittest.TestCase):
    def make_store_and_worker(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        store = RuntimeV2RunStore(Path(self.tmpdir.name) / "runtime_store.json")
        worker = RuntimeV2Worker(store, "worker-c", max_repair_attempts=1)
        return store, worker

    def tearDown(self):
        tmpdir = getattr(self, "tmpdir", None)
        if tmpdir is not None:
            tmpdir.cleanup()

    def test_successful_worker_iteration_completes_run(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c success", "Module C")
        store.enqueue(run["run_id"])
        result = worker.run_once(lambda run, attempt: {"type": "success"})
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(store.get_run(run["run_id"])["state"], "COMPLETED")
        self.assertIsNone(store.claim_next("other"))

    def test_retryable_failure_is_repaired_and_completed(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c repair", "Module C")
        store.enqueue(run["run_id"])

        def executor(run_record, attempt):
            if attempt == 0:
                return {"type": "retryable", "reason": "first_test_failure"}
            return {"type": "success"}

        result = worker.run_once(executor)
        self.assertEqual(result["status"], "REPAIRED")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(store.get_run(run["run_id"])["state"], "COMPLETED")

    def test_approval_required_enters_waiting_approval(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c approval", "Module C")
        store.enqueue(run["run_id"])
        result = worker.run_once(lambda run, attempt: {"type": "approval_required", "reason": "high_risk_action"})
        self.assertEqual(result["status"], "WAITING_APPROVAL")
        self.assertEqual(store.get_run(run["run_id"])["state"], "WAITING_APPROVAL")

    def test_fatal_failure_records_terminal_stop(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c fatal", "Module C")
        store.enqueue(run["run_id"])
        result = worker.run_once(lambda run, attempt: {"type": "fatal", "reason": "non_recoverable"})
        self.assertEqual(result["status"], "FAILED_FATAL")
        self.assertIn(store.get_run(run["run_id"])["state"], {"CANCELLED", "FAILED_FATAL"})

    def test_terminal_run_is_not_mutated(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c terminal", "Module C")
        for state in ["PLANNED", "READY", "RUNNING", "TESTING", "COMMITTING", "COMPLETED"]:
            run = store.transition_run(run["run_id"], state)
        store.enqueue(run["run_id"])
        result = worker.run_once()
        self.assertEqual(result["status"], "SKIPPED_TERMINAL")
        self.assertEqual(store.get_run(run["run_id"])["state"], "COMPLETED")

    def test_worker_events_are_persisted(self):
        store, worker = self.make_store_and_worker()
        run = store.create_run("module c events", "Module C")
        store.enqueue(run["run_id"])
        worker.run_once(lambda run, attempt: {"type": "success"})
        event_types = [event["event_type"] for event in store.list_events(run["run_id"])]
        self.assertIn("WORKER_ITERATION_COMPLETED", event_types)
        reloaded = RuntimeV2RunStore(store.path)
        reloaded_types = [event["event_type"] for event in reloaded.list_events(run["run_id"])]
        self.assertIn("WORKER_ITERATION_COMPLETED", reloaded_types)


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/AUTONOMOUS_WORKER_LOOP_AND_REPAIR_POLICY_MODULE_C.md <<'EOF'
# Runtime v2 Module C - Autonomous Worker Loop and Repair Policy

## Objective

Module C connects the Module B persistent run store and queue contract to a bounded autonomous worker iteration.

## Worker Loop Contract

One worker iteration performs at most one queue claim and one bounded task attempt sequence:

1. claim next queued item;
2. skip terminal runs safely;
3. drive run from `RECEIVED` to `RUNNING` through valid Module A transitions;
4. execute a task executor;
5. map task outcome to success, retryable repair, approval gate, or fatal stop;
6. write append-only worker evidence events;
7. ack queue item when the worker path reaches terminal handling.

## Repair Policy

Retryable failures transition through:

```text
RUNNING -> FAILED_RETRYABLE -> REPAIRING -> TESTING
```

The worker then retries within a bounded `max_repair_attempts` budget.

## Approval Policy

Approval-required outcomes transition to `WAITING_APPROVAL` and do not auto-complete. This represents the OpenClaw Web control-plane approval boundary.

## Fatal Policy

Fatal outcomes are converted to a safe terminal stop using existing Module A transitions. The worker records `WORKER_FATAL_FAILURE` evidence.

## Evidence Policy

Worker decisions are appended to the persistent event log. Long execution logs are written to `reports/execution/`; concise test results are written to `reports/testing/`.

## Non-Goals

- No real Codex execution yet.
- No production deployment.
- No product repository mutation.
- No approval UI implementation yet.
EOF

summary "Generated Module C files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_B_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module C",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_B_final_sha": os.environ.get("MODULE_B_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "successful_worker_iteration_completes_run",
        "retryable_failure_is_repaired_and_completed",
        "approval_required_enters_waiting_approval",
        "fatal_failure_records_terminal_stop",
        "terminal_run_is_not_mutated",
        "worker_events_are_persisted",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_C_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_C_execution_report.md <<EOF
# Runtime v2 Module C Execution Report

## Module

Autonomous Worker Loop and Repair Policy

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module B Baseline

$MODULE_B_FINAL_SHA

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

- \`docs/runtime_v2/AUTONOMOUS_WORKER_LOOP_AND_REPAIR_POLICY_MODULE_C.md\`
- \`schemas/runtime_v2/worker_iteration.schema.json\`
- \`scripts/lib/runtime_v2_worker.py\`
- \`tests/runtime_v2/test_worker_loop.py\`
- \`docs/testing/MODULE_C_TEST_PLAN.md\`
- \`reports/testing/module_C_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_C_bootstrap_latest.log\`

## Module C Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_C_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module C tests passed" "runtime-v2(module-c): add autonomous worker loop and repair policy"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module C tests failed" "runtime-v2(module-c): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
