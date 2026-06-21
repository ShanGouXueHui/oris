#!/usr/bin/env python3
"""Compatibility entrypoint for the local-only ORIS Dev Employee intake API."""

from __future__ import annotations

from dev_employee_runtime.intake_config import (
    CATALOG_DIR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    QUEUE_DIR,
    TASK_ID_RE,
    auth_ok,
    default_task_id,
    json_response,
    registry,
    resolve_project,
    sanitize_list,
)
from dev_employee_runtime.intake_goal import annotate_descriptor, create_goal, post_enqueue, write_runtime_prompt
from dev_employee_runtime.intake_server import Handler, main
from dev_employee_runtime.intake_status import evidence_summary, list_goals, task_status

__all__ = [
    "CATALOG_DIR",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "Handler",
    "QUEUE_DIR",
    "TASK_ID_RE",
    "annotate_descriptor",
    "auth_ok",
    "create_goal",
    "default_task_id",
    "evidence_summary",
    "json_response",
    "list_goals",
    "main",
    "post_enqueue",
    "registry",
    "resolve_project",
    "sanitize_list",
    "task_status",
    "write_runtime_prompt",
]


if __name__ == "__main__":
    raise SystemExit(main())
