"""Execution approval contract for ORIS Dev Employee."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecutionApproval:
    enabled: bool
    approved_task_run_id: str | None
    approved_mode: str
    allowed_modes: list[str]
    required_safety_checks: list[str]
    approval_note: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_approval(path: str | Path = "config/dev_employee_execution_approval.json") -> ExecutionApproval:
    target = Path(path)
    with target.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("execution approval config must be a JSON object")
    return ExecutionApproval(
        enabled=bool(raw.get("enabled", False)),
        approved_task_run_id=raw.get("approved_task_run_id"),
        approved_mode=str(raw.get("approved_mode", "dry_run_plan_only")),
        allowed_modes=[str(item) for item in raw.get("allowed_modes", ["dry_run_plan_only"])],
        required_safety_checks=[str(item) for item in raw.get("required_safety_checks", [])],
        approval_note=str(raw.get("approval_note", "")),
        metadata={"source": str(target)},
    )


def evaluate_approval(
    *,
    approval: ExecutionApproval,
    execution_packet: dict[str, Any],
) -> dict[str, Any]:
    planning = execution_packet.get("planning_snapshot", {})
    metadata = planning.get("metadata", {}) if isinstance(planning, dict) else {}
    task_run_id = None
    latest = planning.get("latest_cycle_index", {}) if isinstance(planning, dict) else {}
    latest_metadata = latest.get("metadata", {}) if isinstance(latest, dict) else {}
    smoke_json = latest_metadata.get("smoke_json")
    if isinstance(smoke_json, str):
        try:
            task_run_id = json.loads(smoke_json).get("task_run_id")
        except json.JSONDecodeError:
            task_run_id = None

    safety = {
        "latest_validation_ok": bool(planning.get("latest_validation_ok")) if isinstance(planning, dict) else False,
        "bootstrap_ok": bool(planning.get("bootstrap_ok")) if isinstance(planning, dict) else False,
        "blocking_dirty_tracked_count_zero": metadata.get("blocking_dirty_tracked_count") == 0,
        "blocking_untracked_count_zero": metadata.get("blocking_untracked_count") == 0,
    }
    required_ok = all(safety.get(name, False) for name in approval.required_safety_checks)
    mode_ok = approval.approved_mode in approval.allowed_modes
    task_ok = approval.approved_task_run_id is not None and approval.approved_task_run_id == task_run_id
    allowed = bool(approval.enabled and required_ok and mode_ok and task_ok)
    return {
        "allowed": allowed,
        "enabled": approval.enabled,
        "approved_mode": approval.approved_mode,
        "mode_ok": mode_ok,
        "required_safety_ok": required_ok,
        "task_run_id": task_run_id,
        "approved_task_run_id": approval.approved_task_run_id,
        "task_ok": task_ok,
        "safety": safety,
        "approval": approval.to_dict(),
    }


def load_execution_packet(path: str | Path = "logs/dev_employee/latest_execution_packet.json") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("execution packet must be a JSON object")
    return raw


def write_approval_result(path: str | Path, result: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_approval_markdown(result: dict[str, Any]) -> str:
    safety = result.get("safety", {}) if isinstance(result.get("safety"), dict) else {}
    approval = result.get("approval", {}) if isinstance(result.get("approval"), dict) else {}
    lines = [
        "# Dev Employee Execution Approval Result",
        "",
        f"- allowed: `{result.get('allowed')}`",
        f"- enabled: `{result.get('enabled')}`",
        f"- approved_mode: `{result.get('approved_mode')}`",
        f"- mode_ok: `{result.get('mode_ok')}`",
        f"- required_safety_ok: `{result.get('required_safety_ok')}`",
        f"- task_ok: `{result.get('task_ok')}`",
        f"- task_run_id: `{result.get('task_run_id')}`",
        f"- approved_task_run_id: `{result.get('approved_task_run_id')}`",
        "",
        "## Safety checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for name, value in safety.items():
        lines.append(f"| `{name}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Approval config",
            "",
            f"- source: `{approval.get('metadata', {}).get('source') if isinstance(approval.get('metadata'), dict) else ''}`",
            f"- note: {approval.get('approval_note', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def write_approval_markdown(path: str | Path, result: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_approval_markdown(result), encoding="utf-8")
