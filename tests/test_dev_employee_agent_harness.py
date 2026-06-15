import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.dev_employee_agent_harness as harness_module
from scripts.dev_employee_agent_harness import AgentHarness
from scripts.dev_employee_openclaw_provider import ProviderResult, ProviderUnavailable


class AgentHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projects = {
            "demo": {
                "name": "Demo Project",
                "type": "test_project",
                "forbidden_scope": ["private-config"],
            }
        }
        self.session = {
            "session_id": "chat-harness-test",
            "selected_project": None,
            "current_task_id": None,
            "messages": [],
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.trace_patch = patch.object(harness_module, "TRACE_DIR", Path(self.tmp.name) / "traces")
        self.trace_patch.start()

    def tearDown(self) -> None:
        self.trace_patch.stop()
        self.tmp.cleanup()

    def test_explicit_control_is_deterministic(self) -> None:
        harness = AgentHarness("auto")
        session = {**self.session, "current_task_id": "goal-demo"}
        with patch.object(harness_module, "configured_provider", side_effect=AssertionError("provider must not run")):
            outcome = harness.analyze(
                session=session,
                user_message="停止任务",
                projects=self.projects,
                current_task={"task_id": "goal-demo"},
            )
        self.assertEqual(outcome.result.intent, "cancel")
        self.assertEqual(outcome.selected_provider, "deterministic_fallback")
        self.assertFalse(outcome.fallback_used)

    def test_openclaw_result_is_policy_validated(self) -> None:
        fake_provider = type(
            "Provider",
            (),
            {
                "analyze": lambda self, **kwargs: ProviderResult(
                    intent="create_task",
                    assistant_message="已理解。",
                    project_key="demo",
                    objective="为 Demo Project 增加 /healthz 接口并测试",
                    constraints=["Keep it small."],
                    provider="openclaw_infer_gateway",
                )
            },
        )()
        harness = AgentHarness("openclaw")
        with patch.object(harness_module, "configured_provider", return_value=fake_provider):
            outcome = harness.analyze(
                session=self.session,
                user_message="为 Demo Project 增加 /healthz 接口并测试",
                projects=self.projects,
                current_task=None,
            )
        self.assertEqual(outcome.selected_provider, "openclaw_infer_gateway")
        self.assertFalse(outcome.fallback_used)
        self.assertTrue(outcome.result.raw_metadata["agent_harness"])
        self.assertTrue(any("selected standalone project" in item for item in outcome.result.constraints))

    def test_provider_failure_falls_back_and_is_visible(self) -> None:
        class FailingProvider:
            def analyze(self, **kwargs):
                raise ProviderUnavailable("down")

        harness = AgentHarness("auto")
        with patch.object(harness_module, "configured_provider", return_value=FailingProvider()):
            outcome = harness.analyze(
                session=self.session,
                user_message="给 Demo Project 增加一个健康检查接口并完成测试",
                projects=self.projects,
                current_task=None,
            )
        self.assertTrue(outcome.fallback_used)
        self.assertEqual(outcome.selected_provider, "deterministic_fallback")
        self.assertTrue(outcome.result.raw_metadata["harness_fallback"])

    def test_trace_contains_metadata_but_not_raw_message(self) -> None:
        harness = AgentHarness("deterministic")
        harness.analyze(
            session=self.session,
            user_message="给 Demo Project 增加一个健康检查接口并完成测试",
            projects=self.projects,
            current_task=None,
        )
        files = list((Path(self.tmp.name) / "traces").glob("*.jsonl"))
        self.assertEqual(len(files), 1)
        content = files[0].read_text(encoding="utf-8")
        self.assertIn("harness_decision", content)
        self.assertIn("message_length", content)
        self.assertNotIn("健康检查", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)
