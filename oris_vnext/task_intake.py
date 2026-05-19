"""Pilot task intake builder for ORIS Dev Employee."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .task_kernel import DevTask, TaskKernel


@dataclass(frozen=True)
class TaskIntakeRecord:
    ok: bool
    created_at: str
    request_summary: str
    objective: str
    repo: str
    task_type: str
    source: str
    constraints: list[str]
    task_run_id: str | None = None
    task_run: dict[str, Any] | None = None
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


def load_config(path: str | Path = "config/dev_employee_task_intake.json") -> dict[str, Any]:
    return load_json(path)


def normalize_task_input(
    *,
    request_summary: str,
    objective: str,
    config: dict[str, Any],
    repo: str | None = None,
    source: str | None = None,
    constraints: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> DevTask:
    merged_constraints = list(config.get("default_constraints", []))
    if constraints:
        merged_constraints.extend(constraints)
    return DevTask(
        request_summary=request_summary.strip(),
        repo=repo or str(config.get("default_repo", "ShanGouXueHui/oris")),
        objective=objective.strip(),
        constraints=merged_constraints,
        source=source or str(config.get("default_source", "pilot_manual")),
        metadata=metadata or {},
        task_type=str(config.get("default_task_type", "dev_task")),
    )


def build_task_intake_record(
    *,
    task: DevTask,
    persist_task_run: bool = True,
    kernel_config_path: str | Path = "config/dev_employee_runtime.json",
) -> TaskIntakeRecord:
    kernel = TaskKernel(kernel_config_path)
    task_run = kernel.create_dev_task_run(task, persist=persist_task_run)
    return TaskIntakeRecord(
        ok=True,
        created_at=utc_now(),
        request_summary=task.request_summary,
        objective=task.objective,
        repo=task.repo,
        task_type=task.task_type,
        source=task.source,
        constraints=task.constraints,
        task_run_id=task_run.task_run_id,
        task_run=asdict(task_run),
        metadata={"persist_task_run": persist_task_run},
    )


def write_intake_record(path: str | Path, record: TaskIntakeRecord) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a Dev Employee pilot task intake record.")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--config", default="config/dev_employee_task_intake.json")
    parser.add_argument("--kernel-config", default="config/dev_employee_runtime.json")
    parser.add_argument("--out", default="run/dev_employee/task_intake/latest_task_input.json")
    parser.add_argument("--no-persist", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = load_config(args.config)
    task = normalize_task_input(
        request_summary=args.summary,
        objective=args.objective,
        config=config,
        repo=args.repo,
        source=args.source,
    )
    record = build_task_intake_record(
        task=task,
        persist_task_run=not args.no_persist,
        kernel_config_path=args.kernel_config,
    )
    write_intake_record(args.out, record)
    print(json.dumps({"ok": record.ok, "task_run_id": record.task_run_id, "out": args.out}, ensure_ascii=False, sort_keys=True))
    return 0 if record.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
