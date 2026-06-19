from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

from .agent_skill_policy import ensure_skill_visible
from .candidate_validation import candidate_policy_compatibility
from .models import RuntimeContext
from .policy import PolicyApplication
from .profile_tool_policy import enable_profile_tools
from .runtime_validation import validate_candidate_with_installed_runtime
from .state import load_json, sha256_file


_REDACTED_KEYS = {
    "token",
    "password",
    "secret",
    "credential",
    "credentials",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "private_key",
}


def _validation_safe_copy(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            normalized = str(key).replace("-", "_").lower()
            if normalized in _REDACTED_KEYS or normalized.endswith("_token"):
                result[str(key)] = "__SCHEMA_VALIDATION_REDACTED__"
            else:
                result[str(key)] = _validation_safe_copy(child)
        return result
    if isinstance(value, list):
        return [_validation_safe_copy(child) for child in value]
    return copy.deepcopy(value)


def _write_restricted_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def build_private_candidate(
    context: RuntimeContext,
    temp_root: Path,
) -> tuple[Path, dict[str, Any]]:
    candidate = _validation_safe_copy(load_json(context.openclaw_config))
    tools = candidate.get("tools")
    if not isinstance(tools, dict):
        raise RuntimeError("OpenClaw tools policy is missing")
    tool_policy = enable_profile_tools(
        tools,
        context.approved_tools,
        context.profile_expansion,
        context.required_profile,
    )
    skill_policy = ensure_skill_visible(candidate, context.routing_skill_name)
    application = PolicyApplication(tool_policy, skill_policy)
    candidate_file = temp_root / "candidate.json"
    _write_restricted_json(candidate_file, candidate)
    return candidate_file, application.evidence()


def inspect_private_candidate(
    context: RuntimeContext,
    candidate_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    compatibility = candidate_policy_compatibility(context, candidate_path)
    runtime_validation = validate_candidate_with_installed_runtime(candidate_path)
    return compatibility, runtime_validation


def candidate_evidence(candidate_path: Path) -> dict[str, Any]:
    return {
        "sha256": sha256_file(candidate_path),
        "private_temporary_location": True,
        "sensitive_values_redacted": True,
        "active_config_replaced": False,
        "candidate_config_recorded": False,
    }
