#!/usr/bin/env python3
"""Diagnose the controlled Web Console consolez submit attempt.

This script is read-only except for writing a sanitized diagnostic report into
logs/dev_employee/web_console_submit_diagnostics and committing it. It does not
print or persist token values.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PRODUCT_DIR = Path("/home/admin/projects/oris-final-acceptance-api")
SERVICE_PATH = Path.home() / ".config" / "systemd" / "user" / "oris-dev-employee-web-console.service"
AUDIT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_audit"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "web_console_submit_diagnostics"
TASK_ID = "web-console-submit-consolez-20260531-r1"
BASE_INTAKE = "http://127.0.0.1:18892"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], cwd: Path = ORIS_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)


def get_json(url: str) -> tuple[int, Any]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}
    except urllib.error.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc)}


def audit_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not AUDIT_DIR.exists():
        return events
    for path in sorted(AUDIT_DIR.glob("web_console_audit_*.jsonl")):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                events.append(json.loads(raw))
    return events


def service_submit_enabled() -> bool | None:
    if not SERVICE_PATH.exists():
        return None
    text = SERVICE_PATH.read_text(encoding="utf-8")
    if "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1" in text:
        return True
    if "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0" in text:
        return False
    return None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    status_code, status_body = get_json(f"{BASE_INTAKE}/goals/{TASK_ID}")
    audits = audit_events()
    matching_audits = [event for event in audits if event.get("task_id") == TASK_ID]
    report = {
        "diagnosed_at": now_iso(),
        "task_id": TASK_ID,
        "intake_status_code": status_code,
        "intake_task_status": status_body.get("status") if isinstance(status_body, dict) else None,
        "intake_has_catalog": bool(status_body.get("catalog")) if isinstance(status_body, dict) else False,
        "intake_queue_count": len(status_body.get("queue", [])) if isinstance(status_body, dict) else None,
        "intake_runs_count": len(status_body.get("runs", [])) if isinstance(status_body, dict) else None,
        "service_submit_enabled": service_submit_enabled(),
        "web_console_active": run(["systemctl", "--user", "is-active", "oris-dev-employee-web-console.service"]).stdout.strip(),
        "bridge_active": run(["systemctl", "--user", "is-active", "oris-dev-employee-bridge.service"]).stdout.strip(),
        "intake_active": run(["systemctl", "--user", "is-active", "oris-dev-employee-intake.service"]).stdout.strip(),
        "audit_total_events": len(audits),
        "matching_audit_count": len(matching_audits),
        "matching_audit_summaries": [
            {
                "ts": event.get("ts"),
                "action": event.get("action"),
                "result": event.get("result"),
                "reason": event.get("reason"),
                "upstream_status": event.get("upstream_status"),
                "project_key": event.get("project_key"),
                "task_id": event.get("task_id"),
            }
            for event in matching_audits[-5:]
        ],
        "product_contains_consolez": "consolez" in (PRODUCT_DIR / "app" / "main.py").read_text(encoding="utf-8") if (PRODUCT_DIR / "app" / "main.py").exists() else False,
        "product_head": run(["git", "rev-parse", "HEAD"], cwd=PRODUCT_DIR).stdout.strip(),
        "product_remote_main": (run(["git", "ls-remote", "origin", "refs/heads/main"], cwd=PRODUCT_DIR).stdout.split() or [None])[0],
        "oris_tracked_status": run(["git", "status", "--short", "--untracked-files=no"]).stdout,
        "product_status": run(["git", "status", "--short"], cwd=PRODUCT_DIR).stdout,
    }
    report["likely_stage"] = (
        "submitted_to_intake_or_later" if report["intake_task_status"] not in {None, "unknown"}
        else "not_submitted_to_intake"
    )
    report_path = REPORT_DIR / "consolez-submit-diagnostic-20260531-r1.json"
    write_json(report_path, report)
    add = run(["git", "add", str(report_path.relative_to(ORIS_DIR))])
    if add.returncode != 0:
        print(add.stderr, end="")
        return add.returncode
    if run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        commit = run(["git", "commit", "-m", "test(dev-employee): diagnose Web console submit attempt"])
        print(commit.stdout, end="")
        print(commit.stderr, end="")
        if commit.returncode != 0:
            return commit.returncode
        push = run(["git", "push", "origin", "main"])
        print(push.stdout, end="")
        print(push.stderr, end="")
        if push.returncode != 0:
            return push.returncode
    log = run(["git", "log", "-1", "--oneline"])
    print(log.stdout, end="")
    print(json.dumps({"ok": True, "report_path": str(report_path), "likely_stage": report["likely_stage"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
