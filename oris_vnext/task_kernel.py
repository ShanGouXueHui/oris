"""ORIS vNext Task Kernel scaffold.

This module is intentionally small and stdlib-only. It establishes the
Phase 2 contract for Dev Employee task intake, worker binding, and execution
ledger recording without taking over OpenClaw channel handling.
"""

from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


UTC = timezone.utc


class KernelConfigError(ValueError):
    """Raised when the Dev Employee runtime config is invalid."""


@dataclass(frozen=True)
class DevTask:
    """Normalized engineering task request handled by Dev Employee."""

    request_summary: str
    repo: str
    objective: str
    constraints: list[str] = field(default_factory=list)
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)
    task_type: str = "dev_task"


@dataclass(frozen=True)
class WorkerProfile:
    """Configured worker profile selected by Task Kernel."""

    name: str
    description: str
    allowed_task_types: list[str]
    model_roles: dict[str, str]
    required_bootstrap_docs: list[str]


@dataclass
class TaskRun:
    """Execution ledger record for a normalized task."""

    task_run_id: str
    task_type: str
    worker_profile: str
    status: str
    created_at: str
    updated_at: str
    request_summary: str
    repo: str
    objective: str
    model_role: str
    executor_plan: list[str]
    constraints: list[str] = field(default_factory=list)
    source: str = "manual"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class WorkerRegistry:
    """Worker profile registry backed by config/dev_employee_runtime.json."""

    def __init__(self, config: Mapping[str, Any]) -> None:
        self._config = config
        self._profiles = self._load_profiles(config.get("worker_profiles", {}))

    @staticmethod
    def _load_profiles(raw_profiles: Mapping[str, Any]) -> dict[str, WorkerProfile]:
        profiles: dict[str, WorkerProfile] = {}
        for name, raw in raw_profiles.items():
            profiles[name] = WorkerProfile(
                name=name,
                description=str(raw.get("description", "")),
                allowed_task_types=list(raw.get("allowed_task_types", [])),
                model_roles=dict(raw.get("model_roles", {})),
                required_bootstrap_docs=list(raw.get("required_bootstrap_docs", [])),
            )
        return profiles

    def get(self, name: str) -> WorkerProfile:
        try:
            return self._profiles[name]
        except KeyError as exc:
            raise KernelConfigError(f"unknown worker profile: {name}") from exc

    def select_for_task(self, task_type: str) -> WorkerProfile:
        task_cfg = self._config.get("task_types", {}).get(task_type)
        if not task_cfg:
            raise KernelConfigError(f"unknown task type: {task_type}")
        profile_name = task_cfg.get("default_worker_profile")
        profile = self.get(str(profile_name))
        if task_type not in profile.allowed_task_types:
            raise KernelConfigError(
                f"worker profile {profile.name} does not allow task type {task_type}"
            )
        return profile


class ExecutionLedger:
    """Append-only JSONL ledger for task_run records."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, task_run: TaskRun) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fp:
            fp.write(task_run.to_json_line() + "\n")


class TaskKernel:
    """Minimal ORIS-native task kernel for Phase 2 Dev Employee scaffold."""

    def __init__(self, config_path: str | Path = "config/dev_employee_runtime.json") -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config(self.config_path)
        self.worker_registry = WorkerRegistry(self.config)
        ledger_path = Path(
            self.config.get("execution_ledger", {}).get(
                "path",
                self.config.get("runtime", {}).get("default_ledger_path", "run/dev_employee/task_runs.jsonl"),
            )
        )
        self.ledger = ExecutionLedger(ledger_path)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise KernelConfigError(f"config file not found: {path}")
        with path.open("r", encoding="utf-8") as fp:
            raw = json.load(fp)
        if not isinstance(raw, dict):
            raise KernelConfigError("runtime config must be a JSON object")
        for key in ("runtime", "task_types", "worker_profiles", "executors", "execution_ledger"):
            if key not in raw:
                raise KernelConfigError(f"runtime config missing required key: {key}")
        return raw

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def create_dev_task_run(self, task: DevTask, *, persist: bool = True) -> TaskRun:
        worker = self.worker_registry.select_for_task(task.task_type)
        task_cfg = self.config["task_types"][task.task_type]
        model_role = str(task_cfg.get("default_model_role", worker.model_roles.get("planning", "coding")))
        allowed_executors = list(task_cfg.get("allowed_executors", []))
        now = self._now()
        task_run = TaskRun(
            task_run_id=f"dev-{uuid.uuid4().hex[:12]}",
            task_type=task.task_type,
            worker_profile=worker.name,
            status="planned",
            created_at=now,
            updated_at=now,
            request_summary=task.request_summary,
            repo=task.repo,
            objective=task.objective,
            model_role=model_role,
            executor_plan=allowed_executors,
            constraints=task.constraints,
            source=task.source,
            metadata={
                **task.metadata,
                "required_bootstrap_docs": worker.required_bootstrap_docs,
                "human_approval_before_write": bool(
                    task_cfg.get("requires_human_approval_before_write", True)
                ),
            },
        )
        if persist:
            self.ledger.append(task_run)
        return task_run


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a dry-run ORIS Dev Employee task_run.")
    parser.add_argument("--config", default="config/dev_employee_runtime.json")
    parser.add_argument("--repo", default="ShanGouXueHui/oris")
    parser.add_argument("--summary", default="Phase 2 scaffold smoke task")
    parser.add_argument("--objective", default="Validate Dev Employee task kernel scaffold")
    parser.add_argument("--no-persist", action="store_true")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    kernel = TaskKernel(args.config)
    task_run = kernel.create_dev_task_run(
        DevTask(
            request_summary=args.summary,
            repo=args.repo,
            objective=args.objective,
            constraints=["dry_run", "no_external_execution"],
            source="cli",
        ),
        persist=not args.no_persist,
    )
    print(task_run.to_json_line())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
