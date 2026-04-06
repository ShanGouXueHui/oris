#!/usr/bin/env python3
import json
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from lib.runtime_config import config, rel_path, read_feishu_verification_token, local_service_value, feishu_api

CFG = config()
ROOT = rel_path("feishu_callback_server_log").parents[1]
LOG_PATH = rel_path("feishu_callback_server_log")
WORKER_SCRIPT = ROOT / "scripts" / "feishu_worker_skeleton.py"

HOST = local_service_value("feishu_callback_bind_host")
PORT = int(local_service_value("feishu_callback_bind_port"))
EVENT_PATH = feishu_api("callback_local_path")
HEALTH_PATH = feishu_api("callback_health_path")
EXECUTE_SEND_DEFAULT = bool((((CFG.get("bridges") or {}).get("execution") or {}).get("feishu_execute_send_default")))

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def append_jsonl(path, record):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def json_response(handler, code, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

class Handler(BaseHTTPRequestHandler):
    server_version = "ORISFeishuCallback/1.0"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path == HEALTH_PATH:
            json_response(self, 200, {
                "ok": True,
                "service": "oris-feishu-callback-server",
                "listen": f"http://{HOST}:{PORT}",
                "event_path": EVENT_PATH,
                "execute_send_default": EXECUTE_SEND_DEFAULT,
            })
            return
        json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != EVENT_PATH:
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
            append_jsonl(LOG_PATH, {
                "ts": utc_now(),
                "ok": False,
                "mode": "invalid_json",
                "error": str(e),
                "raw_preview": raw[:500].decode("utf-8", errors="ignore"),
            })
            json_response(self, 400, {"code": 1, "msg": f"invalid_json: {e}"})
            return

        # challenge verification
        if "challenge" in payload:
            expected_token = read_feishu_verification_token()
            incoming_token = payload.get("token")
            if expected_token and incoming_token and incoming_token != expected_token:
                append_jsonl(LOG_PATH, {
                    "ts": utc_now(),
                    "ok": False,
                    "mode": "challenge_rejected",
                    "reason": "verification_token_mismatch",
                })
                json_response(self, 403, {"code": 1, "msg": "verification_token_mismatch"})
                return

            append_jsonl(LOG_PATH, {
                "ts": utc_now(),
                "ok": True,
                "mode": "challenge",
            })
            json_response(self, 200, {"challenge": payload.get("challenge")})
            return

        cmd = [
            "/usr/bin/python3",
            str(WORKER_SCRIPT),
            "--payload-json",
            json.dumps(payload, ensure_ascii=False),
        ]
        if EXECUTE_SEND_DEFAULT:
            cmd.append("--execute-send")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            append_jsonl(LOG_PATH, {
                "ts": utc_now(),
                "ok": False,
                "mode": "worker_failed",
                "stdout_preview": (result.stdout or "")[:1000],
                "stderr_preview": (result.stderr or "")[:1000],
            })
            json_response(self, 500, {"code": 1, "msg": "worker_failed"})
            return

        try:
            worker_result = json.loads(result.stdout)
        except Exception:
            append_jsonl(LOG_PATH, {
                "ts": utc_now(),
                "ok": False,
                "mode": "worker_non_json",
                "stdout_preview": (result.stdout or "")[:1000],
            })
            json_response(self, 500, {"code": 1, "msg": "worker_non_json"})
            return

        append_jsonl(LOG_PATH, {
            "ts": utc_now(),
            "ok": True,
            "mode": "event_processed",
            "worker_mode": worker_result.get("worker_mode"),
            "transport_mode": ((worker_result.get("transport_result") or {}).get("mode")),
            "send_mode": ((worker_result.get("send_result") or {}).get("mode")) if worker_result.get("send_result") else None,
        })
        json_response(self, 200, {"code": 0})

def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(json.dumps({
        "ok": True,
        "service": "oris-feishu-callback-server",
        "listen": f"http://{HOST}:{PORT}",
        "event_path": EVENT_PATH,
        "execute_send_default": EXECUTE_SEND_DEFAULT,
    }, ensure_ascii=False))
    server.serve_forever()

if __name__ == "__main__":
    main()
