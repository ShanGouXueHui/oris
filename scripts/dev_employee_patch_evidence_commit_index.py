#!/usr/bin/env python3
"""Patch ORIS Dev Employee evidence commit indexing.

Adds a small second-stage index that maps task_id -> ORIS commit that added the
primary task evidence. This gives Web/OpenClaw status pages a stable
`oris_evidence_commit_sha` without rewriting the already-committed task-run JSON.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
BRIDGE = ORIS_DIR / "scripts" / "dev_employee_supervised_bridge_v2.py"
INTAKE = ORIS_DIR / "scripts" / "dev_employee_intake_api.py"
TASK_ID = "web-adapter-goal-ping-endpoint-20260529-r1"


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


def patch_bridge() -> bool:
    text = BRIDGE.read_text(encoding="utf-8")
    changed = False
    if "EVIDENCE_COMMIT_INDEX_DIR" not in text:
        text = text.replace(
            "SKILL_RESOLUTION_DIR = LOG_DIR / \"skill_resolution\"\n",
            "SKILL_RESOLUTION_DIR = LOG_DIR / \"skill_resolution\"\nEVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / \"evidence_commit_index\"\n",
            1,
        )
        changed = True
    if "def record_evidence_commit_index(" not in text:
        marker = "def next_recommended_action(status: str) -> str:\n"
        function = '''def record_evidence_commit_index(
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


'''
        text = text.replace(marker, function + marker, 1)
        changed = True
    old_success = '''        oris_result = commit_push_oris(task, run_state, product_result, checks, codex_result)
        if not oris_result.get("ok"):
            return fail_task(task_path, task, "blocked_oris_push_failed", {"product_result": product_result, "oris_result": oris_result})
        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "finished_at": now_iso()})
'''
    new_success = '''        oris_result = commit_push_oris(task, run_state, product_result, checks, codex_result)
        if not oris_result.get("ok"):
            return fail_task(task_path, task, "blocked_oris_push_failed", {"product_result": product_result, "oris_result": oris_result})
        evidence_index_result = record_evidence_commit_index(task_id, "completed", oris_result, product_result)
        task.update({"status": "completed", "product_result": product_result, "oris_result": oris_result, "oris_evidence_index_result": evidence_index_result, "finished_at": now_iso()})
'''
    if old_success in text:
        text = text.replace(old_success, new_success, 1)
        changed = True
    old_failure = '''    evidence_result = commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    triage_result = run_failure_triage(task["task_id"])
'''
    new_failure = '''    evidence_result = commit_push_oris_failure(task, status, extra)
    task["failure_evidence_result"] = evidence_result
    evidence_index_result = record_evidence_commit_index(task["task_id"], status, evidence_result)
    task["failure_evidence_index_result"] = evidence_index_result
    if not evidence_result.get("ok"):
        task["oris_evidence_push_failed"] = True
    triage_result = run_failure_triage(task["task_id"])
'''
    if old_failure in text:
        text = text.replace(old_failure, new_failure, 1)
        changed = True
    if changed:
        BRIDGE.write_text(text, encoding="utf-8")
    return changed


def patch_intake() -> bool:
    text = INTAKE.read_text(encoding="utf-8")
    changed = False
    if "EVIDENCE_COMMIT_INDEX_DIR" not in text:
        text = text.replace(
            "LOG_DIR = ORIS_DIR / \"logs\" / \"dev_employee\"\n",
            "LOG_DIR = ORIS_DIR / \"logs\" / \"dev_employee\"\nEVIDENCE_COMMIT_INDEX_DIR = LOG_DIR / \"evidence_commit_index\"\n",
            1,
        )
        changed = True
    old = '''def evidence_summary(task_id: str, primary_run: dict[str, Any] | None) -> dict[str, Any]:
    files = [
'''
    new = '''def evidence_summary(task_id: str, primary_run: dict[str, Any] | None) -> dict[str, Any]:
    index_path = EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"
    evidence_index = read_json(index_path) if index_path.exists() else {}
    files = [
'''
    if old in text:
        text = text.replace(old, new, 1)
        changed = True
    old_files = '''        evidence_file("host_pytest_werror_log", LOG_DIR / f"{task_id}_host_pytest_werror.txt"),
    ]
    completed = primary_run or {}
    return {
        "repo": ORIS_REPO,
        "branch": DEFAULT_BRANCH,
        "files": [item for item in files if item["exists"]],
        "product_commit_sha": completed.get("product_commit_sha"),
        "product_remote_sha": completed.get("product_remote_sha"),
        "oris_evidence_sha": completed.get("oris_evidence_sha"),
        "strict_result_schema": completed.get("strict_result_schema"),
        "skill_resolver_report_json": completed.get("skill_resolver_report_json"),
    }
'''
    new_files = '''        evidence_file("host_pytest_werror_log", LOG_DIR / f"{task_id}_host_pytest_werror.txt"),
        evidence_file("evidence_commit_index", EVIDENCE_COMMIT_INDEX_DIR / f"{task_id}.json"),
    ]
    completed = primary_run or {}
    return {
        "repo": ORIS_REPO,
        "branch": DEFAULT_BRANCH,
        "files": [item for item in files if item["exists"]],
        "product_commit_sha": completed.get("product_commit_sha"),
        "product_remote_sha": completed.get("product_remote_sha"),
        "oris_evidence_sha": completed.get("oris_evidence_sha"),
        "oris_evidence_commit_sha": evidence_index.get("oris_evidence_commit_sha"),
        "oris_evidence_remote_sha": evidence_index.get("oris_evidence_remote_sha"),
        "evidence_index_commit_sha": evidence_index.get("evidence_index_commit_sha"),
        "strict_result_schema": completed.get("strict_result_schema"),
        "skill_resolver_report_json": completed.get("skill_resolver_report_json"),
    }
'''
    if old_files in text:
        text = text.replace(old_files, new_files, 1)
        changed = True
    if changed:
        INTAKE.write_text(text, encoding="utf-8")
    return changed


def backfill_ping_index() -> Path:
    evidence_path = ORIS_DIR / "orchestration" / "task_runs" / f"{TASK_ID}.json"
    if not evidence_path.exists():
        raise SystemExit(f"ERROR: missing evidence file {evidence_path}")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    rel = evidence_path.relative_to(ORIS_DIR).as_posix()
    log = run(["git", "log", "--format=%H", "--", rel], check=True).stdout.splitlines()
    if not log:
        raise SystemExit(f"ERROR: unable to find evidence commit for {rel}")
    evidence_commit = log[-1] if len(log) > 1 else log[0]
    # Use the oldest commit that touched the newly added task evidence when available.
    index = {
        "task_id": TASK_ID,
        "status": evidence.get("status"),
        "indexed_at": now_iso(),
        "oris_evidence_commit_sha": evidence_commit,
        "oris_evidence_remote_sha": evidence_commit,
        "oris_evidence_files": [rel],
        "product_commit_sha": evidence.get("product_commit_sha"),
        "product_remote_sha": evidence.get("product_remote_sha"),
        "backfilled": True,
    }
    path = ORIS_DIR / "logs" / "dev_employee" / "evidence_commit_index" / f"{TASK_ID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    bridge_changed = patch_bridge()
    intake_changed = patch_intake()
    backfill_path = backfill_ping_index()
    run(["python3", "-m", "py_compile", "scripts/dev_employee_supervised_bridge_v2.py", "scripts/dev_employee_intake_api.py"], check=True)
    run(["git", "add", "scripts/dev_employee_supervised_bridge_v2.py", "scripts/dev_employee_intake_api.py", str(backfill_path.relative_to(ORIS_DIR))], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "feat(dev-employee): index ORIS evidence commits"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": True, "bridge_changed": bridge_changed, "intake_changed": intake_changed, "backfill_index": str(backfill_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
