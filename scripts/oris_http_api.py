#!/usr/bin/env python3
import json
import subprocess
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
INFER_SCRIPT = ROOT / "scripts" / "oris_infer.py"
PLAN_PATH = ROOT / "orchestration" / "runtime_plan.json"
HOST = "127.0.0.1"
PORT = 8788

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

class Handler(BaseHTTPRequestHandler):
    server_version = "ORISHTTP/1.0"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            json_response(self, 200, {
                "ok": True,
                "service": "oris-http-api",
                "host": HOST,
                "port": PORT,
            })
            return

        if parsed.path == "/runtime/plan":
            if not PLAN_PATH.exists():
                json_response(self, 404, {"ok": False, "error": "runtime_plan_not_found"})
                return
            try:
                data = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
                json_response(self, 200, {"ok": True, "runtime_plan": data})
            except Exception as e:
                json_response(self, 500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path != "/infer":
            json_response(self, 404, {"ok": False, "error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except Exception:
            length = 0

        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as e:
            json_response(self, 400, {"ok": False, "error": f"invalid_json: {e}"})
            return

        role = payload.get("role")
        prompt = payload.get("prompt")
        request_id = payload.get("request_id") or str(uuid.uuid4())
        source = payload.get("source") or "http_api"
        show_raw = bool(payload.get("show_raw", False))

        if not isinstance(role, str) or not role.strip():
            json_response(self, 400, {"ok": False, "error": "missing_role"})
            return
        if not isinstance(prompt, str) or not prompt.strip():
            json_response(self, 400, {"ok": False, "error": "missing_prompt"})
            return

        cmd = [
            "/usr/bin/python3",
            str(INFER_SCRIPT),
            "--role", role.strip(),
            "--prompt", prompt,
            "--request-id", request_id,
            "--source", source,
        ]
        if show_raw:
            cmd.append("--show-raw")

        result = run_cmd(cmd)

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if not stdout:
            json_response(self, 500, {
                "ok": False,
                "error": "empty_executor_output",
                "stderr": stderr[:1000],
            })
            return

        try:
            data = json.loads(stdout)
        except Exception as e:
            json_response(self, 500, {
                "ok": False,
                "error": f"executor_output_not_json: {e}",
                "stdout_preview": stdout[:1000],
                "stderr": stderr[:1000],
            })
            return

        status = 200 if result.returncode == 0 and data.get("ok") else 502
        json_response(self, status, data)

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(json.dumps({
        "ok": True,
        "service": "oris-http-api",
        "listen": f"http://{HOST}:{PORT}"
    }, ensure_ascii=False))
    server.serve_forever()

if __name__ == "__main__":
    main()
