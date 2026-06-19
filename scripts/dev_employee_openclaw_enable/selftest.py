from __future__ import annotations

from . import selftest_policy as policy_checks
from . import selftest_telemetry as telemetry_checks


def run_selftests() -> bool:
    telemetry_checks.test_telemetry_correlation()
    telemetry_checks.test_output_metadata()
    policy_checks.test_agent_skill_policy()
    policy_checks.test_profile_tool_policy()
    return True
