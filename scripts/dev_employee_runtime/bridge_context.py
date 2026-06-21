from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings

ORIS_DIR = discover_repo_root()
RUNTIME_SETTINGS = load_runtime_settings(ORIS_DIR)
PROJECTS_DIR = RUNTIME_SETTINGS.projects_root
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
SKILL_RESOLUTION_DIR = LOG_DIR / "skill_resolution"
EVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / "evidence_commit_index"
DEFAULT_CODEX = Path.home() / ".npm-global" / "bin" / "codex"


def run(cmd: list[str], cwd: Path, log_path: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, env=env, check=False)
    except FileNotFoundError as exc:
        proc = subprocess.CompletedProcess(cmd, 127, "", f"FileNotFoundError: {exc}\n")
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc


def safe_path(path_value: str, roots: list[Path]) -> Path:
    path = Path(path_value).expanduser().resolve()
    for root in roots:
        try:
            path.relative_to(root.resolve())
            return path
        except ValueError:
            continue
    raise ValueError(f"unsafe path outside allowed roots: {path}")


def select_python(product_path: Path) -> str:
    venv_python = product_path / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return "python3"


def claim_task(path: Path) -> Path | None:
    try:
        task = read_json(path)
    except Exception:
        return None
    task_id = str(task.get("task_id") or path.name.removesuffix(".queued.json"))
    running = QUEUE_DIR / f"{task_id}.running.json"
    if running.exists():
        return None
    if not path.exists():
        return None
    os.replace(path, running)
    task["status"] = "running"
    task["started_at"] = now_iso()
    atomic_write_json(running, task)
    return running


def strict_result_schema(task: dict[str, Any]) -> bool:
    value = task.get("strict_result_schema")
    if value is None:
        return bool(task.get("task_objective"))
    return bool(value)


def minimum_result_payload(task: dict[str, Any], product_path: str | None, strict: bool) -> dict[str, Any]:
    return {
        "status": "failed",
        "summary": "Codex did not produce a valid structured result; host bridge generated the minimal failure payload.",
        "files_changed": [],
        "tests_run": [],
        "checks": [],
        "risks": ["missing_or_invalid_codex_result"],
        "next_steps": ["Inspect Codex log and retry after fixing the root cause."],
        "product_path": product_path,
        "task_id": task.get("task_id"),
        "strict_result_schema": strict,
        "skill_resolution_required": bool(task.get("skill_resolution_required")),
    }


def autonomous_summary(codex_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": codex_result.get("status"),
        "summary": codex_result.get("summary"),
        "files_changed": codex_result.get("files_changed", []),
        "tests_run": codex_result.get("tests_run", []),
        "risks": codex_result.get("risks", []),
        "next_steps": codex_result.get("next_steps", []),
    }


def next_recommended_action(status: str, failure_code: str | None = None) -> str:
    if status == "blocked":
        return "human_required_for_policy_or_credential_block"
    if failure_code in {"codex_auth_preflight_failed", "codex_auth_failure"}:
        return "repair_codex_auth_or_credentials_then_retry"
    if failure_code in {"codex_invalid_result", "skill_resolution_missing"}:
        return "retry_after_prompt_or_skill_resolver_repair"
    if status == "failed":
        return "inspect_evidence_then_retry_terminal_failure"
    return "none"
