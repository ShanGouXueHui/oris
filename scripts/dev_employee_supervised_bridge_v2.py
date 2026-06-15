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
- For autonomous tasks with strict_result_schema=true, validate the Codex result
  contract and skill resolver evidence before host-side checks, Git operations,
  or evidence completion.
- Failure paths must also persist GitHub-verifiable ORIS evidence whenever
  committing/pushing the ORIS repository is still possible.
- Failure paths should also run deterministic failure triage so the next repair
  loop can proceed without asking the human for routine engineering decisions.
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

from dev_employee_codex_auth_preflight import classify_codex_failure, run_codex_auth_preflight
from dev_employee_result_validator import validate_result
from dev_employee_task_states import classify as classify_task_state

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
SKILL_RESOLUTION_DIR = LOG_DIR / "skill_resolution"
EVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / "evidence_commit_index"
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
    claimed = QUEUE_DIR / f"{task['task_id']}.running.json"
    try:
        path.rename(claimed)
    except FileNotFoundError:
        return None
    task["status"] = "running"
    task["claimed_at"] = now_iso()
    write_json(claimed, task)
    return claimed


def strict_result_schema(task: dict[str, Any]) -> bool:
    value = task.get("strict_result_schema")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return False


def minimum_result_payload(task: dict[str, Any], product_path: str | None, strict: bool) -> dict[str, Any]:
    task_id = task["task_id"]
    if not strict:
        return {
            "task_id": task_id,
            "status": "local_checks_passed",
            "product_path": product_path,
            "changed_files": [],
            "check_logs": {},
            "notes": "Local checks passed; outer supervised bridge must finish final verification.",
        }
    return {
        "task_id": task_id,
        "status": "local_checks_passed",
        "product_path": product_path,
        "plan": ["Inspect durable context", "Resolve capabilities", "Design minimal change", "Implement", "Run checks", "Repair failures if any"],
        "design_summary": "Summarize the selected design and why it satisfies the objective.",
        "skill_resolution": {
            "needed": [],
            "used_existing": [],
            "downloaded_quarantine": [],
            "blocked": [],
        },
        "changed_files": [],
        "check_logs": {},
        "iteration_summary": [{"attempt": 1, "result": "local checks passed"}],
        "blockers": [],
        "notes": "Local checks passed; outer supervised bridge must finish final verification.",
    }


def build_runtime_prompt(task: dict[str, Any], base_prompt: str, result_path: Path) -> str:
    task_id = task["task_id"]
    product_path = task.get("expected_product_path") or task.get("product_path")
    strict = strict_result_schema(task)
    runtime_contract = {
        "task_id": task_id,
        "product_path": product_path,
        "codex_result_path": str(result_path),
        "strict_result_schema": strict,
        "task_objective": task.get("task_objective"),
        "constraints": task.get("constraints", []),
        "expected_checks": task.get("expected_checks", []),
        "skill_resolver_report_json": str(SKILL_RESOLUTION_DIR / f"{task_id}.json"),
        "skill_resolver_report_markdown": str(SKILL_RESOLUTION_DIR / f"{task_id}.md"),
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
        + "If `strict_result_schema` is true, the result JSON must include the full autonomous evidence fields: "
        + "plan, design_summary, skill_resolution, changed_files, check_logs, iteration_summary, blockers, and notes. "
        + "You must also run the ORIS skill resolver first and copy its `skill_resolution` object exactly into the final result JSON.\n\n"
        + "```json\n"
        + json.dumps(runtime_contract, ensure_ascii=False, indent=2)
        + "\n```\n\n"
        + "Minimum required success result JSON:\n\n"
        + "```json\n"
        + json.dumps(minimum_result_payload(task, product_path, strict), ensure_ascii=False, indent=2)
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
        log.write(f"strict_result_schema={strict_result_schema(task)}\n")
        log.write("command=codex exec --skip-git-repo-check ...\n\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, stdout=log, stderr=subprocess.STDOUT, text=True, check=False)
        log.write(f"\nfinished_at={now_iso()}\nreturn_code={proc.returncode}\n")
    return proc.returncode


def validate_codex_result(task: dict[str, Any], codex_result: dict[str, Any]) -> list[str]:
    return validate_result(
        codex_result,
        expected_task_id=task["task_id"],
        strict=strict_result_schema(task),
    )


def validate_skill_resolution_evidence(task: dict[str, Any], codex_result: dict[str, Any]) -> list[str]:
    if not strict_result_schema(task):
        return []
    task_id = task["task_id"]
    report_path = SKILL_RESOLUTION_DIR / f"{task_id}.json"
    errors: list[str] = []
    if not report_path.is_file():
        return [f"missing skill resolver report: {report_path}"]
    try:
        report = read_json(report_path)
    except Exception as exc:
        return [f"unable to read skill resolver report {report_path}: {exc!r}"]
    report_resolution = report.get("skill_resolution")
    result_resolution = codex_result.get("skill_resolution")
    if not isinstance(report_resolution, dict):
        errors.append("skill resolver report missing object field: skill_resolution")
    if not isinstance(result_resolution, dict):
        errors.append("codex result missing object field: skill_resolution")
    if isinstance(report_resolution, dict) and isinstance(result_resolution, dict) and report_resolution != result_resolution:
        errors.append("codex result skill_resolution does not match skill resolver report")
    if report.get("task_id") != task_id:
        errors.append(f"skill resolver report task_id mismatch: {report.get('task_id')!r}")
    return errors


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
    run(["git", "add", "app/main.py", "app/__init__.py", "tests"], cwd=product_path)
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


def autonomous_summary(codex_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "plan": codex_result.get("plan"),
        "design_summary": codex_result.get("design_summary"),
        "skill_resolution": codex_result.get("skill_resolution"),
        "changed_files": codex_result.get("changed_files"),
        "iteration_summary": codex_result.get("iteration_summary"),
        "blockers": codex_result.get("blockers"),
        "notes": codex_result.get("notes"),
    }


def existing_relative(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return str(path.relative_to(ORIS_DIR))
    except ValueError:
        return None


def add_existing(files: list[str], path: Path) -> None:
    rel = existing_relative(path)
    if rel and rel not in files:
        files.append(rel)


def collect_task_log_files(task_id: str) -> list[str]:
    files: list[str] = []
    if LOG_DIR.exists():
        for path in sorted(LOG_DIR.glob(f"{task_id}*")):
            if path.is_file():
                add_existing(files, path)
    return files


def commit_files(files: list[str], message: str) -> dict[str, Any]:
    unique_files = list(dict.fromkeys(files))
    if not unique_files:
        return {"ok": False, "stage": "git_add", "error": "no files to commit"}
    add = run(["git", "add", *unique_files], cwd=ORIS_DIR)
    if add.returncode != 0:
        return {"ok": False, "stage": "git_add", "stdout": add.stdout, "stderr": add.stderr, "files": unique_files}
    staged = run(["git", "diff", "--cached", "--quiet"], cwd=ORIS_DIR)
    if staged.returncode == 0:
        sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
        committed = False
    else:
        commit = run(["git", "commit", "-m", message], cwd=ORIS_DIR)
        if commit.returncode != 0:
            return {"ok": False, "stage": "oris_commit", "stdout": commit.stdout, "stderr": commit.stderr, "files": unique_files}
        sha = run(["git", "rev-parse", "HEAD"], cwd=ORIS_DIR).stdout.strip()
        committed = True
    push = run(["git", "push", "origin", "main"], cwd=ORIS_DIR)
    remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=ORIS_DIR)
    remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else None
    return {
        "ok": push.returncode == 0 and remote_sha == sha,
        "committed": committed,
        "commit_sha": sha,
        "remote_sha": remote_sha,
        "push_stdout": push.stdout,
        "push_stderr": push.stderr,
        "files": unique_files,
    }


def commit_push_oris(
    task: dict[str, Any],
    run_state: dict[str, Any],
    product_result: dict[str, Any],
    checks: dict[str, Any],
    codex_result: dict[str, Any],
) -> dict[str, Any]:
    task_id = task["task_id"]
    skill_json_path = SKILL_RESOLUTION_DIR / f"{task_id}.json"
    skill_md_path = SKILL_RESOLUTION_DIR / f"{task_id}.md"
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
        "strict_result_schema": strict_result_schema(task),
        "task_objective": task.get("task_objective"),
        "skill_resolver_report_json": str(skill_json_path) if skill_json_path.exists() else None,
        "skill_resolver_report_markdown": str(skill_md_path) if skill_md_path.exists() else None,
        "autonomous_result": autonomous_summary(codex_result),
    }
    write_json(RUN_DIR / f"{task_id}.json", evidence)
    write_json(RUN_DIR / f"{task_id}.supervised_result.json", evidence)
    latest = {
        "task_id": task_id,
        "status": "completed",
        "product_commit_sha": product_result["commit_sha"],
        "product_remote_sha": product_result["remote_sha"],
        "oris_evidence_pending": False,
        "strict_result_schema": strict_result_schema(task),
        "updated_at": now_iso(),
    }
    write_json(LOG_DIR / "latest_task_progress.json", latest)
    (LOG_DIR / "latest_task_progress.md").write_text(
        f"# Latest Dev Employee Task Progress\n\nTask id: `{task_id}`\n\nStatus: completed\n\nProduct commit SHA: `{product_result['commit_sha']}`\n\nRemote verification: `{product_result['remote_sha']}`\n\nStrict result schema: `{strict_result_schema(task)}`\n\nORIS evidence pending: `false`\n",
        encoding="utf-8",
    )
    files = [
        f"orchestration/task_runs/{task_id}.json",
        f"orchestration/task_runs/{task_id}.supervised_result.json",
        "logs/dev_employee/latest_task_progress.json",
        "logs/dev_employee/latest_task_progress.md",
    ]
    for path in [skill_json_path, skill_md_path]:
        add_existing(files, path)
    for result in checks["results"]:
        add_existing(files, Path(result["log"]))
    return commit_files(files, f"docs(dev-employee): complete supervised task {task_id}")


def record_evidence_commit_index(
    task_id: str,
    status: str,
    evidence_result: dict[str, Any],
    product_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not evidence_result.get("commit_sha"):
        return {"ok": False, "stage": "missing_evidence_commit_sha", "evidence_result": evidence_result}
    index = {
        "task_id": task_id,
        "status": status,
        "indexed_at": now_iso(),
        "oris_evidence_commit_sha": evidence_result.get("commit_sha"),
        "oris_evidence_remote_sha": evidence_result.get("remote_sha"),
        "oris_evidence_files": evidence_result.get("files", []),
        "product_commit_sha": product_result.get("commit_sha") if product_result else None,
        "product_remote_sha": product_result.get("remote_sha") if product_result else None,
    }
    index_path = EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"
    write_json(index_path, index)
    return commit_files(
        [f"logs/dev_employee/evidence_commit_index/{task_id}.json"],
        f"docs(dev-employee): index evidence commit {task_id}",
    )


def next_recommended_action(status: str, failure_code: str | None = None) -> str:
    if failure_code == "codex_authentication":
        return "Reauthenticate Codex as Linux user admin, verify non-interactive and bridge-context preflight, then rerun with a new task id."
    if status in {"blocked_result_schema_invalid", "blocked_skill_resolution_invalid"}:
        return "Inspect GitHub failure evidence and Codex log; update autonomous prompt, resolver, or bridge enforcement, then rerun with a new task id."
    if status in {"blocked_host_checks_failed", "local_checks_failed"}:
        return "Inspect host check logs from GitHub evidence; fix product implementation or tests, then rerun with a new task id."
    if status in {"codex_failed", "failed", "preflight_failed"}:
        return "Inspect executor preflight and Codex logs; repair authentication, tooling, or resource issue, then rerun with a new task id."
    if status in {"blocked_product_push_failed", "blocked_oris_push_failed", "remote_verification_failed"}:
        return "Inspect Git push evidence and repository state; resolve Git synchronization or permissions issue, then rerun or resume safely."
    return "Inspect failure details and available logs; apply the smallest safe platform or product fix, then rerun with a new task id."


def commit_push_oris_failure(task: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    task_id = task["task_id"]
    skill_json_path = SKILL_RESOLUTION_DIR / f"{task_id}.json"
    skill_md_path = SKILL_RESOLUTION_DIR / f"{task_id}.md"
    state = classify_task_state(status, extra or {})
    failure_code = state.get("failure_code")
    evidence = {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": failure_code,
        "updated_at": now_iso(),
        "strict_result_schema": strict_result_schema(task),
        "task_objective": task.get("task_objective"),
        "failure_stage": status,
        "failure_details": extra or {},
        "codex_result_path": task.get("codex_result_path"),
        "codex_log_path": task.get("codex_log_path"),
        "skill_resolver_report_json": str(skill_json_path) if skill_json_path.exists() else None,
        "skill_resolver_report_markdown": str(skill_md_path) if skill_md_path.exists() else None,
        "next_recommended_action": next_recommended_action(status, failure_code),
    }
    if extra:
        for optional_key in ["checks", "product_result", "oris_result", "codex_result", "schema_errors", "skill_resolution_errors", "return_code", "last_error", "failure_code", "legacy_status", "executor_preflight", "codex_auth_preflight_log_path"]:
            if optional_key in extra:
                evidence[optional_key] = extra[optional_key]
    write_json(RUN_DIR / f"{task_id}.json", evidence)
    write_json(RUN_DIR / f"{task_id}.failure_result.json", evidence)
    latest = {
        "task_id": task_id,
        "status": status,
        "canonical_status": state["canonical_status"],
        "terminal": state["terminal"],
        "failure_code": failure_code,
        "oris_evidence_pending": False,
        "strict_result_schema": strict_result_schema(task),
        "updated_at": now_iso(),
        "next_recommended_action": evidence["next_recommended_action"],
    }
    write_json(LOG_DIR / "latest_task_progress.json", latest)
    (LOG_DIR / "latest_task_progress.md").write_text(
        f"# Latest Dev Employee Task Progress\n\nTask id: `{task_id}`\n\nStatus: {status}\n\nStrict result schema: `{strict_result_schema(task)}`\n\nORIS evidence pending: `false`\n\nNext recommended action: {evidence['next_recommended_action']}\n",
        encoding="utf-8",
    )
    files = [
        f"orchestration/task_runs/{task_id}.json",
        f"orchestration/task_runs/{task_id}.failure_result.json",
        "logs/dev_employee/latest_task_progress.json",
        "logs/dev_employee/latest_task_progress.md",
    ]
    for path in [skill_json_path, skill_md_path]:
        add_existing(files, path)
    for rel in collect_task_log_files(task_id):
        if rel not in files:
            files.append(rel)
    if extra and isinstance(extra.get("checks"), dict):
        for result in extra["checks"].get("results", []):
            if isinstance(result, dict) and result.get("log"):
                add_existing(files, Path(result["log"]))
    return commit_files(files, f"docs(dev-employee): record failed supervised task {task_id}")


def run_failure_triage(task_id: str) -> dict[str, Any]:
    script = ORIS_DIR / "scripts" / "dev_employee_failure_triage.py"
    log_path = LOG_DIR / f"{task_id}_failure_triage.txt"
    if not script.exists():
        return {"ok": False, "stage": "triage_script_missing", "script": str(script)}
    proc = run(["python3", str(script), "--task-id", task_id, "--commit"], cwd=ORIS_DIR, log_path=log_path)
    return {
        "ok": proc.returncode == 0,
        "return_code": proc.returncode,
        "log": str(log_path),
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def fail_task(task_path: Path, task: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> int:
    task.update({"status": status, "finished_at": now_iso()})
    if extra:
        task.update(extra)
    evidence_result = commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    evidence_index_result = record_evidence_commit_index(task["task_id"], status, evidence_result)
    task["failure_evidence_index_result"] = evidence_index_result
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    triage_result = run_failure_triage(task["task_id"])
    task["failure_triage_result"] = triage_result
    if not triage_result.get("ok"):
        task["failure_triage_failed"] = True
    # Do not rewrite orchestration/task_runs/<task_id>.json after failure evidence
    # and triage commits; keep richer terminal runtime state only in the queue file.
    failed_path = QUEUE_DIR / f"{task['task_id']}.failed.json"
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
        codex_bin = safe_path(task.get("codex_bin") or str(DEFAULT_CODEX), [Path("/home/admin")])
        workdir = safe_path(task.get("workdir", str(PROJECTS_DIR)), [PROJECTS_DIR])
        preflight_log = LOG_DIR / f"{task_id}.codex_auth_preflight.json"
        task.update({
            "status": "preflight",
            "codex_log_path": str(codex_log),
            "codex_result_path": str(result_path),
            "codex_auth_preflight_log_path": str(preflight_log),
            "started_at": now_iso(),
        })
        write_json(RUN_DIR / f"{task_id}.json", task)
        executor_preflight = run_codex_auth_preflight(
            codex_bin,
            workdir,
            log_path=preflight_log,
        )
        if not executor_preflight.get("ok"):
            return fail_task(
                task_path,
                task,
                "preflight_failed",
                {
                    "failure_code": executor_preflight.get("failure_code") or "codex_preflight_failed",
                    "executor_preflight": executor_preflight,
                    "codex_auth_preflight_log_path": str(preflight_log),
                },
            )
        task["status"] = "codex_running"
        task["executor_preflight"] = {
            key: executor_preflight.get(key)
            for key in ["ok", "status", "executor_path", "executor_version", "linux_user", "uid", "home", "workdir"]
        }
        write_json(RUN_DIR / f"{task_id}.json", task)
        rc = invoke_codex(task, codex_log, result_path)
        if rc != 0:
            codex_output = codex_log.read_text(encoding="utf-8", errors="replace") if codex_log.exists() else ""
            failure_code = classify_codex_failure(codex_output, rc)
            return fail_task(
                task_path,
                task,
                "failed",
                {
                    "return_code": rc,
                    "failure_code": failure_code,
                    "legacy_status": "codex_failed",
                },
            )
        if not result_path.is_file():
            return fail_task(task_path, task, "blocked_missing_codex_result")
        codex_result = read_json(result_path)
        schema_errors = validate_codex_result(task, codex_result)
        if schema_errors:
            return fail_task(
                task_path,
                task,
                "blocked_result_schema_invalid",
                {"schema_errors": schema_errors, "codex_result": codex_result},
            )
        skill_errors = validate_skill_resolution_evidence(task, codex_result)
        if skill_errors:
            return fail_task(
                task_path,
                task,
                "blocked_skill_resolution_invalid",
                {"skill_resolution_errors": skill_errors, "codex_result": codex_result},
            )
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
        oris_result = commit_push_oris(task, run_state, product_result, checks, codex_result)
        if not oris_result.get("ok"):
            return fail_task(task_path, task, "blocked_oris_push_failed", {"product_result": product_result, "oris_result": oris_result})
        evidence_index_result = record_evidence_commit_index(task_id, "completed", oris_result, product_result)
        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "oris_evidence_index_result": evidence_index_result, "finished_at": now_iso()})
        # Do not rewrite orchestration/task_runs/<task_id>.json after ORIS evidence
        # commit; keep richer terminal runtime state only in the queue file.
        done_path = QUEUE_DIR / f"{task_id}.done.json"
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
