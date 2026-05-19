#!/usr/bin/env python3
"""Export a compact operator dashboard for Dev Employee controlled pilot."""

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


def safe_load(path: str) -> dict:
    target = Path(path)
    if not target.exists():
        return {"_missing": True, "_path": path}
    return load_json(target)


def main() -> int:
    readiness = safe_load("logs/dev_employee/latest_commercial_readiness.json")
    task_list = safe_load("logs/dev_employee/latest_task_list.json")
    task_status = safe_load("logs/dev_employee/latest_task_status.json")
    task_binding = safe_load("logs/dev_employee/latest_task_binding.json")
    plan_audit = safe_load("logs/dev_employee/latest_plan_audit.json")
    cycle_index = safe_load("logs/dev_employee/latest_cycle_index.json")
    execution_packet = safe_load("logs/dev_employee/latest_execution_packet.json")

    dashboard = {
        "ok": bool(readiness.get("ok")) and bool(cycle_index.get("ok")),
        "generated_at": utc_now(),
        "commercial_status": readiness.get("status"),
        "cycle_ok": cycle_index.get("ok"),
        "validation_check_count": cycle_index.get("check_count"),
        "task_count": task_list.get("item_count"),
        "task_run_id": task_status.get("task_run_id") or task_binding.get("task_run_id"),
        "task_state": task_status.get("state"),
        "plan_recommendation": plan_audit.get("recommendation"),
        "execution_mode": execution_packet.get("mode"),
        "approval_allowed": readiness.get("metadata", {}).get("approval_allowed") if isinstance(readiness.get("metadata"), dict) else None,
        "legacy_review_tracked_count": readiness.get("metadata", {}).get("legacy_review_tracked_count") if isinstance(readiness.get("metadata"), dict) else None,
        "legacy_review_untracked_count": readiness.get("metadata", {}).get("legacy_review_untracked_count") if isinstance(readiness.get("metadata"), dict) else None,
        "source_files": {
            "commercial_readiness": "logs/dev_employee/latest_commercial_readiness.json",
            "task_list": "logs/dev_employee/latest_task_list.json",
            "task_status": "logs/dev_employee/latest_task_status.json",
            "task_binding": "logs/dev_employee/latest_task_binding.json",
            "plan_audit": "logs/dev_employee/latest_plan_audit.json",
            "cycle_index": "logs/dev_employee/latest_cycle_index.json",
            "execution_packet": "logs/dev_employee/latest_execution_packet.json",
        },
    }

    json_out = Path("logs/dev_employee/latest_operator_dashboard.json")
    md_out = Path("logs/dev_employee/latest_operator_dashboard.md")
    json_out.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(
        "# Dev Employee Operator Dashboard\n\n"
        f"- ok: `{dashboard['ok']}`\n"
        f"- generated_at: `{dashboard['generated_at']}`\n"
        f"- commercial_status: `{dashboard['commercial_status']}`\n"
        f"- cycle_ok: `{dashboard['cycle_ok']}`\n"
        f"- validation_check_count: `{dashboard['validation_check_count']}`\n"
        f"- task_count: `{dashboard['task_count']}`\n"
        f"- task_run_id: `{dashboard['task_run_id']}`\n"
        f"- task_state: `{dashboard['task_state']}`\n"
        f"- plan_recommendation: `{dashboard['plan_recommendation']}`\n"
        f"- execution_mode: `{dashboard['execution_mode']}`\n"
        f"- approval_allowed: `{dashboard['approval_allowed']}`\n"
        f"- legacy_review_tracked_count: `{dashboard['legacy_review_tracked_count']}`\n"
        f"- legacy_review_untracked_count: `{dashboard['legacy_review_untracked_count']}`\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "dashboard_ok": dashboard["ok"], "json_out": str(json_out), "md_out": str(md_out)}, ensure_ascii=False, sort_keys=True))
    return 0 if dashboard["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
