#!/usr/bin/env python3
"""ORIS Dev Employee supervised bridge v3.

v3 keeps the validated v2 delivery/evidence functions, while replacing queue
ownership with the transactional queue kernel:

- atomic exactly-once claim per task;
- explicit worker concurrency slots;
- renewable lease and execution deadline;
- cancellation checks during Codex execution;
- deterministic rollback to a clean product baseline on cancel/timeout;
- no automatic retry after worker loss;
- canonical terminal queue records and append-only lifecycle events.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import dev_employee_supervised_bridge_v2 as v2
from dev_employee_queue_kernel import (
    DEFAULT_KERNEL,
    LeaseMismatch,
    TaskNotFound,
    atomic_write_json,
    default_worker_id,
    now_iso,
    parse_dt,
    read_json,
)
from dev_employee_task_states import classify as classify_task_state

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
QUEUE_DIR = ORIS_DIR / "orchestration/dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration/task_runs"
LOG_DIR = ORIS_DIR / "logs/dev_employee"
WORKER_SLOT_DIR = ORIS_DIR / "run/dev_employee_worker_slots"

WORKER_ID = os.environ.get("ORIS_DEV_EMPLOYEE_WORKER_ID") or default_worker_id()
LEASE_SECONDS = max(15, int(os.environ.get("ORIS_DEV_EMPLOYEE_LEASE_SECONDS", "60")))
HEARTBEAT_SECONDS = max(2, int(os.environ.get("ORIS_DEV_EMPLOYEE_HEARTBEAT_SECONDS", "10")))
EXECUTION_TIMEOUT_SECONDS = max(60, int(os.environ.get("ORIS_DEV_EMPLOYEE_EXECUTION_TIMEOUT_SECONDS", "7200")))
MAX_CONCURRENCY = max(1, int(os.environ.get("ORIS_DEV_EMPLOYEE_MAX_CONCURRENCY", "1")))


def current_time() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def write_runtime_state(task: dict[str, Any]) -> None:
    atomic_write_json(RUN_DIR / f"{task['task_id']}.json", task)


def heartbeat(task: dict[str, Any], phase: str) -> dict[str, Any]:
    result = DEFAULT_KERNEL.heartbeat(
        task["task_id"],
        task["lease_token"],
        phase=phase,
        lease_seconds=LEASE_SECONDS,
    )
    task.update(
        {
            "phase": phase,
            "heartbeat_at": result["task"].get("heartbeat_at"),
            "lease_expires_at": result["task"].get("lease_expires_at"),
        }
    )
    return result


def acquire_worker_slot() -> tuple[int, Path] | None:
    WORKER_SLOT_DIR.mkdir(parents=True, exist_ok=True)
    for slot in range(MAX_CONCURRENCY):
        path = WORKER_SLOT_DIR / f"slot-{slot}.lock"
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            continue
        payload = {
            "slot": slot,
            "worker_id": WORKER_ID,
            "worker_pid": os.getpid(),
            "acquired_at": now_iso(),
            "max_concurrency": MAX_CONCURRENCY,
        }
        os.ftruncate(fd, 0)
        os.write(fd, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        os.fsync(fd)
        return fd, path
    return None


def prepare_product_baseline(task: dict[str, Any]) -> dict[str, Any]:
    product_value = task.get("expected_product_path") or task.get("product_path")
    if not product_value:
        return {"ok": False, "failure_code": "product_path_missing"}
    try:
        product_path = v2.safe_path(str(product_value), [PROJECTS_DIR])
    except Exception as exc:
        return {"ok": False, "failure_code": "product_path_invalid", "error": repr(exc)}
    status = v2.run(["git", "status", "--porcelain"], cwd=product_path)
    if status.returncode != 0:
        return {
            "ok": False,
            "failure_code": "product_git_status_failed",
            "stdout": status.stdout,
            "stderr": status.stderr,
        }
    if status.stdout.strip():
        return {
            "ok": False,
            "failure_code": "product_worktree_not_clean",
            "status_porcelain": status.stdout,
        }
    head = v2.run(["git", "rev-parse", "HEAD"], cwd=product_path)
    remote = v2.run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=product_path)
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    head_sha = head.stdout.strip() if head.returncode == 0 else None
    if not head_sha or not remote_sha or head_sha != remote_sha:
        return {
            "ok": False,
            "failure_code": "product_baseline_remote_mismatch",
            "head_sha": head_sha,
            "remote_sha": remote_sha,
            "head_stderr": head.stderr,
            "remote_stderr": remote.stderr,
        }
    baseline = {
        "ok": True,
        "product_path": str(product_path),
        "head_sha": head_sha,
        "remote_sha": remote_sha,
        "captured_at": now_iso(),
        "worktree_clean": True,
    }
    task["product_baseline"] = baseline
    return baseline


def rollback_product(task: dict[str, Any], reason: str) -> dict[str, Any]:
    baseline = task.get("product_baseline") if isinstance(task.get("product_baseline"), dict) else {}
    product_path_value = baseline.get("product_path")
    baseline_sha = baseline.get("head_sha")
    log_path = LOG_DIR / f"{task['task_id']}_product_rollback.txt"
    if not product_path_value or not baseline_sha:
        result = {"ok": False, "failure_code": "rollback_baseline_missing", "reason": reason}
        log_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
    product_path = Path(str(product_path_value)).resolve()
    commands = [
        ["git", "reset", "--hard", str(baseline_sha)],
        ["git", "clean", "-fd"],
        ["git", "status", "--porcelain"],
        ["git", "rev-parse", "HEAD"],
    ]
    results: list[dict[str, Any]] = []
    for command in commands:
        completed = v2.run(command, cwd=product_path)
        results.append(
            {
                "command": " ".join(command),
                "return_code": completed.returncode,
                "stdout": completed.stdout[-4000:],
                "stderr": completed.stderr[-4000:],
            }
        )
    status_output = results[2]["stdout"].strip()
    final_head = results[3]["stdout"].strip()
    ok = all(item["return_code"] == 0 for item in results) and not status_output and final_head == baseline_sha
    payload = {
        "ok": ok,
        "reason": reason,
        "baseline_sha": baseline_sha,
        "final_head": final_head,
        "worktree_clean": not status_output,
        "commands": results,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["log"] = str(log_path)
    DEFAULT_KERNEL.append_event(
        task["task_id"],
        "product_rollback",
        status="cancelled" if reason == "cancel_requested" else "failed",
        actor=WORKER_ID,
        details={"ok": ok, "reason": reason, "baseline_sha": baseline_sha, "final_head": final_head},
    )
    return payload


def stop_process(process: subprocess.Popen[str], log: Any, reason: str) -> None:
    log.write(f"\nexecutor_stop_reason={reason}\n")
    log.flush()
    process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def invoke_codex(task: dict[str, Any], log_path: Path, result_path: Path) -> int:
    prompt_path = v2.safe_path(task["prompt_path"], [ORIS_DIR, PROJECTS_DIR])
    workdir = v2.safe_path(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])
    base_prompt = prompt_path.read_text(encoding="utf-8")
    prompt_text = v2.build_runtime_prompt(task, base_prompt, result_path)
    command = v2.build_codex_command(task, prompt_text)
    environment = os.environ.copy()
    environment.setdefault("PYTHONUNBUFFERED", "1")
    deadline = parse_dt(task.get("execution_deadline_at"))

    with log_path.open("w", encoding="utf-8") as log:
        log.write("===== ORIS supervised bridge v3 Codex phase =====\n")
        log.write(f"task_id={task['task_id']}\n")
        log.write(f"worker_id={WORKER_ID}\n")
        log.write(f"started_at={now_iso()}\n")
        log.write(f"workdir={workdir}\n")
        log.write(f"prompt_path={prompt_path}\n")
        log.write(f"codex_result_path={result_path}\n")
        log.write(f"execution_deadline_at={task.get('execution_deadline_at')}\n")
        log.write("command=codex exec --skip-git-repo-check ...\n\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=str(workdir),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        task["executor_pid"] = process.pid
        next_heartbeat = 0.0
        while True:
            return_code = process.poll()
            if return_code is not None:
                log.write(f"\nfinished_at={now_iso()}\nreturn_code={return_code}\n")
                return return_code
            monotonic = time.monotonic()
            if monotonic >= next_heartbeat:
                lease = heartbeat(task, "executing")
                write_runtime_state(task)
                if lease.get("cancel_requested"):
                    task["executor_stop_reason"] = "cancel_requested"
                    stop_process(process, log, "cancel_requested")
                    return 130
                if deadline and current_time() >= deadline:
                    task["executor_stop_reason"] = "execution_timeout"
                    stop_process(process, log, "execution_timeout")
                    return 124
                next_heartbeat = monotonic + HEARTBEAT_SECONDS
            time.sleep(1)


def fail_task(
    task_path: Path,
    task: dict[str, Any],
    status: str,
    extra: dict[str, Any] | None = None,
    *,
    run_triage: bool = True,
) -> int:
    state = classify_task_state(status, extra or {})
    task.update(
        {
            "status": status,
            "canonical_status": state["canonical_status"],
            "terminal": True,
            "finished_at": now_iso(),
        }
    )
    if extra:
        task.update(extra)
    evidence_result = v2.commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    task["failure_evidence_index_result"] = v2.record_evidence_commit_index(task["task_id"], status, evidence_result)
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    if run_triage and state["canonical_status"] != "cancelled":
        triage = v2.run_failure_triage(task["task_id"])
        task["failure_triage_result"] = triage
        if not triage.get("ok"):
            task["failure_triage_failed"] = True
    suffix = "cancelled" if state["canonical_status"] == "cancelled" else "failed"
    atomic_write_json(task_path, task)
    target = DEFAULT_KERNEL.task_path(task["task_id"], suffix)
    os.replace(task_path, target)
    try:
        DEFAULT_KERNEL.release_claim(task["task_id"], task["lease_token"], terminal_status=state["canonical_status"])
    except (LeaseMismatch, TaskNotFound):
        pass
    print(f"TASK_TERMINAL {task['task_id']} {state['canonical_status']}")
    return 1 if state["canonical_status"] != "cancelled" else 0


def cancel_with_rollback(task_path: Path, task: dict[str, Any], reason: str) -> int:
    rollback = rollback_product(task, reason)
    return fail_task(
        task_path,
        task,
        "cancelled" if reason == "cancel_requested" else "failed",
        {
            "failure_code": "user_cancelled" if reason == "cancel_requested" else reason,
            "rollback_result": rollback,
        },
        run_triage=reason != "cancel_requested",
    )


def cancellation_requested(task: dict[str, Any], phase: str) -> bool:
    lease = heartbeat(task, phase)
    write_runtime_state(task)
    return bool(lease.get("cancel_requested"))


def run_task(task_path: Path) -> int:
    task = read_json(task_path)
    task_id = task["task_id"]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    codex_log = LOG_DIR / f"{task_id}.codex.log"
    result_path = RUN_DIR / f"{task_id}.codex_result.json"

    try:
        heartbeat(task, "claimed")
        task.update(
            {
                "status": "preflight",
                "codex_log_path": str(codex_log),
                "codex_result_path": str(result_path),
                "codex_auth_preflight_log_path": str(LOG_DIR / f"{task_id}.codex_auth_preflight.json"),
                "started_at": task.get("started_at") or now_iso(),
            }
        )
        write_runtime_state(task)

        codex_bin = v2.safe_path(task.get("codex_bin") or str(v2.DEFAULT_CODEX), [Path("/home/admin")])
        workdir = v2.safe_path(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])
        executor_preflight = v2.run_codex_auth_preflight(
            codex_bin,
            workdir,
            log_path=Path(task["codex_auth_preflight_log_path"]),
        )
        if not executor_preflight.get("ok"):
            return fail_task(
                task_path,
                task,
                "preflight_failed",
                {
                    "failure_code": executor_preflight.get("failure_code") or "codex_preflight_failed",
                    "executor_preflight": executor_preflight,
                },
            )

        baseline = prepare_product_baseline(task)
        if not baseline.get("ok"):
            return fail_task(
                task_path,
                task,
                "preflight_failed",
                {
                    "failure_code": baseline.get("failure_code") or "product_preflight_failed",
                    "product_preflight": baseline,
                },
            )
        task["executor_preflight"] = {
            key: executor_preflight.get(key)
            for key in ["ok", "status", "executor_path", "executor_version", "linux_user", "uid", "home", "workdir"]
        }
        write_runtime_state(task)

        if cancellation_requested(task, "planning"):
            return cancel_with_rollback(task_path, task, "cancel_requested")

        task["status"] = "codex_running"
        write_runtime_state(task)
        return_code = invoke_codex(task, codex_log, result_path)
        if return_code == 130 or task.get("executor_stop_reason") == "cancel_requested":
            return cancel_with_rollback(task_path, task, "cancel_requested")
        if return_code == 124 or task.get("executor_stop_reason") == "execution_timeout":
            return cancel_with_rollback(task_path, task, "execution_timeout")
        if return_code != 0:
            codex_output = codex_log.read_text(encoding="utf-8", errors="replace") if codex_log.exists() else ""
            return cancel_with_rollback(task_path, task, v2.classify_codex_failure(codex_output, return_code))

        if not result_path.is_file():
            return cancel_with_rollback(task_path, task, "blocked_missing_codex_result")
        codex_result = read_json(result_path)
        schema_errors = v2.validate_codex_result(task, codex_result)
        if schema_errors:
            rollback = rollback_product(task, "blocked_result_schema_invalid")
            return fail_task(task_path, task, "blocked_result_schema_invalid", {"schema_errors": schema_errors, "codex_result": codex_result, "rollback_result": rollback})
        skill_errors = v2.validate_skill_resolution_evidence(task, codex_result)
        if skill_errors:
            rollback = rollback_product(task, "blocked_skill_resolution_invalid")
            return fail_task(task_path, task, "blocked_skill_resolution_invalid", {"skill_resolution_errors": skill_errors, "codex_result": codex_result, "rollback_result": rollback})
        if codex_result.get("status") != "local_checks_passed":
            rollback = rollback_product(task, "blocked_codex_result_not_passed")
            return fail_task(task_path, task, "blocked_codex_result_not_passed", {"codex_result": codex_result, "rollback_result": rollback})

        product_path = v2.safe_path(codex_result["product_path"], [PROJECTS_DIR])
        if str(product_path) != str(task["product_baseline"]["product_path"]):
            rollback = rollback_product(task, "product_path_changed_by_executor")
            return fail_task(task_path, task, "blocked", {"failure_code": "product_path_changed_by_executor", "rollback_result": rollback})

        checks = v2.final_check(product_path, task_id)
        if not checks["ok"]:
            rollback = rollback_product(task, "local_checks_failed")
            return fail_task(task_path, task, "local_checks_failed", {"checks": checks, "rollback_result": rollback})

        if cancellation_requested(task, "local_checks_passed"):
            return cancel_with_rollback(task_path, task, "cancel_requested")

        heartbeat(task, "committing")
        write_runtime_state(task)
        product_result = v2.commit_push_product(
            product_path,
            task.get("product_commit_message", f"refactor(api): complete supervised task {task_id}"),
        )
        if not product_result.get("ok"):
            return fail_task(task_path, task, "remote_verification_failed", {"product_result": product_result})

        heartbeat(task, "pushing")
        write_runtime_state(task)
        run_state = {
            "product_path": str(product_path),
            "codex_result_path": str(result_path),
            "codex_log_path": str(codex_log),
        }
        oris_result = v2.commit_push_oris(task, run_state, product_result, checks, codex_result)
        if not oris_result.get("ok"):
            return fail_task(
                task_path,
                task,
                "remote_verification_failed",
                {"product_result": product_result, "oris_result": oris_result},
            )
        evidence_index_result = v2.record_evidence_commit_index(task_id, "completed", oris_result, product_result)
        task.update(
            {
                "status": "completed",
                "canonical_status": "completed",
                "terminal": True,
                "product_result": product_result,
                "oris_result": oris_result,
                "oris_evidence_index_result": evidence_index_result,
                "finished_at": now_iso(),
            }
        )
        atomic_write_json(task_path, task)
        done_path = DEFAULT_KERNEL.task_path(task_id, "done")
        os.replace(task_path, done_path)
        DEFAULT_KERNEL.release_claim(task_id, task["lease_token"], terminal_status="completed")
        print(f"TASK_COMPLETED {task_id} product={product_result['commit_sha']} oris={oris_result['commit_sha']}")
        return 0
    except Exception as exc:
        try:
            phase = str(task.get("phase") or "")
            extra: dict[str, Any] = {"last_error": repr(exc), "failure_code": "bridge_exception"}
            if phase not in {"committing", "pushing"} and task.get("product_baseline"):
                extra["rollback_result"] = rollback_product(task, "bridge_exception")
            return fail_task(task_path, task, "failed", extra)
        except Exception as terminal_exc:
            print(f"TASK_FATAL {task_id} primary={exc!r} terminal={terminal_exc!r}")
            return 1


def run_once(verbose_idle: bool = False) -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    for item in sorted(QUEUE_DIR.glob("*.queued.json")):
        try:
            descriptor = read_json(item)
        except Exception:
            continue
        claim = DEFAULT_KERNEL.claim(
            item,
            worker_id=WORKER_ID,
            lease_seconds=int(descriptor.get("lease_seconds") or LEASE_SECONDS),
            execution_timeout_seconds=int(descriptor.get("execution_timeout_seconds") or EXECUTION_TIMEOUT_SECONDS),
        )
        if claim:
            print(f"CLAIMED {claim.path} worker={WORKER_ID}")
            return run_task(claim.path)
    if verbose_idle:
        print("NO_QUEUED_TASK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the leased ORIS supervised bridge v3")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--verbose-idle", action="store_true")
    args = parser.parse_args()

    slot = acquire_worker_slot()
    if slot is None:
        print(f"NO_WORKER_SLOT max_concurrency={MAX_CONCURRENCY}")
        return 0
    slot_fd, slot_path = slot
    print(f"WORKER_SLOT_ACQUIRED path={slot_path} worker={WORKER_ID}")
    try:
        if args.watch:
            while True:
                run_once(verbose_idle=args.verbose_idle)
                time.sleep(max(1, args.interval))
        return run_once(verbose_idle=True if args.once else args.verbose_idle)
    finally:
        try:
            fcntl.flock(slot_fd, fcntl.LOCK_UN)
        finally:
            os.close(slot_fd)


if __name__ == "__main__":
    raise SystemExit(main())
