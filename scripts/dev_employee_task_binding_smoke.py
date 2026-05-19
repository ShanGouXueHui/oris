#!/usr/bin/env python3
"""Smoke test for Dev Employee task-planning binding."""

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
    json_out = Path("run/dev_employee/task_binding_smoke/binding.json")
    md_out = Path("run/dev_employee/task_binding_smoke/binding.md")
    write_binding_json(json_out, binding)
    write_binding_markdown(md_out, binding)
    payload = binding.to_dict()
    ok = bool(payload.get("ok")) and payload.get("approved_for_real_execution") is False
    print(json.dumps({"ok": ok, "binding_ok": payload.get("ok"), "task_run_id": payload.get("task_run_id")}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
