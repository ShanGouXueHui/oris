#!/usr/bin/env bash

# ORIS Runtime v2 Module B official bootstrap script.
# Policy: do not use `set -e`; terminal output stays short; detailed logs are written as GitHub evidence.

VERSION="2026-06-22-runtime-v2-module-b-official"
ORIS_REPO_URL="${ORIS_REPO_URL:-https://github.com/ShanGouXueHui/oris.git}"
PRODUCT_REPO_URL="${PRODUCT_REPO_URL:-https://github.com/ShanGouXueHui/oris-commercial-insight-employee.git}"
WORKDIR="${ORIS_WORKDIR:-$HOME/projects}"
ORIS_DIR="${ORIS_DIR:-$WORKDIR/oris}"
BRANCH="${ORIS_BRANCH:-main}"
COMMIT_AND_PUSH="${ORIS_MODULE_B_COMMIT_AND_PUSH:-1}"
MODULE_A_FINAL_SHA="c244e2467fe153377b370df0ffc35d541b8b3ef1"
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
    docs/runtime_v2/PERSISTENT_RUN_STORE_AND_QUEUE_CONTRACT_MODULE_B.md \
    schemas/runtime_v2/run_record.schema.json \
    schemas/runtime_v2/queue_item.schema.json \
    scripts/lib/runtime_v2_run_store.py \
    tests/runtime_v2/test_run_store_queue.py \
    docs/testing/MODULE_B_TEST_PLAN.md \
    reports/testing/module_B_test_result.json \
    reports/testing/latest_test_result.json \
    reports/execution/module_B_execution_report.md \
    reports/execution/module_B_bootstrap_latest.log >> "$LOG_FILE" 2>&1

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
p = Path("reports/execution/module_B_execution_report.md")
text = p.read_text(encoding="utf-8")
text = text.replace("Pending until evidence commit completes.", "$evidence_sha")
p.write_text(text, encoding="utf-8")
PY

  git add reports/execution/module_B_execution_report.md reports/execution/module_B_bootstrap_latest.log >> "$LOG_FILE" 2>&1
  if ! git diff --cached --quiet >> "$LOG_FILE" 2>&1; then
    git commit -m "runtime-v2(module-b): record evidence commit sha" >> "$LOG_FILE" 2>&1
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
  summary "Evidence: reports/testing/latest_test_result.json; reports/execution/module_B_execution_report.md"
  return 0
}

mkdir -p "$WORKDIR"
summary "ORIS Runtime v2 Module B official bootstrap $VERSION starting..."

TEMP_LOG="/tmp/oris_module_B_bootstrap_$$.log"
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
LOG_FILE="$ORIS_DIR/reports/execution/module_B_bootstrap_latest.log"
{
  echo "# Module B bootstrap log"
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

DUPLICATE_BOOTSTRAPS="$(find scripts -maxdepth 1 -type f -name 'bootstrap_runtime_v2_module_b*.sh' ! -name 'bootstrap_runtime_v2_module_b.sh' -print 2>> "$LOG_FILE")"
if [ -n "$DUPLICATE_BOOTSTRAPS" ]; then
  echo "duplicate_module_b_bootstraps=$DUPLICATE_BOOTSTRAPS" >> "$LOG_FILE"
  fail_short "duplicate Module B bootstrap entrypoints found; keep one official entry only"
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
  echo "module_A_expected_final_sha=$MODULE_A_FINAL_SHA"
  echo "product_check_status=$PRODUCT_CHECK_STATUS"
  echo "product_head=$PRODUCT_HEAD"
  echo "product_module0_sha=$MODULE0_SHA"
  echo ""
  echo "# module A evidence check"
  if [ -f reports/testing/latest_test_result.json ]; then cat reports/testing/latest_test_result.json; else echo "missing reports/testing/latest_test_result.json"; fi
} >> "$LOG_FILE" 2>&1

mkdir -p docs/runtime_v2 schemas/runtime_v2 scripts/lib tests/runtime_v2 docs/testing reports/testing reports/execution

cat > docs/testing/MODULE_B_TEST_PLAN.md <<'EOF'
# Module B Test Plan - Persistent Run Store and Queue Contract

## Scope

Validate the minimal durable Runtime v2 substrate for run records, queue items, state transitions, and append-only events.

## Test Targets

1. Run records persist across store reloads.
2. Idempotent run creation returns the existing run for the same key.
3. Queue items persist and can be claimed exactly once.
4. State transitions follow the Module A state machine.
5. Terminal states reject further transitions.
6. Event records are append-only and survive reload.

## Acceptance

Module B passes only when tests pass and evidence is written to:

- `reports/testing/module_B_test_result.json`
- `reports/testing/latest_test_result.json`
- `reports/execution/module_B_execution_report.md`
EOF

cat > schemas/runtime_v2/run_record.schema.json <<'EOF'
{
  "version": "runtime_v2_module_B",
  "type": "object",
  "required": ["run_id", "objective", "module", "state", "created_at", "updated_at"],
  "properties": {
    "run_id": {"type": "string"},
    "objective": {"type": "string"},
    "module": {"type": "string"},
    "state": {"type": "string"},
    "idempotency_key": {"type": ["string", "null"]},
    "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
    "context_pack_ref": {"type": ["string", "null"]},
    "created_at": {"type": "string"},
    "updated_at": {"type": "string"}
  }
}
EOF

cat > schemas/runtime_v2/queue_item.schema.json <<'EOF'
{
  "version": "runtime_v2_module_B",
  "type": "object",
  "required": ["queue_id", "run_id", "status", "priority", "created_at", "updated_at"],
  "properties": {
    "queue_id": {"type": "string"},
    "run_id": {"type": "string"},
    "status": {"enum": ["QUEUED", "CLAIMED", "ACKED", "DEAD"]},
    "priority": {"type": "integer"},
    "worker_id": {"type": ["string", "null"]},
    "idempotency_key": {"type": ["string", "null"]},
    "created_at": {"type": "string"},
    "updated_at": {"type": "string"}
  }
}
EOF

cat > scripts/lib/runtime_v2_run_store.py <<'EOF'
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RunStoreError(Exception):
    pass


class InvalidTransitionError(RunStoreError):
    pass


class NotFoundError(RunStoreError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RuntimeV2RunStore:
    def __init__(self, path: Path | str, state_machine_path: Path | str = "schemas/runtime_v2/state_machine.schema.json") -> None:
        self.path = Path(path)
        self.state_machine_path = Path(state_machine_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._states, self._terminal_states, self._transitions = self._load_state_machine()
        if not self.path.exists():
            self._write({"runs": {}, "queue": {}, "events": []})

    def _load_state_machine(self) -> Tuple[set[str], set[str], set[tuple[str, str]]]:
        data = json.loads(self.state_machine_path.read_text(encoding="utf-8"))
        states = set(data["states"])
        terminal_states = set(data["terminal_states"])
        transitions = {tuple(item) for item in data["transitions"]}
        return states, terminal_states, transitions

    def _read(self) -> Dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        os.replace(tmp, self.path)

    def _append_event(self, data: Dict[str, Any], event_type: str, run_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None) -> None:
        data["events"].append({
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "run_id": run_id,
            "payload": payload or {},
            "created_at": utc_now(),
        })

    def create_run(self, objective: str, module: str, acceptance_criteria: Optional[List[str]] = None, context_pack_ref: Optional[str] = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if idempotency_key:
            for run in data["runs"].values():
                if run.get("idempotency_key") == idempotency_key:
                    return run
        run_id = str(uuid.uuid4())
        now = utc_now()
        run = {
            "run_id": run_id,
            "objective": objective,
            "module": module,
            "state": "RECEIVED",
            "idempotency_key": idempotency_key,
            "acceptance_criteria": acceptance_criteria or [],
            "context_pack_ref": context_pack_ref,
            "created_at": now,
            "updated_at": now,
        }
        data["runs"][run_id] = run
        self._append_event(data, "RUN_CREATED", run_id, {"module": module})
        self._write(data)
        return run

    def get_run(self, run_id: str) -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        return data["runs"][run_id]

    def transition_run(self, run_id: str, target_state: str, actor: str = "runtime", reason: str = "") -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        run = data["runs"][run_id]
        source_state = run["state"]
        if source_state in self._terminal_states:
            raise InvalidTransitionError(f"terminal run cannot transition: {source_state} -> {target_state}")
        if target_state not in self._states:
            raise InvalidTransitionError(f"unknown target state: {target_state}")
        if (source_state, target_state) not in self._transitions:
            raise InvalidTransitionError(f"invalid transition: {source_state} -> {target_state}")
        run["state"] = target_state
        run["updated_at"] = utc_now()
        self._append_event(data, "RUN_STATE_TRANSITIONED", run_id, {"from": source_state, "to": target_state, "actor": actor, "reason": reason})
        self._write(data)
        return run

    def enqueue(self, run_id: str, priority: int = 100, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
        data = self._read()
        if run_id not in data["runs"]:
            raise NotFoundError(f"run not found: {run_id}")
        if idempotency_key:
            for item in data["queue"].values():
                if item.get("idempotency_key") == idempotency_key:
                    return item
        queue_id = str(uuid.uuid4())
        now = utc_now()
        item = {
            "queue_id": queue_id,
            "run_id": run_id,
            "status": "QUEUED",
            "priority": int(priority),
            "worker_id": None,
            "idempotency_key": idempotency_key,
            "created_at": now,
            "updated_at": now,
        }
        data["queue"][queue_id] = item
        self._append_event(data, "QUEUE_ITEM_ENQUEUED", run_id, {"queue_id": queue_id, "priority": priority})
        self._write(data)
        return item

    def claim_next(self, worker_id: str) -> Optional[Dict[str, Any]]:
        data = self._read()
        queued = [item for item in data["queue"].values() if item["status"] == "QUEUED"]
        if not queued:
            return None
        queued.sort(key=lambda item: (item["priority"], item["created_at"]))
        item = queued[0]
        item["status"] = "CLAIMED"
        item["worker_id"] = worker_id
        item["updated_at"] = utc_now()
        self._append_event(data, "QUEUE_ITEM_CLAIMED", item["run_id"], {"queue_id": item["queue_id"], "worker_id": worker_id})
        self._write(data)
        return item

    def ack_queue_item(self, queue_id: str) -> Dict[str, Any]:
        data = self._read()
        if queue_id not in data["queue"]:
            raise NotFoundError(f"queue item not found: {queue_id}")
        item = data["queue"][queue_id]
        item["status"] = "ACKED"
        item["updated_at"] = utc_now()
        self._append_event(data, "QUEUE_ITEM_ACKED", item["run_id"], {"queue_id": queue_id})
        self._write(data)
        return item

    def list_events(self, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        data = self._read()
        events = data["events"]
        if run_id is not None:
            return [event for event in events if event.get("run_id") == run_id]
        return events
EOF

cat > tests/runtime_v2/test_run_store_queue.py <<'EOF'
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_run_store import InvalidTransitionError, RuntimeV2RunStore


class RuntimeV2RunStoreTests(unittest.TestCase):
    def make_store(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        path = Path(self.tmpdir.name) / "runtime_store.json"
        return RuntimeV2RunStore(path)

    def tearDown(self):
        tmpdir = getattr(self, "tmpdir", None)
        if tmpdir is not None:
            tmpdir.cleanup()

    def test_run_record_persists_across_reload(self):
        store = self.make_store()
        run = store.create_run("build module b", "Module B", ["tests pass"])
        reloaded = RuntimeV2RunStore(store.path)
        self.assertEqual(reloaded.get_run(run["run_id"])["objective"], "build module b")
        self.assertEqual(reloaded.get_run(run["run_id"])["state"], "RECEIVED")

    def test_create_run_is_idempotent(self):
        store = self.make_store()
        first = store.create_run("same", "Module B", idempotency_key="run-key")
        second = store.create_run("same", "Module B", idempotency_key="run-key")
        self.assertEqual(first["run_id"], second["run_id"])

    def test_queue_claim_is_exactly_once(self):
        store = self.make_store()
        run = store.create_run("queue", "Module B")
        store.enqueue(run["run_id"], priority=10, idempotency_key="queue-key")
        claimed = store.claim_next("worker-1")
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["status"], "CLAIMED")
        self.assertIsNone(store.claim_next("worker-2"))
        acked = store.ack_queue_item(claimed["queue_id"])
        self.assertEqual(acked["status"], "ACKED")

    def test_state_transition_validation(self):
        store = self.make_store()
        run = store.create_run("transition", "Module B")
        run = store.transition_run(run["run_id"], "PLANNED")
        run = store.transition_run(run["run_id"], "READY")
        self.assertEqual(run["state"], "READY")
        with self.assertRaises(InvalidTransitionError):
            store.transition_run(run["run_id"], "COMPLETED")

    def test_terminal_state_protection(self):
        store = self.make_store()
        run = store.create_run("terminal", "Module B")
        for state in ["PLANNED", "READY", "RUNNING", "TESTING", "COMMITTING", "COMPLETED"]:
            run = store.transition_run(run["run_id"], state)
        self.assertEqual(run["state"], "COMPLETED")
        with self.assertRaises(InvalidTransitionError):
            store.transition_run(run["run_id"], "CANCELLED")

    def test_event_log_is_append_only_and_persistent(self):
        store = self.make_store()
        run = store.create_run("events", "Module B")
        store.enqueue(run["run_id"])
        store.transition_run(run["run_id"], "PLANNED")
        before = store.list_events(run["run_id"])
        reloaded = RuntimeV2RunStore(store.path)
        after = reloaded.list_events(run["run_id"])
        self.assertEqual(len(before), len(after))
        self.assertGreaterEqual(len(after), 3)


if __name__ == "__main__":
    unittest.main()
EOF

cat > docs/runtime_v2/PERSISTENT_RUN_STORE_AND_QUEUE_CONTRACT_MODULE_B.md <<'EOF'
# Runtime v2 Module B - Persistent Run Store and Queue Contract

## Objective

Module B converts Module A's state-machine design into a minimal durable runtime substrate that can store runs, queue work, validate state transitions, and retain an append-only event trail.

## Runtime Store

The implementation is `scripts/lib/runtime_v2_run_store.py`.

The store persists a JSON document with three sections:

- `runs`: run records keyed by `run_id`;
- `queue`: queue items keyed by `queue_id`;
- `events`: append-only event records.

Writes are atomic at file level via temp-file write followed by replace.

## Run Record Contract

Run records are described in `schemas/runtime_v2/run_record.schema.json`.

A run starts in `RECEIVED` and may transition only through Module A's canonical state machine in `schemas/runtime_v2/state_machine.schema.json`.

## Queue Contract

Queue items are described in `schemas/runtime_v2/queue_item.schema.json`.

Queue statuses are:

- `QUEUED`
- `CLAIMED`
- `ACKED`
- `DEAD`

`claim_next(worker_id)` claims the highest-priority queued item exactly once.

## Idempotency

`create_run(..., idempotency_key=...)` returns the existing run for the same idempotency key.

`enqueue(..., idempotency_key=...)` returns the existing queue item for the same idempotency key.

## Recovery Semantics

A worker can recover state by loading the durable store file and reading:

- latest run state;
- queue item status;
- append-only event sequence.

## Non-Goals

- No production database yet.
- No distributed locking yet.
- No product repository mutation.
- No deployment workflow.
EOF

summary "Generated Module B files. Running stdlib tests quietly..."
TEST_COMMAND="$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p test_*.py -q"
$PYTHON_BIN -m unittest discover -s tests/runtime_v2 -p 'test_*.py' -q >> "$LOG_FILE" 2>&1
TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then TEST_STATUS="passed"; else TEST_STATUS="failed"; fi

export TEST_RC TEST_STATUS BASE_SHA PRODUCT_HEAD MODULE0_SHA PRODUCT_CHECK_STATUS TEST_COMMAND VERSION MODULE_A_FINAL_SHA LOG_FILE
"$PYTHON_BIN" - <<'PY' >> "$LOG_FILE" 2>&1
import json
import os
from datetime import datetime, timezone
from pathlib import Path

result = {
    "module": "Runtime v2 Module B",
    "bootstrap_version": os.environ.get("VERSION", ""),
    "status": os.environ.get("TEST_STATUS", "failed"),
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "test_command": os.environ.get("TEST_COMMAND", ""),
    "test_exit_code": int(os.environ.get("TEST_RC", "1")),
    "base_sha": os.environ.get("BASE_SHA", ""),
    "module_A_final_sha": os.environ.get("MODULE_A_FINAL_SHA", ""),
    "product_repo_check_status": os.environ.get("PRODUCT_CHECK_STATUS", ""),
    "product_repo_head": os.environ.get("PRODUCT_HEAD", ""),
    "product_repo_module0_sha": os.environ.get("MODULE0_SHA", ""),
    "old_interactive_insight_product_continued": False,
    "log_file": os.environ.get("LOG_FILE", ""),
    "checks": [
        "run_record_persists_across_reload",
        "create_run_is_idempotent",
        "queue_claim_is_exactly_once",
        "state_transition_validation",
        "terminal_state_protection",
        "event_log_is_append_only_and_persistent",
    ],
}
Path("reports/testing").mkdir(parents=True, exist_ok=True)
Path("reports/testing/module_B_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
Path("reports/testing/latest_test_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
PY

cat > reports/execution/module_B_execution_report.md <<EOF
# Runtime v2 Module B Execution Report

## Module

Persistent Run Store and Queue Contract

## Bootstrap Version

$VERSION

## Base Commit

$BASE_SHA

## Module A Baseline

$MODULE_A_FINAL_SHA

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

- \`docs/runtime_v2/PERSISTENT_RUN_STORE_AND_QUEUE_CONTRACT_MODULE_B.md\`
- \`schemas/runtime_v2/run_record.schema.json\`
- \`schemas/runtime_v2/queue_item.schema.json\`
- \`scripts/lib/runtime_v2_run_store.py\`
- \`tests/runtime_v2/test_run_store_queue.py\`
- \`docs/testing/MODULE_B_TEST_PLAN.md\`
- \`reports/testing/module_B_test_result.json\`
- \`reports/testing/latest_test_result.json\`
- \`reports/execution/module_B_bootstrap_latest.log\`

## Module B Evidence Commit SHA

Pending until evidence commit completes.
EOF

if [ "$COMMIT_AND_PUSH" != "1" ]; then
  summary "Tests $TEST_STATUS. Commit/push skipped by ORIS_MODULE_B_COMMIT_AND_PUSH=$COMMIT_AND_PUSH"
  summary "Log: $LOG_FILE"
  exit "$TEST_RC"
fi

if [ "$TEST_RC" -eq 0 ]; then
  commit_and_push_evidence "DONE: Runtime v2 Module B tests passed" "runtime-v2(module-b): add persistent run store and queue contract"
  exit $?
else
  commit_and_push_evidence "FAILED: Runtime v2 Module B tests failed" "runtime-v2(module-b): record failed bootstrap evidence"
  exit "$TEST_RC"
fi
