from __future__ import annotations

import ipaddress
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


FREE_MESH_SERVICE = "oris-free-mesh-api.service"
EXPECTED_PROTOCOL_VERSION = 2


def _load_config(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "oris_free_mesh_api.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Free Mesh API config must be an object")
    return value


def _loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def endpoint_from_config(repo_root: Path) -> tuple[str, int, str]:
    config = _load_config(repo_root)
    host = str(config.get("host") or "127.0.0.1")
    port = int(config.get("port") or 8789)
    if not _loopback_host(host):
        raise RuntimeError("Free Mesh API must remain loopback-only")
    if port < 1 or port > 65535:
        raise RuntimeError("Free Mesh API port is invalid")
    return host, port, f"http://{host}:{port}/v1/health"


def validate_health_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError("Free Mesh health response must be an object")
    protocol_version = value.get("protocol_version")
    tool_calling = value.get("tool_calling")
    service = value.get("service")
    healthy = value.get("ok") is True
    accepted = (
        healthy
        and service == "oris-free-mesh-api"
        and protocol_version == EXPECTED_PROTOCOL_VERSION
        and tool_calling is True
    )
    return {
        "accepted": accepted,
        "healthy": healthy,
        "service_matches": service == "oris-free-mesh-api",
        "protocol_version": protocol_version,
        "expected_protocol_version": EXPECTED_PROTOCOL_VERSION,
        "tool_calling": tool_calling is True,
        "raw_response_recorded": False,
    }


def _service_state() -> str:
    result = subprocess.run(
        ["systemctl", "--user", "is-active", FREE_MESH_SERVICE],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "").strip() or "unknown"


def probe_free_mesh_protocol(
    repo_root: Path,
    *,
    attempts: int = 20,
    delay_seconds: float = 0.5,
    timeout_seconds: float = 3.0,
) -> dict[str, Any]:
    host, port, url = endpoint_from_config(repo_root)
    last_error_type = ""
    http_status: int | None = None
    validation: dict[str, Any] = {}
    completed_attempts = 0
    for index in range(max(1, attempts)):
        completed_attempts = index + 1
        try:
            request = urllib.request.Request(
                url,
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                http_status = int(response.status)
                body = json.loads(response.read().decode("utf-8"))
            validation = validate_health_payload(body)
            if http_status == 200 and validation.get("accepted"):
                break
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            UnicodeDecodeError,
            RuntimeError,
        ) as exc:
            last_error_type = type(exc).__name__
        if index + 1 < attempts:
            time.sleep(delay_seconds)
    service_state = _service_state()
    passed = (
        service_state == "active"
        and http_status == 200
        and validation.get("accepted") is True
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "service_state": service_state,
        "listener_loopback": _loopback_host(host),
        "port": port,
        "http_status": http_status,
        "attempts": completed_attempts,
        "last_error_type": last_error_type or None,
        **validation,
        "endpoint_recorded": False,
        "authentication_value_recorded": False,
        "conversation_content_recorded": False,
        "tool_schema_recorded": False,
        "tool_arguments_or_results_recorded": False,
    }
