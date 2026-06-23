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
