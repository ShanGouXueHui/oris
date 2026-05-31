#!/usr/bin/env python3
"""Offline nginx -t validator for read-only ORIS Web Console config, v2.

This version is self-contained for nginx prefix testing: it creates the minimal
files nginx expects under a temporary prefix and does not install or reload the
real Nginx service.
"""

from __future__ import annotations

import json
import shutil
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
        top_conf = conf_dir / "nginx.conf"
        top_conf.write_text("daemon off;\nevents { worker_connections 64; }\nhttp {\n    include mime.types;\n    default_type application/octet-stream;\n    include " + str(rendered) + ";\n}\n", encoding="utf-8")
        test = run([nginx_bin, "-t", "-p", str(prefix), "-c", str(top_conf)])
        rendered_text = rendered.read_text(encoding="utf-8") if rendered.exists() else ""
        checks = {
            "rendered_exists": rendered.exists(),
            "does_not_proxy_intake": "proxy_pass http://127.0.0.1:18892" not in rendered_text,
            "proxies_web_console": "proxy_pass http://127.0.0.1:18893" in rendered_text,
            "post_goals_blocked": "location = /api/goals" in rendered_text and "limit_except GET" in rendered_text and "return 403" in rendered_text,
            "has_basic_auth": "auth_basic" in rendered_text and "auth_basic_user_file" in rendered_text,
        }
        report.update({"openssl_return_code": openssl.returncode, "renderer_return_code": render.returncode, "nginx_test_return_code": test.returncode, "nginx_test_stdout": test.stdout[-2000:], "nginx_test_stderr": test.stderr[-2000:], "checks": checks})
    report["ok"] = report.get("openssl_return_code") == 0 and report.get("renderer_return_code") == 0 and report.get("nginx_test_return_code") == 0 and all((report.get("checks") or {}).values())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
