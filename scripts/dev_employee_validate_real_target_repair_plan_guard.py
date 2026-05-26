#!/usr/bin/env python3
"""Validate positive repair target guard behavior for the real product repo.

This runner creates a synthetic *planning-only* failure evidence + triage pair
whose target is the real final-acceptance product path/repo. It then runs the
repair-from-triage helper without --enqueue and verifies that target_guard allows
the target because product_path basename matches product_repo slug.

It intentionally does not enqueue a Codex repair task and does not modify the
product repository.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
TRIAGE_DIR = ORIS_DIR / "logs" / "dev_employee" / "failure_triage"
REPAIR_PLAN_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_plans"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_guard_tests"
FAILED_TASK_ID = "failure-evidence-real-target-plan-only-20260526-r1"
REPAIR_TASK_ID = "repair-real-target-guard-plan-20260526-r1"
PRODUCT_PATH = "/home/admin/projects/oris-final-acceptance-api"
PRODUCT_REPO = "ShanGouXueHui/oris-final-acceptance-api"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_synthetic_failure_and_triage() -> tuple[Path, Path]:
    failure_path = RUN_DIR / f"{FAILED_TASK_ID}.failure_result.json"
    triage_path = TRIAGE_DIR / f"{FAILED_TASK_ID}.json"
    failure = {
        "task_id": FAILED_TASK_ID,
        "status": "blocked_host_checks_failed",
        "updated_at": now_iso(),
        "strict_result_schema": True,
        "task_objective": "Synthetic real-target repair guard validation. Planning only; do not enqueue or modify product code.",
        "failure_stage": "blocked_host_checks_failed",
        "product_path": PRODUCT_PATH,
        "codex_result_path": str(RUN_DIR / f"{FAILED_TASK_ID}.codex_result.json"),
        "codex_log_path": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}.codex.log"),
        "next_recommended_action": "Generate a repair plan for real target guard validation only.",
        "checks": {
            "ok": False,
            "python_bin": f"{PRODUCT_PATH}/.venv/bin/python",
            "results": [
                {
                    "cmd": f"{PRODUCT_PATH}/.venv/bin/python -m pytest -q",
                    "return_code": 1,
                    "log": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}_host_pytest.txt"),
                }
            ],
        },
    }
    triage = {
        "task_id": FAILED_TASK_ID,
        "triaged_at": now_iso(),
        "source_evidence": str(failure_path),
        "status": "blocked_host_checks_failed",
        "strict_result_schema": True,
        "classification": {
            "category": "host_checks_failed",
            "root_cause": "Synthetic positive target-guard validation failure; no real product failure is asserted.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Generate a repair plan and verify target guard only. Do not enqueue in this validation.",
            "repair_scope": "product_or_test_environment",
            "failed_checks": [
                {
                    "cmd": f"{PRODUCT_PATH}/.venv/bin/python -m pytest -q",
                    "return_code": 1,
                    "log": str(ORIS_DIR / "logs" / "dev_employee" / f"{FAILED_TASK_ID}_host_pytest.txt"),
                }
            ],
        },
        "evidence_links": {
            "codex_log_path": failure["codex_log_path"],
            "codex_result_path": failure["codex_result_path"],
        },
        "next_step_contract": {
            "ask_human_for_routine_decision": False,
            "rerun_requires_new_task_id": True,
            "must_preserve_original_failure_evidence": True,
        },
    }
    write_json(failure_path, failure)
    write_json(triage_path, triage)
    return failure_path, triage_path


def main() -> int:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    run(["python3", "-m", "py_compile", "scripts/dev_employee_repair_from_triage.py"], check=True)

    failure_path, triage_path = write_synthetic_failure_and_triage()
    proc = run([
        "python3",
        "scripts/dev_employee_repair_from_triage.py",
        "--failed-task-id",
        FAILED_TASK_ID,
        "--new-task-id",
        REPAIR_TASK_ID,
        "--product-path",
        PRODUCT_PATH,
        "--product-repo",
        PRODUCT_REPO,
    ])
    plan_path = REPAIR_PLAN_DIR / f"{REPAIR_TASK_ID}.json"
    plan = read_json(plan_path) if plan_path.exists() else {}
    target_guard = plan.get("target_guard", {}) if isinstance(plan, dict) else {}

    report = {
        "validated_at": now_iso(),
        "failed_task_id": FAILED_TASK_ID,
        "repair_task_id": REPAIR_TASK_ID,
        "failure_path": str(failure_path),
        "triage_path": str(triage_path),
        "plan_path": str(plan_path),
        "repair_from_triage_return_code": proc.returncode,
        "product_path": PRODUCT_PATH,
        "product_repo": PRODUCT_REPO,
        "target_guard": target_guard,
        "expected": {
            "return_code": 0,
            "target_guard_enqueue_allowed": True,
            "mismatch_reason": None,
            "no_enqueue_attempted": True,
        },
    }
    ok = (
        proc.returncode == 0
        and target_guard.get("enqueue_allowed") is True
        and target_guard.get("mismatch_reason") is None
        and target_guard.get("product_path") == PRODUCT_PATH
        and target_guard.get("product_repo") == PRODUCT_REPO
    )
    report["ok"] = ok
    report_path = REPORT_DIR / "real-target-repair-plan-guard-20260526-r1.json"
    write_json(report_path, report)

    files = [
        str(failure_path.relative_to(ORIS_DIR)),
        str(triage_path.relative_to(ORIS_DIR)),
        str(plan_path.relative_to(ORIS_DIR)),
        str(report_path.relative_to(ORIS_DIR)),
    ]
    run(["git", "add", *files], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate real-target repair plan guard"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": ok, "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
