#!/usr/bin/env python3
"""Export the latest Dev Employee task-planning binding.

This script binds latest_task_intake, latest_planning_packet, and
latest_execution_packet into fixed GitHub-visible artifacts. It does not run
Codex and does not perform git operations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.task_binding import (
    build_task_planning_binding,
    write_binding_json,
    write_binding_markdown,
)


def main() -> int:
    binding = build_task_planning_binding()
    json_out = Path("logs/dev_employee/latest_task_binding.json")
    md_out = Path("logs/dev_employee/latest_task_binding.md")
    write_binding_json(json_out, binding)
    write_binding_markdown(md_out, binding)
    payload = binding.to_dict()
    print(
        json.dumps(
            {
                "ok": True,
                "binding_ok": payload.get("ok"),
                "task_run_id": payload.get("task_run_id"),
                "json_out": str(json_out),
                "md_out": str(md_out),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
