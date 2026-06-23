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
