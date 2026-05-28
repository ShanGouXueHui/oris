#!/usr/bin/env python3
"""Install ORIS Dev Employee intake API as a systemd user service.

This installer writes only local user-level service/config files. It does not
open public ports and does not print token values.
"""

from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_NAME = "oris-dev-employee-intake.service"
SERVICE_PATH = SYSTEMD_USER_DIR / SERVICE_NAME

SERVICE_CONTENT = f"""[Unit]
Description=ORIS Dev Employee Intake API
After=network.target

[Service]
Type=simple
WorkingDirectory={ORIS_DIR}
EnvironmentFile={ENV_FILE}
Environment=ORIS_DEV_EMPLOYEE_INTAKE_HOST=127.0.0.1
Environment=ORIS_DEV_EMPLOYEE_INTAKE_PORT=18892
ExecStart=/usr/bin/python3 {ORIS_DIR}/scripts/dev_employee_intake_api.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
"""


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def read_env_lines() -> list[str]:
    if not ENV_FILE.exists():
        return []
    return ENV_FILE.read_text(encoding="utf-8").splitlines()


def ensure_env_key(key: str) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = read_env_lines()
    if any(line.strip().startswith(f"{key}=") for line in lines):
        return
    with ENV_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{key}={secrets.token_urlsafe(32)}\n")
    ENV_FILE.chmod(0o600)


def main() -> int:
    if not (ORIS_DIR / "scripts" / "dev_employee_intake_api.py").exists():
        raise SystemExit("ERROR: dev_employee_intake_api.py not found")
    ensure_env_key("ORIS_DEV_EMPLOYEE_INTAKE_TOKEN")
    ensure_env_key("ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN")
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", SERVICE_NAME])
    run(["systemctl", "--user", "restart", SERVICE_NAME])
    run(["systemctl", "--user", "is-active", SERVICE_NAME])
    print(f"INSTALLED {SERVICE_NAME}")
    print(f"SERVICE_PATH={SERVICE_PATH}")
    print("BIND=127.0.0.1:18892")
    print("TOKEN_VALUES_NOT_PRINTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
