#!/usr/bin/env python3
"""Install ORIS Dev Employee Web Console as a systemd user service.

The service is local-only and proxies to the already verified local intake
service. It does not expose the console publicly.
"""

from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
ENV_FILE = Path.home() / ".config" / "oris" / "dev_employee_enqueue.env"
SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_NAME = "oris-dev-employee-web-console.service"
SERVICE_PATH = SYSTEMD_USER_DIR / SERVICE_NAME

SERVICE_CONTENT = f"""[Unit]
Description=ORIS Dev Employee Web Console
After=network.target oris-dev-employee-intake.service

[Service]
Type=simple
WorkingDirectory={ORIS_DIR}
EnvironmentFile={ENV_FILE}
Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST=127.0.0.1
Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT=18893
Environment=ORIS_DEV_EMPLOYEE_INTAKE_URL=http://127.0.0.1:18892
Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST=oris-final-acceptance-api
Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0
ExecStart=/usr/bin/python3 {ORIS_DIR}/scripts/dev_employee_web_console.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
"""


def ensure_env_key(key: str) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    if any(line.strip().startswith(f"{key}=") for line in existing):
        return
    with ENV_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"{key}={secrets.token_urlsafe(32)}\n")
    ENV_FILE.chmod(0o600)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def main() -> int:
    script = ORIS_DIR / "scripts" / "dev_employee_web_console.py"
    if not script.exists():
        raise SystemExit(f"ERROR: missing {script}")
    if not ENV_FILE.exists():
        raise SystemExit(f"ERROR: missing local env file {ENV_FILE}; install intake service first")
    ensure_env_key("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN")
    SYSTEMD_USER_DIR.mkdir(parents=True, exist_ok=True)
    SERVICE_PATH.write_text(SERVICE_CONTENT, encoding="utf-8")
    run(["python3", "-m", "py_compile", "scripts/dev_employee_web_console.py"])
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", SERVICE_NAME])
    run(["systemctl", "--user", "restart", SERVICE_NAME])
    run(["systemctl", "--user", "is-active", SERVICE_NAME])
    print(f"INSTALLED {SERVICE_NAME}")
    print(f"SERVICE_PATH={SERVICE_PATH}")
    print("BIND=127.0.0.1:18893")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
