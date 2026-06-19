from __future__ import annotations

import hashlib
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import RuntimeContext
from .process import CommandResult, run


_REDACT_PATTERNS = (
    re.compile(
        r"(authorization|bearer|token|password|secret|cookie|api[_-]?key)\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
)
_DROP_MARKERS = (
    "token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "credential",
    "private marker",
    "/private/",
)


@dataclass(frozen=True)
class ServiceSnapshot:
    active_state: str
    main_pid: str
    http_status: int

    @property
    def healthy(self) -> bool:
        return self.active_state == "active" and self.http_status == 200

    def evidence(self) -> dict[str, Any]:
        return {
            "active_state": self.active_state,
            "main_pid_present": bool(self.main_pid and self.main_pid != "0"),
            "http_status": self.http_status,
            "healthy": self.healthy,
        }


class GatewayServiceError(RuntimeError):
    def __init__(self, code: str, safe_evidence: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.safe_evidence = safe_evidence


def _http_status(url: str, timeout: int = 5) -> int:
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return 0


def service_snapshot(context: RuntimeContext) -> ServiceSnapshot:
    active = run(["systemctl", "--user", "is-active", context.gateway_service])
    pid = run(
        [
            "systemctl",
            "--user",
            "show",
            context.gateway_service,
            "-p",
            "MainPID",
            "--value",
        ]
    )
    return ServiceSnapshot(
        active_state=active.stdout.strip() if active.returncode == 0 else "inactive",
        main_pid=pid.stdout.strip() if pid.returncode == 0 else "",
        http_status=_http_status(context.gateway_url.rstrip("/") + "/"),
    )


def _digest(result: CommandResult) -> dict[str, Any]:
    combined = (result.stdout + "\n" + result.stderr).encode("utf-8", errors="replace")
    return {
        "returncode": result.returncode,
        "stdout_bytes": len(result.stdout.encode("utf-8", errors="replace")),
        "stderr_bytes": len(result.stderr.encode("utf-8", errors="replace")),
        "output_sha256": hashlib.sha256(combined).hexdigest(),
    }


def _safe_rows(text: str, limit: int) -> list[str]:
    rows: list[str] = []
    for raw in text.splitlines():
        lowered = raw.lower()
        if any(marker in lowered for marker in _DROP_MARKERS):
            continue
        value = raw
        for pattern in _REDACT_PATTERNS:
            value = pattern.sub("<redacted>", value)
        value = value.strip()
        if not value:
            continue
        rows.append(value[:320])
        if len(rows) >= limit:
            break
    return rows


def capture_service_failure(context: RuntimeContext) -> dict[str, Any]:
    status = run(
        [
            "systemctl",
            "--user",
            "status",
            context.gateway_service,
            "--no-pager",
            "--lines=40",
        ],
        timeout=30,
    )
    journal = run(
        [
            "journalctl",
            "--user",
            "-u",
            context.gateway_service,
            "--no-pager",
            "--output=short-monotonic",
            "-n",
            "80",
        ],
        timeout=30,
    )
    return {
        "snapshot": service_snapshot(context).evidence(),
        "systemctl": {
            **_digest(status),
            "status_rows": _safe_rows(status.stdout + "\n" + status.stderr, 40),
        },
        "journalctl": {
            **_digest(journal),
            "journal_rows": _safe_rows(journal.stdout + "\n" + journal.stderr, 80),
        },
        "bounded": True,
        "sanitized": True,
        "raw_config_recorded": False,
        "secret_values_recorded": False,
    }


def restart_service_and_wait(
    context: RuntimeContext,
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    before = service_snapshot(context)
    restarted = run(["systemctl", "--user", "restart", context.gateway_service])
    if restarted.returncode != 0:
        raise GatewayServiceError(
            "gateway_restart_failed",
            {
                "before": before.evidence(),
                "restart": _digest(restarted),
                "failure_diagnostics": capture_service_failure(context),
            },
        )
    deadline = time.monotonic() + timeout_seconds
    after = service_snapshot(context)
    while time.monotonic() < deadline:
        after = service_snapshot(context)
        if after.healthy:
            return {"before": before.evidence(), "after": after.evidence()}
        time.sleep(1)
    raise GatewayServiceError(
        "gateway_health_timeout",
        {
            "before": before.evidence(),
            "after": after.evidence(),
            "failure_diagnostics": capture_service_failure(context),
        },
    )
