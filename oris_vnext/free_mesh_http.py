from __future__ import annotations

import json
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .free_mesh_compat import chat_payload, load_json, model_to_role, models_payload
from .free_mesh_inference import FreeMeshInference
from .openai_chat_contract import ChatContractError, parse_chat_request


_MAX_REQUEST_BYTES = 4 * 1024 * 1024


def _deep_get(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _read_token(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        token = _deep_get(
            load_json(path),
            ("services", "oris_api", "bearerToken"),
        )
    except Exception:
        return None
    return token if isinstance(token, str) and token else None


def _provided_token(handler: BaseHTTPRequestHandler) -> str | None:
    authorization = handler.headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        return authorization[len("Bearer ") :].strip()
    fallback = handler.headers.get("X-ORIS-API-Key", "").strip()
    return fallback or None


def _send_json(
    handler: BaseHTTPRequestHandler,
    status: int,
    payload: dict[str, Any],
) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def build_handler(repo_root: Path) -> type[BaseHTTPRequestHandler]:
    secrets_path = Path.home() / ".openclaw" / "secrets.json"
    inference = FreeMeshInference(repo_root)

    class Handler(BaseHTTPRequestHandler):
        server_version = "ORISFreeMesh/2.0"

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _authorized(self) -> bool:
            expected = _read_token(secrets_path)
            provided = _provided_token(self)
            return bool(expected and provided and expected == provided)

        def _body(self) -> dict[str, Any]:
            raw_length = self.headers.get("Content-Length", "0")
            length = int(raw_length or "0")
            if length <= 0 or length > _MAX_REQUEST_BYTES:
                raise ChatContractError("invalid request size")
            raw = self.rfile.read(length)
            value = json.loads(raw.decode("utf-8"))
            if not isinstance(value, dict):
                raise ChatContractError("request body must be an object")
            return value

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/v1/health":
                _send_json(
                    self,
                    200,
                    {
                        "ok": True,
                        "service": "oris-free-mesh-api",
                        "protocol_version": 2,
                        "tool_calling": True,
                    },
                )
                return
            if path == "/v1/models":
                if not self._authorized():
                    _send_json(self, 401, _error("unauthorized", "invalid token"))
                    return
                _send_json(self, 200, models_payload())
                return
            _send_json(self, 404, _error("not_found", "path not found"))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/v1/chat/completions":
                _send_json(self, 404, _error("not_found", "path not found"))
                return
            if not self._authorized():
                _send_json(self, 401, _error("unauthorized", "invalid token"))
                return
            try:
                request = parse_chat_request(self._body())
            except (ChatContractError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
                _send_json(self, 400, _error("invalid_request", "invalid chat request"))
                return
            request_id = self.headers.get("X-Request-Id") or str(uuid.uuid4())
            logical_model, role = model_to_role(
                request.model,
                requires_tools=request.has_tools,
            )
            returncode, result = inference.run(
                role=role,
                request=request,
                request_id=request_id,
            )
            if returncode == 0 and result.get("ok"):
                message = result.get("message")
                if not isinstance(message, dict):
                    message = {
                        "role": "assistant",
                        "content": str(result.get("text") or ""),
                    }
                payload = chat_payload(
                    request_id=request_id,
                    model=logical_model,
                    message=message,
                    finish_reason=str(result.get("finish_reason") or "") or None,
                    used_model=result.get("used_model"),
                    used_provider=result.get("used_provider"),
                )
                payload["oris"]["latency_ms"] = result.get("latency_ms")
                payload["oris"]["slow"] = result.get("slow")
                _send_json(self, 200, payload)
                return
            _send_json(
                self,
                502,
                _error(
                    "free_mesh_infer_failed",
                    str(result.get("error") or "ORIS inference failed"),
                ),
            )

    return Handler
