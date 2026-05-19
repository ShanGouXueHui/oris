#!/usr/bin/env python3
"""Export latest Dev Employee task status artifact.

This script reads latest_task_binding and writes a GitHub-visible status file.
It does not execute Codex and does not perform git operations.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def main() -> int:
    config = load_json("config/dev_employee_task_status.json")
    binding = load_json("logs/dev_employee/latest_task_binding.json")
    requested_state = os.getenv("ORIS_DEV_TASK_STATE", "reviewed")
    allowed_states = set(config.get("allowed_states", []))
    if requested_state not in allowed_states:
        raise SystemExit(f"invalid ORIS_DEV_TASK_STATE={requested_state}")

    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "task_run_id": binding.get("task_run_id"),
        "state": requested_state,
        "previous_state": "planned",
        "request_summary": binding.get("request_summary"),
        "objective": binding.get("objective"),
        "execution_mode": binding.get("execution_mode"),
        "approved_for_real_execution": binding.get("approved_for_real_execution"),
        "source_files": {
            "task_binding": "logs/dev_employee/latest_task_binding.json",
            "task_status_config": "config/dev_employee_task_status.json"
        },
        "policy": config.get("policy", {})
    }

    json_out = Path(config.get("latest_status_json", "logs/dev_employee/latest_task_status.json"))
    md_out = Path(config.get("latest_status_md", "logs/dev_employee/latest_task_status.md"))
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(
        "# Dev Employee Latest Task Status\n\n"
        f"- ok: `{payload['ok']}`\n"
        f"- generated_at: `{payload['generated_at']}`\n"
        f"- task_run_id: `{payload['task_run_id']}`\n"
        f"- previous_state: `{payload['previous_state']}`\n"
        f"- state: `{payload['state']}`\n"
        f"- execution_mode: `{payload['execution_mode']}`\n"
        f"- approved_for_real_execution: `{payload['approved_for_real_execution']}`\n"
        f"- request_summary: {payload['request_summary']}\n"
        f"- objective: {payload['objective']}\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "state": requested_state, "json_out": str(json_out), "md_out": str(md_out)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
