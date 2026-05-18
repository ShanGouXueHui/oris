#!/usr/bin/env python3
"""Export the latest Dev Employee execution approval result.

This script reads the latest execution packet and the approval config, then
writes JSON and Markdown review files under logs/dev_employee/. It does not run
Codex and does not perform git operations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.execution_approval import (
    evaluate_approval,
    load_approval,
    load_execution_packet,
    write_approval_markdown,
    write_approval_result,
)


def main() -> int:
    result = evaluate_approval(
        approval=load_approval("config/dev_employee_execution_approval.json"),
        execution_packet=load_execution_packet("logs/dev_employee/latest_execution_packet.json"),
    )
    json_out = Path("logs/dev_employee/latest_execution_approval.json")
    md_out = Path("logs/dev_employee/latest_execution_approval.md")
    write_approval_result(json_out, result)
    write_approval_markdown(md_out, result)
    print(
        json.dumps(
            {
                "ok": True,
                "allowed": result.get("allowed"),
                "enabled": result.get("enabled"),
                "required_safety_ok": result.get("required_safety_ok"),
                "task_ok": result.get("task_ok"),
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
