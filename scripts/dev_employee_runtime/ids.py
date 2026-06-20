from __future__ import annotations

import re


TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$")
PROJECT_KEY_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{1,80}$")


def require_task_id(value: object) -> str:
    task_id = str(value or "").strip()
    if not TASK_ID_RE.fullmatch(task_id):
        raise ValueError("invalid task_id")
    return task_id


def require_project_key(value: object) -> str:
    project_key = str(value or "").strip()
    if not PROJECT_KEY_RE.fullmatch(project_key):
        raise ValueError("invalid project_key")
    return project_key
