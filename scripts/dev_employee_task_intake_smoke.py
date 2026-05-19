#!/usr/bin/env python3
"""Smoke test for Dev Employee pilot task intake."""

from __future__ import annotations

import json
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
    config = load_config("config/dev_employee_task_intake.json")
    task = normalize_task_input(
        request_summary="Pilot task intake smoke",
        objective="Validate that a pilot task can be normalized into DevTask and task_run.",
        config=config,
        metadata={"smoke": True},
    )
    record = build_task_intake_record(task=task, persist_task_run=False)
    out = Path("run/dev_employee/task_intake_smoke/task_input.json")
    write_intake_record(out, record)
    payload = record.to_dict()
    ok = payload.get("ok") is True and payload.get("task_type") == "dev_task"
    print(json.dumps({"ok": ok, "task_type": payload.get("task_type"), "out": str(out)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
