from __future__ import annotations

from pathlib import Path
from typing import Any

from dev_employee_runtime.json_store import read_json
from dev_employee_runtime.paths import repo_relative
from dev_employee_runtime.intake_config import (
    CATALOG_DIR,
    DEFAULT_BRANCH,
    EVIDENCE_COMMIT_INDEX_DIR,
    LOG_DIR,
    ORIS_DIR,
    ORIS_REPO,
    QUEUE_DIR,
    RUN_DIR,
    TASK_ID_RE,
)
from dev_employee_task_states import classify as classify_task_state


def evidence_file(label: str, path: Path) -> dict[str, Any]:
    rel = repo_relative(path, ORIS_DIR)
    return {
        "label": label,
        "exists": path.exists(),
        "local_path": str(path),
        "repo": ORIS_REPO if rel else None,
        "branch": DEFAULT_BRANCH if rel else None,
        "repo_path": rel,
    }


def evidence_summary(task_id: str, primary_run: dict[str, Any] | None) -> dict[str, Any]:
    index_path = EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"
    evidence_index = read_json(index_path) if index_path.exists() else {}
    files = [
        evidence_file("task_run_json", RUN_DIR / f"{task_id}.json"),
        evidence_file("codex_result_json", RUN_DIR / f"{task_id}.codex_result.json"),
        evidence_file("skill_resolution_json", LOG_DIR / "skill_resolution" / f"{task_id}.json"),
        evidence_file("skill_resolution_markdown", LOG_DIR / "skill_resolution" / f"{task_id}.md"),
        evidence_file("codex_log", LOG_DIR / f"{task_id}.codex.log"),
        evidence_file("host_py_compile_log", LOG_DIR / f"{task_id}_host_py_compile.txt"),
        evidence_file("host_pytest_log", LOG_DIR / f"{task_id}_host_pytest.txt"),
        evidence_file("host_pytest_werror_log", LOG_DIR / f"{task_id}_host_pytest_werror.txt"),
        evidence_file("evidence_commit_index", EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"),
    ]
    completed = primary_run or {}
    return {
        "repo": ORIS_REPO,
        "branch": DEFAULT_BRANCH,
        "files": [item for item in files if item["exists"]],
        "product_commit_sha": completed.get("product_commit_sha"),
        "product_remote_sha": completed.get("product_remote_sha"),
        "oris_evidence_sha": completed.get("oris_evidence_sha"),
        "oris_evidence_commit_sha": evidence_index.get("oris_evidence_commit_sha"),
        "oris_evidence_remote_sha": evidence_index.get("oris_evidence_remote_sha"),
        "evidence_index_commit_sha": evidence_index.get("evidence_index_commit_sha"),
        "strict_result_schema": completed.get("strict_result_schema"),
        "skill_resolver_report_json": completed.get("skill_resolver_report_json"),
    }


def task_status(task_id: str) -> dict[str, Any]:
    if not TASK_ID_RE.match(task_id):
        raise ValueError("invalid task_id")
    catalog_path = CATALOG_DIR / f"{task_id}.json"
    catalog = read_json(catalog_path) if catalog_path.exists() else None
    queue = []
    seen_queue_paths: set[Path] = set()
    for suffix in ["queued", "running", "done", "failed"]:
        candidates = [QUEUE_DIR / f"{task_id}.{suffix}.json"]
        candidates.extend(sorted(QUEUE_DIR.glob(f"{task_id}*.{suffix}.json")))
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen_queue_paths or not path.exists():
                continue
            seen_queue_paths.add(resolved)
            queue.append({"suffix": suffix, "path": str(path), "data": read_json(path)})
    runs = []
    for path in sorted(RUN_DIR.glob(f"{task_id}*.json")) if RUN_DIR.exists() else []:
        runs.append({"path": str(path), "data": read_json(path)})
    primary_run = read_json(RUN_DIR / f"{task_id}.json") if (RUN_DIR / f"{task_id}.json").exists() else None
    status = "unknown"
    if primary_run:
        status = str(primary_run.get("status") or status)
    elif runs:
        status = str((runs[0].get("data") or {}).get("status") or status)
    elif queue:
        status = str((queue[0].get("data") or {}).get("status") or queue[0].get("suffix") or status)
    elif catalog:
        status = str(catalog.get("status") or status)
    state = classify_task_state(status, primary_run or {})
    latest = None
    latest_path = LOG_DIR / "latest_task_progress.json"
    if latest_path.exists():
        latest = read_json(latest_path)
    evidence = {
        "task_run_json": str(RUN_DIR / f"{task_id}.json") if (RUN_DIR / f"{task_id}.json").exists() else None,
        "codex_result_json": str(RUN_DIR / f"{task_id}.codex_result.json") if (RUN_DIR / f"{task_id}.codex_result.json").exists() else None,
        "skill_resolution_json": str(LOG_DIR / "skill_resolution" / f"{task_id}.json") if (LOG_DIR / "skill_resolution" / f"{task_id}.json").exists() else None,
        "codex_log": str(LOG_DIR / f"{task_id}.codex.log") if (LOG_DIR / f"{task_id}.codex.log").exists() else None,
    }
    return {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": state["failure_code"],
        "catalog": catalog,
        "queue": queue,
        "runs": runs,
        "latest_task_progress": latest,
        "evidence": evidence,
        "github_evidence": evidence_summary(task_id, primary_run),
    }


def list_goals() -> dict[str, Any]:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(CATALOG_DIR.glob("*.json")):
        data = read_json(path)
        task_id = str(data.get("task_id") or "")
        current = task_status(task_id) if task_id else {}
        items.append({
            "task_id": task_id or None,
            "project_key": data.get("project_key"),
            "status": current.get("status") or data.get("status"),
            "canonical_status": current.get("canonical_status"),
            "terminal": current.get("terminal"),
            "failure_code": current.get("failure_code"),
            "created_at": data.get("created_at"),
            "path": str(path),
        })
    return {"catalog_dir": str(CATALOG_DIR), "items": items}
