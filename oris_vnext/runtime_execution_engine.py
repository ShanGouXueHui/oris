from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .openai_chat_contract import ChatRequest
from .runtime_execution_state import RuntimeExecutionState
from .runtime_provider_client import ToolProtocolUnsupported, execute_provider


class RuntimeExecutionEngine:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.plan_path = repo_root / "orchestration" / "runtime_plan.json"
        self.state = RuntimeExecutionState(repo_root)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError(f"{path.name} must be an object")
        return value

    @staticmethod
    def _ordered_candidates(role_plan: dict[str, Any]) -> list[dict[str, Any]]:
        chain = role_plan.get("failover_chain")
        if not isinstance(chain, list):
            return []
        primary = role_plan.get("execution_primary")
        ordered: list[dict[str, Any]] = []
        if isinstance(primary, str):
            first = next(
                (
                    item
                    for item in chain
                    if isinstance(item, dict) and item.get("model_id") == primary
                ),
                None,
            )
            if first is not None:
                ordered.append(first)
        for item in chain:
            if not isinstance(item, dict):
                continue
            if primary and item.get("model_id") == primary:
                continue
            if item.get("blocked"):
                continue
            ordered.append(item)
        return ordered

    @staticmethod
    def _safe_attempt(
        provider_id: str,
        model_id: str,
        status: str,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "provider_id": provider_id,
            "model_id": model_id,
            "status": status,
            **extra,
            "conversation_content_recorded": False,
            "tool_arguments_or_results_recorded": False,
        }

    def execute(
        self,
        role: str,
        request: ChatRequest,
        *,
        show_raw: bool = False,
    ) -> dict[str, Any]:
        plan = self._load_json(self.plan_path)
        role_plan = (plan.get("plans") or {}).get(role)
        if not isinstance(role_plan, dict):
            raise RuntimeError(f"role not found in runtime_plan.json: {role}")
        candidates = self._ordered_candidates(role_plan)
        retry_attempts = int(role_plan.get("retry_attempts") or 0)
        backoff = role_plan.get("retry_backoff_seconds") or []
        if not isinstance(backoff, list):
            backoff = []
        runtime_state = self.state.load()
        secrets = self.state.load_secrets()
        attempts: list[dict[str, Any]] = []

        for item in candidates:
            provider_id = str(item.get("provider_id") or "")
            model_id = str(item.get("model_id") or "")
            if not provider_id or not model_id:
                continue
            api_key = self.state.provider_key(provider_id, secrets)
            if not api_key:
                error_class = "missing_key"
                runtime_state = self.state.mark_failure(
                    runtime_state,
                    model_id,
                    provider_id,
                    role,
                    error_class,
                    "missing_api_key",
                )
                attempts.append(
                    self._safe_attempt(
                        provider_id,
                        model_id,
                        "skipped",
                        reason="missing_api_key",
                        error_class=error_class,
                    )
                )
                continue

            last_error = ""
            for attempt in range(1, retry_attempts + 2):
                try:
                    response = execute_provider(
                        provider_id,
                        model_id,
                        request,
                        api_key,
                    )
                    runtime_state = self.state.mark_success(
                        runtime_state,
                        model_id,
                        provider_id,
                        role,
                    )
                    self.state.feedback(model_id, role, "success")
                    output: dict[str, Any] = {
                        "ok": True,
                        "role": role,
                        "selected_model": role_plan.get("selected_model"),
                        "execution_primary": role_plan.get("execution_primary"),
                        "used_provider": provider_id,
                        "used_model": model_id,
                        "attempt": attempt,
                        "message": response.message,
                        "finish_reason": response.finish_reason,
                        "text": response.text,
                        "tool_call_count": response.tool_call_count,
                        "attempts_log": attempts,
                        "request_metadata": request.metadata(),
                    }
                    if show_raw:
                        output["raw"] = response.raw
                    return output
                except ToolProtocolUnsupported as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    attempts.append(
                        self._safe_attempt(
                            provider_id,
                            model_id,
                            "skipped",
                            reason="tool_protocol_unsupported",
                            error_class="tool_protocol_unsupported",
                        )
                    )
                    break
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    error_class = self.state.classify_error(last_error)
                    attempts.append(
                        self._safe_attempt(
                            provider_id,
                            model_id,
                            "failure",
                            attempt=attempt,
                            error_class=error_class,
                            error_type=type(exc).__name__,
                        )
                    )
                    if attempt <= retry_attempts:
                        delay = backoff[attempt - 1] if attempt - 1 < len(backoff) else 1
                        time.sleep(float(delay))
            if last_error:
                error_class = self.state.classify_error(last_error)
                runtime_state = self.state.mark_failure(
                    runtime_state,
                    model_id,
                    provider_id,
                    role,
                    error_class,
                    last_error,
                )
                self.state.feedback(model_id, role, "failure", last_error)

        return {
            "ok": False,
            "role": role,
            "selected_model": role_plan.get("selected_model"),
            "execution_primary": role_plan.get("execution_primary"),
            "error": "all_failover_candidates_exhausted",
            "attempts_log": attempts,
            "request_metadata": request.metadata(),
        }
