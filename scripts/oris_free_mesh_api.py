#!/usr/bin/env python3
"""Local ORIS Free Mesh API.

This service presents logical model IDs while routing real inference through
scripts/oris_infer.py and the existing runtime_plan failover chain.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.free_mesh_compat import chat_payload, messages_to_prompt, model_to_role, models_payload

CONFIG_PATH = REPO_ROOT / "config/oris_free_mesh_api.json"
INFER_SCRIPT = REPO_ROOT / "scripts/oris_infer.py"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"
LATENCY_LOG_PATH = REPO_ROOT / "logs/dev_employee/free_mesh_latency_events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latency_threshold_ms() -> int:
    try:
        return max(1, int(os.getenv("ORIS_FREE_MESH_SLOW_MS", "15000")))
    except Exception:
        return 15000


def warmup_enabled() -> bool:
    return os.getenv("ORIS_FREE_MESH_WARMUP", "1").lower() not in {"0", "false", "no"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def deep_get(data: dict, keys: list[str]):
    cur = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def read_token() -> str | None:
    if not SECRETS_PATH.exists():
        return None
    try:
        data = load_json(SECRETS_PATH)
    except Exception:
        return None
    token = deep_get(data, ["services", "oris_api", "bearerToken"])
    return token if isinstance(token, str) and token else None


def get_auth_token(handler: BaseHTTPRequestHandler) -> str | None:
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    fallback = handler.headers.get("X-ORIS-API-Key", "").strip()
    return fallback or None


def authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = read_token()
    provided = get_auth_token(handler)
    return bool(expected and provided and expected == provided)


def send_json(handler: BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def run_infer(*, role: str, prompt: str, request_id: str, source: str = "free_mesh_api") -> tuple[int, dict]:
    cmd = [
        "/usr/bin/python3",
        str(INFER_SCRIPT),
        "--role",
        role,
        "--prompt",
        prompt,
        "--request-id",
        request_id,
        "--source",
        source,
    ]
    started = time.perf_counter()
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    stdout = (result.stdout or "").strip()
    threshold_ms = latency_threshold_ms()

    if not stdout:
        payload = {"ok": False, "error": "empty_oris_infer_output", "stderr": (result.stderr or "")[-1000:]}
    else:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            payload = {"ok": False, "error": f"invalid_oris_infer_json: {exc}", "stdout": stdout[-1000:]}
            result = subprocess.CompletedProcess(result.args, 2, result.stdout, result.stderr)

    if isinstance(payload, dict):
        payload.setdefault("latency_ms", elapsed_ms)
        payload.setdefault("slow", elapsed_ms > threshold_ms)
        append_jsonl(
            LATENCY_LOG_PATH,
            {
                "ts": utc_now(),
                "request_id": request_id,
                "source": source,
                "role": role,
                "ok": bool(payload.get("ok")),
                "elapsed_ms": elapsed_ms,
                "slow": elapsed_ms > threshold_ms,
                "threshold_ms": threshold_ms,
                "used_model": payload.get("used_model"),
                "used_provider": payload.get("used_provider"),
                "error": payload.get("error"),
                "status": payload.get("status"),
            },
        )

    return result.returncode, payload


def warmup_once() -> None:
    request_id = f"free-mesh-warmup-{uuid.uuid4()}"
    try:
        run_infer(
            role="primary_general",
            prompt="Reply with exactly: ORIS_FREE_MESH_WARMUP_OK",
            request_id=request_id,
            source="free_mesh_warmup",
        )
    except Exception as exc:
        append_jsonl(
            LATENCY_LOG_PATH,
            {
                "ts": utc_now(),
                "request_id": request_id,
                "source": "free_mesh_warmup",
                "role": "primary_general",
                "ok": False,
                "error": f"warmup_failed: {type(exc).__name__}: {exc}",
            },
        )


def start_warmup_thread() -> None:
    if not warmup_enabled():
        return
    thread = threading.Thread(target=warmup_once, name="oris-free-mesh-warmup", daemon=True)
    thread.start()


class Handler(BaseHTTPRequestHandler):
    server_version = "ORISFreeMesh/1.0"

    def log_message(self, fmt, *args):
        return

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length > 0 else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("request body must be a JSON object")
        return parsed

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/v1/health":
            send_json(self, 200, {"ok": True, "service": "oris-free-mesh-api"})
            return
        if path == "/v1/models":
            if not authorized(self):
                send_json(self, 401, {"error": {"code": "unauthorized", "message": "missing or invalid token"}})
                return
            send_json(self, 200, models_payload())
            return
        send_json(self, 404, {"error": {"code": "not_found", "message": "path not found"}})

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/v1/chat/completions":
            send_json(self, 404, {"error": {"code": "not_found", "message": "path not found"}})
            return
        if not authorized(self):
            send_json(self, 401, {"error": {"code": "unauthorized", "message": "missing or invalid token"}})
            return
        request_id = self.headers.get("X-Request-Id") or str(uuid.uuid4())
        try:
            body = self.read_body()
        except Exception as exc:
            send_json(self, 400, {"error": {"code": "invalid_json", "message": str(exc)}})
            return
        logical_model, role = model_to_role(str(body.get("model") or "openrouter/auto"))
        prompt = messages_to_prompt(body.get("messages"))
        if not prompt:
            send_json(self, 400, {"error": {"code": "missing_messages", "message": "messages are required"}})
            return
        rc, infer = run_infer(role=role, prompt=prompt, request_id=request_id)
        if rc == 0 and infer.get("ok"):
            payload = chat_payload(
                request_id=request_id,
                model=logical_model,
                text=infer.get("text", ""),
                used_model=infer.get("used_model"),
                used_provider=infer.get("used_provider"),
            )
            payload.setdefault("oris", {})["latency_ms"] = infer.get("latency_ms")
            payload.setdefault("oris", {})["slow"] = infer.get("slow")
            send_json(self, 200, payload)
            return
        send_json(self, 502, {"error": {"code": "free_mesh_infer_failed", "message": "ORIS inference failed", "details": infer}})


def main() -> int:
    cfg = load_json(CONFIG_PATH)
    host = str(cfg.get("host", "127.0.0.1"))
    port = int(cfg.get("port", 8789))
    server = ThreadingHTTPServer((host, port), Handler)
    print(json.dumps({"ok": True, "service": "oris-free-mesh-api", "listen": f"http://{host}:{port}"}, ensure_ascii=False))
    start_warmup_thread()
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
