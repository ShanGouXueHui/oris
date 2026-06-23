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
