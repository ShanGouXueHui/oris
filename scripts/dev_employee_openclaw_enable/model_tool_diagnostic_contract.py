from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import EvidenceTarget
from .task_contract import (
    load_json_object,
    require_integer,
    require_mapping,
    require_string,
)


CONFIG_PATH = Path(
    "config/dev_employee/openclaw_model_tool_call_diagnostic.json"
)


@dataclass(frozen=True)
class DiagnosticTurn:
    intent: str
    message_template: str
    expected_tool: str | None = None


@dataclass(frozen=True)
class ModelToolDiagnosticContract:
    session_prefix: str
    control_turn: DiagnosticTurn
    oris_turn: DiagnosticTurn
    turn_timeout_seconds: int
    telemetry_wait_seconds: int
    evidence: EvidenceTarget


def _turn(value: Any, label: str) -> DiagnosticTurn:
    mapping = require_mapping(value, label)
    expected = mapping.get("expected_tool")
    if expected is not None and not isinstance(expected, str):
        raise RuntimeError(f"invalid string: {label}.expected_tool")
    return DiagnosticTurn(
        intent=require_string(mapping.get("intent"), f"{label}.intent"),
        message_template=require_string(
            mapping.get("message_template"),
            f"{label}.message_template",
        ),
        expected_tool=expected,
    )


def load_model_tool_diagnostic_contract(
    repo_root: Path,
) -> ModelToolDiagnosticContract:
    root = load_json_object(repo_root / CONFIG_PATH)
    if root.get("schema_version") != 1:
        raise RuntimeError("unsupported model tool diagnostic schema")
    control = _turn(root.get("control_turn"), "control_turn")
    oris = _turn(root.get("oris_turn"), "oris_turn")
    if "{tool_name}" not in control.message_template:
        raise RuntimeError("control turn must contain {tool_name}")
    if not oris.expected_tool:
        raise RuntimeError("ORIS turn expected tool is required")
    evidence = require_mapping(root.get("evidence"), "evidence")
    return ModelToolDiagnosticContract(
        session_prefix=require_string(root.get("session_prefix"), "session_prefix"),
        control_turn=control,
        oris_turn=oris,
        turn_timeout_seconds=require_integer(
            root.get("turn_timeout_seconds"),
            "turn_timeout_seconds",
        ),
        telemetry_wait_seconds=require_integer(
            root.get("telemetry_wait_seconds"),
            "telemetry_wait_seconds",
        ),
        evidence=EvidenceTarget(
            directory=repo_root
            / require_string(evidence.get("directory"), "evidence.directory"),
            filename_prefix=require_string(
                evidence.get("filename_prefix"),
                "evidence.filename_prefix",
            ),
            commit_message_prefix=require_string(
                evidence.get("commit_message_prefix"),
                "evidence.commit_message_prefix",
            ),
        ),
    )
