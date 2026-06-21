#!/usr/bin/env python3
"""Compatibility entrypoint for the local-only ORIS Dev Employee intake API."""

from __future__ import annotations

from dev_employee_runtime.intake_config import json_response, resolve_project
from dev_employee_runtime.intake_goal import create_goal
from dev_employee_runtime.intake_server import Handler, main
from dev_employee_runtime.intake_status import evidence_summary, list_goals, task_status

__all__ = [
    "Handler",
    "create_goal",
    "evidence_summary",
    "json_response",
    "list_goals",
    "main",
    "resolve_project",
    "task_status",
]


if __name__ == "__main__":
    raise SystemExit(main())
