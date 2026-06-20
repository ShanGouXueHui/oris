from __future__ import annotations

from collections.abc import Callable

from . import selftest_policy as policy_checks
from . import selftest_telemetry as telemetry_checks
from .effective_tool_surface_selftest import test_effective_tool_surface_parser


class AutomaticSelftestFailure(RuntimeError):
    def __init__(self, check_name: str) -> None:
        super().__init__(check_name)
        self.check_name = check_name


def _run(check_name: str, check: Callable[[], None]) -> None:
    try:
        check()
    except Exception as exc:
        raise AutomaticSelftestFailure(check_name) from exc


def run_selftests() -> bool:
    checks: tuple[tuple[str, Callable[[], None]], ...] = (
        ("telemetry_correlation", telemetry_checks.test_telemetry_correlation),
        ("output_metadata", telemetry_checks.test_output_metadata),
        ("agent_skill_policy", policy_checks.test_agent_skill_policy),
        ("profile_tool_policy", policy_checks.test_profile_tool_policy),
        ("effective_tool_surface_parser", test_effective_tool_surface_parser),
    )
    for check_name, check in checks:
        _run(check_name, check)
    return True
