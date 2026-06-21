from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dev_employee_runtime.json_store import read_json
from dev_employee_runtime.bridge_context import (
    DEFAULT_CODEX,
    LOG_DIR,
    ORIS_DIR,
    PROJECTS_DIR,
    SKILL_RESOLUTION_DIR,
    run,
    safe_path,
    select_python,
    strict_result_schema,
)
from dev_employee_result_validator import validate_result


def build_runtime_prompt(task: dict[str, Any], base_prompt: str, result_path: Path) -> str:
    descriptor = json.dumps(task, ensure_ascii=False, indent=2, sort_keys=True)
    strict = strict_result_schema(task)
    required = """

# REQUIRED FINAL RESULT CONTRACT

At the end of execution, write exactly one JSON object to this path:
{result_path}

The JSON object MUST match the ORIS autonomous result validator contract.

Required top-level JSON fields:
- task_id: runtime task id, exactly as provided in ORIS_DEV_EMPLOYEE_TASK_ID
- status: one of local_checks_passed, local_checks_failed, blocked
- product_path: target product repository path
- plan: array of concrete steps you followed
- skill_resolution: object with exactly these array fields: needed, used_existing, downloaded_quarantine, blocked
- changed_files: array of changed product file paths; empty array is allowed if the requested work already exists
- check_logs: object mapping check names to log paths or concise check evidence
- iteration_summary: array of attempt/result/action objects or strings
- notes: array of residual notes; empty array is allowed

Recommended optional fields:
- blockers: required and non-empty if status is blocked
- summary: concise human-readable completion summary
- risks: array of residual risks or empty array
- next_steps: array of concrete follow-up actions or empty array
- skill_resolver_report_json: path to the JSON skill evidence report when skill resolution is required
- skill_resolver_report_md: path to the Markdown skill evidence report when skill resolution is required

Status semantics:
- Use local_checks_passed only when implementation state is correct and local checks have passed.
- Use local_checks_failed when local checks fail or you cannot complete the product-side work.
- Use blocked only for policy, credential, missing access, or unsafe-operation blocks, and include blockers.

Do not use status values success, failed, or passed. Do not include secrets, tokens, raw session IDs, or private prompts in the JSON.
""".format(result_path=result_path)
    if task.get("skill_resolution_required"):
        required += """

# REQUIRED SKILL RESOLUTION EVIDENCE

Because skill_resolution_required=true, before making product changes you must:
1. Resolve the applicable OpenClaw skill or routing rule.
2. Write a JSON report to skill_resolver_report_json.
3. Write a markdown report to skill_resolver_report_md.
4. Include the resolved skill name and evidence paths in the final result JSON.

The skill_resolution field in the final result JSON must still contain the required object:
{
  "needed": [...],
  "used_existing": [...],
  "downloaded_quarantine": [...],
  "blocked": []
}
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
    # The subprocess cwd is already set to product_path by invoke_codex().
    # Codex CLI 0.133.0 rejects `codex exec --cwd ...`, so do not pass --cwd.
    codex_bin = safe_path(task.get("codex_bin") or str(DEFAULT_CODEX), [Path.home()])
    argv = [str(codex_bin), "exec", "--sandbox", "workspace-write"]
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
