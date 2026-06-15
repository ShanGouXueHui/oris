import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from scripts.dev_employee_queue_kernel import (
    QueueKernel,
    generate_retry_task_id,
    now,
    request_fingerprint,
)


class QueueKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.kernel = QueueKernel(
            queue_dir=root / "queue",
            event_dir=root / "events",
            control_dir=root / "controls",
            lock_dir=root / "locks",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_queued(self, task_id: str) -> Path:
        path = self.kernel.task_path(task_id, "queued")
        path.write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "status": "queued",
                    "attempt": 1,
                    "max_attempts": 3,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_claim_is_exactly_once_and_creates_lease(self) -> None:
        queued = self.write_queued("task-claim")
        first = self.kernel.claim(
            queued,
            worker_id="worker-a",
            lease_seconds=30,
            execution_timeout_seconds=300,
        )
        second = self.kernel.claim(
            queued,
            worker_id="worker-b",
            lease_seconds=30,
            execution_timeout_seconds=300,
        )

        self.assertIsNotNone(first)
        self.assertIsNone(second)
        running = json.loads(first.path.read_text(encoding="utf-8"))
        self.assertEqual(running["status"], "running")
        self.assertEqual(running["phase"], "claimed")
        self.assertEqual(running["worker_id"], "worker-a")
        self.assertTrue(running["lease_token"])
        self.assertTrue(self.kernel.lock_path("task-claim").is_file())

    def test_heartbeat_updates_phase_and_observes_cancel(self) -> None:
        claimed = self.kernel.claim(self.write_queued("task-heartbeat"), worker_id="worker-a")
        self.assertIsNotNone(claimed)

        cancel = self.kernel.request_cancel(
            "task-heartbeat",
            requested_by="operator",
            reason="test cancellation",
        )
        heartbeat = self.kernel.heartbeat(
            "task-heartbeat",
            claimed.lease_token,
            phase="executing",
        )

        self.assertEqual(cancel["status"], "cancel_requested")
        self.assertTrue(heartbeat["cancel_requested"])
        self.assertEqual(heartbeat["task"]["phase"], "executing")

    def test_cancel_queued_is_terminal_and_idempotent(self) -> None:
        self.write_queued("task-cancel")
        first = self.kernel.request_cancel(
            "task-cancel",
            requested_by="operator",
            reason="no longer needed",
        )
        second = self.kernel.request_cancel(
            "task-cancel",
            requested_by="operator",
            reason="no longer needed",
        )

        self.assertEqual(first["status"], "cancelled")
        self.assertTrue(first["terminal"])
        self.assertEqual(second["status"], "cancelled")
        self.assertTrue(second["idempotent"])
        self.assertTrue(self.kernel.task_path("task-cancel", "cancelled").is_file())
        self.assertFalse(self.kernel.task_path("task-cancel", "queued").exists())

    def test_expired_lease_fails_instead_of_automatic_requeue(self) -> None:
        claimed = self.kernel.claim(
            self.write_queued("task-expire"),
            worker_id="other-host:999999:dead",
            lease_seconds=15,
        )
        self.assertIsNotNone(claimed)
        running = json.loads(claimed.path.read_text(encoding="utf-8"))
        running["lease_expires_at"] = (now() - timedelta(seconds=5)).isoformat(timespec="seconds")
        claimed.path.write_text(json.dumps(running), encoding="utf-8")

        summary = self.kernel.expire_stale(fallback_max_age_minutes=1)

        self.assertEqual(len(summary["expired"]), 1)
        failed_path = self.kernel.task_path("task-expire", "failed")
        failed = json.loads(failed_path.read_text(encoding="utf-8"))
        self.assertEqual(failed["failure_code"], "lease_expired")
        self.assertTrue(failed["terminal"])
        self.assertFalse(self.kernel.task_path("task-expire", "queued").exists())

    def test_event_ledger_is_append_only_jsonl(self) -> None:
        self.kernel.append_event("task-events", "accepted", status="accepted")
        self.kernel.append_event("task-events", "validated", status="validated")
        lines = self.kernel.event_path("task-events").read_text(encoding="utf-8").splitlines()
        events = [json.loads(line) for line in lines]
        self.assertEqual([event["event_type"] for event in events], ["accepted", "validated"])
        self.assertNotEqual(events[0]["event_id"], events[1]["event_id"])

    def test_request_fingerprint_is_stable_and_material(self) -> None:
        first = {
            "project_key": "project-a",
            "objective": "  Build the feature  ",
            "constraints": [" minimal ", "tested"],
            "expected_checks": ["pytest -q"],
            "commit_message": "feat: add feature",
        }
        equivalent = {
            "commit_message": "feat: add feature",
            "expected_checks": ["pytest -q"],
            "constraints": ["minimal", "tested"],
            "objective": "Build the feature",
            "project_key": "project-a",
        }
        changed = {**equivalent, "objective": "Build another feature"}

        self.assertEqual(request_fingerprint(first), request_fingerprint(equivalent))
        self.assertNotEqual(request_fingerprint(first), request_fingerprint(changed))

    def test_retry_id_is_new_and_monotonic(self) -> None:
        task_id = generate_retry_task_id("goal-demo", {"goal-demo", "goal-demo-r1", "goal-demo-r2"})
        self.assertEqual(task_id, "goal-demo-r3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
