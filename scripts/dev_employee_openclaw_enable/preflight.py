from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from .agent_acceptance import discover_agent_cli
from .context import load_context
from .gateway import verify_plugin_runtime, verify_public_routes
from .policy import validate_denied_baseline
from .skill import validate_skill_install_target
from .state import listener_is_loopback_only, load_json


def _compile_sources(package_root: Path) -> bool:
    for path in sorted(package_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    return True


def _run_check(
    payload: dict[str, Any],
    key: str,
    operation: Callable[[], Any],
) -> Any | None:
    try:
        value = operation()
        payload[key] = bool(value)
        return value
    except Exception as exc:
        payload[key] = False
        if payload.get("failure_stage") is None:
            payload["failure_stage"] = key
            payload["failure_type"] = type(exc).__name__
        return None


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def run_preflight(result_path: Path) -> bool:
    payload: dict[str, Any] = {
        "result": "FAILED",
        "failure_stage": None,
        "failure_type": None,
        "context_loaded": False,
        "python_compiled": False,
        "readiness_evidence_ready": False,
        "tools_denied_baseline": False,
        "agent_cli_supported": False,
        "gateway_transport_supported": False,
        "skill_install_target_ready": False,
        "routing_skill_source_valid": False,
        "plugin_runtime_ok": False,
        "public_routes_ok": False,
        "internal_listeners_private": False,
        "source_files_modified": False,
        "config_mutated": False,
        "gateway_restarted": False,
        "secret_values_recorded": False,
    }

    package_root = Path(__file__).resolve().parent
    _run_check(payload, "python_compiled", lambda: _compile_sources(package_root))
    context = _run_check(payload, "context_loaded", load_context)
    if context is None:
        _write_result(result_path, payload)
        return False

    readiness = _run_check(
        payload,
        "readiness_evidence_ready",
        lambda: load_json(context.readiness_evidence).get("result") == "READY",
    )
    denied = _run_check(
        payload,
        "tools_denied_baseline",
        lambda: len(validate_denied_baseline(context).get("approved_denied") or [])
        == len(context.approved_tools),
    )
    cli = _run_check(payload, "agent_cli_supported", discover_agent_cli)
    agent_cli_supported = bool(
        isinstance(cli, dict)
        and cli.get("session_flag")
        and cli.get("message_flag")
        and cli.get("json_flag")
    )
    payload["agent_cli_supported"] = agent_cli_supported
    payload["gateway_transport_supported"] = agent_cli_supported
    if isinstance(cli, dict):
        payload["agent_cli"] = cli

    skill_ready = _run_check(
        payload,
        "skill_install_target_ready",
        lambda: validate_skill_install_target(context),
    )
    payload["routing_skill_source_valid"] = bool(skill_ready)

    runtime = _run_check(
        payload,
        "plugin_runtime_ok",
        lambda: verify_plugin_runtime(context).get("ok") is True,
    )
    routes = _run_check(
        payload,
        "public_routes_ok",
        lambda: verify_public_routes(context).get("ok") is True,
    )
    listeners = _run_check(
        payload,
        "internal_listeners_private",
        lambda: all(
            listener_is_loopback_only(port) for port in context.internal_ports
        ),
    )

    required = (
        payload["python_compiled"],
        payload["context_loaded"],
        bool(readiness),
        bool(denied),
        agent_cli_supported,
        payload["gateway_transport_supported"],
        bool(skill_ready),
        bool(runtime),
        bool(routes),
        bool(listeners),
    )
    ok = all(required)
    payload["result"] = "READY" if ok else "FAILED"
    if not ok and payload.get("failure_stage") is None:
        for key in (
            "python_compiled",
            "context_loaded",
            "readiness_evidence_ready",
            "tools_denied_baseline",
            "agent_cli_supported",
            "gateway_transport_supported",
            "skill_install_target_ready",
            "plugin_runtime_ok",
            "public_routes_ok",
            "internal_listeners_private",
        ):
            if payload.get(key) is not True:
                payload["failure_stage"] = key
                payload["failure_type"] = "CheckFailed"
                break
    _write_result(result_path, payload)
    return ok


def main() -> int:
    if len(sys.argv) != 2:
        print("result JSON path argument is required", file=sys.stderr)
        return 64
    result_path = Path(sys.argv[1]).expanduser().resolve()
    try:
        return 0 if run_preflight(result_path) else 1
    except Exception as exc:
        _write_result(
            result_path,
            {
                "result": "FAILED",
                "failure_stage": "preflight_bootstrap",
                "failure_type": type(exc).__name__,
                "source_files_modified": False,
                "config_mutated": False,
                "gateway_restarted": False,
                "secret_values_recorded": False,
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
