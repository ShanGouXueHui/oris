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
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
HOST = "127.0.0.1"
PORT = 8788

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def read_bearer_token():
    if not SECRETS_PATH.exists():
        return None
    try:
        data = load_json(SECRETS_PATH)
        return (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken"))
    except Exception:
        return None

def parse_json_output(text: str):
    text = (text or "").strip()
    if not text:
        raise RuntimeError("empty output")
    return json.loads(text)

def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

def v1_ok(request_id, data):
    return {
        "ok": True,
        "request_id": request_id,
        "data": data,
        "error": None,
    }

def v1_err(request_id, code, message, details=None):
    return {
        "ok": False,
        "request_id": request_id,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }

def extract_bearer(handler):
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    api_key = handler.headers.get("X-ORIS-API-Key", "").strip()
    if api_key:
        return api_key
    return None

def require_bearer(handler):
    expected = read_bearer_token()
    provided = extract_bearer(handler)
    return bool(expected and provided and provided == expected)

class Handler(BaseHTTPRequestHandler):
    server_version = "ORISHTTP/2.0"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/v1/health":
            json_response(self, 200, v1_ok(None, {
                "service": "oris-http-api",
                "version": "v1",
                "listen": f"http://{HOST}:{PORT}",
            }))
            return

        if path == "/v1/runtime/plan":
            request_id = self.headers.get("X-Request-Id") or str(uuid.uuid4())
            if not require_bearer(self):
                json_response(self, 401, v1_err(request_id, "unauthorized", "missing or invalid bearer token"))
                return
            if not PLAN_PATH.exists():
                json_response(self, 404, v1_err(request_id, "runtime_plan_not_found", "runtime plan file not found"))
                return
            try:
                data = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
                json_response(self, 200, v1_ok(request_id, {"runtime_plan": data}))
            except Exception as e:
                json_response(self, 500, v1_err(request_id, "runtime_plan_read_failed", f"{type(e).__name__}: {e}"))
            return

        json_response(self, 404, v1_err(None, "not_found", "path not found"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path != "/v1/infer":
            json_response(self, 404, v1_err(None, "not_found", "path not found"))
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except Exception:
            length = 0

        raw = self.rfile.read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as e:
            json_response(self, 400, v1_err(None, "invalid_json", str(e)))
            return

        request_id = payload.get("request_id") or self.headers.get("X-Request-Id") or str(uuid.uuid4())

        if not require_bearer(self):
            json_response(self, 401, v1_err(request_id, "unauthorized", "missing or invalid bearer token"))
            return

        role = payload.get("role")
        prompt = payload.get("prompt")
        source = payload.get("source") or "http_api_v1"
        show_raw = bool(payload.get("show_raw", False))

        if not isinstance(role, str) or not role.strip():
            json_response(self, 400, v1_err(request_id, "missing_role", "role is required"))
            return

        if not isinstance(prompt, str) or not prompt.strip():
            json_response(self, 400, v1_err(request_id, "missing_prompt", "prompt is required"))
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
            json_response(self, 500, v1_err(request_id, "empty_executor_output", "executor returned empty output", stderr[:1000]))
            return

        try:
            data = json.loads(stdout)
        except Exception as e:
            json_response(self, 500, v1_err(request_id, "executor_output_not_json", str(e), {"stdout_preview": stdout[:1000], "stderr": stderr[:1000]}))
            return

        if result.returncode == 0 and data.get("ok"):
            wrapped = v1_ok(request_id, {
                "role": data.get("role"),
                "selected_model": data.get("selected_model"),
                "execution_primary": data.get("execution_primary"),
                "used_provider": data.get("used_provider"),
                "used_model": data.get("used_model"),
                "attempt": data.get("attempt"),
                "text": data.get("text"),
                "attempts_log": data.get("attempts_log", []),
                "source": data.get("source"),
            })
            json_response(self, 200, wrapped)
        else:
            json_response(self, 502, v1_err(
                request_id,
                "inference_failed",
                "all_failover_candidates_exhausted",
                {
                    "selected_model": data.get("selected_model"),
                    "execution_primary": data.get("execution_primary"),
                    "attempts_log": data.get("attempts_log", []),
                }
            ))

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
