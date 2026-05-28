#!/usr/bin/env python3
"""Validate systemd-managed ORIS Dev Employee intake API service.

This validator is intentionally narrow: it checks the user service state and
local loopback read-only endpoints. It does not submit goals, stop/start bridge,
modify queue files, or push commits.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
SERVICE_NAME = "oris-dev-employee-intake.service"
BASE_URL = "http://127.0.0.1:18892"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)


def get_json(path: str) -> tuple[int, Any]:
    request = urllib.request.Request(BASE_URL + path, method="GET")
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main() -> int:
    active = run(["systemctl", "--user", "is-active", SERVICE_NAME]).stdout.strip()
    enabled = run(["systemctl", "--user", "is-enabled", SERVICE_NAME]).stdout.strip()
    health_status, health = get_json("/health")
    projects_status, projects = get_json("/projects")
    status = run(["git", "status", "--short", "--untracked-files=no"]).stdout
    report = {
        "validated_at": now_iso(),
        "service_name": SERVICE_NAME,
        "active": active,
        "enabled": enabled,
        "health_status": health_status,
        "health": health,
        "projects_status": projects_status,
        "projects_contains_final_acceptance": "oris-final-acceptance-api" in projects.get("projects", []),
        "final_oris_tracked_status": status,
    }
    report["ok"] = (
        active == "active"
        and enabled in {"enabled", "enabled-runtime"}
        and health_status == 200
        and health.get("status") == "ok"
        and projects_status == 200
        and report["projects_contains_final_acceptance"] is True
        and status == ""
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
