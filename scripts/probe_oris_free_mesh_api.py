#!/usr/bin/env python3
"""Probe ORIS Free Mesh API end to end.

This verifies the logical model endpoint without exposing any secret value.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

URL = "http://127.0.0.1:8789/v1/chat/completions"
SECRETS_PATH = Path.home() / ".openclaw" / "secrets.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def read_token() -> str:
    data = load_json(SECRETS_PATH)
    token = (((data.get("services") or {}).get("oris_api") or {}).get("bearerToken") or "")
    if not token:
        raise RuntimeError("missing services.oris_api.bearerToken in secrets")
    return str(token)


def post_chat(prompt: str) -> dict:
    body = {
        "model": "openrouter/auto",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={
            "Authorization": f"Bearer {read_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-Id": "free-mesh-probe"
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        return {"error": True, "status": exc.code, "payload": payload[:2000]}


def main() -> int:
    payload = post_chat("Reply with exactly: ORIS_FREE_MESH_OK")
    text = ""
    try:
        text = payload["choices"][0]["message"]["content"]
    except Exception:
        text = ""
    result = {
        "ok": bool(text),
        "text_preview": text[:200],
        "model": payload.get("model"),
        "oris": payload.get("oris"),
        "error": payload.get("error", False),
        "status": payload.get("status"),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
