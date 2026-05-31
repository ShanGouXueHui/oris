#!/usr/bin/env python3
"""Prepare an install candidate for the read-only ORIS Web Console Nginx route.

This script is intentionally non-destructive:
- renders a production Nginx candidate into /tmp by default;
- does not write /etc/nginx;
- does not create htpasswd files;
- does not reload Nginx;
- writes a JSON preflight report that can be reviewed before any install step.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
RENDERER = ORIS_DIR / "scripts" / "dev_employee_render_nginx_readonly_console.py"
REPORT_DIR = ORIS_DIR / "logs" / "dev_employee" / "nginx_readonly_console_preflight"
DEFAULT_OUTPUT = Path("/tmp/oris-dev-employee-web-console.readonly.conf")
SERVICE_FILE = Path.home() / ".config" / "systemd" / "user" / "oris-dev-employee-web-console.service"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def get_json(url: str) -> tuple[int, Any]:
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}
    except urllib.error.URLError as exc:
        return 599, {"error": "url_error", "message": str(exc)}


def service_submit_enabled() -> bool | None:
    if not SERVICE_FILE.exists():
        return None
    text = SERVICE_FILE.read_text(encoding="utf-8")
    if "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1" in text:
        return True
    if "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0" in text:
        return False
    return None


def load_renderer_result(output: str) -> dict[str, Any]:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"ok": False, "raw": output}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare read-only Web Console Nginx install candidate")
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--htpasswd-file", required=True)
    parser.add_argument("--tls-cert", required=True)
    parser.add_argument("--tls-key", required=True)
    parser.add_argument("--access-log", default="/var/log/nginx/oris-dev-employee-console.access.log")
    parser.add_argument("--error-log", default="/var/log/nginx/oris-dev-employee-console.error.log")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--require-existing-files", action="store_true", help="Fail if htpasswd/cert/key do not exist yet")
    args = parser.parse_args()

    output = Path(args.output)
    render = run([
        "python3",
        str(RENDERER),
        "--server-name",
        args.server_name,
        "--htpasswd-file",
        args.htpasswd_file,
        "--tls-cert",
        args.tls_cert,
        "--tls-key",
        args.tls_key,
        "--access-log",
        args.access_log,
        "--error-log",
        args.error_log,
        "--output",
        str(output),
    ])
    renderer_result = load_renderer_result(render.stdout)
    health_code, health_body = get_json("http://127.0.0.1:18893/health")
    service_active = run(["systemctl", "--user", "is-active", "oris-dev-employee-web-console.service"]).stdout.strip()
    intake_active = run(["systemctl", "--user", "is-active", "oris-dev-employee-intake.service"]).stdout.strip()
    bridge_active = run(["systemctl", "--user", "is-active", "oris-dev-employee-bridge.service"]).stdout.strip()
    file_checks = {
        "htpasswd_exists": Path(args.htpasswd_file).exists(),
        "tls_cert_exists": Path(args.tls_cert).exists(),
        "tls_key_exists": Path(args.tls_key).exists(),
    }
    rendered_text = output.read_text(encoding="utf-8") if output.exists() else ""
    safety_checks = {
        "candidate_exists": output.exists(),
        "renderer_ok": bool(renderer_result.get("ok")),
        "web_console_health_ok": health_code == 200 and isinstance(health_body, dict) and health_body.get("service") == "dev_employee_web_console",
        "web_console_service_active": service_active == "active",
        "intake_service_active": intake_active == "active",
        "bridge_service_active": bridge_active == "active",
        "submit_disabled": service_submit_enabled() is False,
        "does_not_proxy_intake": "proxy_pass http://127.0.0.1:18892" not in rendered_text,
        "proxies_web_console": "proxy_pass http://127.0.0.1:18893" in rendered_text,
        "blocks_post_goals": "location = /api/goals" in rendered_text and "if ($request_method !~ ^(GET)$) { return 403; }" in rendered_text,
        "has_basic_auth": "auth_basic" in rendered_text and "auth_basic_user_file" in rendered_text,
        "keeps_production_443_80": "listen 443 ssl http2;" in rendered_text and "listen 80;" in rendered_text,
    }
    required_files_ok = all(file_checks.values()) if args.require_existing_files else True
    ok = all(safety_checks.values()) and required_files_ok
    report = {
        "prepared_at": now_iso(),
        "ok": ok,
        "server_name": args.server_name,
        "candidate_path": str(output),
        "renderer_result": renderer_result,
        "file_checks": file_checks,
        "require_existing_files": args.require_existing_files,
        "service_status": {
            "web_console": service_active,
            "intake": intake_active,
            "bridge": bridge_active,
            "submit_enabled": service_submit_enabled(),
            "health_status": health_code,
        },
        "safety_checks": safety_checks,
        "install_command_preview": [
            "sudo install -m 0644 " + str(output) + " /etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf",
            "sudo nginx -t",
            "sudo systemctl reload nginx",
        ],
        "notes": [
            "This script did not install or reload Nginx.",
            "Only install after reviewing the candidate config and confirming TLS/htpasswd paths.",
            "Public write operations remain blocked at Nginx and Web Console layers."
        ],
    }
    report_path = REPORT_DIR / f"nginx-readonly-console-preflight-{args.server_name.replace('.', '-')}.json"
    write_json(report_path, report)
    print(json.dumps({"ok": ok, "report_path": str(report_path), "candidate_path": str(output), "file_checks": file_checks, "safety_checks": safety_checks}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
