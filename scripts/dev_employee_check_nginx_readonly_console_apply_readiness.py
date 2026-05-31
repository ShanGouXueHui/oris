#!/usr/bin/env python3
"""Check readiness for applying the read-only ORIS Web Console Nginx route.

This script does not install or reload Nginx. It is stricter than dry-run:
- refuses placeholder domains;
- runs the dry-run installer;
- uses sudo test -f for htpasswd/cert/key paths;
- verifies the candidate still blocks writes and does not proxy intake;
- prints a compact JSON readiness result.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
INSTALLER = ORIS_DIR / "scripts" / "dev_employee_install_nginx_readonly_console.py"
DEFAULT_CANDIDATE = Path("/tmp/oris-dev-employee-web-console.readonly.conf")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)


def parse_json(stdout: str) -> dict[str, Any]:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"ok": False, "raw": stdout[-2000:]}


def placeholder_domain(domain: str) -> bool:
    lowered = domain.strip().lower()
    return lowered in {"example.com", "oris.example.com", "localhost"} or lowered.endswith(".example.com") or lowered.endswith(".invalid")


def sudo_test_file(path: str) -> dict[str, Any]:
    proc = run(["sudo", "test", "-f", path])
    return {"path": path, "ok": proc.returncode == 0, "return_code": proc.returncode, "stderr": proc.stderr[-500:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Check apply readiness for read-only ORIS Web Console Nginx route")
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--htpasswd-file", required=True)
    parser.add_argument("--tls-cert", required=True)
    parser.add_argument("--tls-key", required=True)
    parser.add_argument("--candidate", default=str(DEFAULT_CANDIDATE))
    args = parser.parse_args()

    installer = run([
        "python3", str(INSTALLER),
        "--server-name", args.server_name,
        "--htpasswd-file", args.htpasswd_file,
        "--tls-cert", args.tls_cert,
        "--tls-key", args.tls_key,
        "--candidate", args.candidate,
    ])
    installer_result = parse_json(installer.stdout)
    candidate = Path(args.candidate)
    candidate_text = candidate.read_text(encoding="utf-8") if candidate.exists() else ""
    sudo_file_checks = {
        "htpasswd": sudo_test_file(args.htpasswd_file),
        "tls_cert": sudo_test_file(args.tls_cert),
        "tls_key": sudo_test_file(args.tls_key),
    }
    checks = {
        "not_placeholder_domain": not placeholder_domain(args.server_name),
        "dry_run_ok": installer.returncode == 0 and bool(installer_result.get("ok")),
        "candidate_exists": candidate.exists(),
        "sudo_files_exist": all(item.get("ok") for item in sudo_file_checks.values()),
        "does_not_proxy_intake": "proxy_pass http://127.0.0.1:18892" not in candidate_text,
        "proxies_web_console": "proxy_pass http://127.0.0.1:18893" in candidate_text,
        "blocks_post_goals": "location = /api/goals" in candidate_text and "if ($request_method !~ ^(GET)$) { return 403; }" in candidate_text,
        "keeps_submit_readonly_layer": "if ($request_method !~ ^(GET|HEAD)$) { return 403; }" in candidate_text,
        "has_basic_auth": "auth_basic" in candidate_text and "auth_basic_user_file" in candidate_text,
    }
    report = {
        "checked_at": now_iso(),
        "ok": all(checks.values()),
        "server_name": args.server_name,
        "candidate": str(candidate),
        "installer_return_code": installer.returncode,
        "installer_result": installer_result,
        "sudo_file_checks": sudo_file_checks,
        "checks": checks,
        "next_command_if_ok": "python3 scripts/dev_employee_install_nginx_readonly_console.py --server-name {server} --htpasswd-file {htpasswd} --tls-cert {cert} --tls-key {key} --apply".format(server=args.server_name, htpasswd=args.htpasswd_file, cert=args.tls_cert, key=args.tls_key),
        "notes": [
            "This script did not install or reload Nginx.",
            "Run --apply only if ok is true and the server_name is a real domain you intend to expose.",
            "The installed route remains read-only; POST /api/goals stays blocked."
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
