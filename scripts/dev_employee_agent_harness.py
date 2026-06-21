#!/usr/bin/env python3
"""Provider-neutral Agent Harness for ORIS conversational development tasks.

The harness sits between the conversation orchestrator and model/provider
adapters. It owns deterministic control routing, provider selection, policy
validation, structured-output validation, fallback visibility, and sanitized
trace events. It does not create tasks, mutate queues, execute Codex, or touch
product repositories.
"""

from __future__ import annotations

import json
import os
import time
import traceback
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.paths import discover_repo_root

DEFAULT_ORIS_DIR = discover_repo_root()
DEFAULT_TRACE_DIR = DEFAULT_ORIS_DIR / "logs" / "dev_employee" / "agent_harness"
DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class HarnessOutcome:
    ok: bool
    result: dict[str, Any]
    trace_file: Path
    attempts: int


def trace_path(trace_dir: Path, task_id: str) -> Path:
    return trace_dir / f"{task_id}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jsonl"


def append_trace(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_event = {
        "ts": now_iso(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe_event, ensure_ascii=False, sort_keys=True) + "\n")


class AgentHarness:
    def __init__(self, *, trace_dir: Path = DEFAULT_TRACE_DIR, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self.trace_dir = trace_dir
        self.max_retries = max(0, max_retries)

    def validate_result(self, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("agent result must be a JSON object")
        status = value.get("status")
        if status not in {"success", "failed", "blocked", "needs_human"}:
            raise ValueError("agent result status must be success, failed, blocked or needs_human")
        if "summary" not in value:
            raise ValueError("agent result must contain summary")
        return value

    def deterministic(self, task: dict[str, Any]) -> dict[str, Any] | None:
        if task.get("strict_result_schema") is False:
            return None
        if not task.get("task_id"):
            return {"status": "failed", "summary": "missing task_id", "checks": [], "artifacts": []}
        return None

    def analyze(self, task: dict[str, Any], agent_call: Callable[[dict[str, Any]], Any]) -> HarnessOutcome:
        task_id = str(task.get("task_id") or "unknown")
        path = trace_path(self.trace_dir, task_id)
        append_trace(path, {"event": "harness_start", "task_id": task_id, "strict_result_schema": bool(task.get("strict_result_schema"))})
        deterministic = self.deterministic(task)
        if deterministic is not None:
            append_trace(path, {"event": "deterministic_result", "status": deterministic["status"]})
            return HarnessOutcome(True, deterministic, path, 0)
        last_error: str | None = None
        for attempt in range(1, self.max_retries + 2):
            append_trace(path, {"event": "agent_attempt_start", "attempt": attempt})
            try:
                result = self.validate_result(agent_call(task))
                append_trace(path, {"event": "agent_attempt_success", "attempt": attempt, "status": result.get("status")})
                return HarnessOutcome(True, result, path, attempt)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                append_trace(path, {"event": "agent_attempt_failed", "attempt": attempt, "error_type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(limit=6)})
        fallback = {
            "status": "failed",
            "summary": "Agent Harness failed after retries; no product action was executed by the harness itself.",
            "checks": [],
            "artifacts": [],
            "error": last_error,
        }
        append_trace(path, {"event": "harness_failed", "error": last_error})
        return HarnessOutcome(False, fallback, path, self.max_retries + 1)


def analyze_with_harness(task: dict[str, Any], agent_call: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    max_retries = int(os.environ.get("ORIS_AGENT_HARNESS_MAX_RETRIES", str(DEFAULT_MAX_RETRIES)))
    outcome = AgentHarness(max_retries=max_retries).analyze(task, agent_call)
    result = dict(outcome.result)
    result.setdefault("artifacts", [])
    result["artifacts"].append({"label": "agent_harness_trace", "path": str(outcome.trace_file)})
    result["harness"] = {"ok": outcome.ok, "attempts": outcome.attempts}
    return result
