from __future__ import annotations

from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json
from dev_employee_runtime.paths import repo_relative
from dev_employee_runtime.bridge_context import (
    EVIDENCE_COMMIT_INDEX_DIR,
    LOG_DIR,
    ORIS_DIR,
    QUEUE_DIR,
    RUN_DIR,
    run,
    strict_result_schema,
    next_recommended_action,
)


def add_existing(files: list[str], path: Path) -> None:
    rel = repo_relative(path, ORIS_DIR)
    if rel and path.exists() and rel not in files:
        files.append(rel)


def collect_task_log_files(task_id: str) -> list[str]:
    files: list[str] = []
    add_existing(files, LOG_DIR / f"{task_id}.codex.log")
    add_existing(files, LOG_DIR / f"{task_id}_host_py_compile.txt")
    add_existing(files, LOG_DIR / f"{task_id}_host_pytest.txt")
    add_existing(files, LOG_DIR / f"{task_id}_host_pytest_werror.txt")
    add_existing(files, LOG_DIR / "skill_resolution" / f"{task_id}.json")
    add_existing(files, LOG_DIR / "skill_resolution" / f"{task_id}.md")
    return files


def commit_files(files: list[str], message: str) -> dict[str, Any]:
    existing = [path for path in files if (ORIS_DIR / path).exists()]
    if not existing:
        return {"changed": False, "commit_sha": run(["git", "rev-parse", "HEAD"], ORIS_DIR).stdout.strip(), "files": []}
    status_before = run(["git", "status", "--short", "--", *existing], ORIS_DIR).stdout.strip()
    if not status_before:
        return {"changed": False, "commit_sha": run(["git", "rev-parse", "HEAD"], ORIS_DIR).stdout.strip(), "files": existing}
    # Evidence artifacts are intentionally generated under ignored runtime directories.
    # These paths are selected explicitly by the bridge after repo-relative filtering, so
    # force-add only this bounded allow-list instead of broad ignored directories.
    add = run(["git", "add", "-f", "--", *existing], ORIS_DIR)
    if add.returncode != 0:
        return {
            "changed": False,
            "stage": "git_add",
            "git_add_failed": True,
            "git_add_rc": add.returncode,
            "stdout": add.stdout[-4000:],
            "stderr": add.stderr[-4000:],
            "files": existing,
        }
    commit = run(["git", "commit", "-m", message], ORIS_DIR)
    if commit.returncode != 0:
        return {
            "changed": False,
            "stage": "git_commit",
            "commit_failed": True,
            "commit_rc": commit.returncode,
            "stdout": commit.stdout[-4000:],
            "stderr": commit.stderr[-4000:],
            "files": existing,
        }
    sha = run(["git", "rev-parse", "HEAD"], ORIS_DIR).stdout.strip()
    push = run(["git", "push"], ORIS_DIR)
    remote = run(["git", "rev-parse", "origin/HEAD"], ORIS_DIR).stdout.strip()
    return {"changed": True, "commit_sha": sha, "push_rc": push.returncode, "remote_sha": remote, "files": existing}


def commit_push_oris(
    task_id: str,
    run_json: Path,
    codex_result_path: Path,
    codex_result: dict[str, Any],
    final: dict[str, Any],
    product_commit: dict[str, Any],
    preflight: dict[str, Any] | None = None,
) -> dict[str, Any]:
    status_path = LOG_DIR / "latest_task_progress.json"
    snapshot = {
        "task_id": task_id,
        "updated_at": now_iso(),
        "status": codex_result.get("status"),
        "summary": codex_result.get("summary"),
        "final_check_ok": final.get("ok"),
        "product_commit_sha": product_commit.get("commit_sha"),
        "product_remote_sha": product_commit.get("remote_sha"),
        "preflight_ok": preflight.get("ok") if isinstance(preflight, dict) else None,
    }
    atomic_write_json(status_path, snapshot)
    files = [
        repo_relative(run_json, ORIS_DIR),
        repo_relative(codex_result_path, ORIS_DIR),
        repo_relative(status_path, ORIS_DIR),
        *collect_task_log_files(task_id),
    ]
    files = [item for item in files if item]
    return commit_files(files, f"chore(dev-employee): add evidence for {task_id}")


def record_evidence_commit_index(
    task_id: str,
    product_commit: dict[str, Any],
    evidence_commit: dict[str, Any],
    run_json: Path,
    codex_result_path: Path,
) -> dict[str, Any]:
    EVIDENCE_COMMIT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    index_path = EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"
    payload = {
        "task_id": task_id,
        "recorded_at": now_iso(),
        "product_commit_sha": product_commit.get("commit_sha"),
        "product_remote_sha": product_commit.get("remote_sha"),
        "oris_evidence_commit_sha": evidence_commit.get("commit_sha"),
        "oris_evidence_remote_sha": evidence_commit.get("remote_sha"),
        "run_json": repo_relative(run_json, ORIS_DIR),
        "codex_result_json": repo_relative(codex_result_path, ORIS_DIR),
        "evidence_files": evidence_commit.get("files", []),
    }
    atomic_write_json(index_path, payload)
    commit = commit_files([repo_relative(index_path, ORIS_DIR) or ""], f"chore(dev-employee): index evidence for {task_id}")
    payload["evidence_index_commit_sha"] = commit.get("commit_sha")
    payload["evidence_index_remote_sha"] = commit.get("remote_sha")
    atomic_write_json(index_path, payload)
    commit = commit_files([repo_relative(index_path, ORIS_DIR) or ""], f"chore(dev-employee): finalize evidence index for {task_id}")
    payload["evidence_index_final_commit_sha"] = commit.get("commit_sha")
    payload["evidence_index_final_remote_sha"] = commit.get("remote_sha")
    return payload


def commit_push_oris_failure(task: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    task_id = str(task.get("task_id"))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    failure = {
        "task_id": task_id,
        "status": status,
        "canonical_status": status,
        "terminal": True,
        "updated_at": now_iso(),
        "strict_result_schema": strict_result_schema(task),
        "failure_code": (extra or {}).get("failure_code"),
        "failure_details": extra or {},
        "next_recommended_action": next_recommended_action(status, (extra or {}).get("failure_code")),
    }
    run_json = RUN_DIR / f"{task_id}.json"
    atomic_write_json(run_json, failure)
    latest_path = LOG_DIR / "latest_task_progress.json"
    atomic_write_json(latest_path, {"task_id": task_id, "updated_at": now_iso(), "status": status, "failure_code": failure["failure_code"]})
    files = [repo_relative(run_json, ORIS_DIR), repo_relative(latest_path, ORIS_DIR), *collect_task_log_files(task_id)]
    files = [item for item in files if item]
    result = commit_files(files, f"chore(dev-employee): add failure evidence for {task_id}")
    if result.get("commit_sha"):
        failure["oris_evidence_sha"] = result.get("commit_sha")
        failure["oris_evidence_remote_sha"] = result.get("remote_sha")
        atomic_write_json(run_json, failure)
        second = commit_files([repo_relative(run_json, ORIS_DIR) or ""], f"chore(dev-employee): finalize failure evidence for {task_id}")
        failure["oris_evidence_index_sha"] = second.get("commit_sha")
    return {"failure_record": failure, "evidence_commit": result}


def run_failure_triage(task_id: str) -> dict[str, Any]:
    triage_script = ORIS_DIR / "scripts" / "dev_employee_failure_triage.py"
    if not triage_script.exists():
        return {"ok": False, "skipped": True, "reason": "triage_script_missing"}
    log_path = LOG_DIR / f"{task_id}_failure_triage.txt"
    proc = run(["python3", str(triage_script), "--task-id", task_id], ORIS_DIR, log_path)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode, "log": str(log_path)}


def fail_task(task_path: Path, task: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> int:
    task_id = str(task.get("task_id"))
    failure_evidence = commit_push_oris_failure(task, status, extra)
    triage = run_failure_triage(task_id)
    task.update({
        "status": status,
        "canonical_status": status,
        "terminal": True,
        "finished_at": now_iso(),
        "failure_evidence": failure_evidence,
        "failure_triage": triage,
        "next_recommended_action": next_recommended_action(status, (extra or {}).get("failure_code")),
    })
    target = QUEUE_DIR / f"{task_id}.{status}.json"
    atomic_write_json(task_path, task)
    task_path.replace(target)
    return 2 if status == "blocked" else 1
