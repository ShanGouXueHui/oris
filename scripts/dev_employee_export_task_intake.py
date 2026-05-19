#!/usr/bin/env python3
"""Export a latest pilot task intake record for Dev Employee.

The exporter creates a normalized DevTask/task_run record from a pilot request.
It does not execute Codex and does not perform git operations.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.task_intake import (
    build_task_intake_record,
    load_config,
    normalize_task_input,
    write_intake_record,
)


def main() -> int:
    summary = os.getenv("ORIS_DEV_TASK_SUMMARY", "Pilot task intake export")
    objective = os.getenv(
        "ORIS_DEV_TASK_OBJECTIVE",
        "Create a normalized pilot DevTask and task_run for controlled planning only.",
    )
    config = load_config("config/dev_employee_task_intake.json")
    task = normalize_task_input(
        request_summary=summary,
        objective=objective,
        config=config,
        metadata={"exporter": "dev_employee_export_task_intake"},
    )
    record = build_task_intake_record(task=task, persist_task_run=True)
    json_out = Path("logs/dev_employee/latest_task_intake.json")
    md_out = Path("logs/dev_employee/latest_task_intake.md")
    write_intake_record(json_out, record)
    payload = record.to_dict()
    md_out.write_text(
        "# Dev Employee Latest Task Intake\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- created_at: `{payload['created_at']}`\n"
        f"- task_run_id: `{payload['task_run_id']}`\n"
        f"- repo: `{payload['repo']}`\n"
        f"- task_type: `{payload['task_type']}`\n"
        f"- source: `{payload['source']}`\n"
        f"- request_summary: {payload['request_summary']}\n"
        f"- objective: {payload['objective']}\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "task_run_id": record.task_run_id,
                "json_out": str(json_out),
                "md_out": str(md_out),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
