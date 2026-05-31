#!/usr/bin/env python3
"""Offline nginx -t validator for read-only ORIS Web Console config, v3.

Production template keeps listen 443/80. For offline testing as an unprivileged
user, this script renders the production config, verifies production invariants,
then rewrites only the temporary test copy to random high loopback ports before
running nginx -t. It does not install or reload real Nginx.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ORIS_DIR = Path("/home/admin/projects/oris")
RENDERER = ORIS_DIR / "scripts" / "dev_employee_render_nginx_readonly_console.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], cwd: Path = ORIS_DIR) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    nginx_bin = shutil.which("nginx")
    openssl_bin = shutil.which("openssl")
    report: dict[str, object] = {"validated_at": now_iso(), "nginx_found": bool(nginx_bin), "openssl_found": bool(openssl_bin), "ok": False}
    if not nginx_bin:
        print(json.dumps({**report, "error": "nginx_not_found"}, ensure_ascii=False, indent=2))
        return 2
    if not openssl_bin:
        print(json.dumps({**report, "error": "openssl_not_found"}, ensure_ascii=False, indent=2))
        return 2

    https_port = free_port()
    http_port = free_port()
    with tempfile.TemporaryDirectory(prefix="oris-nginx-readonly-", dir="/var/tmp") as tmp:
        tmpdir = Path(tmp)
        prefix = tmpdir / "prefix"
        conf_dir = prefix / "conf"
        logs_dir = prefix / "logs"
        cert_dir = tmpdir / "certs"
        conf_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        cert_dir.mkdir(parents=True, exist_ok=True)
        (conf_dir / "mime.types").write_text("types {}\n", encoding="utf-8")
        htpasswd = tmpdir / "htpasswd"
        htpasswd.write_text("oris:placeholder\n", encoding="utf-8")
        cert = cert_dir / "fullchain.pem"
        key = cert_dir / "privkey.pem"
        openssl = run([openssl_bin, "req", "-x509", "-nodes", "-newkey", "rsa:2048", "-days", "1", "-subj", "/CN=oris.local", "-keyout", str(key), "-out", str(cert)])
        rendered = conf_dir / "oris-dev-employee-web-console.readonly.conf"
        render = run(["python3", str(RENDERER), "--server-name", "oris.local", "--htpasswd-file", str(htpasswd), "--tls-cert", str(cert), "--tls-key", str(key), "--access-log", str(logs_dir / "access.log"), "--error-log", str(logs_dir / "error.log"), "--output", str(rendered)])
        production_text = rendered.read_text(encoding="utf-8") if rendered.exists() else ""
        test_text = production_text.replace("listen 443 ssl http2;", f"listen 127.0.0.1:{https_port} ssl http2;").replace("listen 80;", f"listen 127.0.0.1:{http_port};")
        rendered.write_text(test_text, encoding="utf-8")
        top_conf = conf_dir / "nginx.conf"
        top_conf.write_text("pid " + str(logs_dir / "nginx.pid") + ";\nerror_log " + str(logs_dir / "nginx-error.log") + " warn;\ndaemon off;\nevents { worker_connections 64; }\nhttp {\n    access_log off;\n    include mime.types;\n    default_type application/octet-stream;\n    include " + str(rendered) + ";\n}\n", encoding="utf-8")
        test = run([nginx_bin, "-t", "-p", str(prefix), "-c", str(top_conf)])
        checks = {
            "rendered_exists": rendered.exists(),
            "production_keeps_https_443": "listen 443 ssl http2;" in production_text,
            "production_keeps_http_80": "listen 80;" in production_text,
            "offline_uses_high_https_port": f"listen 127.0.0.1:{https_port} ssl http2;" in test_text,
            "offline_uses_high_http_port": f"listen 127.0.0.1:{http_port};" in test_text,
            "does_not_proxy_intake": "proxy_pass http://127.0.0.1:18892" not in production_text,
            "proxies_web_console": "proxy_pass http://127.0.0.1:18893" in production_text,
            "post_goals_blocked": "location = /api/goals" in production_text and "if ($request_method !~ ^(GET)$) { return 403; }" in production_text,
            "root_non_read_blocked": "if ($request_method !~ ^(GET|HEAD)$) { return 403; }" in production_text,
            "has_basic_auth": "auth_basic" in production_text and "auth_basic_user_file" in production_text,
            "top_level_logs_are_temp": str(logs_dir) in top_conf.read_text(encoding="utf-8"),
        }
        report.update({"openssl_return_code": openssl.returncode, "renderer_return_code": render.returncode, "nginx_test_return_code": test.returncode, "nginx_test_stdout": test.stdout[-2000:], "nginx_test_stderr": test.stderr[-2000:], "offline_https_port": https_port, "offline_http_port": http_port, "checks": checks})
    report["ok"] = report.get("openssl_return_code") == 0 and report.get("renderer_return_code") == 0 and report.get("nginx_test_return_code") == 0 and all((report.get("checks") or {}).values())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
