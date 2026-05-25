#!/usr/bin/env python3
"""ORIS Dev Employee supervised bridge v2.

This bridge invokes Codex for local code/test work, then performs host-side
post-processing: final checks, product commit/push, remote verification, and
ORIS evidence commit/push.

Important host-side rules:
- Never rely on a bare `python` binary. Prefer the product repository virtualenv
  interpreter, then fall back to `python3`.
- Never rely on hardcoded task IDs inside reusable prompts. The bridge injects
  the claimed runtime task descriptor into the Codex prompt and treats that
  runtime descriptor as the authoritative contract.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
DEFAULT_CODEX = Path("/home/admin/.npm-global/bin/codex")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    resolved_roots = [root.resolve() for root in roots]
    if not any(path == root or root in path.parents for root in resolved_roots):
        raise ValueError(f"path outside allowed roots: {path}")
    return path


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
    if task.get("status") != "queued":
        return None
    claimed = path.with_suffix(".running.json")
    try:
        path.rename(claimed)
    except FileNotFoundError:
        return None
    task["status"] = "running"
    task["claimed_at"] = now_iso()
    write_json(claimed, task)
    return claimed


def build_runtime_prompt(task: dict[str, Any], base_prompt: str, result_path: Path) -> str:
    task_id = task["task_id"]
    product_path = task.get("expected_product_path") or task.get("product_path")
    runtime_contract = {
        "task_id": task_id,
        "product_path": product_path,
        "codex_result_path": str(result_path),
        "status_required_on_success": "local_checks_passed",
        "outer_bridge_owns": [
            "host-side final checks",
            "product git commit and push",
            "product GitHub remote verification",
            "ORIS evidence commit and push",
        ],
    }
    return (
        base_prompt
        + "\n\n---\n\n"
        + "# ORIS RUNTIME TASK DESCRIPTOR — AUTHORITATIVE\n\n"
        + "The following runtime descriptor is injected by the host supervised bridge after claiming the queued task. "
        + "It overrides any hardcoded task id or codex_result path that may appear in the reusable prompt above.\n\n"
        + "You MUST write the structured result file exactly to `codex_result_path` below, using exactly this `task_id`. "
        + "Do not write the result to any other task id.\n\n"
        + "```json\n"
        + json.dumps(runtime_contract, ensure_ascii=False, indent=2)
        + "\n```\n\n"
        + "Minimum required success result JSON:\n\n"
        + "```json\n"
        + json.dumps(
            {
                "task_id": task_id,
                "status": "local_checks_passed",
                "product_path": product_path,
                "changed_files": [],
                "check_logs": {},
                "notes": "Local checks passed; outer supervised bridge must finish final verification.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n```\n"
    )


def build_codex_command(task: dict[str, Any], prompt_text: str) -> list[str]:
    codex_bin = safe_path(task.get("codex_bin") or str(DEFAULT_CODEX), [Path("/home/admin")])
    cmd = [
        str(codex_bin),
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        task.get("sandbox", "workspace-write"),
    ]
    for extra_dir in task.get("extra_write_dirs", []):
        cmd.extend(["--add-dir", str(safe_path(extra_dir, [PROJECTS_DIR]))])
    cmd.append(prompt_text)
    return cmd


def invoke_codex(task: dict[str, Any], log_path: Path, result_path: Path) -> int:
    prompt_path = safe_path(task["prompt_path"], [ORIS_DIR, PROJECTS_DIR])
    workdir = safe_path(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])
    base_prompt = prompt_path.read_text(encoding="utf-8")
    prompt_text = build_runtime_prompt(task, base_prompt, result_path)
    cmd = build_codex_command(task, prompt_text)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    with log_path.open("w", encoding="utf-8") as log:
        log.write("===== ORIS supervised bridge v2 Codex phase =====\n")
        log.write(f"task_id={task['task_id']}\n")
        log.write(f"started_at={now_iso()}\n")
        log.write(f"workdir={workdir}\n")
        log.write(f"prompt_path={prompt_path}\n")
        log.write(f"codex_result_path={result_path}\n")
        log.write("command=codex exec --skip-git-repo-check ...\n\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, stdout=log, stderr=subprocess.STDOUT, text=True, check=False)
        log.write(f"\nfinished_at={now_iso()}\nreturn_code={proc.returncode}\n")
    return proc.returncode


def final_check(product_path: Path, task_id: str) -> dict[str, Any]:
    python_bin = select_python(product_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(product_path)
    py_compile_log = LOG_DIR / f"{task_id}_host_py_compile.txt"
    pytest_log = LOG_DIR / f"{task_id}_host_pytest.txt"
    pytest_werror_log = LOG_DIR / f"{task_id}_host_pytest_werror.txt"
    checks = [
        ([python_bin, "-m", "py_compile", "app/main.py"], py_compile_log, env),
        ([python_bin, "-m", "pytest", "-q"], pytest_log, env),
        ([python_bin, "-m", "pytest", "-q", "-W", "error::DeprecationWarning"], pytest_werror_log, env),
    ]
    results = []
    for cmd, log_path, check_env in checks:
        proc = run(cmd, cwd=product_path, log_path=log_path, env=check_env)
        results.append({"cmd": " ".join(cmd), "return_code": proc.returncode, "log": str(log_path)})
    ok = all(item["return_code"] == 0 for item in results)
    return {"ok": ok, "python_bin": python_bin, "results": results}


def commit_push_product(product_path: Path, message: str) -> dict[str, Any]:
    status_before = run(["git", "status", "--short"], cwd=product_path)
    run(["git", "add", "app/main.py", "app/__init__.py"], cwd=product_path)
    staged = run(["git", "diff", "--cached", "--quiet"], cwd=product_path)
    if staged.returncode == 0:
        commit_sha = run(["git", "rev-parse", "HEAD"], cwd=product_path).stdout.strip()
        committed = False
    else:
        commit = run(["git", "commit", "-m", message], cwd=product_path)
        if commit.returncode != 0:
            return {"ok": False, "stage": "commit", "stdout": commit.stdout, "stderr": commit.stderr}
        commit_sha = run(["git", "rev-parse", "HEAD"], cwd=product_path).stdout.strip()
        committed = True
    push = run(["git", "push", "origin", "main"], cwd=product_path)
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=product_path)
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {
        "ok": push.returncode == 0 and remote_sha == commit_sha,
        "committed": committed,
        "commit_sha": commit_sha,
        "remote_sha": remote_sha,
        "status_before": status_before.stdout,
        "push_stdout": push.stdout,
        "push_stderr": push.stderr,
        "remote_stdout": remote.stdout,
        "remote_stderr": remote.stderr,
    }


def commit_push_oris(task: dict[str, Any], run_state: dict[str, Any], product_result: dict[str, Any], checks: dict[str, Any]) -> dict[str, Any]:
    task_id = task["task_id"]
    evidence = {
        "task_id": task_id,
        "status": "completed",
        "updated_at": now_iso(),
        "product_path": run_state["product_path"],
        "product_commit_sha": product_result["commit_sha"],
        "product_remote_sha": product_result["remote_sha"],
        "checks": checks,
        "codex_result_path": run_state["codex_result_path"],
        "codex_log_path": run_state["codex_log_path"],
    }
    write_json(RUN_DIR / f"{task_id}.json", evidence)
    write_json(RUN_DIR / f"{task_id}.supervised_result.json", evidence)
    latest = {
        "task_id": task_id,
        "status": "completed",
        "product_commit_sha": product_result["commit_sha"],
        "product_remote_sha": product_result["remote_sha"],
        "oris_evidence_pending": False,
        "updated_at": now_iso(),
    }
    write_json(LOG_DIR / "latest_task_progress.json", latest)
    (LOG_DIR / "latest_task_progress.md").write_text(
        f"# Latest Dev Employee Task Progress\n\nTask id: `{task_id}`\n\nStatus: completed\n\nProduct commit SHA: `{product_result['commit_sha']}`\n\nRemote verification: `{product_result['remote_sha']}`\n\nORIS evidence pending: `false`\n",
        encoding="utf-8",
    )
    files = [
        f"orchestration/task_runs/{task_id}.json",
        f"orchestration/task_runs/{task_id}.supervised_result.json",
        "logs/dev_employee/latest_task_progress.json",
        "logs/dev_employee/latest_task_progress.md",
    ]
    for result in checks["results"]:
        try:
            files.append(str(Path(result["log"]).relative_to(ORIS_DIR)))
        except ValueError:
            pass
    run(["git", "add", *files], cwd=ORIS_DIR)
    staged = run(["git", "diff", "--cached", "--quiet"], cwd=ORIS_DIR)
    if staged.returncode == 0:
        sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
        committed = False
    else:
        commit = run(["git", "commit", "-m", f"docs(dev-employee): complete supervised task {task_id}"], cwd=ORIS_DIR)
        if commit.returncode != 0:
            return {"ok": False, "stage": "oris_commit", "stdout": commit.stdout, "stderr": commit.stderr}
        sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
        committed = True
    push = run(["git", "push", "origin", "main"], cwd=ORIS_DIR)
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ORIS_DIR)
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {"ok": push.returncode == 0 and remote_sha == sha, "committed": committed, "commit_sha": sha, "remote_sha": remote_sha, "push_stdout": push.stdout, "push_stderr": push.stderr}


def fail_task(task_path: Path, task: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> int:
    task.update({"status": status, "finished_at": now_iso()})
    if extra:
        task.update(extra)
    write_json(RUN_DIR / f"{task['task_id']}.json", task)
    failed_path = task_path.with_suffix(".failed.json")
    write_json(failed_path, task)
    task_path.unlink(missing_ok=True)
    print(f"TASK_FAILED {task['task_id']} {status}")
    return 1


def run_task(task_path: Path) -> int:
    task = read_json(task_path)
    task_id = task["task_id"]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    codex_log = LOG_DIR / f"{task_id}.codex.log"
    result_path = RUN_DIR / f"{task_id}.codex_result.json"

    try:
        task.update({"status": "codex_running", "codex_log_path": str(codex_log), "codex_result_path": str(result_path), "started_at": now_iso()})
        write_json(RUN_DIR / f"{task_id}.json", task)
        rc = invoke_codex(task, codex_log, result_path)
        if rc != 0:
            return fail_task(task_path, task, "codex_failed", {"return_code": rc})
        if not result_path.is_file():
            return fail_task(task_path, task, "blocked_missing_codex_result")
        codex_result = read_json(result_path)
        if codex_result.get("status") != "local_checks_passed":
            return fail_task(task_path, task, "blocked_codex_result_not_passed", {"codex_result": codex_result})
        product_path = safe_path(codex_result["product_path"], [PROJECTS_DIR])
        checks = final_check(product_path, task_id)
        if not checks["ok"]:
            return fail_task(task_path, task, "blocked_host_checks_failed", {"checks": checks})
        product_result = commit_push_product(product_path, task.get("product_commit_message", f"refactor(api): complete supervised task {task_id}"))
        if not product_result.get("ok"):
            return fail_task(task_path, task, "blocked_product_push_failed", {"product_result": product_result})
        run_state = {"product_path": str(product_path), "codex_result_path": str(result_path), "codex_log_path": str(codex_log)}
        oris_result = commit_push_oris(task, run_state, product_result, checks)
        if not oris_result.get("ok"):
            return fail_task(task_path, task, "blocked_oris_push_failed", {"product_result": product_result, "oris_result": oris_result})
        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "finished_at": now_iso()})
        write_json(RUN_DIR / f"{task_id}.json", task)
        done_path = task_path.with_suffix(".done.json")
        write_json(done_path, task)
        task_path.unlink(missing_ok=True)
        print(f"TASK_COMPLETED {task_id} product={product_result['commit_sha']} oris={oris_result['commit_sha']}")
        return 0
    except Exception as exc:
        return fail_task(task_path, task, "bridge_exception", {"last_error": repr(exc)})


def run_once(verbose_idle: bool = False) -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    for item in sorted(QUEUE_DIR.glob("*.queued.json")):
        claimed = claim_task(item)
        if claimed:
            print(f"CLAIMED {claimed}")
            return run_task(claimed)
    if verbose_idle:
        print("NO_QUEUED_TASK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one ORIS supervised bridge queued task")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--verbose-idle", action="store_true", help="print NO_QUEUED_TASK when idle")
    args = parser.parse_args()
    if args.watch:
        while True:
            run_once(verbose_idle=args.verbose_idle)
            time.sleep(args.interval)
    return run_once(verbose_idle=True if args.once else args.verbose_idle)


if __name__ == "__main__":
    raise SystemExit(main())
