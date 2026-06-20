from __future__ import annotations

import hashlib
import json
from typing import Any


_ALLOWED_ERROR_KINDS = {"missing-path", "schema", "resolvability"}
_ALLOWED_INPUT_MODES = {"value", "json", "builder", "unset"}


def _message_rule_code(message: str) -> str:
    lowered = message.lower()
    compact = lowered.replace("_", "").replace("-", "").replace(" ", "")
    if "allow" in compact and "alsoallow" in compact and (
        "cannotsetboth" in compact or "samescope" in compact
    ):
        return "tools_allow_also_allow_mutually_exclusive"
    if "unknown" in lowered and "key" in lowered:
        return "unknown_config_key"
    if "invalid" in lowered and "profile" in lowered:
        return "invalid_tool_profile"
    return "unclassified_validation_error"


def _safe_error(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    message = value.get("message")
    if kind not in _ALLOWED_ERROR_KINDS or not isinstance(message, str):
        return None
    return {
        "kind": kind,
        "rule_code": _message_rule_code(message),
        "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
    }


def summarize_dry_run_output(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return {
            "json_parsed": False,
            "raw_output_recorded": False,
        }
    if not isinstance(payload, dict):
        return {
            "json_parsed": False,
            "raw_output_recorded": False,
        }
    errors = [
        safe
        for item in payload.get("errors", [])
        if (safe := _safe_error(item)) is not None
    ]
    modes = payload.get("inputModes")
    input_modes = (
        [item for item in modes if item in _ALLOWED_INPUT_MODES]
        if isinstance(modes, list)
        else []
    )
    checks = payload.get("checks")
    safe_checks = {
        key: bool(checks.get(key))
        for key in ("schema", "resolvability", "resolvabilityComplete")
        if isinstance(checks, dict) and isinstance(checks.get(key), bool)
    }
    return {
        "json_parsed": True,
        "ok": payload.get("ok") is True,
        "operations": payload.get("operations")
        if isinstance(payload.get("operations"), int)
        else None,
        "input_modes": input_modes,
        "checks": safe_checks,
        "error_count": len(errors),
        "errors": errors[:10],
        "refs_checked": payload.get("refsChecked")
        if isinstance(payload.get("refsChecked"), int)
        else None,
        "skipped_exec_refs": payload.get("skippedExecRefs")
        if isinstance(payload.get("skippedExecRefs"), int)
        else None,
        "raw_output_recorded": False,
        "secret_refs_recorded": False,
    }
