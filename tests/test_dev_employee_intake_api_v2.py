import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.dev_employee_intake_api_v2 as intake
from scripts.dev_employee_queue_kernel import QueueKernel


class IntakeApiV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.catalog_dir = root / "catalog"
        self.queue_dir = root / "queue"
        self.prompt_dir = root / "prompts"
        self.catalog_dir.mkdir()
        self.queue_dir.mkdir()
        self.prompt_dir.mkdir()
        self.kernel = QueueKernel(
            queue_dir=self.queue_dir,
            event_dir=root / "events",
            control_dir=root / "controls",
            lock_dir=root / "locks",
        )
        self.patchers = [
            patch.object(intake, "CATALOG_DIR", self.catalog_dir),
            patch.object(intake, "QUEUE_DIR", self.queue_dir),
            patch.object(intake, "DEFAULT_KERNEL", self.kernel),
            patch.object(
                intake.v1,
                "resolve_project",
                return_value={
                    "project_key": "demo",
                    "name": "Demo",
                    "type": "product",
                    "product_path": str(root / "product"),
                    "product_repo": "example/demo",
                    "default_branch": "main",
                    "allowed_scope": [],
                    "forbidden_scope": [],
                },
            ),
        ]
        for item in self.patchers:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patchers):
            item.stop()
        self.tmp.cleanup()

    def base_payload(self) -> dict:
        return {
            "task_id": "goal-demo-001",
            "project_key": "demo",
            "objective": "Add a deterministic demo endpoint with exact response coverage.",
            "constraints": ["Keep the change minimal."],
            "expected_checks": ["pytest -q"],
            "commit_message": "feat(api): add demo endpoint",
        }

    def fake_prompt(self, task_id, objective, constraints, checks, project):
        path = self.prompt_dir / f"{task_id}.md"
        path.write_text(objective, encoding="utf-8")
        return path

    def fake_enqueue(self, payload):
        path = self.queue_dir / f"{payload['task_id']}.queued.json"
        descriptor = {
            "task_id": payload["task_id"],
            "status": "queued",
            "prompt_path": payload["prompt_path"],
            "product_path": payload["product_path"],
        }
        path.write_text(json.dumps(descriptor), encoding="utf-8")
        return 201, {"task_id": payload["task_id"], "status": "queued", "path": str(path)}

    def fake_annotation(self, response, objective, constraints, checks):
        return {"annotated": True, "path": response["path"]}

    def test_same_task_and_request_is_idempotent_but_conflict_is_rejected(self) -> None:
        with (
            patch.object(intake.v1, "write_runtime_prompt", side_effect=self.fake_prompt),
            patch.object(intake.v1, "post_enqueue", side_effect=self.fake_enqueue) as enqueue,
            patch.object(intake.v1, "annotate_descriptor", side_effect=self.fake_annotation),
            patch.object(intake, "task_status", return_value={"status": "queued", "terminal": False}),
        ):
            first = intake.create_goal(self.base_payload())
            replay = intake.create_goal(self.base_payload())
            changed = {**self.base_payload(), "objective": "Add a different deterministic endpoint with exact response coverage."}
            with self.assertRaises(intake.IntakeConflict):
                intake.create_goal(changed)

        self.assertEqual(first["status"], "queued")
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(enqueue.call_count, 1)
        catalog = json.loads((self.catalog_dir / "goal-demo-001.json").read_text(encoding="utf-8"))
        self.assertTrue(catalog["request_fingerprint"])
        descriptor = json.loads((self.queue_dir / "goal-demo-001.queued.json").read_text(encoding="utf-8"))
        self.assertEqual(descriptor["attempt"], 1)
        self.assertEqual(descriptor["max_attempts"], 3)

    def test_cancel_goal_moves_queued_task_to_cancelled(self) -> None:
        catalog = {
            "task_id": "goal-demo-cancel",
            "status": "queued",
            "project_key": "demo",
        }
        (self.catalog_dir / "goal-demo-cancel.json").write_text(json.dumps(catalog), encoding="utf-8")
        (self.queue_dir / "goal-demo-cancel.queued.json").write_text(
            json.dumps({"task_id": "goal-demo-cancel", "status": "queued"}),
            encoding="utf-8",
        )
        with patch.object(
            intake,
            "task_status",
            side_effect=[
                {"status": "queued", "terminal": False, "lifecycle": {"lease": None}},
                {"status": "cancelled", "canonical_status": "cancelled", "terminal": True},
            ],
        ):
            result = intake.cancel_goal("goal-demo-cancel", {"reason": "operator test"})

        self.assertEqual(result["status"], "cancelled")
        self.assertTrue((self.queue_dir / "goal-demo-cancel.cancelled.json").is_file())
        self.assertFalse((self.queue_dir / "goal-demo-cancel.queued.json").exists())

    def test_retry_reuses_active_retry_instead_of_duplicate_submission(self) -> None:
        original = {
            "task_id": "goal-demo-failed",
            "status": "failed",
            "project_key": "demo",
            "objective": "Add a deterministic demo endpoint with exact response coverage.",
            "constraints": [],
            "expected_checks": ["pytest -q"],
            "commit_message": "feat(api): add demo endpoint",
            "attempt": 1,
            "max_attempts": 3,
            "latest_retry_task_id": "goal-demo-failed-r1",
            "retries": [{"task_id": "goal-demo-failed-r1", "attempt": 2}],
        }
        active_retry = {
            "task_id": "goal-demo-failed-r1",
            "status": "queued",
            "project_key": "demo",
            "objective": original["objective"],
        }
        (self.catalog_dir / "goal-demo-failed.json").write_text(json.dumps(original), encoding="utf-8")
        (self.catalog_dir / "goal-demo-failed-r1.json").write_text(json.dumps(active_retry), encoding="utf-8")

        def status(task_id):
            if task_id == "goal-demo-failed":
                return {"status": "failed", "canonical_status": "failed", "terminal": True}
            return {"status": "queued", "canonical_status": "queued", "terminal": False}

        with patch.object(intake, "task_status", side_effect=status):
            result = intake.retry_goal("goal-demo-failed", {})

        self.assertTrue(result["idempotent_replay"])
        self.assertEqual(result["task_id"], "goal-demo-failed-r1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
