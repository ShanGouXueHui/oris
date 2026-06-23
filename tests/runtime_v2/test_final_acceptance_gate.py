import json
import unittest
from pathlib import Path


class RuntimeV2FinalAcceptanceGateTests(unittest.TestCase):
    def test_module_a_to_g_execution_reports_exist(self):
        for module in "ABCDEFG":
            self.assertTrue(Path(f"reports/execution/module_{module}_execution_report.md").exists(), module)

    def test_runtime_core_files_exist(self):
        expected = [
            "scripts/lib/runtime_v2_run_store.py",
            "scripts/lib/runtime_v2_worker.py",
            "scripts/lib/runtime_v2_executor.py",
            "scripts/lib/runtime_v2_evidence_publisher.py",
            "scripts/lib/runtime_v2_approval_gate.py",
            "scripts/lib/runtime_v2_acceptance_harness.py",
        ]
        for path in expected:
            self.assertTrue(Path(path).exists(), path)

    def test_module_g_latest_result_was_passed_before_final_gate(self):
        data = json.loads(Path("reports/testing/latest_test_result.json").read_text(encoding="utf-8"))
        self.assertEqual(data.get("module"), "Runtime v2 Module G")
        self.assertEqual(data.get("status"), "passed")
        self.assertEqual(data.get("test_exit_code"), 0)

    def test_no_product_repo_mutation_declared(self):
        data = json.loads(Path("reports/testing/latest_test_result.json").read_text(encoding="utf-8"))
        self.assertFalse(data.get("old_interactive_insight_product_continued"))


if __name__ == "__main__":
    unittest.main()
