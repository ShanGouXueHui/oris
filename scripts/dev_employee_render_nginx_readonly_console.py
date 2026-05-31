#!/usr/bin/env python3
"""Render and statically validate ORIS Dev Employee read-only Nginx config.

This script does not install or reload Nginx. It renders the template to a target
path and verifies conservative safety invariants.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
TEMPLATE = ORIS_DIR / "ops" / "nginx" / "oris-dev-employee-web-console.readonly.conf.template"
DEFAULT_OUTPUT = Path("/tmp/oris-dev-employee-web-console.readonly.conf")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def active_config_lines(rendered: str) -> str:
    """Return config text with full-line comments removed."""
    lines: list[str] = []
    for raw in rendered.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(raw)
    return "\n".join(lines)


def validate(rendered: str) -> dict[str, object]:
    active = active_config_lines(rendered)
    checks = {
        "no_intake_proxy": "proxy_pass http://127.0.0.1:18892" not in active,
        "web_console_proxy_only": "proxy_pass http://127.0.0.1:18893" in active,
        "blocks_post_goals": "location = /api/goals" in active and "if ($request_method !~ ^(GET)$) { return 403; }" in active,
        "blocks_non_read_root": "if ($request_method !~ ^(GET|HEAD)$) { return 403; }" in active,
        "has_basic_auth": "auth_basic" in active and "auth_basic_user_file" in active,
        "has_https": "listen 443 ssl" in active,
        "has_http_redirect": "listen 80" in active and "return 301 https://$host$request_uri" in active,
        "has_body_limit": "client_max_body_size 64k" in active,
        "has_rate_limit": "limit_req_zone" in active and "limit_req zone=oris_dev_employee_console_read" in active,
        "no_placeholders": "__" not in rendered,
    }
    return {"ok": all(checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Render read-only ORIS Web Console Nginx config")
    parser.add_argument("--server-name", required=True)
    parser.add_argument("--htpasswd-file", default="/etc/nginx/oris-dev-employee.htpasswd")
    parser.add_argument("--tls-cert", default="/etc/letsencrypt/live/example/fullchain.pem")
    parser.add_argument("--tls-key", default="/etc/letsencrypt/live/example/privkey.pem")
    parser.add_argument("--access-log", default="/var/log/nginx/oris-dev-employee-console.access.log")
    parser.add_argument("--error-log", default="/var/log/nginx/oris-dev-employee-console.error.log")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    template = TEMPLATE.read_text(encoding="utf-8")
    rendered = (
        template
        .replace("__SERVER_NAME__", args.server_name)
        .replace("__HTPASSWD_FILE__", args.htpasswd_file)
        .replace("__TLS_CERT__", args.tls_cert)
        .replace("__TLS_KEY__", args.tls_key)
        .replace("__ACCESS_LOG__", args.access_log)
        .replace("__ERROR_LOG__", args.error_log)
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    result = validate(rendered)
    result.update({"rendered_at": now_iso(), "output": str(output), "server_name": args.server_name})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
