#!/usr/bin/env python3
"""Patch ORIS Dev Employee Web Console with submit audit logging.

The audit log is local JSONL and intentionally excludes token/header values.
It records POST /api/goals attempts, including blocked attempts such as
unauthorized, submit_disabled, invalid body, and project_not_allowed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
CONSOLE = ORIS_DIR / "scripts" / "dev_employee_web_console.py"
POLICY = ORIS_DIR / "docs" / "DEV_EMPLOYEE_WEB_CONSOLE_ACCESS_POLICY_2026-05-29.md"


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
    if "WEB_CONSOLE_AUDIT_DIR" in text and "write_audit_event(" in text:
        return False
    changed = False
    if "from datetime import datetime, timezone" not in text:
        text = text.replace("import urllib.request\n", "import urllib.request\nfrom datetime import datetime, timezone\n", 1)
        changed = True
    if "ORIS_DIR = Path(" not in text:
        text = text.replace(
            "DEFAULT_ENV_FILE = Path.home() / \".config\" / \"oris\" / \"dev_employee_enqueue.env\"\n",
            "ORIS_DIR = Path(\"/home/admin/projects/oris\")\nWEB_CONSOLE_AUDIT_DIR = ORIS_DIR / \"logs\" / \"dev_employee\" / \"web_console_audit\"\nDEFAULT_ENV_FILE = Path.home() / \".config\" / \"oris\" / \"dev_employee_enqueue.env\"\n",
            1,
        )
        changed = True
    marker = "def load_env(path: Path) -> dict[str, str]:\n"
    audit_helpers = '''def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def audit_path() -> Path:
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d")
    return WEB_CONSOLE_AUDIT_DIR / f"web_console_audit_{stamp}.jsonl"


def write_audit_event(handler: BaseHTTPRequestHandler, event: dict[str, Any]) -> None:
    safe = {
        "ts": now_iso(),
        "remote_addr": handler.client_address[0] if handler.client_address else None,
        "method": handler.command,
        "path": handler.path,
        **event,
    }
    # Never persist token/header values.
    for forbidden in ["token", "headers", "authorization", "x_oris_console_token", "x-oris-console-token"]:
        safe.pop(forbidden, None)
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")


'''
    if audit_helpers not in text:
        text = text.replace(marker, audit_helpers + marker, 1)
        changed = True
    old = '''    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/goals":
            return json_response(self, 404, {"error": "not_found"})
        try:
            if not console_auth_ok(self):
                return json_response(self, 401, {"error": "unauthorized"})
            if not submit_enabled():
                return json_response(self, 403, {"error": "submit_disabled"})
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            project_key = str(payload.get("project_key") or "")
            if project_key not in allowed_projects():
                return json_response(self, 403, {"error": "project_not_allowed", "project_key": project_key})
            status, body = intake_request("POST", "/goals", body=payload, auth=True)
            return json_response(self, status, body)
        except Exception as exc:
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})
'''
    new = '''    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/goals":
            return json_response(self, 404, {"error": "not_found"})
        event_base = {"action": "submit_goal"}
        try:
            if not console_auth_ok(self):
                write_audit_event(self, {**event_base, "result": "rejected", "reason": "unauthorized"})
                return json_response(self, 401, {"error": "unauthorized"})
            if not submit_enabled():
                write_audit_event(self, {**event_base, "result": "rejected", "reason": "submit_disabled"})
                return json_response(self, 403, {"error": "submit_disabled"})
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 80_000:
                write_audit_event(self, {**event_base, "result": "rejected", "reason": "invalid_body_length", "body_length": length})
                return json_response(self, 400, {"error": "invalid_body_length"})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            project_key = str(payload.get("project_key") or "")
            task_id = str(payload.get("task_id") or "")
            objective = str(payload.get("objective") or "")
            if project_key not in allowed_projects():
                write_audit_event(self, {**event_base, "result": "rejected", "reason": "project_not_allowed", "project_key": project_key, "task_id": task_id})
                return json_response(self, 403, {"error": "project_not_allowed", "project_key": project_key})
            status, body = intake_request("POST", "/goals", body=payload, auth=True)
            write_audit_event(
                self,
                {
                    **event_base,
                    "result": "submitted" if 200 <= status < 300 else "upstream_error",
                    "upstream_status": status,
                    "project_key": project_key,
                    "task_id": task_id or (body.get("task_id") if isinstance(body, dict) else None),
                    "objective_length": len(objective),
                    "constraints_count": len(payload.get("constraints") or []),
                    "expected_checks_count": len(payload.get("expected_checks") or []),
                },
            )
            return json_response(self, status, body)
        except Exception as exc:
            write_audit_event(self, {**event_base, "result": "error", "reason": type(exc).__name__})
            return json_response(self, 400, {"error": type(exc).__name__, "message": str(exc)})
'''
    if old in text:
        text = text.replace(old, new, 1)
        changed = True
    if changed:
        CONSOLE.write_text(text, encoding="utf-8")
    return changed


def patch_policy() -> bool:
    text = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    block = """
## Submit audit logging

The Web Console writes local JSONL audit records for every `POST /api/goals` attempt.

Audit directory:

```text
logs/dev_employee/web_console_audit/
```

Audit events intentionally exclude token/header values. Events may include:

- timestamp;
- remote address;
- action;
- result;
- rejection reason;
- project key;
- task id;
- objective length;
- constraints/check count;
- upstream intake status.

Submit remains disabled by default. Audit logging must be verified before enabling submit in any public or reverse-proxied environment.
"""
    if "## Submit audit logging" in text:
        return False
    POLICY.write_text(text.rstrip() + "\n" + block + "\n", encoding="utf-8")
    return True


def main() -> int:
    run(["git", "fetch", "origin", "main"], check=True)
    run(["git", "reset", "--hard", "origin/main"], check=True)
    console_changed = patch_console()
    policy_changed = patch_policy()
    run(["python3", "-m", "py_compile", "scripts/dev_employee_web_console.py"], check=True)
    run(["git", "add", "scripts/dev_employee_web_console.py", "docs/DEV_EMPLOYEE_WEB_CONSOLE_ACCESS_POLICY_2026-05-29.md"], check=True)
    staged = run(["git", "diff", "--cached", "--quiet"])
    if staged.returncode != 0:
        run(["git", "commit", "-m", "feat(dev-employee): audit Web console submit attempts"], check=True)
        run(["git", "push", "origin", "main"], check=True)
    run(["git", "log", "-1", "--oneline"], check=True)
    print({"ok": True, "console_changed": console_changed, "policy_changed": policy_changed})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
