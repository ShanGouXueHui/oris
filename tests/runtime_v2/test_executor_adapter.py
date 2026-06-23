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
