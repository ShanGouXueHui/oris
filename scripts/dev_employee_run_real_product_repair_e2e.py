#!/usr/bin/env python3
"""Run a real product repair execution E2E validation.

This runner creates a small, useful, controlled failing test in the real product
repository, then uses the triage-driven repair path to enqueue a repair task.
The supervised bridge/Codex must repair the product by implementing GET /healthz,
run host checks, commit/push the product change, and commit ORIS evidence.

Safety boundaries:
- Requires clean ORIS and product working trees at start.
- Does not use synthetic fixture paths.
- If the repair task fails or times out, it attempts to restore only the known
  controlled product files it created/allowed Codex to touch.
- Does not commit secrets, .env, .venv, caches, browser profiles, or queue JSON.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PRODUCT_DIR = Path("/home/admin/projects/oris-final-acceptance-api")
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
TRIAGE_DIR = ORIS_DIR / "logs" / "dev_employee" / "failure_triage"
REPAIR_PLAN_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_plans"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "repair_execution_tests"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
PRODUCT_REPO = "ShanGouXueHui/oris-final-acceptance-api"
FAILED_TASK_ID = "failure-evidence-real-product-healthz-20260526-r1"
REPAIR_TASK_ID = "repair-real-product-healthz-20260526-r1"
TEST_FILE = PRODUCT_DIR / "tests" / "test_healthz_repair.py"
BRIDGE_SERVICE = "oris-dev-employee-bridge.service"
ENQUEUE_SERVICE = "oris-dev-employee-enqueue.service"
MAX_WAIT_SECONDS = 420


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_status(path: Path) -> str:
    return run(["git", "status", "--short"], cwd=path).stdout


def git_tracked_status(path: Path) -> str:
    return run(["git", "status", "--short", "--untracked-files=no"], cwd=path).stdout


def service_active(service: str) -> bool:
    return run(["systemctl", "--user", "is-active", service]).stdout.strip() == "active"


def require_clean_trees() -> None:
    # ORIS can legitimately contain old untracked runtime logs/evidence on host.
    # Require no tracked/staged ORIS modifications, but do not block on untracked
    # runtime noise.
    oris_tracked_status = git_tracked_status(ORIS_DIR)
    product_status = git_status(PRODUCT_DIR)
    if oris_tracked_status:
        raise SystemExit(f"ERROR: ORIS tracked working tree is not clean before E2E:\n{oris_tracked_status}")
    if product_status:
        raise SystemExit(f"ERROR: product working tree is not clean before E2E:\n{product_status}")


def write_failing_healthz_test() -> None:
    TEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    TEST_FILE.write_text(
        "from fastapi.testclient import TestClient\n\n"
        "from app.main import app\n\n\n"
        "client = TestClient(app)\n\n\n"
        "def test_healthz_endpoint_returns_ok():\n"
        "    response = client.get('/healthz')\n"
        "    assert response.status_code == 200\n"
        "    assert response.json() == {'status': 'ok'}\n",
        encoding="utf-8",
    )


def run_targeted_failure_check() -> tuple[int, Path]:
    log_path = LOG_DIR / f"{FAILED_TASK_ID}_host_pytest.txt"
    python_bin = PRODUCT_DIR / ".venv" / "bin" / "python"
    proc = run([str(python_bin), "-m", "pytest", "-q", "tests/test_healthz_repair.py"], cwd=PRODUCT_DIR)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout + proc.stderr, encoding="utf-8")
    return proc.returncode, log_path


def write_failure_and_triage(failure_return_code: int, failure_log: Path) -> tuple[Path, Path]:
    failure_path = RUN_DIR / f"{FAILED_TASK_ID}.failure_result.json"
    triage_path = TRIAGE_DIR / f"{FAILED_TASK_ID}.json"
    failure = {
        "task_id": FAILED_TASK_ID,
        "status": "blocked_host_checks_failed",
        "updated_at": now_iso(),
        "strict_result_schema": True,
        "task_objective": "Real product repair E2E seed: add GET /healthz endpoint so tests/test_healthz_repair.py passes.",
        "failure_stage": "blocked_host_checks_failed",
        "product_path": str(PRODUCT_DIR),
        "codex_result_path": str(RUN_DIR / f"{FAILED_TASK_ID}.codex_result.json"),
        "codex_log_path": str(LOG_DIR / f"{FAILED_TASK_ID}.codex.log"),
        "next_recommended_action": "Implement GET /healthz returning {'status': 'ok'} and keep all existing tests passing.",
        "checks": {
            "ok": False,
            "python_bin": str(PRODUCT_DIR / ".venv" / "bin" / "python"),
            "results": [
                {
                    "cmd": f"{PRODUCT_DIR}/.venv/bin/python -m pytest -q tests/test_healthz_repair.py",
                    "return_code": failure_return_code,
                    "log": str(failure_log),
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
            "root_cause": "The real product has a new controlled failing test requiring GET /healthz to return {'status': 'ok'}.",
            "routine_autonomous_repair_allowed": True,
            "recommended_action": "Add a minimal FastAPI GET /healthz endpoint returning {'status': 'ok'}, run full host checks, and commit the product changes.",
            "repair_scope": "product_or_test_environment",
            "failed_checks": [
                {
                    "cmd": f"{PRODUCT_DIR}/.venv/bin/python -m pytest -q tests/test_healthz_repair.py",
                    "return_code": failure_return_code,
                    "log": str(failure_log),
                }
            ],
        },
        "evidence_links": {
            "codex_log_path": str(LOG_DIR / f"{FAILED_TASK_ID}.codex.log"),
            "codex_result_path": str(RUN_DIR / f"{FAILED_TASK_ID}.codex_result.json"),
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


def enqueue_repair() -> subprocess.CompletedProcess[str]:
    return run([
        "python3",
        "scripts/dev_employee_repair_from_triage.py",
        "--failed-task-id",
        FAILED_TASK_ID,
        "--new-task-id",
        REPAIR_TASK_ID,
        "--product-path",
        str(PRODUCT_DIR),
        "--product-repo",
        PRODUCT_REPO,
        "--enqueue",
        "--commit-plan",
    ], cwd=ORIS_DIR)


def wait_for_completion() -> dict[str, Any]:
    deadline = time.time() + MAX_WAIT_SECONDS
    last_status_output = ""
    while time.time() < deadline:
        status_proc = run(["python3", "scripts/dev_employee_task_status.py", "--task-id", REPAIR_TASK_ID], cwd=ORIS_DIR)
        last_status_output = status_proc.stdout + status_proc.stderr
        evidence_path = RUN_DIR / f"{REPAIR_TASK_ID}.json"
        if evidence_path.exists():
            try:
                evidence = read_json(evidence_path)
                status = evidence.get("status")
                if status == "completed":
                    return {"completed": True, "status": status, "evidence": evidence, "last_status_output": last_status_output}
                if isinstance(status, str) and status.startswith("blocked") or status in {"codex_failed", "bridge_exception"}:
                    return {"completed": False, "status": status, "evidence": evidence, "last_status_output": last_status_output}
            except Exception:
                pass
        time.sleep(15)
    return {"completed": False, "status": "timeout", "last_status_output": last_status_output}


def restore_product_if_needed(success: bool) -> None:
    if success:
        return
    run(["git", "restore", "app/main.py", "app/__init__.py"], cwd=PRODUCT_DIR)
    if TEST_FILE.exists():
        run(["rm", "-f", str(TEST_FILE)], cwd=PRODUCT_DIR)


def final_product_checks() -> dict[str, Any]:
    python_bin = PRODUCT_DIR / ".venv" / "bin" / "python"
    checks = []
    for cmd in [
        [str(python_bin), "-m", "pytest", "-q", "tests/test_healthz_repair.py"],
        [str(python_bin), "-m", "pytest", "-q"],
        [str(python_bin), "-m", "pytest", "-q", "-W", "error::DeprecationWarning"],
    ]:
        proc = run(cmd, cwd=PRODUCT_DIR)
        checks.append({"cmd": " ".join(cmd), "return_code": proc.returncode, "stdout_tail": proc.stdout[-1200:], "stderr_tail": proc.stderr[-1200:]})
    return {"ok": all(item["return_code"] == 0 for item in checks), "results": checks}


def commit_report(report: dict[str, Any]) -> None:
    report_path = REPORT_DIR / "real-product-healthz-repair-e2e-20260526-r1.json"
    write_json(report_path, report)
    run(["git", "fetch", "origin", "main"], cwd=ORIS_DIR)
    run(["git", "pull", "--ff-only", "origin", "main"], cwd=ORIS_DIR)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], cwd=ORIS_DIR, check=True)
    staged = run(["git", "diff", "--cached", "--quiet"], cwd=ORIS_DIR)
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate real product repair e2e"], cwd=ORIS_DIR, check=True)
        run(["git", "push", "origin", "main"], cwd=ORIS_DIR, check=True)


def main() -> int:
    report: dict[str, Any] = {
        "started_at": now_iso(),
        "failed_task_id": FAILED_TASK_ID,
        "repair_task_id": REPAIR_TASK_ID,
        "product_path": str(PRODUCT_DIR),
        "product_repo": PRODUCT_REPO,
    }
    success = False
    try:
        run(["git", "fetch", "origin", "main"], cwd=ORIS_DIR, check=True)
        run(["git", "reset", "--hard", "origin/main"], cwd=ORIS_DIR, check=True)
        run(["git", "fetch", "origin", "main"], cwd=PRODUCT_DIR, check=True)
        run(["git", "reset", "--hard", "origin/main"], cwd=PRODUCT_DIR, check=True)
        require_clean_trees()
        run(["systemctl", "--user", "is-active", ENQUEUE_SERVICE], check=True)
        if not service_active(BRIDGE_SERVICE):
            run(["systemctl", "--user", "restart", BRIDGE_SERVICE], check=True)
            time.sleep(3)
        run(["systemctl", "--user", "is-active", BRIDGE_SERVICE], check=True)

        product_head_before = run(["git", "rev-parse", "HEAD"], cwd=PRODUCT_DIR, check=True).stdout.strip()
        report["product_head_before"] = product_head_before

        write_failing_healthz_test()
        failure_rc, failure_log = run_targeted_failure_check()
        report["initial_failure_return_code"] = failure_rc
        report["initial_failure_log"] = str(failure_log)
        if failure_rc == 0:
            raise SystemExit("ERROR: controlled healthz test unexpectedly passed before repair")

        failure_path, triage_path = write_failure_and_triage(failure_rc, failure_log)
        report["failure_path"] = str(failure_path)
        report["triage_path"] = str(triage_path)

        enqueue_proc = enqueue_repair()
        report["enqueue_return_code"] = enqueue_proc.returncode
        report["enqueue_stdout_tail"] = enqueue_proc.stdout[-2000:]
        report["enqueue_stderr_tail"] = enqueue_proc.stderr[-2000:]
        if enqueue_proc.returncode != 0:
            raise SystemExit("ERROR: repair enqueue failed")

        wait_result = wait_for_completion()
        report["wait_result"] = wait_result
        success = bool(wait_result.get("completed"))
        if success:
            product_head_after = run(["git", "rev-parse", "HEAD"], cwd=PRODUCT_DIR, check=True).stdout.strip()
            product_remote = run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=PRODUCT_DIR, check=True).stdout.split()[0]
            report["product_head_after"] = product_head_after
            report["product_remote_after"] = product_remote
            report["final_checks"] = final_product_checks()
            success = product_head_after == product_remote and report["final_checks"].get("ok") is True
        report["ok"] = success
    except BaseException as exc:
        report["ok"] = False
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)
        raise
    finally:
        restore_product_if_needed(success)
        report.setdefault("ok", success)
        report["finished_at"] = now_iso()
        report["final_product_status"] = git_status(PRODUCT_DIR)
        report["final_oris_tracked_status"] = git_tracked_status(ORIS_DIR)
        commit_report(report)
        run(["git", "log", "-1", "--oneline"], cwd=ORIS_DIR)
        print(json.dumps({"ok": report.get("ok"), "repair_task_id": REPAIR_TASK_ID}, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
