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
