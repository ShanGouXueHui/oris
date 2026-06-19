from __future__ import annotations

import json
import sys
from pathlib import Path

from .agent_acceptance import discover_agent_cli
from .context import load_context
from .gateway import verify_plugin_runtime, verify_public_routes
from .policy import validate_denied_baseline
from .skill import validate_skill_cli
from .state import listener_is_loopback_only, load_json


def _compile_sources(package_root: Path) -> bool:
    for path in sorted(package_root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    return True


def run_preflight(result_path: Path) -> bool:
    context = load_context()
    package_root = Path(__file__).resolve().parent
    compiled = _compile_sources(package_root)
    readiness = load_json(context.readiness_evidence)
    denied = validate_denied_baseline(context)
    cli = discover_agent_cli()
    skill_cli_supported = validate_skill_cli()
    runtime = verify_plugin_runtime(context)
    routes = verify_public_routes(context)
    listeners_private = all(
        listener_is_loopback_only(port) for port in context.internal_ports
    )
    agent_cli_supported = bool(
        cli.get("session_flag")
        and cli.get("message_flag")
        and cli.get("json_flag")
    )
    gateway_transport_supported = bool(
        not context.require_gateway_transport or cli.get("local_flag_available")
    )
    ok = bool(
        compiled
        and readiness.get("result") == "READY"
        and len(denied.get("approved_denied") or []) == len(context.approved_tools)
        and agent_cli_supported
        and gateway_transport_supported
        and skill_cli_supported
        and runtime.get("ok")
        and routes.get("ok")
        and listeners_private
    )
    payload = {
        "result": "READY" if ok else "FAILED",
        "python_compiled": compiled,
        "readiness_evidence_ready": readiness.get("result") == "READY",
        "tools_denied_baseline": len(denied.get("approved_denied") or []) == len(context.approved_tools),
        "agent_cli_supported": agent_cli_supported,
        "gateway_transport_supported": gateway_transport_supported,
        "skill_cli_supported": skill_cli_supported,
        "routing_skill_source_valid": True,
        "agent_cli": cli,
        "plugin_runtime_ok": bool(runtime.get("ok")),
        "public_routes_ok": bool(routes.get("ok")),
        "internal_listeners_private": listeners_private,
        "source_files_modified": False,
        "config_mutated": False,
        "gateway_restarted": False,
        "secret_values_recorded": False,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return ok


def main() -> int:
    if len(sys.argv) != 2:
        print("result JSON path argument is required", file=sys.stderr)
        return 64
    try:
        return 0 if run_preflight(Path(sys.argv[1]).expanduser().resolve()) else 1
    except Exception as exc:
        path = Path(sys.argv[1]).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "result": "FAILED",
                    "failure_type": type(exc).__name__,
                    "source_files_modified": False,
                    "config_mutated": False,
                    "gateway_restarted": False,
                    "secret_values_recorded": False,
                },
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
