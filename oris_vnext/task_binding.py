"""Bind pilot task intake to planning and execution packets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TaskPlanningBinding:
    ok: bool
    generated_at: str
    task_run_id: str | None
    request_summary: str | None
    objective: str | None
    planning_packet_ok: bool | None
    execution_packet_ok: bool | None
    execution_mode: str | None
    approved_for_real_execution: bool | None
    source_files: dict[str, str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def build_task_planning_binding(
    *,
    task_intake_path: str | Path = "logs/dev_employee/latest_task_intake.json",
    planning_packet_path: str | Path = "logs/dev_employee/latest_planning_packet.json",
    execution_packet_path: str | Path = "logs/dev_employee/latest_execution_packet.json",
) -> TaskPlanningBinding:
    task = load_json(task_intake_path)
    planning = load_json(planning_packet_path)
    execution = load_json(execution_packet_path)
    task_run_id = task.get("task_run_id")
    planning_ok = planning.get("ok") if isinstance(planning.get("ok"), bool) else None
    execution_ok = execution.get("ok") if isinstance(execution.get("ok"), bool) else None
    approved = execution.get("approved_for_real_execution")
    approved_bool = approved if isinstance(approved, bool) else None
    ok = bool(task.get("ok")) and planning_ok is True and execution_ok is True and approved_bool is False
    return TaskPlanningBinding(
        ok=ok,
        generated_at=utc_now(),
        task_run_id=str(task_run_id) if task_run_id else None,
        request_summary=task.get("request_summary"),
        objective=task.get("objective"),
        planning_packet_ok=planning_ok,
        execution_packet_ok=execution_ok,
        execution_mode=execution.get("mode"),
        approved_for_real_execution=approved_bool,
        source_files={
            "task_intake": str(task_intake_path),
            "planning_packet": str(planning_packet_path),
            "execution_packet": str(execution_packet_path),
        },
        metadata={
            "task_type": task.get("task_type"),
            "worker_profile": task.get("task_run", {}).get("worker_profile") if isinstance(task.get("task_run"), dict) else None,
            "model_role": task.get("task_run", {}).get("model_role") if isinstance(task.get("task_run"), dict) else None,
            "constraints": task.get("constraints", []),
        },
    )


def write_binding_json(path: str | Path, binding: TaskPlanningBinding) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(binding.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_binding_markdown(path: str | Path, binding: TaskPlanningBinding) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = binding.to_dict()
    lines = [
        "# Dev Employee Task Planning Binding",
        "",
        f"- ok: `{data['ok']}`",
        f"- generated_at: `{data['generated_at']}`",
        f"- task_run_id: `{data['task_run_id']}`",
        f"- request_summary: {data['request_summary']}",
        f"- objective: {data['objective']}",
        f"- planning_packet_ok: `{data['planning_packet_ok']}`",
        f"- execution_packet_ok: `{data['execution_packet_ok']}`",
        f"- execution_mode: `{data['execution_mode']}`",
        f"- approved_for_real_execution: `{data['approved_for_real_execution']}`",
        "",
        "## Source files",
        "",
    ]
    for key, value in data["source_files"].items():
        lines.append(f"- {key}: `{value}`")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
