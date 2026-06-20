from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_REQUEST_OPTION_KEYS = (
    "temperature",
    "top_p",
    "max_tokens",
    "max_completion_tokens",
    "stop",
    "presence_penalty",
    "frequency_penalty",
    "seed",
    "response_format",
    "parallel_tool_calls",
)


class ChatContractError(ValueError):
    pass


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: tuple[dict[str, Any], ...]
    tools: tuple[dict[str, Any], ...]
    tool_choice: Any
    options: dict[str, Any]

    @property
    def has_tools(self) -> bool:
        return bool(self.tools)

    @property
    def tool_names(self) -> tuple[str, ...]:
        names: list[str] = []
        for tool in self.tools:
            function = tool.get("function")
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                names.append(function["name"])
        return tuple(names)

    def provider_payload(self, model_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model_id,
            "messages": copy.deepcopy(list(self.messages)),
            **copy.deepcopy(self.options),
        }
        if self.tools:
            payload["tools"] = copy.deepcopy(list(self.tools))
        if self.tool_choice is not None:
            payload["tool_choice"] = copy.deepcopy(self.tool_choice)
        return payload

    def metadata(self) -> dict[str, Any]:
        return {
            "message_count": len(self.messages),
            "tool_count": len(self.tools),
            "tool_choice_present": self.tool_choice is not None,
            "structured_tool_history": any(
                message.get("role") == "tool" or bool(message.get("tool_calls"))
                for message in self.messages
            ),
            "conversation_content_recorded": False,
            "tool_schema_recorded": False,
            "tool_arguments_or_results_recorded": False,
        }


def _validate_messages(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list) or not value:
        raise ChatContractError("messages must be a non-empty list")
    messages: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ChatContractError("each message must be an object")
        role = item.get("role")
        if role not in {"system", "developer", "user", "assistant", "tool"}:
            raise ChatContractError("unsupported message role")
        if role == "tool" and not isinstance(item.get("tool_call_id"), str):
            raise ChatContractError("tool message requires tool_call_id")
        messages.append(copy.deepcopy(item))
    return tuple(messages)


def _validate_tools(value: Any) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ChatContractError("tools must be a list")
    tools: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or item.get("type") != "function":
            raise ChatContractError("only function tools are supported")
        function = item.get("function")
        if not isinstance(function, dict):
            raise ChatContractError("function tool definition is missing")
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise ChatContractError("function tool name is required")
        if name in names:
            raise ChatContractError("duplicate function tool name")
        parameters = function.get("parameters")
        if parameters is not None and not isinstance(parameters, dict):
            raise ChatContractError("function parameters must be an object")
        names.add(name)
        tools.append(copy.deepcopy(item))
    return tuple(tools)


def parse_chat_request(value: Any) -> ChatRequest:
    if not isinstance(value, dict):
        raise ChatContractError("chat request must be an object")
    model = value.get("model")
    if not isinstance(model, str) or not model:
        raise ChatContractError("model is required")
    messages = _validate_messages(value.get("messages"))
    tools = _validate_tools(value.get("tools"))
    tool_choice = copy.deepcopy(value.get("tool_choice"))
    options = {
        key: copy.deepcopy(value[key])
        for key in _REQUEST_OPTION_KEYS
        if key in value
    }
    return ChatRequest(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        options=options,
    )


def load_chat_request(path: Path) -> ChatRequest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return parse_chat_request(raw)


def legacy_prompt_request(prompt: str, model: str = "openrouter/auto") -> ChatRequest:
    if not isinstance(prompt, str) or not prompt:
        raise ChatContractError("prompt is required")
    return ChatRequest(
        model=model,
        messages=({"role": "user", "content": prompt},),
        tools=(),
        tool_choice=None,
        options={"temperature": 0.2},
    )


def normalize_assistant_message(
    payload: Any,
    allowed_tool_names: tuple[str, ...],
) -> tuple[dict[str, Any], str]:
    if not isinstance(payload, dict):
        raise ChatContractError("provider response must be an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ChatContractError("provider response choices are missing")
    choice = choices[0]
    message = choice.get("message")
    if not isinstance(message, dict):
        raise ChatContractError("provider response message is missing")
    result: dict[str, Any] = {"role": "assistant"}
    content = message.get("content")
    result["content"] = content if isinstance(content, (str, list)) or content is None else str(content)
    tool_calls = message.get("tool_calls")
    if tool_calls is not None:
        if not isinstance(tool_calls, list):
            raise ChatContractError("provider tool_calls must be a list")
        allowed = set(allowed_tool_names)
        normalized_calls: list[dict[str, Any]] = []
        for call in tool_calls:
            if not isinstance(call, dict) or call.get("type") != "function":
                raise ChatContractError("provider returned an invalid tool call")
            function = call.get("function")
            if not isinstance(function, dict):
                raise ChatContractError("provider tool call function is missing")
            name = function.get("name")
            arguments = function.get("arguments")
            if not isinstance(name, str) or name not in allowed:
                raise ChatContractError("provider returned an unauthorized tool name")
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
            call_id = call.get("id")
            if not isinstance(call_id, str) or not call_id:
                raise ChatContractError("provider tool call id is missing")
            normalized_calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": name, "arguments": arguments},
                }
            )
        result["tool_calls"] = normalized_calls
    if result.get("content") in {None, ""} and not result.get("tool_calls"):
        raise ChatContractError("provider returned neither content nor tool calls")
    finish_reason = choice.get("finish_reason")
    if not isinstance(finish_reason, str) or not finish_reason:
        finish_reason = "tool_calls" if result.get("tool_calls") else "stop"
    return result, finish_reason
