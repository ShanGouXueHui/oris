#!/usr/bin/env python3
"""Create a controlled blocked_skill_resolution_invalid task.

This is a negative-path verification helper for the ORIS supervised bridge. It
pre-writes a valid strict Codex result and a valid resolver report with an
intentional skill_resolution mismatch, then queues the task with a local fake
Codex executable that exits successfully. The bridge should validate the
pre-written result, detect the mismatch, and commit failure evidence to GitHub.

No product repository files are modified.
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
PRODUCT_PATH = Path("/home/admin/projects/oris-final-acceptance-api")
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
        "print('FAKE_CODEX_SUCCESS controlled negative-path test')\n"
        "sys.exit(0)\n",
        encoding="utf-8",
    )
    FAKE_CODEX.chmod(0o755)


def write_control_files(task_id: str) -> None:
    prompt_path = PROMPT_DIR / f"{task_id}.md"
    resolver_json = SKILL_DIR / f"{task_id}.json"
    resolver_md = SKILL_DIR / f"{task_id}.md"
    codex_result = RUN_DIR / f"{task_id}.codex_result.json"
    objective = (
        "Controlled skill resolver mismatch failure evidence test. The pre-written "
        "resolver report and strict result intentionally disagree to verify "
        "blocked_skill_resolution_invalid evidence persistence."
    )

    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        "# Controlled skill-resolution mismatch test\n\n"
        "This prompt is intentionally executed by a local fake Codex binary. "
        "The bridge must use the pre-written result and resolver report, then "
        "block on skill_resolution mismatch.\n",
        encoding="utf-8",
    )

    write_json(
        resolver_json,
        {
            "task_id": task_id,
            "resolved_at": now_iso(),
            "objective": objective,
            "skill_resolution": {
                "needed": ["github_evidence"],
                "used_existing": ["scripts/dev_employee_supervised_bridge_v2.py"],
                "downloaded_quarantine": [],
                "blocked": [],
            },
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
        f"# Controlled Skill Resolution Mismatch — {task_id}\n\n"
        "Resolver report intentionally says `github_evidence`; Codex result intentionally says `fastapi_pytest`.\n",
        encoding="utf-8",
    )

    write_json(
        codex_result,
        {
            "task_id": task_id,
            "status": "local_checks_passed",
            "product_path": str(PRODUCT_PATH),
            "plan": [
                "Pre-write resolver report",
                "Pre-write strict result with intentional skill_resolution mismatch",
                "Let bridge enforcement block the task",
            ],
            "design_summary": "Controlled negative-path test for bridge skill resolver enforcement; no product files are changed.",
            "skill_resolution": {
                "needed": ["fastapi_pytest"],
                "used_existing": ["prompts/dev_employee_autonomous_development_task_template_20260526.md"],
                "downloaded_quarantine": [],
                "blocked": [],
            },
            "changed_files": [],
            "check_logs": {},
            "iteration_summary": [
                {"attempt": 1, "result": "pre-written mismatch result ready for bridge validation"}
            ],
            "blockers": [],
            "notes": "Expected outer bridge status: blocked_skill_resolution_invalid.",
        },
    )

    descriptor = {
        "task_id": task_id,
        "status": "queued",
        "created_at": now_iso(),
        "created_by": "dev_employee_run_skill_resolution_invalid_test.py",
        "prompt_path": str(prompt_path),
        "workdir": "/home/admin/projects",
        "codex_bin": str(FAKE_CODEX),
        "sandbox": "workspace-write",
        "extra_write_dirs": [str(ORIS_DIR)],
        "expected_product_repo": "ShanGouXueHui/oris-final-acceptance-api",
        "expected_product_path": str(PRODUCT_PATH),
        "product_commit_message": "test(dev-employee): should not be used",
        "notes": "Controlled skill_resolution mismatch failure evidence test",
        "strict_result_schema": True,
        "autonomy_mode": "goal_driven",
        "task_objective": objective,
        "constraints": ["Do not modify product code.", "Expected failure path only."],
        "expected_checks": [],
    }
    write_json(QUEUE_DIR / f"{task_id}.queued.json", descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run controlled blocked_skill_resolution_invalid evidence test")
    parser.add_argument("--task-id", default="failure-evidence-skill-resolution-invalid-20260526-r1")
    parser.add_argument("--no-restart", action="store_true", help="do not restart the bridge service before queuing")
    parser.add_argument("--wait-seconds", type=int, default=45)
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
    print(f"===== create controlled mismatch task: {task_id} =====")
    write_fake_codex()
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
