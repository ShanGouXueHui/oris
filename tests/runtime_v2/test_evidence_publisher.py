import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path("scripts/lib").resolve()))

from runtime_v2_evidence_publisher import MissingEvidenceError, RuntimeV2EvidencePublisher
from runtime_v2_executor import RuntimeV2Executor
from runtime_v2_run_store import RuntimeV2RunStore
from runtime_v2_worker import RuntimeV2Worker


class RuntimeV2EvidencePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "reports/testing").mkdir(parents=True)
        (self.root / "reports/testing/a.json").write_text('{"status":"passed"}', encoding="utf-8")
        (self.root / "reports/execution").mkdir(parents=True)
        (self.root / "reports/execution/a.md").write_text('# ok', encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_artifact_hash_capture(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        index = publisher.build_index("Module E", "passed", ["reports/testing/a.json", "reports/execution/a.md"])
        self.assertEqual(index["module"], "Module E")
        self.assertEqual(len(index["artifacts"]), 2)
        self.assertTrue(all(len(item["sha256"]) == 64 for item in index["artifacts"]))

    def test_missing_artifact_protection(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        with self.assertRaises(MissingEvidenceError):
            publisher.build_index("Module E", "failed", ["missing.txt"])

    def test_deterministic_index_id(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        first = publisher.build_index("Module E", "passed", ["reports/testing/a.json", "reports/execution/a.md"])
        second = publisher.build_index("Module E", "passed", ["reports/execution/a.md", "reports/testing/a.json"])
        self.assertEqual(first["index_id"], second["index_id"])

    def test_publish_plan_generation(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        plan = publisher.create_publish_plan("main", "runtime-v2(module-e): evidence", ["b", "a"], "reports/evidence/index.json", issue_number=15)
        self.assertEqual(plan["branch"], "main")
        self.assertEqual(plan["files"], ["a", "b"])
        self.assertEqual(plan["issue_update"]["issue_number"], 15)

    def test_issue_payload_generation(self):
        publisher = RuntimeV2EvidencePublisher(self.root)
        payload = publisher.create_issue_update_payload(15, "Module E passed", "reports/evidence/index.json")
        self.assertIn("Module E passed", payload["body"])
        self.assertIn("reports/evidence/index.json", payload["body"])

    def test_executor_worker_evidence_aggregation(self):
        evidence_dir = self.root / "executor_evidence"
        executor = RuntimeV2Executor(evidence_dir)
        store = RuntimeV2RunStore(self.root / "runtime_store.json")
        worker = RuntimeV2Worker(store, "worker-e")
        run = store.create_run("module e aggregation", "Module E")
        store.enqueue(run["run_id"])
        worker.run_once(executor.as_worker_executor({"action_type": "write_evidence", "payload": {"note": "ok"}, "risk_level": "LOW"}))
        artifact_paths = [str(path.relative_to(self.root)) for path in evidence_dir.glob("*.json")]
        self.assertEqual(len(artifact_paths), 1)
        publisher = RuntimeV2EvidencePublisher(self.root)
        index = publisher.build_index("Module E", "passed", artifact_paths)
        self.assertEqual(len(index["artifacts"]), 1)


if __name__ == "__main__":
    unittest.main()
