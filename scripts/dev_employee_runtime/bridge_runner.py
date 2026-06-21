from __future__ import annotations

import argparse
import os
import time
import traceback
from pathlib import Path

from dev_employee_runtime.clock import now_iso
from dev_employee_runtime.json_store import atomic_write_json, read_json
from dev_employee_runtime.paths import repo_relative
from dev_employee_runtime.bridge_context import (
    LOG_DIR,
    ORIS_DIR,
    PROJECTS_DIR,
    QUEUE_DIR,
    RUN_DIR,
    SKILL_RESOLUTION_DIR,
    autonomous_summary,
    claim_task,
    minimum_result_payload,
    strict_result_schema,
)
from dev_employee_runtime.bridge_codex import (
    commit_push_product,
    final_check,
    invoke_codex,
    validate_codex_result,
    validate_skill_resolution_evidence,
)
from dev_employee_runtime.bridge_evidence import commit_files, commit_push_oris, fail_task, record_evidence_commit_index
from dev_employee_codex_auth_preflight import classify_codex_failure, run_codex_auth_preflight


def run_task(task_path: Path) -> int:
    try:
        return _run_task_impl(task_path)
    except Exception as exc:  # defensive terminalization: never leave claimed tasks stale-running
        try:
            task = read_json(task_path) if task_path.exists() else {}
        except Exception:
            task = {}
        task_id = str(task.get("task_id") or task_path.name.removesuffix(".running.json"))
        task["task_id"] = task_id
        return fail_task(
            task_path,
            task,
            "failed",
            {
                "failure_code": "bridge_unhandled_exception",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback_tail": traceback.format_exc()[-4000:],
            },
        )


def _run_task_impl(task_path: Path) -> int:
    task = read_json(task_path)
    task_id = str(task.get("task_id") or task_path.name.removesuffix(".running.json"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SKILL_RESOLUTION_DIR.mkdir(parents=True, exist_ok=True)

    product_path_value = task.get("product_path")
    product_path: Path | None = None
    try:
        if product_path_value:
            product_path = Path(str(product_path_value)).expanduser().resolve()
            product_path.relative_to(PROJECTS_DIR.resolve())
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
    final_evidence = commit_files([repo_relative(run_json, ORIS_DIR) or ""], f"chore(dev-employee): finalize task evidence for {task_id}")
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
