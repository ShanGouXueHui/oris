#!/usr/bin/env python3
"""Validate ORIS Dev Employee Codex result JSON files.

This validator intentionally avoids external dependencies. It enforces the
minimum autonomous result contract used by the supervised bridge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = [
    "task_id",
    "status",
    "product_path",
    "plan",
    "skill_resolution",
    "changed_files",
    "check_logs",
    "iteration_summary",
    "notes",
]

ALLOWED_STATUS = {"local_checks_passed", "blocked", "local_checks_failed"}

SKILL_REQUIRED_FIELDS = ["needed", "used_existing", "downloaded_quarantine", "blocked"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_result(data: dict[str, Any], expected_task_id: str | None = None, strict: bool = True) -> list[str]:
    errors: list[str] = []

    if expected_task_id and data.get("task_id") != expected_task_id:
        errors.append(f"task_id mismatch: expected {expected_task_id!r}, got {data.get('task_id')!r}")

    status = data.get("status")
    if status not in ALLOWED_STATUS:
        errors.append(f"invalid status: {status!r}")

    if not strict:
        return errors

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: {field}")

    if "plan" in data and not isinstance(data["plan"], list):
        errors.append("plan must be a list")
    if "changed_files" in data and not isinstance(data["changed_files"], list):
        errors.append("changed_files must be a list")
    if "check_logs" in data and not isinstance(data["check_logs"], dict):
        errors.append("check_logs must be an object")
    if "iteration_summary" in data and not isinstance(data["iteration_summary"], list):
        errors.append("iteration_summary must be a list")

    skill_resolution = data.get("skill_resolution")
    if not isinstance(skill_resolution, dict):
        errors.append("skill_resolution must be an object")
    else:
        for field in SKILL_REQUIRED_FIELDS:
            if field not in skill_resolution:
                errors.append(f"skill_resolution missing required field: {field}")
            elif not isinstance(skill_resolution[field], list):
                errors.append(f"skill_resolution.{field} must be a list")

    if status == "blocked" and not data.get("blockers"):
        errors.append("blocked result must include non-empty blockers")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ORIS Dev Employee result JSON")
    parser.add_argument("path")
    parser.add_argument("--task-id")
    parser.add_argument("--non-strict", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    data = load_json(path)
    errors = validate_result(data, expected_task_id=args.task_id, strict=not args.non_strict)
    output = {"ok": not errors, "path": str(path), "errors": errors}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
