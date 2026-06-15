#!/usr/bin/env python3
"""Runtime wrapper for the conversation-first ORIS Web Console.

All chat/admin behavior remains implemented in v3. This wrapper reports the
actual OpenClaw CLI/Gateway provider readiness instead of the obsolete HTTP URL
configuration assumption.
"""

from __future__ import annotations

import os
from http.server import ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

import dev_employee_web_console_v3 as v3
from dev_employee_openclaw_provider import configured_provider


class Handler(v3.Handler):
    server_version = "oris-dev-employee-web-console/0.4"

    def do_GET(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/health":
            provider = configured_provider()
            return v3.json_response(
                self,
                200,
                {
                    "status": "ok",
                    "service": "dev_employee_web_console_v4",
                    "default_experience": "conversation",
                    "admin_route": "/admin",
                    "openclaw_provider_configured": provider is not None,
                    "openclaw_provider_type": type(provider).__name__ if provider is not None else None,
                    "openclaw_gateway_required": os.environ.get("ORIS_OPENCLAW_REQUIRE_GATEWAY", "1").strip().lower()
                    not in {"0", "false", "no"},
                },
            )
        return super().do_GET()


def main() -> int:
    host = os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_HOST", v3.DEFAULT_HOST)
    port = int(os.environ.get("ORIS_DEV_EMPLOYEE_WEB_CONSOLE_PORT", str(v3.DEFAULT_PORT)))
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Refusing to bind non-loopback host")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ORIS conversational Web Console v4 listening on http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
