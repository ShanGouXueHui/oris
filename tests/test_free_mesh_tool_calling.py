from __future__ import annotations

import json
import stat
from pathlib import Path

from oris_vnext.free_mesh_compat import chat_payload, model_to_role
from oris_vnext.free_mesh_inference import FreeMeshInference
from oris_vnext.openai_chat_contract import (
    ChatContractError,
    normalize_assistant_message,
    parse_chat_request,
)


def sample_request() -> dict:
    return {
        "model": "openrouter/auto",
        "messages": [{"role": "user", "content": "private content"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "session_status",
                    "description": "private description",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        "tool_choice": "auto",
        "temperature": 0,
    }


def test_chat_request_preserves_tool_protocol_without_metadata_leak() -> None:
    request = parse_chat_request(sample_request())
    payload = request.provider_payload("qwen3.6-plus")
    assert payload["model"] == "qwen3.6-plus"
    assert payload["messages"] == sample_request()["messages"]
    assert payload["tools"] == sample_request()["tools"]
    assert payload["tool_choice"] == "auto"
    metadata = request.metadata()
    assert metadata == {
        "message_count": 1,
        "tool_count": 1,
        "tool_choice_present": True,
        "structured_tool_history": False,
        "conversation_content_recorded": False,
        "tool_schema_recorded": False,
        "tool_arguments_or_results_recorded": False,
    }
    assert "private content" not in json.dumps(metadata)
    assert "session_status" not in json.dumps(metadata)


def test_provider_tool_call_is_normalized_and_authorized() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "session_status",
                                "arguments": {},
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }
    message, finish_reason = normalize_assistant_message(
        response,
        ("session_status",),
    )
    assert finish_reason == "tool_calls"
    assert message["tool_calls"][0]["function"] == {
        "name": "session_status",
        "arguments": "{}",
    }


def test_provider_cannot_inject_unapproved_tool() -> None:
    response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "write",
                                "arguments": "{}",
                            },
                        }
                    ],
                }
            }
        ]
    }
    raised = False
    try:
        normalize_assistant_message(response, ("session_status",))
    except ChatContractError:
        raised = True
    assert raised


def test_tool_requests_use_tool_calling_role() -> None:
    assert model_to_role("openrouter/auto", requires_tools=True) == (
        "openrouter/auto",
        "tool_calling",
    )
    assert model_to_role("openrouter/auto", requires_tools=False)[1] == "primary_general"


def test_chat_payload_preserves_tool_call_message() -> None:
    message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "session_status",
                    "arguments": "{}",
                },
            }
        ],
    }
    payload = chat_payload(
        request_id="request-1",
        model="openrouter/auto",
        message=message,
        finish_reason="tool_calls",
    )
    choice = payload["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    assert choice["message"] == message


def test_private_request_file_is_mode_600() -> None:
    request = parse_chat_request(sample_request())
    path = FreeMeshInference._private_request_file(request)
    try:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        stored = json.loads(Path(path).read_text(encoding="utf-8"))
        assert stored["tools"] == sample_request()["tools"]
    finally:
        path.unlink(missing_ok=True)


def run_all() -> None:
    test_chat_request_preserves_tool_protocol_without_metadata_leak()
    test_provider_tool_call_is_normalized_and_authorized()
    test_provider_cannot_inject_unapproved_tool()
    test_tool_requests_use_tool_calling_role()
    test_chat_payload_preserves_tool_call_message()
    test_private_request_file_is_mode_600()


if __name__ == "__main__":
    run_all()
