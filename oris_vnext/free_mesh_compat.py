"""Compatibility helpers for ORIS Free Mesh logical models."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


LOGICAL_MODELS = {
    "oris/free-auto": "primary_general",
    "oris/free-coding": "coding",
    "oris/free-report": "report_generation",
    "oris/free-fallback": "free_fallback",
    "oris/free-cn": "cn_candidate_pool",
}


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def model_to_role(model: str | None) -> tuple[str, str]:
    logical_model = model or "oris/free-auto"
    return logical_model, LOGICAL_MODELS.get(logical_model, "primary_general")


def messages_to_prompt(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    parts: list[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "user"))
        content = msg.get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            )
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts).strip()


def models_payload() -> dict[str, Any]:
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {"id": model_id, "object": "model", "created": now, "owned_by": "oris-free-mesh"}
            for model_id in sorted(LOGICAL_MODELS)
        ],
    }


def chat_payload(*, request_id: str, model: str, text: str, used_model: str | None = None, used_provider: str | None = None) -> dict[str, Any]:
    return {
        "id": f"chatcmpl-oris-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "oris": {"used_model": used_model, "used_provider": used_provider, "routing": "runtime_plan_free_mesh"},
    }
