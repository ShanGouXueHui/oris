#!/usr/bin/env python3
"""Run read-only Web Console Nginx commands from local .env.

The local .env is ignored by git. This wrapper reads non-secret route settings
from .env and delegates to the existing dry-run/readiness/apply scripts.
It does not store Basic Auth passwords or TLS private key content.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
ENV_PATH = ORIS_DIR / ".env"
INSTALLER = ORIS_DIR / "scripts" / "dev_employee_install_nginx_readonly_console.py"
READINESS = ORIS_DIR / "scripts" / "dev_employee_check_nginx_readonly_console_apply_readiness.py"


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def require(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise SystemExit(f"ERROR: missing {key} in {ENV_PATH}")
    return value


def run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, check=False)
    return proc.returncode


def command(values: dict[str, str], mode: str) -> list[str]:
    server = require(values, "ORIS_NGINX_READONLY_CONSOLE_SERVER_NAME")
    htpasswd = require(values, "ORIS_NGINX_READONLY_CONSOLE_HTPASSWD_FILE")
    cert = require(values, "ORIS_NGINX_READONLY_CONSOLE_TLS_CERT")
    key = require(values, "ORIS_NGINX_READONLY_CONSOLE_TLS_KEY")
    candidate = values.get("ORIS_NGINX_READONLY_CONSOLE_CANDIDATE", "/tmp/oris-dev-employee-web-console.readonly.conf")
    base = [
        "python3",
        str(READINESS if mode == "readiness" else INSTALLER),
        "--server-name",
        server,
        "--htpasswd-file",
        htpasswd,
        "--tls-cert",
        cert,
        "--tls-key",
        key,
    ]
    if mode in {"dry-run", "readiness"}:
        base.extend(["--candidate", candidate])
    if mode == "apply":
        base.extend(["--candidate", candidate, "--apply"])
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description="Run read-only console Nginx workflow from .env")
    parser.add_argument("mode", choices=["show", "dry-run", "readiness", "apply"])
    args = parser.parse_args()
    values = load_env(ENV_PATH)
    if args.mode == "show":
        safe = {key: value for key, value in values.items() if "PASSWORD" not in key and "TOKEN" not in key}
        print(json.dumps({"env_path": str(ENV_PATH), "values": safe}, ensure_ascii=False, indent=2))
        return 0
    return run(command(values, args.mode))


if __name__ == "__main__":
    raise SystemExit(main())
