#!/usr/bin/env python3
"""Conversation-first ORIS Web Console v5 with Agent Harness.

This runtime keeps the v3 conversation UI and API contract, routes model intent
through the provider-neutral Agent Harness, and exposes the engineering console
at an explicitly labeled /admin route.
"""

from __future__ import annotations

import os
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

import dev_employee_chat_orchestrator as chat_orchestrator
from dev_employee_agent_harness import HARNESS_VERSION, analyze_with_harness

# The existing process_message function resolves analyze_message from its module
# globals at runtime. Replace only that provider boundary; task lifecycle logic
# remains unchanged and authoritative in the existing orchestrator/intake chain.
chat_orchestrator.analyze_message = analyze_with_harness

import dev_employee_web_console_v3 as v3  # noqa: E402
import dev_employee_web_console_v2 as admin_console  # noqa: E402
from dev_employee_openclaw_provider import configured_provider  # noqa: E402


def admin_page() -> str:
    content = admin_console.page()
    content = content.replace(
        "<title>ORIS Dev Employee Console</title>",
        "<title>ORIS Admin Console</title>",
        1,
    )
    content = content.replace(
        "<h1>ORIS Dev Employee Console</h1>",
        "<h1>ORIS Admin Console — engineering diagnostics</h1>",
        1,
    )
    content = content.replace(
        "Local-only prototype over the verified intake/status service. Do not expose publicly without auth/reverse-proxy policy.",
        "Restricted engineering diagnostics over the verified ORIS intake and lifecycle services.",
        1,
    )
    return content


class Handler(v3.Handler):
    server_version = "oris-dev-employee-web-console/0.5"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            provider = configured_provider()
            return v3.json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "dev_employee_web_console_v5",
                    "default_experience": "conversation",
                    "admin_route": "/admin",
                    "agent_harness_enabled": True,
                    "agent_harness_version": HARNESS_VERSION,
                    "agent_harness_provider_mode": os.environ.get("ORIS_AGENT_HARNESS_PROVIDER", "auto"),
                    "openclaw_provider_configured": provider is not None,
                    "openclaw_provider_type": type(provider).__name__ if provider is not None else None,
                    "openclaw_gateway_required": os.environ.get("ORIS_OPENCLAW_REQUIRE_GATEWAY", "1").strip().lower()
                    not in {"0", "false", "no"},
                },
            )
        if path == "/admin":
            return v3.html_response(self, 200, admin_page())
        return super().do_GET()


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", v3.DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(v3.DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS conversational Web Console v5 with Agent Harness listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
