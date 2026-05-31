#!/usr/bin/env python3
"""Dry-run/apply installer for the read-only ORIS Web Console Nginx route.

Default mode is dry-run. It prints the commands that would be executed.
Use --apply to install, run nginx -t, and reload Nginx.

The installer intentionally installs only the read-only route: POST /api/goals is
blocked at Nginx layer and Web Console submit remains disabled by service policy.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PREFLIGHT = ORIS_DIR / "scripts" / "dev_employee_prepare_nginx_readonly_console_install.py"
DEFAULT_TARGET = Path("/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def load_json_from_stdout(stdout: str) -> dict[str, Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": False, "raw": stdout}


def is_placeholder_domain(server_name: str) -> bool:
    lowered = server_name.strip().lower()
    return lowered in {"example.com", "oris.example.com", "localhost"} or lowered.endswith(".example.com") or lowered.endswith(".invalid")


def sudo_file_exists(path: str) -> dict[str, Any]:
    proc = run(["sudo", "test", "-f", path])
    return {"path": path, "ok": proc.returncode == 0, "return_code": proc.returncode, "stderr": proc.stderr[-500:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install read-only ORIS Web Console Nginx config")
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--htpasswd-file", required=True)
    parser.add_argument("--tls-cert", required=True)
    parser.add_argument("--tls-key", required=True)
    parser.add_argument("--candidate", default="/tmp/oris-dev-employee-web-console.readonly.conf")
    parser.add_argument("--target", default=str(DEFAULT_TARGET))
    parser.add_argument("--apply", action="store_true", help="Actually install and reload Nginx")
    args = parser.parse_args()

    candidate = Path(args.candidate)
    target = Path(args.target)
    preflight_cmd = [
        "python3", str(PREFLIGHT),
        "--server-name", args.server_name,
        "--htpasswd-file", args.htpasswd_file,
        "--tls-cert", args.tls_cert,
        "--tls-key", args.tls_key,
        "--output", str(candidate),
    ]
    preflight = run(preflight_cmd)
    preflight_result = load_json_from_stdout(preflight.stdout)
    commands = [
        ["sudo", "install", "-m", "0644", str(candidate), str(target)],
        ["sudo", "nginx", "-t"],
        ["sudo", "systemctl", "reload", "nginx"],
    ]
    report: dict[str, Any] = {
        "planned_at": now_iso(),
        "apply": args.apply,
        "server_name": args.server_name,
        "candidate": str(candidate),
        "target": str(target),
        "preflight_return_code": preflight.returncode,
        "preflight_result": preflight_result,
        "commands": [" ".join(cmd) for cmd in commands],
        "ok": False,
    }
    if preflight.returncode != 0 or not preflight_result.get("ok"):
        report["error"] = "preflight_failed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if not candidate.exists():
        report["error"] = "candidate_missing"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if not args.apply:
        report["ok"] = True
        report["mode"] = "dry_run"
        report["notes"] = [
            "No files were installed.",
            "Run again with --apply only after reviewing the candidate and confirming TLS/htpasswd paths.",
            "Public write operations remain blocked."
        ]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if is_placeholder_domain(args.server_name):
        report["error"] = "refusing_placeholder_domain"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    if not shutil.which("sudo"):
        report["error"] = "sudo_not_found"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    sudo_file_checks = {
        "htpasswd": sudo_file_exists(args.htpasswd_file),
        "tls_cert": sudo_file_exists(args.tls_cert),
        "tls_key": sudo_file_exists(args.tls_key),
    }
    report["sudo_file_checks"] = sudo_file_checks
    if not all(item.get("ok") for item in sudo_file_checks.values()):
        report["error"] = "required_file_missing_or_unreadable_by_sudo"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1
    results: list[dict[str, Any]] = []
    for cmd in commands:
        proc = run(cmd)
        results.append({"cmd": " ".join(cmd), "return_code": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]})
        if proc.returncode != 0:
            report["ok"] = False
            report["mode"] = "apply"
            report["results"] = results
            report["error"] = "command_failed"
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return proc.returncode
    report["ok"] = True
    report["mode"] = "apply"
    report["results"] = results
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
