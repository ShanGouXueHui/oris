from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from .free_mesh_compat import messages_to_prompt
from .openai_chat_contract import ChatContractError, ChatRequest, normalize_assistant_message


_OPENAI_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "alibaba_bailian": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "tencent_hunyuan": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
    "zhipu": "https://api.z.ai/api/paas/v4/chat/completions",
}


class ProviderExecutionError(RuntimeError):
    pass


class ToolProtocolUnsupported(ProviderExecutionError):
    pass


@dataclass(frozen=True)
class ProviderResponse:
    provider_id: str
    model_id: str
    message: dict[str, Any]
    finish_reason: str
    raw: dict[str, Any]

    @property
    def text(self) -> str:
        content = self.message.get("content")
        return content if isinstance(content, str) else ""

    @property
    def tool_call_count(self) -> int:
        calls = self.message.get("tool_calls")
        return len(calls) if isinstance(calls, list) else 0


def provider_timeout_seconds() -> int:
    value = os.getenv("ORIS_PROVIDER_TIMEOUT_SECONDS", "12")
    try:
        return max(3, int(value))
    except Exception:
        return 12


def post_json(
    url: str,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout: int | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers=headers,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(
        request,
        timeout=timeout or provider_timeout_seconds(),
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ProviderExecutionError("provider returned a non-object response")
    return payload


def _openai_headers(provider_id: str, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ORIS-Runtime-Executor/2.0",
    }
    if provider_id == "openrouter":
        headers["HTTP-Referer"] = "https://orisfy.com"
        headers["X-Title"] = "ORIS Free Mesh"
    return headers


def call_openai_compatible(
    provider_id: str,
    model_id: str,
    request: ChatRequest,
    api_key: str,
) -> ProviderResponse:
    endpoint = _OPENAI_ENDPOINTS.get(provider_id)
    if endpoint is None:
        raise ProviderExecutionError(f"unsupported OpenAI-compatible provider: {provider_id}")
    body = request.provider_payload(model_id)
    body.setdefault("temperature", 0.2)
    payload = post_json(endpoint, _openai_headers(provider_id, api_key), body)
    try:
        message, finish_reason = normalize_assistant_message(
            payload,
            request.tool_names,
        )
    except ChatContractError as exc:
        raise ProviderExecutionError(str(exc)) from exc
    return ProviderResponse(
        provider_id=provider_id,
        model_id=model_id,
        message=message,
        finish_reason=finish_reason,
        raw=payload,
    )


def _gemini_text(payload: dict[str, Any]) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderExecutionError("gemini returned no candidate content") from exc
    text = "".join(
        str(part.get("text") or "")
        for part in parts
        if isinstance(part, dict)
    ).strip()
    if not text:
        raise ProviderExecutionError("gemini returned no text")
    return text


def call_gemini(
    model_id: str,
    request: ChatRequest,
    api_key: str,
) -> ProviderResponse:
    if request.has_tools:
        raise ToolProtocolUnsupported("gemini tool protocol is not enabled")
    clean_model = model_id.split("/", 1)[1] if model_id.startswith("models/") else model_id
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{clean_model}:generateContent?key={api_key}"
    )
    prompt = messages_to_prompt(list(request.messages))
    payload = post_json(
        url,
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "ORIS-Runtime-Executor/2.0",
        },
        {"contents": [{"parts": [{"text": prompt}]}]},
    )
    return ProviderResponse(
        provider_id="gemini",
        model_id=model_id,
        message={"role": "assistant", "content": _gemini_text(payload)},
        finish_reason="stop",
        raw=payload,
    )


def execute_provider(
    provider_id: str,
    model_id: str,
    request: ChatRequest,
    api_key: str,
) -> ProviderResponse:
    if provider_id in _OPENAI_ENDPOINTS:
        return call_openai_compatible(provider_id, model_id, request, api_key)
    if provider_id == "gemini":
        return call_gemini(model_id, request, api_key)
    raise ProviderExecutionError(f"unsupported provider: {provider_id}")
