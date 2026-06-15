import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.dev_employee_chat_orchestrator as orchestrator
from scripts.dev_employee_chat_store import ChatSessionStore


class ChatOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env_patch = patch.dict(os.environ, {"ORIS_OPENCLAW_BIN": "/nonexistent/openclaw"})
        self.env_patch.start()
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = ChatSessionStore(root / "sessions", root / "locks")
        self.projects = {
            "demo": {
                "project_key": "demo",
                "name": "Demo Project",
                "type": "test_project",
                "product_path": str(root / "product"),
                "product_repo": "example/demo",
                "default_branch": "main",
                "allowed_scope": ["app/", "tests/"],
                "forbidden_scope": [".env", "secrets"],
                "notes": "Demo project",
            }
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()
        self.env_patch.stop()

    def test_natural_language_goal_creates_task_and_card(self) -> None:
        session = self.store.create()
        calls = []

        def fake_intake(method, path, body=None):
            calls.append((method, path, body))
            if method == "POST" and path == "/goals":
                return 201, {"task_id": body["task_id"], "status": "queued"}
            if method == "GET" and path.startswith("/goals/"):
                task_id = path.removeprefix("/goals/")
                return 200, {
                    "task_id": task_id,
                    "status": "queued",
                    "canonical_status": "queued",
                    "terminal": False,
                    "catalog": {"project_key": "demo", "attempt": 1, "max_attempts": 3},
                }
            raise AssertionError((method, path, body))

        with (
            patch.object(orchestrator, "allowed_projects", return_value=self.projects),
            patch.object(orchestrator, "intake", side_effect=fake_intake),
        ):
            updated = orchestrator.process_message(
                session["session_id"],
                "给 Demo Project 增加一个 /healthz 接口并完成测试",
                store=self.store,
            )

        self.assertTrue(updated["current_task_id"].startswith("chat-demo-"))
        self.assertEqual(updated["selected_project"], "demo")
        self.assertEqual(updated["task_lineage"], [updated["current_task_id"]])
        self.assertTrue(any(message.get("type") == "task_card" for message in updated["messages"]))
        post = next(item for item in calls if item[0] == "POST")
        self.assertEqual(post[2]["project_key"], "demo")
        self.assertIn("/healthz", post[2]["objective"])

    def test_status_message_reads_current_task_without_new_submission(self) -> None:
        session = self.store.create()
        session["current_task_id"] = "goal-demo-running"
        session["selected_project"] = "demo"
        self.store.save(session)
        calls = []

        def fake_intake(method, path, body=None):
            calls.append((method, path))
            return 200, {
                "task_id": "goal-demo-running",
                "status": "codex_running",
                "canonical_status": "executing",
                "terminal": False,
                "catalog": {"project_key": "demo"},
            }

        with (
            patch.object(orchestrator, "allowed_projects", return_value=self.projects),
            patch.object(orchestrator, "intake", side_effect=fake_intake),
        ):
            updated = orchestrator.process_message(
                session["session_id"],
                "查看进度",
                store=self.store,
            )

        self.assertFalse(any(method == "POST" for method, _ in calls))
        self.assertIn("正在开发", "\n".join(message["content"] for message in updated["messages"]))

    def test_risky_goal_creates_confirmation_not_task(self) -> None:
        session = self.store.create()
        with (
            patch.object(orchestrator, "allowed_projects", return_value=self.projects),
            patch.object(orchestrator, "intake") as intake_mock,
        ):
            updated = orchestrator.process_message(
                session["session_id"],
                "把 Demo Project 直接部署到生产环境并更新 token",
                store=self.store,
            )

        self.assertIsNotNone(updated["pending_confirmation"])
        self.assertFalse(intake_mock.called)
        self.assertEqual(updated["messages"][-1]["type"], "confirmation_request")


if __name__ == "__main__":
    unittest.main(verbosity=2)
