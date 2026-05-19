#!/usr/bin/env python3
"""Export a simple Dev Employee task list artifact.

This is intentionally small: it reads the latest task intake artifact and writes
GitHub-visible JSON/Markdown files for pilot tracking. It does not run Codex
and does not perform git operations.
"""

from __future__ import annotations

import json
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
    intake_path = Path("logs/dev_employee/latest_task_intake.json")
    intake = load_json(intake_path)
    item = {
        "task_run_id": intake.get("task_run_id"),
        "request_summary": intake.get("request_summary"),
        "objective": intake.get("objective"),
        "task_type": intake.get("task_type"),
        "source": intake.get("source"),
        "status": intake.get("task_run", {}).get("status") if isinstance(intake.get("task_run"), dict) else None,
        "source_file": str(intake_path),
    }
    payload = {
        "ok": True,
        "generated_at": utc_now(),
        "item_count": 1 if item.get("task_run_id") else 0,
        "items": [item] if item.get("task_run_id") else [],
    }
    json_out = Path("logs/dev_employee/latest_task_list.json")
    md_out = Path("logs/dev_employee/latest_task_list.md")
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Dev Employee Task List",
        "",
        f"- generated_at: `{payload['generated_at']}`",
        f"- item_count: `{payload['item_count']}`",
        "",
        "| Task Run | Status | Summary |",
        "| --- | --- | --- |",
    ]
    for row in payload["items"]:
        lines.append(f"| `{row['task_run_id']}` | `{row['status']}` | {row['request_summary']} |")
    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "json_out": str(json_out), "md_out": str(md_out), "item_count": payload["item_count"]}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
