from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class RuntimeExecutionState:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.state_path = repo_root / "orchestration" / "runtime_state.json"
        self.secrets_path = Path.home() / ".openclaw" / "secrets.json"

    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    @staticmethod
    def _save_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _deep_get(data: dict[str, Any], path: tuple[str, ...]) -> Any:
        current: Any = data
        for key in path:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    def load_secrets(self) -> dict[str, Any]:
        value = self._load_json(self.secrets_path, {})
        return value if isinstance(value, dict) else {}

    def provider_key(self, provider_id: str, secrets: dict[str, Any]) -> str | None:
        candidates = {
            "openrouter": (("models", "providers", "openrouter", "apiKey"),),
            "gemini": (("models", "providers", "gemini", "apiKey"),),
            "zhipu": (("models", "providers", "zhipu", "apiKey"),),
            "alibaba_bailian": (
                ("models", "providers", "alibaba_bailian", "apiKey"),
                ("models", "providers", "Alibailian", "apiKey"),
                ("models", "providers", "alibailian", "apiKey"),
                ("models", "providers", "AlibabaBailian", "apiKey"),
            ),
            "tencent_hunyuan": (
                ("models", "providers", "tencent_hunyuan", "apiKey"),
                ("models", "providers", "tencenthunyuan", "apiKey"),
                ("models", "providers", "Tencenthunyuan", "apiKey"),
                ("models", "providers", "tencentHunyuan", "apiKey"),
            ),
        }
        for path in candidates.get(provider_id, ()):
            value = self._deep_get(secrets, path)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def load(self) -> dict[str, Any]:
        state = self._load_json(
            self.state_path,
            {"version": 1, "updated_at": self._now(), "models": {}},
        )
        if not isinstance(state, dict):
            state = {"version": 1, "updated_at": self._now(), "models": {}}
        if not isinstance(state.get("models"), dict):
            state["models"] = {}
        return state

    @staticmethod
    def classify_error(message: str) -> str:
        lowered = (message or "").lower()
        if "tool protocol" in lowered or "tool_choice" in lowered or "tools are not" in lowered:
            return "tool_protocol_unsupported"
        if "missing_api_key" in lowered or "missing api key" in lowered:
            return "missing_key"
        if "http error 402" in lowered or "payment required" in lowered:
            return "priced_out"
        if "http error 429" in lowered or "too many requests" in lowered:
            return "rate_limited"
        unstable = (
            "http error 500",
            "http error 502",
            "http error 503",
            "http error 504",
            "bad gateway",
            "service unavailable",
            "temporarily unavailable",
            "timed out",
            "timeout",
            "connection reset",
            "connection aborted",
        )
        return "provider_unstable" if any(item in lowered for item in unstable) else "execution_error"

    @staticmethod
    def _block_seconds(error_class: str) -> int:
        return {
            "missing_key": 3600,
            "priced_out": 21600,
            "rate_limited": 900,
            "provider_unstable": 600,
            "execution_error": 300,
            "tool_protocol_unsupported": 0,
        }.get(error_class, 300)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def mark_failure(
        self,
        state: dict[str, Any],
        model_id: str,
        provider_id: str,
        role: str,
        error_class: str,
        error_message: str,
    ) -> dict[str, Any]:
        if error_class == "tool_protocol_unsupported":
            return state
        now = datetime.now(timezone.utc)
        entry = state.setdefault("models", {}).setdefault(model_id, {})
        entry["total_failures"] = int(entry.get("total_failures") or 0) + 1
        entry["consecutive_failures"] = int(entry.get("consecutive_failures") or 0) + 1
        entry.update(
            {
                "last_result": "failure",
                "last_role": role,
                "last_error": (error_message or "")[:500],
                "last_error_class": error_class,
                "last_failure_at": now.isoformat(),
                "last_provider_id": provider_id,
                "blocked_until": (
                    now + timedelta(seconds=self._block_seconds(error_class))
                ).isoformat(),
            }
        )
        state["updated_at"] = now.isoformat()
        self._save_json(self.state_path, state)
        return state

    def mark_success(
        self,
        state: dict[str, Any],
        model_id: str,
        provider_id: str,
        role: str,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        entry = state.setdefault("models", {}).setdefault(model_id, {})
        entry["total_successes"] = int(entry.get("total_successes") or 0) + 1
        entry.update(
            {
                "consecutive_failures": 0,
                "last_result": "success",
                "last_role": role,
                "last_error": None,
                "last_error_class": None,
                "last_success_at": now.isoformat(),
                "last_provider_id": provider_id,
                "blocked_until": None,
            }
        )
        state["updated_at"] = now.isoformat()
        self._save_json(self.state_path, state)
        return state

    def feedback(self, model_id: str, role: str, result: str, error: str = "") -> None:
        command = [
            "/usr/bin/python3",
            str(self.repo_root / "scripts" / "runtime_feedback.py"),
            "--model",
            model_id,
            "--role",
            role,
            "--result",
            result,
        ]
        if error:
            command.extend(["--error", error])
        subprocess.run(command, check=False, capture_output=True, text=True)
