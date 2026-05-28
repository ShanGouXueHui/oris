#!/usr/bin/env python3
"""Patch ORIS Dev Employee Web Console security controls.

Adds:
- Web console API token gate separate from intake token.
- Project allowlist filtering/enforcement.
- Submit enable switch, defaulting to disabled in the installer.
- UI token input stored in localStorage and sent as X-ORIS-Console-Token.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
CONSOLE = ORIS_DIR / "scripts" / "dev_employee_web_console.py"
INSTALLER = ORIS_DIR / "scripts" / "dev_employee_install_web_console_service.py"


def run(cmd: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=str(ORIS_DIR), text=True, capture_output=True, check=False)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="")
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def patch_console() -> bool:
    text = CONSOLE.read_text(encoding="utf-8")
    if "CONSOLE_TOKEN_KEY" in text and "submit_enabled()" in text:
        return False
    text = text.replace(
        'INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"\nAUTH_HEADER = "X-ORIS-Token"\n',
        'INTAKE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_INTAKE_TOKEN"\nCONSOLE_TOKEN_KEY = "ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN"\nCONSOLE_AUTH_HEADER = "X-ORIS-Console-Token"\nAUTH_HEADER = "X-ORIS-Token"\n',
        1,
    )
    text = text.replace(
        '''def intake_token() -> str:\n    token = os.environ.get(INTAKE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(INTAKE_TOKEN_KEY)\n    if not token:\n        raise RuntimeError(f"{INTAKE_TOKEN_KEY} missing from environment or local config")\n    return token\n\n\ndef json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:\n''',
        '''def intake_token() -> str:\n    token = os.environ.get(INTAKE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(INTAKE_TOKEN_KEY)\n    if not token:\n        raise RuntimeError(f"{INTAKE_TOKEN_KEY} missing from environment or local config")\n    return token\n\n\ndef console_token() -> str:\n    token = os.environ.get(CONSOLE_TOKEN_KEY) or load_env(DEFAULT_ENV_FILE).get(CONSOLE_TOKEN_KEY)\n    if not token:\n        raise RuntimeError(f"{CONSOLE_TOKEN_KEY} missing from environment or local config")\n    return token\n\n\ndef console_auth_ok(handler: BaseHTTPRequestHandler) -> bool:\n    return (handler.headers.get(CONSOLE_AUTH_HEADER) or "") == console_token()\n\n\ndef allowed_projects() -> set[str]:\n    raw = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST", "oris-final-acceptance-api")\n    return {item.strip() for item in raw.split(",") if item.strip()}\n\n\ndef submit_enabled() -> bool:\n    return os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED", "0").lower() in {"1", "true", "yes", "on"}\n\n\ndef filter_projects(body: Any) -> Any:\n    if not isinstance(body, dict):\n        return body\n    projects = body.get("projects")\n    if not isinstance(projects, list):\n        return body\n    allow = allowed_projects()\n    return {**body, "projects": [item for item in projects if item in allow]}\n\n\ndef json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:\n''',
        1,
    )
    text = text.replace(
        '''      <div class="muted">Human supplies goal and constraints; ORIS decides routine engineering steps.</div>\n      <label>Project</label>\n''',
        '''      <div class="muted">Human supplies goal and constraints; ORIS decides routine engineering steps.</div>\n      <label>Console API token</label>\n      <input id="console_token" type="password" placeholder="paste local console token" />\n      <div class="muted">Stored only in this browser localStorage. Do not expose publicly without reverse-proxy auth.</div>\n      <label>Project</label>\n''',
        1,
    )
    text = text.replace(
        '''const splitLines = (value) => value.split('\\n').map(x => x.trim()).filter(Boolean);\nasync function api(path, options={}) {\n  const resp = await fetch(path, options);\n''',
        '''const splitLines = (value) => value.split('\\n').map(x => x.trim()).filter(Boolean);\nfunction consoleToken() { return document.getElementById('console_token').value.trim(); }\nfunction rememberToken() { localStorage.setItem('oris_console_token', consoleToken()); }\nasync function api(path, options={}) {\n  const headers = Object.assign({}, options.headers || {});\n  const token = consoleToken();\n  if (token) headers['X-ORIS-Console-Token'] = token;\n  const resp = await fetch(path, Object.assign({}, options, {headers}));\n''',
        1,
    )
    text = text.replace(
        '''  const data = await api('/api/projects');\n''',
        '''  rememberToken();\n  const data = await api('/api/projects');\n''',
        1,
    )
    text = text.replace(
        '''  const payload = {\n''',
        '''  rememberToken();\n  const payload = {\n''',
        1,
    )
    text = text.replace(
        '''  const data = await api('/api/goals/' + encodeURIComponent(taskId));\n''',
        '''  rememberToken();\n  const data = await api('/api/goals/' + encodeURIComponent(taskId));\n''',
        1,
    )
    text = text.replace(
        '''loadProjects().catch(e => { document.getElementById('submit_result').textContent = String(e); });\n''',
        '''document.getElementById('console_token').value = localStorage.getItem('oris_console_token') || '';\nloadProjects().catch(e => { document.getElementById('submit_result').textContent = String(e); });\n''',
        1,
    )
    text = text.replace(
        '''        if path == "/api/projects":\n            status, body = intake_request("GET", "/projects")\n            return json_response(self, status, body)\n        if path == "/api/goals":\n            status, body = intake_request("GET", "/goals")\n            return json_response(self, status, body)\n        if path.startswith("/api/goals/"):\n            task_id = unquote(path.removeprefix("/api/goals/"))\n            status, body = intake_request("GET", f"/goals/{task_id}")\n            return json_response(self, status, body)\n''',
        '''        if path == "/api/projects":\n            if not console_auth_ok(self):\n                return json_response(self, 401, {"error": "unauthorized"})\n            status, body = intake_request("GET", "/projects")\n            return json_response(self, status, filter_projects(body))\n        if path == "/api/goals":\n            if not console_auth_ok(self):\n                return json_response(self, 401, {"error": "unauthorized"})\n            status, body = intake_request("GET", "/goals")\n            return json_response(self, status, body)\n        if path.startswith("/api/goals/"):\n            if not console_auth_ok(self):\n                return json_response(self, 401, {"error": "unauthorized"})\n            task_id = unquote(path.removeprefix("/api/goals/"))\n            status, body = intake_request("GET", f"/goals/{task_id}")\n            return json_response(self, status, body)\n''',
        1,
    )
    text = text.replace(
        '''        try:\n            length = int(self.headers.get("Content-Length") or "0")\n            if length <= 0 or length > 80_000:\n                return json_response(self, 400, {"error": "invalid_body_length"})\n            payload = json.loads(self.rfile.read(length).decode("utf-8"))\n            status, body = intake_request("POST", "/goals", body=payload, auth=True)\n            return json_response(self, status, body)\n''',
        '''        try:\n            if not console_auth_ok(self):\n                return json_response(self, 401, {"error": "unauthorized"})\n            if not submit_enabled():\n                return json_response(self, 403, {"error": "submit_disabled"})\n            length = int(self.headers.get("Content-Length") or "0")\n            if length <= 0 or length > 80_000:\n                return json_response(self, 400, {"error": "invalid_body_length"})\n            payload = json.loads(self.rfile.read(length).decode("utf-8"))\n            project_key = str(payload.get("project_key") or "")\n            if project_key not in allowed_projects():\n                return json_response(self, 403, {"error": "project_not_allowed", "project_key": project_key})\n            status, body = intake_request("POST", "/goals", body=payload, auth=True)\n            return json_response(self, status, body)\n''',
        1,
    )
    CONSOLE.write_text(text, encoding="utf-8")
    return True


def patch_installer() -> bool:
    text = INSTALLER.read_text(encoding="utf-8")
    changed = False
    if "import secrets" not in text:
        text = text.replace("from __future__ import annotations\n\nimport subprocess\n", "from __future__ import annotations\n\nimport secrets\nimport subprocess\n", 1)
        changed = True
    if "Environment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0" not in text:
        text = text.replace(
            "Environment=ORIS_DEV_EMPLOYEE_INTAKE_URL=http://127.0.0.1:18892\n",
            "Environment=ORIS_DEV_EMPLOYEE_INTAKE_URL=http://127.0.0.1:18892\nEnvironment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PROJECT_ALLOWLIST=oris-final-acceptance-api\nEnvironment=ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=0\n",
            1,
        )
        changed = True
    if "def ensure_env_key(" not in text:
        text = text.replace(
            '''def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:\n''',
            '''def ensure_env_key(key: str) -> None:\n    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)\n    existing = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []\n    if any(line.strip().startswith(f"{key}=") for line in existing):\n        return\n    with ENV_FILE.open("a", encoding="utf-8") as fh:\n        fh.write(f"{key}={secrets.token_urlsafe(32)}\\n")\n    ENV_FILE.chmod(0o600)\n\n\ndef run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:\n''',
            1,
        )
        changed = True
    if "ensure_env_key(\"ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN\")" not in text:
        text = text.replace(
            '''    if not ENV_FILE.exists():\n        raise SystemExit(f"ERROR: missing local env file {ENV_FILE}; install intake service first")\n''',
            '''    if not ENV_FILE.exists():\n        raise SystemExit(f"ERROR: missing local env file {ENV_FILE}; install intake service first")\n    ensure_env_key("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_TOKEN")\n''',
            1,
        )
        changed = True
    if changed:
        INSTALLER.write_text(text, encoding="utf-8")
    return changed


def main() -> int:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    console_changed = patch_console()
    installer_changed = patch_installer()
    run(["python3", "-m", "py_compile", "scripts/dev_employee_web_console.py", "scripts/dev_employee_install_web_console_service.py"], check=True)
    run(["git", "add", "scripts/dev_employee_web_console.py", "scripts/dev_employee_install_web_console_service.py"], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "feat(dev-employee): gate Web console API with token"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print({"ok": True, "console_changed": console_changed, "installer_changed": installer_changed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
