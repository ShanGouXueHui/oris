#!/usr/bin/env python3
"""Provider-neutral Agent Harness for ORIS conversational development tasks.

The harness sits between the conversation orchestrator and model/provider
adapters. It owns deterministic control routing, provider selection, policy
validation, structured-output validation, fallback visibility, and sanitized
trace events. It does not create tasks, mutate queues, execute Codex, or touch
product repositories.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Prefer package-relative imports when loaded as ``scripts.dev_employee_agent_harness``
# so exception/dataclass identity is shared with package-based tests. Fall back to
# top-level imports when systemd executes the sibling Web script directly and the
# scripts directory is placed on sys.path.
try:
    from .dev_employee_openclaw_provider import (
        DeterministicFallbackProvider,
        ProviderContractError,
        ProviderResult,
        ProviderUnavailable,
        configured_provider,
        explicit_control_intent,
        merge_mandatory_policy,
    )
except ImportError:  # pragma: no cover - exercised by direct script runtime
    from dev_employee_openclaw_provider import (
        DeterministicFallbackProvider,
        ProviderContractError,
        ProviderResult,
        ProviderUnavailable,
        configured_provider,
        explicit_control_intent,
        merge_mandatory_policy,
    )

TRACE_DIR = Path("/home/admin/projects/oris/logs/dev_employee/agent_harness")
HARNESS_VERSION = "1.0"
SUPPORTED_PROVIDER_MODES = {"openclaw", "deterministic", "auto"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def trace_path() -> Path:
    return TRACE_DIR / f"agent_harness_{datetime.now().strftime('%Y%m%d')}.jsonl"


def append_trace(event: dict[str, Any]) -> None:
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    safe = {
        "ts": now_iso(),
        "harness_version": HARNESS_VERSION,
        **event,
    }
    forbidden = {
        "message",
        "prompt",
        "objective",
        "constraints",
        "expected_checks",
        "token",
        "authorization",
        "secret",
        "password",
    }
    for key in list(safe):
        if key.lower() in forbidden:
            safe.pop(key, None)
    with trace_path().open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(safe, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


@dataclass
class HarnessOutcome:
    result: ProviderResult
    provider_mode: str
    selected_provider: str
    fallback_used: bool
    latency_ms: int


class AgentHarness:
    def __init__(self, provider_mode: str | None = None) -> None:
        configured = (provider_mode or os.environ.get("ORIS_AGENT_HARNESS_PROVIDER", "auto")).strip().lower()
        if configured not in SUPPORTED_PROVIDER_MODES:
            raise ValueError(f"unsupported harness provider mode: {configured}")
        self.provider_mode = configured
        self.fallback = DeterministicFallbackProvider()

    def validate_result(self, result: ProviderResult, projects: dict[str, dict[str, Any]]) -> ProviderResult:
        if result.project_key and result.project_key not in projects:
            raise ProviderContractError(f"harness rejected unsupported project: {result.project_key}")
        if result.intent == "create_task":
            if not result.project_key:
                raise ProviderContractError("harness rejected create_task without project_key")
            if not result.objective or len(result.objective.strip()) < 12:
                raise ProviderContractError("harness rejected create_task without concrete objective")
        if not result.assistant_message.strip():
            raise ProviderContractError("harness rejected empty assistant message")
        return result

    def deterministic(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        projects: dict[str, dict[str, Any]],
        current_task: dict[str, Any] | None,
    ) -> ProviderResult:
        return self.fallback.analyze(
            session=session,
            user_message=user_message,
            projects=projects,
            current_task=current_task,
        )

    def analyze(
        self,
        *,
        session: dict[str, Any],
        user_message: str,
        projects: dict[str, dict[str, Any]],
        current_task: dict[str, Any] | None,
    ) -> HarnessOutcome:
        started = time.monotonic()
        selected_provider = "deterministic_fallback"
        fallback_used = False
        failure_type: str | None = None

        try:
            if explicit_control_intent(user_message) or self.provider_mode == "deterministic":
                result = self.deterministic(
                    session=session,
                    user_message=user_message,
                    projects=projects,
                    current_task=current_task,
                )
            else:
                provider = configured_provider() if self.provider_mode in {"auto", "openclaw"} else None
                if provider is None:
                    if self.provider_mode == "openclaw":
                        raise ProviderUnavailable("OpenClaw provider required but unavailable")
                    fallback_used = True
                    result = self.deterministic(
                        session=session,
                        user_message=user_message,
                        projects=projects,
                        current_task=current_task,
                    )
                else:
                    selected_provider = "openclaw_infer_gateway"
                    try:
                        result = provider.analyze(
                            session=session,
                            user_message=user_message,
                            projects=projects,
                            current_task=current_task,
                        )
                        result = merge_mandatory_policy(result, user_message, projects)
                    except (ProviderUnavailable, ProviderContractError) as exc:
                        if self.provider_mode == "openclaw" and os.environ.get(
                            "ORIS_AGENT_HARNESS_ALLOW_FALLBACK", "1"
                        ).strip().lower() in {"0", "false", "no"}:
                            raise
                        failure_type = type(exc).__name__
                        fallback_used = True
                        selected_provider = "deterministic_fallback"
                        result = self.deterministic(
                            session=session,
                            user_message=user_message,
                            projects=projects,
                            current_task=current_task,
                        )
                        result.raw_metadata = {
                            **result.raw_metadata,
                            "harness_fallback": True,
                            "fallback_reason": failure_type,
                        }
            result = self.validate_result(result, projects)
        except Exception as exc:
            latency_ms = int((time.monotonic() - started) * 1000)
            append_trace(
                {
                    "event": "harness_error",
                    "session_id": session.get("session_id"),
                    "message_length": len(user_message),
                    "provider_mode": self.provider_mode,
                    "selected_provider": selected_provider,
                    "fallback_used": fallback_used,
                    "error_type": type(exc).__name__,
                    "latency_ms": latency_ms,
                }
            )
            raise

        latency_ms = int((time.monotonic() - started) * 1000)
        result.raw_metadata = {
            **result.raw_metadata,
            "agent_harness": True,
            "harness_version": HARNESS_VERSION,
            "harness_provider_mode": self.provider_mode,
            "harness_fallback_used": fallback_used,
        }
        append_trace(
            {
                "event": "harness_decision",
                "session_id": session.get("session_id"),
                "message_length": len(user_message),
                "provider_mode": self.provider_mode,
                "selected_provider": selected_provider,
                "fallback_used": fallback_used,
                "fallback_reason": failure_type,
                "intent": result.intent,
                "project_key": result.project_key,
                "requires_confirmation": result.requires_confirmation,
                "current_task_present": bool(session.get("current_task_id")),
                "latency_ms": latency_ms,
            }
        )
        return HarnessOutcome(
            result=result,
            provider_mode=self.provider_mode,
            selected_provider=selected_provider,
            fallback_used=fallback_used,
            latency_ms=latency_ms,
        )


DEFAULT_AGENT_HARNESS = AgentHarness()


def analyze_with_harness(
    *,
    session: dict[str, Any],
    user_message: str,
    projects: dict[str, dict[str, Any]],
    current_task: dict[str, Any] | None,
) -> ProviderResult:
    return DEFAULT_AGENT_HARNESS.analyze(
        session=session,
        user_message=user_message,
        projects=projects,
        current_task=current_task,
    ).result
