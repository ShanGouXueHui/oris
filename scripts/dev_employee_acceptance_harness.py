#!/usr/bin/env python3
"""Reusable ORIS Dev Employee acceptance harness.

Scenario kinds:
- goal_driven: enqueue a normal autonomous development task and wait for evidence.
- repair_seed: seed a controlled failing test, write failure/triage evidence,
  enqueue a repair-from-triage task, and wait for evidence.

Scenario command fields must be argv arrays, not shell strings. This keeps the
harness deterministic and avoids arbitrary shell interpretation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
TRIAGE_DIR = LOG_DIR / "failure_triage"
REPORT_DIR = LOG_DIR / "acceptance_harness"
ENQUEUE_SERVICE = "oris-dev-employee-enqueue.service"
BRIDGE_SERVICE = "oris-dev-employee-bridge.service"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], cwd: Path = ORIS_DIR, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git_status(path: Path, include_untracked: bool = True) -> str:
    cmd = ["git", "status", "--short"]
    if not include_untracked:
        cmd.append("--untracked-files=no")
    return run(cmd, cwd=path).stdout


def service_active(service: str) -> bool:
    return run(["systemctl", "--user", "is-active", service]).stdout.strip() == "active"


def ensure_services() -> None:
    run(["systemctl", "--user", "is-active", ENQUEUE_SERVICE], check=True)
    if not service_active(BRIDGE_SERVICE):
        run(["systemctl", "--user", "restart", BRIDGE_SERVICE], check=True)
        time.sleep(3)
    run(["systemctl", "--user", "is-active", BRIDGE_SERVICE], check=True)


def product_path_from_scenario(scenario: dict[str, Any]) -> Path:
    raw = scenario.get("product_path")
    if not raw:
        raise SystemExit("ERROR: scenario missing product_path")
    path = Path(str(raw)).expanduser().resolve()
    if not str(path).startswith("/home/admin/projects/"):
        raise SystemExit(f"ERROR: product_path outside /home/admin/projects: {path}")
    return path


def require_clean_for_execution(product_path: Path) -> None:
    oris_tracked = git_status(ORIS_DIR, include_untracked=False)
    product_status = git_status(product_path, include_untracked=True)
    if oris_tracked:
        raise SystemExit(f"ERROR: ORIS tracked working tree is not clean:\n{oris_tracked}")
    if product_status:
        raise SystemExit(f"ERROR: product working tree is not clean:\n{product_status}")


def validate_argv(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
        raise SystemExit(f"ERROR: {label} must be a non-empty JSON array of strings")
    return list(value)


def validate_scenario(scenario: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in ["scenario_id", "kind", "product_path", "product_repo"]:
        if not scenario.get(field):
            errors.append(f"missing required field: {field}")
    kind = scenario.get("kind")
    if kind not in {"goal_driven", "repair_seed"}:
        errors.append("kind must be goal_driven or repair_seed")
    if kind == "goal_driven":
        for field in ["task_id", "objective", "commit_message"]:
            if not scenario.get(field):
                errors.append(f"goal_driven scenario missing: {field}")
    if kind == "repair_seed":
        for field in ["failed_task_id", "repair_task_id", "seed_files", "initial_check", "repair_objective", "commit_message"]:
            if not scenario.get(field):
                errors.append(f"repair_seed scenario missing: {field}")
        if scenario.get("initial_check") and not isinstance(scenario["initial_check"], list):
            errors.append("initial_check must be argv array")
    for field in ["expected_checks", "final_checks", "constraints", "notes"]:
        if field in scenario and not isinstance(scenario[field], list):
            errors.append(f"{field} must be a list")
    return errors


def wait_for_task(task_id: str, max_wait_seconds: int) -> dict[str, Any]:
    deadline = time.time() + max_wait_seconds
    last_status_output = ""
    while time.time() < deadline:
        status_proc = run(["python3", "scripts/dev_employee_task_status.py", "--task-id", task_id], cwd=ORIS_DIR)
        last_status_output = status_proc.stdout + status_proc.stderr
        evidence_path = RUN_DIR / f"{task_id}.json"
        if evidence_path.exists():
            try:
                evidence = read_json(evidence_path)
                status = evidence.get("status")
                if status == "completed":
                    return {"completed": True, "status": status, "evidence": evidence, "last_status_output": last_status_output}
                if isinstance(status, str) and (status.startswith("blocked") or status in {"codex_failed", "bridge_exception"}):
                    return {"completed": False, "status": status, "evidence": evidence, "last_status_output": last_status_output}
            except Exception as exc:
                last_status_output += f"\nread evidence error: {exc!r}\n"
        time.sleep(15)
    return {"completed": False, "status": "timeout", "last_status_output": last_status_output}


def run_product_checks(product_path: Path, checks: list[Any]) -> dict[str, Any]:
    results = []
    for index, check in enumerate(checks):
        cmd = validate_argv(check, f"final_checks[{index}]")
        proc = run(cmd, cwd=product_path)
        results.append({"cmd": cmd, "return_code": proc.returncode, "stdout_tail": proc.stdout[-1200:], "stderr_tail": proc.stderr[-1200:]})
    return {"ok": all(item["return_code"] == 0 for item in results), "results": results}


def enqueue_goal_driven(scenario: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3", "scripts/dev_employee_autonomous_enqueue.py",
        "--task-id", scenario["task_id"],
        "--objective", scenario["objective"],
        "--product-path", scenario["product_path"],
        "--product-repo", scenario["product_repo"],
        "--commit-message", scenario["commit_message"],
    ]
    for constraint in scenario.get("constraints", []):
        cmd.extend(["--constraint", str(constraint)])
    for check in scenario.get("expected_checks", []):
        cmd.extend(["--check", " ".join(validate_argv(check, "expected_checks entry"))])
    for note in scenario.get("notes", []):
        cmd.extend(["--note", str(note)])
    return run(cmd, cwd=ORIS_DIR)


def write_seed_files(product_path: Path, scenario: dict[str, Any]) -> list[str]:
    written = []
    for item in scenario.get("seed_files", []):
        rel = item.get("path")
        content = item.get("content")
        if not rel or content is None:
            raise SystemExit("ERROR: seed_files entries require path and content")
        path = (product_path / rel).resolve()
        if product_path.resolve() not in path.parents and path != product_path.resolve():
            raise SystemExit(f"ERROR: seed file outside product path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
        written.append(str(path))
    return written


def run_initial_failure(product_path: Path, scenario: dict[str, Any]) -> tuple[int, Path]:
    log_path = LOG_DIR / f"{scenario['failed_task_id']}_initial_failure.txt"
    cmd = validate_argv(scenario["initial_check"], "initial_check")
    proc = run(cmd, cwd=product_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc.returncode, log_path


def write_failure_and_triage(scenario: dict[str, Any], failure_return_code: int, failure_log: Path) -> tuple[Path, Path]:
    failed_task_id = scenario["failed_task_id"]
    failure_path = RUN_DIR / f"{failed_task_id}.failure_result.json"
    triage_path = TRIAGE_DIR / f"{failed_task_id}.json"
    initial_cmd = validate_argv(scenario["initial_check"], "initial_check")
    failure = {
        "task_id": failed_task_id,
        "status": "blocked_host_checks_failed",
        "updated_at": now_iso(),
        "strict_result_schema": True,
        "task_objective": scenario["repair_objective"],
        "failure_stage": "blocked_host_checks_failed",
        "product_path": scenario["product_path"],
        "codex_result_path": str(RUN_DIR / f"{failed_task_id}.codex_result.json"),
        "codex_log_path": str(LOG_DIR / f"{failed_task_id}.codex.log"),
        "next_recommended_action": scenario["repair_objective"],
        "checks": {"ok": False, "results": [{"cmd": initial_cmd, "return_code": failure_return_code, "log": str(failure_log)}]},
    }
    triage = {
        "task_id": failed_task_id,
        "triaged_at": now_iso(),
        "source_evidence": str(failure_path),
        "status": "blocked_host_checks_failed",
        "strict_result_schema": True,
        "classification": {
            "category": "host_checks_failed",
            "root_cause": scenario.get("root_cause", "Controlled acceptance repair_seed failure."),
            "routine_autonomous_repair_allowed": True,
            "recommended_action": scenario["repair_objective"],
            "repair_scope": scenario.get("repair_scope", "product_or_test_environment"),
            "failed_checks": [{"cmd": initial_cmd, "return_code": failure_return_code, "log": str(failure_log)}],
        },
        "evidence_links": {"codex_log_path": failure["codex_log_path"], "codex_result_path": failure["codex_result_path"]},
        "next_step_contract": {"ask_human_for_routine_decision": False, "rerun_requires_new_task_id": True, "must_preserve_original_failure_evidence": True},
    }
    write_json(failure_path, failure)
    write_json(triage_path, triage)
    return failure_path, triage_path


def enqueue_repair_seed(scenario: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "python3", "scripts/dev_employee_repair_from_triage.py",
        "--failed-task-id", scenario["failed_task_id"],
        "--new-task-id", scenario["repair_task_id"],
        "--product-path", scenario["product_path"],
        "--product-repo", scenario["product_repo"],
        "--enqueue", "--commit-plan",
    ]
    return run(cmd, cwd=ORIS_DIR)


def run_goal_driven_scenario(scenario: dict[str, Any], product_path: Path, max_wait: int) -> dict[str, Any]:
    before = run(["git", "rev-parse", "HEAD"], cwd=product_path, check=True).stdout.strip()
    enqueue_proc = enqueue_goal_driven(scenario)
    wait_result = wait_for_task(scenario["task_id"], max_wait) if enqueue_proc.returncode == 0 else {"completed": False, "status": "enqueue_failed"}
    after = run(["git", "rev-parse", "HEAD"], cwd=product_path).stdout.strip()
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=product_path).stdout.split()[0]
    final_checks = run_product_checks(product_path, scenario.get("final_checks", scenario.get("expected_checks", [])))
    return {"product_head_before": before, "enqueue_return_code": enqueue_proc.returncode, "wait_result": wait_result, "product_head_after": after, "product_remote_after": remote, "final_checks": final_checks, "ok": bool(wait_result.get("completed")) and after == remote and final_checks.get("ok") is True}


def run_repair_seed_scenario(scenario: dict[str, Any], product_path: Path, max_wait: int) -> dict[str, Any]:
    before = run(["git", "rev-parse", "HEAD"], cwd=product_path, check=True).stdout.strip()
    written = write_seed_files(product_path, scenario)
    failure_rc, failure_log = run_initial_failure(product_path, scenario)
    if scenario.get("require_initial_failure", True) and failure_rc == 0:
        raise SystemExit("ERROR: repair_seed initial check unexpectedly passed")
    failure_path, triage_path = write_failure_and_triage(scenario, failure_rc, failure_log)
    enqueue_proc = enqueue_repair_seed(scenario)
    wait_result = wait_for_task(scenario["repair_task_id"], max_wait) if enqueue_proc.returncode == 0 else {"completed": False, "status": "enqueue_failed"}
    after = run(["git", "rev-parse", "HEAD"], cwd=product_path).stdout.strip()
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=product_path).stdout.split()[0]
    final_checks = run_product_checks(product_path, scenario.get("final_checks", scenario.get("expected_checks", [])))
    return {"product_head_before": before, "seed_files_written": written, "initial_failure_return_code": failure_rc, "initial_failure_log": str(failure_log), "failure_path": str(failure_path), "triage_path": str(triage_path), "enqueue_return_code": enqueue_proc.returncode, "wait_result": wait_result, "product_head_after": after, "product_remote_after": remote, "final_checks": final_checks, "ok": bool(wait_result.get("completed")) and after == remote and final_checks.get("ok") is True}


def commit_report(report_path: Path) -> dict[str, Any]:
    run(["git", "fetch", "origin", "main"], cwd=ORIS_DIR)
    run(["git", "pull", "--ff-only", "origin", "main"], cwd=ORIS_DIR)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], cwd=ORIS_DIR, check=True)
    staged = run(["git", "diff", "--cached", "--quiet"], cwd=ORIS_DIR)
    if staged.returncode == 0:
        sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
        return {"ok": True, "committed": False, "commit_sha": sha}
    commit = run(["git", "commit", "-m", "test(dev-employee): record acceptance harness run"], cwd=ORIS_DIR)
    if commit.returncode != 0:
        return {"ok": False, "stage": "git_commit", "stderr": commit.stderr}
    sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
    push = run(["git", "push", "origin", "main"], cwd=ORIS_DIR)
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ORIS_DIR)
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {"ok": push.returncode == 0 and remote_sha == sha, "committed": True, "commit_sha": sha, "remote_sha": remote_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ORIS Dev Employee acceptance scenario")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-wait-seconds", type=int, default=480)
    parser.add_argument("--commit-report", action="store_true")
    args = parser.parse_args()

    scenario_path = Path(args.scenario).expanduser().resolve()
    scenario = read_json(scenario_path)
    errors = validate_scenario(scenario)
    product_path = None if errors else product_path_from_scenario(scenario)
    report: dict[str, Any] = {"started_at": now_iso(), "scenario_path": str(scenario_path), "scenario_id": scenario.get("scenario_id"), "kind": scenario.get("kind"), "validation_errors": errors, "dry_run": args.dry_run}

    try:
        if errors:
            report["ok"] = False
        elif args.dry_run:
            report.update({"ok": True, "product_path": str(product_path), "product_repo": scenario.get("product_repo")})
        else:
            assert product_path is not None
            run(["git", "fetch", "origin", "main"], cwd=ORIS_DIR, check=True)
            run(["git", "reset", "--hard", "origin/main"], cwd=ORIS_DIR, check=True)
            run(["git", "fetch", "origin", "main"], cwd=product_path, check=True)
            run(["git", "reset", "--hard", "origin/main"], cwd=product_path, check=True)
            require_clean_for_execution(product_path)
            ensure_services()
            if scenario["kind"] == "goal_driven":
                report.update(run_goal_driven_scenario(scenario, product_path, args.max_wait_seconds))
            else:
                report.update(run_repair_seed_scenario(scenario, product_path, args.max_wait_seconds))
            report["final_product_status"] = git_status(product_path, include_untracked=True)
            report["final_oris_tracked_status"] = git_status(ORIS_DIR, include_untracked=False)
    except BaseException as exc:
        report["ok"] = False
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        raise
    finally:
        report["finished_at"] = now_iso()
        report_path = REPORT_DIR / f"{scenario.get('scenario_id', 'unknown')}.json"
        write_json(report_path, report)
        if args.commit_report:
            report["report_commit"] = commit_report(report_path)
            write_json(report_path, report)
            commit_report(report_path)
        print(json.dumps({"ok": report.get("ok"), "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
