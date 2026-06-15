#!/usr/bin/env python3
"""Sanitized Codex authentication/readiness preflight for ORIS.

The preflight performs a harmless, read-only ``codex exec`` using the same Linux
identity, HOME, executable, and working directory as the caller. It never reads
or prints authentication files and never persists raw credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import pwd
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUCCESS_MARKER = "ORIS_CODEX_AUTH_OK"
DEFAULT_TIMEOUT_SECONDS = 120

_AUTH_FAILURE_PATTERNS = (
    "refresh_token_reused",
    "failed to refresh token",
    "access token could not be refreshed",
    "401 unauthorized",
    "please log out and sign in again",
    "please sign in",
    "not logged in",
    "authentication required",
)

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization:\s*bearer\s+)[^\s]+"),
    re.compile(r'(?i)("(?:access|refresh|id)_token"\s*:\s*")[^"]+(")'),
    re.compile(r"(?i)((?:access|refresh|id)_token\s*=\s*)[^\s]+"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}(?:\.[a-zA-Z0-9_-]{10,})?\b"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sanitize_text(text: str, limit: int = 4000) -> str:
    value = text or ""
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 2:
            value = pattern.sub(r"\1<REDACTED>\2", value)
        else:
            value = pattern.sub("<REDACTED>", value)
    return value[-limit:]


def classify_codex_failure(text: str, return_code: int | None = None) -> str:
    lowered = (text or "").lower()
    if any(pattern in lowered for pattern in _AUTH_FAILURE_PATTERNS):
        return "codex_authentication"
    if return_code == 124 or "timed out" in lowered:
        return "codex_preflight_timeout"
    if return_code == 127 or "filenotfounderror" in lowered:
        return "codex_executable_missing"
    return "codex_preflight_failed"


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def run_codex_auth_preflight(
    codex_bin: str | Path,
    workdir: str | Path,
    log_path: str | Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    executable = Path(codex_bin).expanduser().resolve()
    cwd = Path(workdir).expanduser().resolve()
    current_user = pwd.getpwuid(os.getuid()).pw_name
    home = Path.home().resolve()
    env = os.environ.copy()
    env["HOME"] = str(home)
    env.setdefault("USER", current_user)
    env.setdefault("LOGNAME", current_user)
    result: dict[str, Any] = {
        "checked_at": now_iso(),
        "ok": False,
        "status": "preflight_failed",
        "failure_code": None,
        "executor_path": str(executable),
        "executor_version": None,
        "linux_user": current_user,
        "uid": os.getuid(),
        "home": str(home),
        "workdir": str(cwd),
        "return_code": None,
        "marker_observed": False,
        "output_tail": "",
    }

    if not executable.is_file():
        result["failure_code"] = "codex_executable_missing"
        result["return_code"] = 127
        result["output_tail"] = "Codex executable is missing."
        _write_result(log_path, result)
        return result
    if not cwd.is_dir():
        result["failure_code"] = "codex_workdir_missing"
        result["return_code"] = 2
        result["output_tail"] = "Codex preflight working directory is missing."
        _write_result(log_path, result)
        return result

    try:
        version_proc = _run([str(executable), "--version"], cwd=cwd, env=env, timeout=min(timeout, 30))
        version_text = sanitize_text(version_proc.stdout + version_proc.stderr, limit=1000).strip()
        result["executor_version"] = version_text.splitlines()[0] if version_text else None
        if version_proc.returncode != 0:
            result["failure_code"] = classify_codex_failure(version_text, version_proc.returncode)
            result["return_code"] = version_proc.returncode
            result["output_tail"] = version_text
            _write_result(log_path, result)
            return result

        prompt = (
            f"Respond with exactly {SUCCESS_MARKER}. "
            "Do not inspect files, do not modify files, and do not run shell commands."
        )
        proc = _run(
            [
                str(executable),
                "exec",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                prompt,
            ],
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
        combined = sanitize_text(proc.stdout + proc.stderr)
        marker_observed = SUCCESS_MARKER in combined
        result.update(
            {
                "return_code": proc.returncode,
                "marker_observed": marker_observed,
                "output_tail": combined,
            }
        )
        if proc.returncode == 0 and marker_observed:
            result["ok"] = True
            result["status"] = "ready"
            result["failure_code"] = None
        else:
            result["failure_code"] = classify_codex_failure(combined, proc.returncode)
    except subprocess.TimeoutExpired as exc:
        output = sanitize_text((exc.stdout or "") + (exc.stderr or ""))
        result.update(
            {
                "return_code": 124,
                "failure_code": "codex_preflight_timeout",
                "output_tail": output or "Codex authentication preflight timed out.",
            }
        )
    except FileNotFoundError as exc:
        result.update(
            {
                "return_code": 127,
                "failure_code": "codex_executable_missing",
                "output_tail": sanitize_text(repr(exc)),
            }
        )
    except Exception as exc:
        result.update(
            {
                "return_code": 1,
                "failure_code": "codex_preflight_exception",
                "output_tail": sanitize_text(repr(exc)),
            }
        )

    _write_result(log_path, result)
    return result


def _write_result(log_path: str | Path | None, result: dict[str, Any]) -> None:
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a sanitized Codex authentication preflight")
    parser.add_argument("--codex-bin", default="/home/admin/.npm-global/bin/codex")
    parser.add_argument("--workdir", default="/home/admin/projects")
    parser.add_argument("--log")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    args = parser.parse_args()
    result = run_codex_auth_preflight(
        args.codex_bin,
        args.workdir,
        log_path=args.log,
        timeout=max(10, args.timeout),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
