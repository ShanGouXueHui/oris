#!/usr/bin/env python3
"""Minimal ORIS Dev Employee host-side executor bridge.

This bridge is intentionally narrow. It consumes JSON task descriptors from a
queue directory, invokes the local Codex CLI against a prompt file, persists
logs/state, and never treats chat text as execution evidence.
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


def safe_resolve(path_value: str, allowed_roots: list[Path]) -> Path:
    path = Path(path_value).expanduser().resolve()
    roots = [root.resolve() for root in allowed_roots]
    if not any(path == root or root in path.parents for root in roots):
        raise ValueError(f"path outside allowed roots: {path}")
    return path


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


def build_codex_command(task: dict[str, Any], prompt_text: str) -> list[str]:
    codex_bin = safe_resolve(task.get("codex_bin") or str(DEFAULT_CODEX), [Path("/home/admin")])
    cmd = [
        str(codex_bin),
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        task.get("sandbox", "workspace-write"),
    ]
    for extra_dir in task.get("extra_write_dirs", []):
        safe_dir = safe_resolve(extra_dir, [PROJECTS_DIR])
        cmd.extend(["--add-dir", str(safe_dir)])
    cmd.append(prompt_text)
    return cmd


def run_one(task_path: Path) -> int:
    task = read_json(task_path)
    task_id = task["task_id"]
    prompt_path = safe_resolve(task["prompt_path"], [ORIS_DIR, PROJECTS_DIR])
    workdir = safe_resolve(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])

    if not prompt_path.is_file():
        raise FileNotFoundError(f"prompt file not found: {prompt_path}")
    prompt_text = prompt_path.read_text(encoding="utf-8")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{task_id}.log"
    run_path = RUN_DIR / f"{task_id}.json"

    task.update({
        "status": "running",
        "started_at": task.get("claimed_at") or now_iso(),
        "log_path": str(log_path),
        "run_path": str(run_path),
        "prompt_path": str(prompt_path),
        "workdir": str(workdir),
    })
    write_json(run_path, task)

    cmd = build_codex_command(task, prompt_text)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"===== ORIS dev employee executor =====\n")
        log.write(f"task_id={task_id}\n")
        log.write(f"started_at={now_iso()}\n")
        log.write(f"workdir={workdir}\n")
        log.write(f"prompt_path={prompt_path}\n")
        log.write("command=codex exec --skip-git-repo-check ...\n\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, stdout=log, stderr=subprocess.STDOUT, text=True)
        rc = proc.returncode
        log.write(f"\nfinished_at={now_iso()}\nreturn_code={rc}\n")

    task["finished_at"] = now_iso()
    task["return_code"] = rc
    task["status"] = "codex_completed" if rc == 0 else "codex_failed"
    write_json(run_path, task)

    done_path = task_path.with_suffix(".done.json" if rc == 0 else ".failed.json")
    write_json(done_path, task)
    task_path.unlink(missing_ok=True)
    return rc


def run_pending_once() -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    pending = sorted(QUEUE_DIR.glob("*.queued.json"))
    if not pending:
        print("NO_QUEUED_TASK")
        return 0
    for item in pending:
        claimed = claim_task(item)
        if claimed is None:
            continue
        print(f"CLAIMED {claimed}")
        try:
            return run_one(claimed)
        except Exception as exc:
            task = read_json(claimed) if claimed.exists() else {"task_id": claimed.stem}
            task["status"] = "bridge_failed"
            task["last_error"] = repr(exc)
            task["finished_at"] = now_iso()
            run_path = RUN_DIR / f"{task.get('task_id', claimed.stem)}.json"
            write_json(run_path, task)
            failed = claimed.with_suffix(".failed.json")
            write_json(failed, task)
            claimed.unlink(missing_ok=True)
            print(f"BRIDGE_FAILED {exc!r}")
            return 2
    print("NO_CLAIMABLE_TASK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ORIS Dev Employee queued tasks through Codex CLI")
    parser.add_argument("--once", action="store_true", help="process one queued task and exit")
    parser.add_argument("--watch", action="store_true", help="poll for queued tasks")
    parser.add_argument("--interval", type=int, default=10, help="poll interval in seconds")
    args = parser.parse_args()

    if args.watch:
        while True:
            run_pending_once()
            time.sleep(args.interval)
    return run_pending_once()


if __name__ == "__main__":
    raise SystemExit(main())
