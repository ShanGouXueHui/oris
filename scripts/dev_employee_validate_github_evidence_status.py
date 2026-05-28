#!/usr/bin/env python3
"""Validate that intake status exposes GitHub evidence refs for a completed task."""

from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "github_evidence_status"
BASE_URL = "http://127.0.0.1:18892"
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


def get_status() -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(f"{BASE_URL}/goals/{TASK_ID}", method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    report: dict[str, Any] = {"validated_at": now_iso(), "task_id": TASK_ID}
    status_code, body = get_status()
    github_evidence = body.get("github_evidence", {}) if isinstance(body, dict) else {}
    files = github_evidence.get("files", []) if isinstance(github_evidence, dict) else []
    labels = sorted(item.get("label") for item in files if isinstance(item, dict))
    ok = (
        status_code == 200
        and body.get("status") == "completed"
        and github_evidence.get("repo") == "ShanGouXueHui/oris"
        and github_evidence.get("branch") == "main"
        and github_evidence.get("product_commit_sha") == "1ce234cf4e6b3179d4b3eebdb85a69263745582b"
        and github_evidence.get("product_remote_sha") == "1ce234cf4e6b3179d4b3eebdb85a69263745582b"
        and github_evidence.get("strict_result_schema") is True
        and "task_run_json" in labels
        and "codex_result_json" in labels
        and "skill_resolution_json" in labels
        and "host_pytest_log" in labels
        and "host_pytest_werror_log" in labels
    )
    report.update(
        {
            "ok": ok,
            "status_code": status_code,
            "task_status": body.get("status"),
            "github_evidence_repo": github_evidence.get("repo"),
            "github_evidence_branch": github_evidence.get("branch"),
            "product_commit_sha": github_evidence.get("product_commit_sha"),
            "product_remote_sha": github_evidence.get("product_remote_sha"),
            "oris_evidence_sha": github_evidence.get("oris_evidence_sha"),
            "strict_result_schema": github_evidence.get("strict_result_schema"),
            "evidence_labels": labels,
            "evidence_file_count": len(files),
        }
    )
    report_path = REPORT_DIR / "github-evidence-status-ping-20260529-r1.json"
    write_json(report_path, report)
    run(["git", "add", str(report_path.relative_to(ORIS_DIR))], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "test(dev-employee): validate GitHub evidence status"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print(json.dumps({"ok": ok, "report_path": str(report_path)}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
