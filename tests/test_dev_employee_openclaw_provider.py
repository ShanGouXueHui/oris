import unittest

from scripts.dev_employee_openclaw_provider import DeterministicFallbackProvider


class OpenClawProviderFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = DeterministicFallbackProvider()
        self.projects = {
            "demo": {
                "name": "Demo Project",
                "type": "test_project",
                "forbidden_scope": [".env", "secrets"],
            }
        }
        self.session = {
            "session_id": "chat-test",
            "selected_project": None,
            "current_task_id": None,
            "messages": [],
        }

    def test_single_project_goal_becomes_create_task(self) -> None:
        result = self.provider.analyze(
            session=self.session,
            user_message="给 Demo Project 增加一个 /healthz 接口并完成测试",
            projects=self.projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "create_task")
        self.assertEqual(result.project_key, "demo")
        self.assertIn("/healthz", result.objective)
        self.assertTrue(result.constraints)

    def test_status_cancel_retry_are_deterministic(self) -> None:
        session = {**self.session, "current_task_id": "goal-demo"}
        expectations = {
            "查看进度": "status",
            "停止任务": "cancel",
            "重试": "retry",
        }
        for message, intent in expectations.items():
            with self.subTest(message=message):
                result = self.provider.analyze(
                    session=session,
                    user_message=message,
                    projects=self.projects,
                    current_task={"task_id": "goal-demo"},
                )
                self.assertEqual(result.intent, intent)

    def test_risky_request_requires_confirmation(self) -> None:
        result = self.provider.analyze(
            session=self.session,
            user_message="把 Demo Project 直接部署到生产环境并使用新的 token",
            projects=self.projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "clarify")
        self.assertTrue(result.requires_confirmation)
        self.assertIsNotNone(result.confirmation_reason)

    def test_multiple_projects_without_match_asks_for_clarification(self) -> None:
        projects = {**self.projects, "another": {"name": "Another Project"}}
        result = self.provider.analyze(
            session=self.session,
            user_message="增加一个新的健康检查接口并测试",
            projects=projects,
            current_task=None,
        )
        self.assertEqual(result.intent, "clarify")
        self.assertIn("哪个项目", result.assistant_message)


if __name__ == "__main__":
    unittest.main(verbosity=2)
