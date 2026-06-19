from __future__ import annotations

from .gateway_http import (
    direct_readonly_probe,
    invoke_tool,
    select_safe_baseline_tool,
    verify_public_routes,
)
from .models import RuntimeContext
from .plugin_runtime import verify_plugin_runtime
from .service_control import restart_service_and_wait, service_snapshot


__all__ = (
    "direct_readonly_probe",
    "gateway_pid",
    "invoke_tool",
    "restart_gateway",
    "select_safe_baseline_tool",
    "verify_plugin_runtime",
    "verify_public_routes",
)


def restart_gateway(context: RuntimeContext, timeout_seconds: int = 45) -> None:
    restart_service_and_wait(context, timeout_seconds)


def gateway_pid(context: RuntimeContext) -> str:
    return service_snapshot(context).main_pid
