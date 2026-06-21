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
from pathlib import Path
from typing import Any

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.paths import discover_repo_root
from dev_employee_runtime.settings import load_runtime_settings
from dev_employee_codex_auth_preflight import classify_codex_failure, run_codex_auth_preflight
from dev_employee_result_validator import validate_result
from dev_employee_task_states import classify as classify_task_state

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


def build_runtime_prompt(task: dict[str, Any], base_prompt: str, result_path: Path) -> str:
    descriptor = json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True)
    strict = strict_result_schema(task)
    required = """

# REQUIRED FINAL RESULT CONTRACT

At the end of execution, write exactly one JSON object to this path:
{result_path}

Required JSON fields:
- status: one of success, failed, blocked
- summary: concise human-readable completion summary
- files_changed: array of changed file paths
- tests_run: array of commands/checks actually executed
- checks: array of check result objects or strings
- risks: array of residual risks or empty array
- next_steps: array of concrete follow-up actions or empty array
- product_path: target product repository path
- task_id: runtime task id

Do not include secrets, tokens, raw session IDs, or private prompts in the JSON.
""".format(result_path=result_path)
    if task.get("skill_resolution_required"):
        required += """

# REQUIRED SKILL RESOLUTION EVIDENCE

Because skill_resolution_required=true, before making product changes you must:
1. Resolve the applicable OpenClaw skill or routing rule.
2. Write a JSON report to skill_resolver_report_json.
3. Write a markdown report to skill_resolver_report_md.
4. Include the resolved skill name and evidence paths in the final result JSON.
"""
    return (
        base_prompt
        + "\n\n---\n\n"
        + "# RUNTIME TASK DESCRIPTOR\n\n"
        + descriptor
        + "\n"
        + required
        + "\n\nStrict schema mode: "
        + str(strict)
        + "\n"
    )


def build_codex_command(task: dict[str, Any], prompt_text: str) -> list[str]:
    product_path = str(task.get("product_path") or "")
    codex_bin = safe_path(task.get("codex_bin") or str(DEFAULT_CODEX), [Path.home()])
    argv = [str(codex_bin), "exec", "--sandbox", "workspace-write", "--cwd", product_path]
    if task.get("codex_model"):
        argv += ["--model", str(task["codex_model"])]
    argv.append(prompt_text)
    return argv


def invoke_codex(task: dict[str, Any], log_path: Path, result_path: Path) -> int:
    prompt_path = safe_path(task["prompt_path"], [ORIS_DIR, PROJECTS_DIR])
    product_path = safe_path(task["product_path"], [PROJECTS_DIR])
    base_prompt = prompt_path.read_text(encoding="utf-8")
    prompt_text = build_runtime_prompt(task, base_prompt, result_path)
    env = dict(os.environ)
    env["ORIS_DEV_EMPLOYEE_RESULT_JSON"] = str(result_path)
    env["ORIS_DEV_EMPLOYEE_TASK_ID"] = str(task.get("task_id") or "")
    env["ORIS_DEV_EMPLOYEE_STRICT_RESULT_SCHEMA"] = "1" if strict_result_schema(task) else "0"
    if task.get("skill_resolution_required"):
        env["ORIS_SKILL_RESOLUTION_REPORT_JSON"] = str(SKILL_RESOLUTION_DIR / f"{task.get('task_id')}.json")
        env["ORIS_SKILL_RESOLUTION_REPORT_MD"] = str(SKILL_RESOLUTION_DIR / f"{task.get('task_id')}.md")
    cmd = build_codex_command({**task, "product_path": str(product_path)}, prompt_text)
    proc = run(cmd, product_path, log_path, env=env)
    return proc.returncode


def validate_codex_result(task: dict[str, Any], codex_result: dict[str, Any]) -> list[str]:
    if not strict_result_schema(task):
        return []
    return validate_result(codex_result)


def validate_skill_resolution_evidence(task: dict[str, Any], codex_result: dict[str, Any]) -> list[str]:
    if not task.get("skill_resolution_required"):
        return []
    errors: list[str] = []
    json_path = Path(str(codex_result.get("skill_resolver_report_json") or SKILL_RESOLUTION_DIR / f"{task.get('task_id')}.json"))
    md_path = Path(str(codex_result.get("skill_resolver_report_md") or SKILL_RESOLUTION_DIR / f"{task.get('task_id')}.md"))
    for label, path in [("skill_resolver_report_json", json_path), ("skill_resolver_report_md", md_path)]:
        try:
            safe_path(str(path), [ORIS_DIR])
        except ValueError as exc:
            errors.append(f"{label} unsafe: {exc}")
            continue
        if not path.exists():
            errors.append(f"{label} missing: {path}")
    if json_path.exists():
        try:
            report = read_json(json_path)
        except Exception as exc:
            errors.append(f"skill_resolver_report_json invalid: {type(exc).__name__}: {exc}")
        else:
            if not report.get("resolved_skill") and not report.get("routing_decision"):
                errors.append("skill_resolver_report_json missing resolved_skill/routing_decision")
    return errors


def final_check(product_path: Path, task_id: str) -> dict[str, Any]:
    py = select_python(product_path)
    compile_log = LOG_DIR / f"{task_id}_host_py_compile.txt"
    pytest_log = LOG_DIR / f"{task_id}_host_pytest.txt"
    werror_log = LOG_DIR / f"{task_id}_host_pytest_werror.txt"
    compile_proc = run([py, "-m", "compileall", "."], product_path, compile_log)
    pytest_proc = run([py, "-m", "pytest", "-q"], product_path, pytest_log)
    werror_proc = run([py, "-m", "pytest", "-q", "-W", "error"], product_path, werror_log)
    return {
        "python": py,
        "compile_rc": compile_proc.returncode,
        "pytest_rc": pytest_proc.returncode,
        "pytest_werror_rc": werror_proc.returncode,
        "compile_log": str(compile_log),
        "pytest_log": str(pytest_log),
        "pytest_werror_log": str(werror_log),
        "ok": compile_proc.returncode == 0 and pytest_proc.returncode == 0 and werror_proc.returncode == 0,
    }


def commit_push_product(product_path: Path, message: str) -> dict[str, Any]:
    status = run(["git", "status", "--short"], product_path)
    if not status.stdout.strip():
        current = run(["git", "rev-parse", "HEAD"], product_path)
        remote = run(["git", "rev-parse", "origin/HEAD"], product_path)
        return {"changed": False, "commit_sha": current.stdout.strip(), "remote_sha": remote.stdout.strip(), "status_short": ""}
    run(["git", "add", "."], product_path)
    commit = run(["git", "commit", "-m", message], product_path)
    if commit.returncode != 0:
        return {"changed": True, "commit_failed": True, "commit_rc": commit.returncode, "stderr": commit.stderr[-4000:]}
    sha = run(["git", "rev-parse", "HEAD"], product_path).stdout.strip()
    push = run(["git", "push"], product_path)
    remote = run(["git", "rev-parse", "origin/HEAD"], product_path).stdout.strip()
    return {"changed": True, "commit_sha": sha, "push_rc": push.returncode, "remote_sha": remote, "status_short": status.stdout}


def autonomous_summary(codex_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": codex_result.get("status"),
        "summary": codex_result.get("summary"),
        "files_changed": codex_result.get("files_changed", []),
        "tests_run": codex_result.get("tests_run", []),
        "risks": codex_result.get("risks", []),
        "next_steps": codex_result.get("next_steps", []),
    }


def existing_relative(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(ORIS_DIR.resolve()).as_posix()
    except ValueError:
        return None


def add_existing(files: list[str], path: Path) -> None:
    rel = existing_relative(path)
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
    run(["git", "add", "--", *existing], ORIS_DIR)
    commit = run(["git", "commit", "-m", message], ORIS_DIR)
    if commit.returncode != 0:
        return {
            "changed": False,
            "commit_failed": True,
            "commit_rc": commit.returncode,
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
        existing_relative(run_json),
        existing_relative(codex_result_path),
        existing_relative(status_path),
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
        "run_json": existing_relative(run_json),
        "codex_result_json": existing_relative(codex_result_path),
        "evidence_files": evidence_commit.get("files", []),
    }
    atomic_write_json(index_path, payload)
    commit = commit_files([existing_relative(index_path) or ""], f"chore(dev-employee): index evidence for {task_id}")
    payload["evidence_index_commit_sha"] = commit.get("commit_sha")
    payload["evidence_index_remote_sha"] = commit.get("remote_sha")
    atomic_write_json(index_path, payload)
    commit = commit_files([existing_relative(index_path) or ""], f"chore(dev-employee): finalize evidence index for {task_id}")
    payload["evidence_index_final_commit_sha"] = commit.get("commit_sha")
    payload["evidence_index_final_remote_sha"] = commit.get("remote_sha")
    return payload


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
    files = [existing_relative(run_json), existing_relative(latest_path), *collect_task_log_files(task_id)]
    files = [item for item in files if item]
    result = commit_files(files, f"chore(dev-employee): add failure evidence for {task_id}")
    if result.get("commit_sha"):
        failure["oris_evidence_sha"] = result.get("commit_sha")
        failure["oris_evidence_remote_sha"] = result.get("remote_sha")
        atomic_write_json(run_json, failure)
        second = commit_files([existing_relative(run_json) or ""], f"chore(dev-employee): finalize failure evidence for {task_id}")
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
    os.replace(task_path, target)
    return 2 if status == "blocked" else 1


def run_task(task_path: Path) -> int:
    task = read_json(task_path)
    task_id = str(task.get("task_id") or task_path.name.removesuffix(".running.json"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SKILL_RESOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    product_path_value = task.get("product_path")
    product_path: Path | None = None
    try:
        if product_path_value:
            product_path = safe_path(str(product_path_value), [PROJECTS_DIR])
    except Exception as exc:
        return fail_task(task_path, task, "blocked", {"failure_code": "unsafe_product_path", "error": str(exc)})

    preflight = run_codex_auth_preflight()
    if not preflight.get("ok"):
        failure_code = "codex_auth_preflight_failed"
        status = "blocked" if preflight.get("classified") == "auth" else "failed"
        return fail_task(task_path, task, status, {"failure_code": failure_code, "preflight": preflight})

    codex_log = LOG_DIR / f"{task_id}.codex.log"
    result_path = RUN_DIR / f"{task_id}.codex_result.json"
    rc = invoke_codex(task, codex_log, result_path)

    strict = strict_result_schema(task)
    if result_path.exists():
        try:
            codex_result = read_json(result_path)
        except Exception as exc:
            codex_result = minimum_result_payload(task, str(product_path) if product_path else None, strict)
            codex_result["parse_error"] = f"{type(exc).__name__}: {exc}"
            atomic_write_json(result_path, codex_result)
    else:
        codex_result = minimum_result_payload(task, str(product_path) if product_path else None, strict)
        codex_result["missing_result_file"] = True
        atomic_write_json(result_path, codex_result)

    schema_errors = validate_codex_result(task, codex_result)
    skill_errors = validate_skill_resolution_evidence(task, codex_result)
    if rc != 0:
        failure = classify_codex_failure(codex_log.read_text(encoding="utf-8") if codex_log.exists() else "")
        codex_result["codex_returncode"] = rc
        codex_result["codex_failure"] = failure
        atomic_write_json(result_path, codex_result)
        status = "blocked" if failure.get("classified") == "auth" else "failed"
        return fail_task(task_path, task, status, {"failure_code": "codex_auth_failure" if status == "blocked" else "codex_failed", "codex_failure": failure})
    if schema_errors:
        codex_result["validation_errors"] = schema_errors
        atomic_write_json(result_path, codex_result)
        return fail_task(task_path, task, "failed", {"failure_code": "codex_invalid_result", "validation_errors": schema_errors})
    if skill_errors:
        codex_result["skill_resolution_errors"] = skill_errors
        atomic_write_json(result_path, codex_result)
        return fail_task(task_path, task, "failed", {"failure_code": "skill_resolution_missing", "skill_resolution_errors": skill_errors})

    if product_path is None:
        return fail_task(task_path, task, "blocked", {"failure_code": "missing_product_path"})
    final = final_check(product_path, task_id)
    if not final.get("ok"):
        codex_result["host_final_check"] = final
        atomic_write_json(result_path, codex_result)
        return fail_task(task_path, task, "failed", {"failure_code": "host_final_check_failed", "final_check": final})

    product_commit = commit_push_product(product_path, str(task.get("commit_message") or f"feat(dev-employee): complete {task_id}"))
    run_payload = {
        "task_id": task_id,
        "status": "success",
        "canonical_status": "success",
        "terminal": True,
        "completed_at": now_iso(),
        "codex_returncode": rc,
        "codex_result": codex_result,
        "autonomous_summary": autonomous_summary(codex_result),
        "host_final_check": final,
        "product_commit": product_commit,
        "product_commit_sha": product_commit.get("commit_sha"),
        "product_remote_sha": product_commit.get("remote_sha"),
        "strict_result_schema": strict,
        "skill_resolver_report_json": codex_result.get("skill_resolver_report_json"),
        "skill_resolver_report_md": codex_result.get("skill_resolver_report_md"),
    }
    run_json = RUN_DIR / f"{task_id}.json"
    atomic_write_json(run_json, run_payload)
    evidence = commit_push_oris(task_id, run_json, result_path, codex_result, final, product_commit, preflight)
    index = record_evidence_commit_index(task_id, product_commit, evidence, run_json, result_path)
    run_payload.update({
        "oris_evidence": evidence,
        "oris_evidence_sha": evidence.get("commit_sha"),
        "oris_evidence_remote_sha": evidence.get("remote_sha"),
        "evidence_commit_index": index,
    })
    atomic_write_json(run_json, run_payload)
    final_evidence = commit_files([existing_relative(run_json) or ""], f"chore(dev-employee): finalize task evidence for {task_id}")
    run_payload["oris_final_evidence_sha"] = final_evidence.get("commit_sha")
    atomic_write_json(run_json, run_payload)

    task.update({
        "status": "done",
        "canonical_status": "success",
        "terminal": True,
        "finished_at": now_iso(),
        "run_json": str(run_json),
        "product_commit_sha": product_commit.get("commit_sha"),
        "product_remote_sha": product_commit.get("remote_sha"),
        "oris_evidence_sha": evidence.get("commit_sha"),
        "evidence_commit_index": index,
        "next_recommended_action": "none",
    })
    atomic_write_json(task_path, task)
    os.replace(task_path, QUEUE_DIR / f"{task_id}.done.json")
    return 0


def run_once(verbose_idle: bool = False) -> int:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    for queued in sorted(QUEUE_DIR.glob("*.queued.json")):
        running = claim_task(queued)
        if running:
            return run_task(running)
    if verbose_idle:
        print("No queued dev employee tasks.", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one supervised ORIS Dev Employee task")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--sleep", type=float, default=5.0)
    args = parser.parse_args()
    if args.loop:
        while True:
            run_once(verbose_idle=True)
            time.sleep(args.sleep)
    return run_once(verbose_idle=True)


if __name__ == "__main__":
    raise SystemExit(main())
