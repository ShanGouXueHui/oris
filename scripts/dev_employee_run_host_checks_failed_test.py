#!/usr/bin/env python3
"""Create a controlled blocked_host_checks_failed task.

This negative-path helper verifies that the ORIS supervised bridge commits host
check failure evidence to GitHub. It pre-writes a valid strict Codex result and
matching skill resolver report, then points the result at a temporary failing
product fixture outside the ORIS repository. The bridge should pass schema and
skill-resolution validation, run host checks, fail on py_compile/pytest, and
commit failure evidence plus host check logs.

No real product repository files are modified.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
FIXTURE_PATH = PROJECTS_DIR / "oris-host-check-failure-fixture"
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"
SKILL_DIR = LOG_DIR / "skill_resolution"
PROMPT_DIR = ORIS_DIR / "run" / "dev_employee_prompts"
FAKE_CODEX = ORIS_DIR / "run" / "dev_employee_test_tools" / "fake_codex_success.py"


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


def unique_task_id(base: str) -> str:
    candidates = [base]
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    candidates.append(f"{base}-{stamp}")
    for candidate in candidates:
        paths = [
            QUEUE_DIR / f"{candidate}.queued.json",
            QUEUE_DIR / f"{candidate}.running.json",
            QUEUE_DIR / f"{candidate}.done.json",
            QUEUE_DIR / f"{candidate}.failed.json",
            RUN_DIR / f"{candidate}.json",
            RUN_DIR / f"{candidate}.failure_result.json",
        ]
        if not any(path.exists() for path in paths):
            return candidate
    raise SystemExit("ERROR: unable to allocate unique task id")


def write_fake_codex() -> None:
    FAKE_CODEX.parent.mkdir(parents=True, exist_ok=True)
    FAKE_CODEX.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('FAKE_CODEX_SUCCESS controlled host-check failure test')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    FAKE_CODEX.chmod(0o755)


def write_failing_product_fixture() -> None:
    if FIXTURE_PATH.exists():
        shutil.rmtree(FIXTURE_PATH)
    (FIXTURE_PATH / "app").mkdir(parents=True, exist_ok=True)
    (FIXTURE_PATH / "tests").mkdir(parents=True, exist_ok=True)
    (FIXTURE_PATH / "app" / "__init__.py").write_text("", encoding="utf-8")
    # Deliberate syntax error. This makes host py_compile fail deterministically.
    (FIXTURE_PATH / "app" / "main.py").write_text(
        "def intentionally_broken(:\n"
        "    return 'host checks should fail'\n",
        encoding="utf-8",
    )
    (FIXTURE_PATH / "tests" / "test_failure.py").write_text(
        "def test_intentional_failure():\n"
        "    assert False, 'controlled host check failure'\n",
        encoding="utf-8",
    )


def write_control_files(task_id: str) -> None:
    prompt_path = PROMPT_DIR / f"{task_id}.md"
    resolver_json = SKILL_DIR / f"{task_id}.json"
    resolver_md = SKILL_DIR / f"{task_id}.md"
    codex_result = RUN_DIR / f"{task_id}.codex_result.json"
    objective = (
        "Controlled host checks failure evidence test. The pre-written strict result "
        "and resolver report match, but host py_compile/pytest must fail against a "
        "temporary product fixture to verify blocked_host_checks_failed evidence."
    )
    skill_resolution = {
        "needed": ["fastapi_pytest", "github_evidence"],
        "used_existing": [
            "scripts/dev_employee_supervised_bridge_v2.py",
            "schemas/dev_employee_task_result.schema.json",
        ],
        "downloaded_quarantine": [],
        "blocked": [],
    }

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        "# Controlled host-check failure test\n\n"
        "This prompt is intentionally executed by a local fake Codex binary. "
        "The bridge must use the pre-written result and resolver report, then "
        "block when host-side checks fail against the temporary fixture.\n",
        encoding="utf-8",
    )

    write_json(
        resolver_json,
        {
            "task_id": task_id,
            "resolved_at": now_iso(),
            "objective": objective,
            "skill_resolution": skill_resolution,
            "capability_matches": [],
            "quarantine_results": [],
            "policy": {
                "third_party_runtime_install_allowed": False,
                "quarantine_only": True,
                "promote_by_internalization_only": True,
            },
        },
    )
    resolver_md.write_text(
        f"# Controlled Host Check Failure — {task_id}\n\n"
        "Resolver report intentionally matches Codex result; only host checks should fail.\n",
        encoding="utf-8",
    )

    write_json(
        codex_result,
        {
            "task_id": task_id,
            "status": "local_checks_passed",
            "product_path": str(FIXTURE_PATH),
            "plan": [
                "Pre-write resolver report",
                "Pre-write strict result with matching skill_resolution",
                "Let bridge run host checks against failing fixture",
            ],
            "design_summary": "Controlled negative-path test for host check evidence; real product repositories are not modified.",
            "skill_resolution": skill_resolution,
            "changed_files": [],
            "check_logs": {},
            "iteration_summary": [
                {"attempt": 1, "result": "pre-written result ready for host-check failure validation"}
            ],
            "blockers": [],
            "notes": "Expected outer bridge status: blocked_host_checks_failed.",
        },
    )

    descriptor = {
        "task_id": task_id,
        "status": "queued",
        "created_at": now_iso(),
        "created_by": "dev_employee_run_host_checks_failed_test.py",
        "prompt_path": str(prompt_path),
        "workdir": "/home/admin/projects",
        "codex_bin": str(FAKE_CODEX),
        "sandbox": "workspace-write",
        "extra_write_dirs": [str(ORIS_DIR)],
        "expected_product_repo": "local/controlled-host-check-failure-fixture",
        "expected_product_path": str(FIXTURE_PATH),
        "product_commit_message": "test(dev-employee): should not be used",
        "notes": "Controlled host checks failure evidence test",
        "strict_result_schema": True,
        "autonomy_mode": "goal_driven",
        "task_objective": objective,
        "constraints": ["Do not modify real product repositories.", "Expected failure path only."],
        "expected_checks": [],
    }
    write_json(QUEUE_DIR / f"{task_id}.queued.json", descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled blocked_host_checks_failed evidence test")
    parser.add_argument("--task-id", default="failure-evidence-host-checks-failed-20260526-r1")
    parser.add_argument("--no-restart", action="store_true", help="do not restart the bridge service before queuing")
    parser.add_argument("--wait-seconds", type=int, default=50)
    args = parser.parse_args()

    os.chdir(ORIS_DIR)
    print("===== sync and static check =====")
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    run(["python3", "-m", "py_compile", "scripts/dev_employee_supervised_bridge_v2.py"], check=True)

    if not args.no_restart:
        print("===== restart bridge =====")
        run(["systemctl", "--user", "restart", "oris-dev-employee-bridge.service"], check=True)
        time.sleep(3)
        run(["systemctl", "--user", "is-active", "oris-dev-employee-bridge.service"], check=True)

    task_id = unique_task_id(args.task_id)
    print(f"===== create controlled host-check failure task: {task_id} =====")
    write_fake_codex()
    write_failing_product_fixture()
    write_control_files(task_id)

    print("===== wait bridge =====")
    time.sleep(args.wait_seconds)

    print("===== task status =====")
    run(["python3", "scripts/dev_employee_task_status.py", "--task-id", task_id])

    print("===== latest commit =====")
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(f"TASK_ID={task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
