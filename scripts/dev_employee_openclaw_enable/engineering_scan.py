from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.dev_employee_quality.policy import load_policy
from scripts.dev_employee_quality.repository import scan_repository

from .code_audit_scope import (
    architecture_paths,
    load_code_audit_scope,
    source_paths,
)
from .engineering_scan_ast import scan_python_architecture
from .engineering_scan_policy import (
    AUTHORITIES,
    active_path_findings,
    contract_error,
    legacy_path_findings,
)
from .evidence_config import load_standalone_evidence_target
from .models import RuntimeContext


_POLICY_EVIDENCE_CONFIG = Path(
    "config/dev_employee/openclaw_policy_diagnostic_evidence.json"
)
_ADDITIONAL_AUTHORITIES = {
    "sanitize_effective_tool_surface": (
        "scripts/dev_employee_openclaw_enable/effective_surface_inventory.py"
    ),
    "probe_approved_effective_tool_surface": (
        "scripts/dev_employee_openclaw_enable/effective_surface_inventory.py"
    ),
    "load_standalone_evidence_target": (
        "scripts/dev_employee_openclaw_enable/evidence_config.py"
    ),
    "load_model_tool_diagnostic_contract": (
        "scripts/dev_employee_openclaw_enable/model_tool_diagnostic_contract.py"
    ),
    "sanitize_agent_acceptance": (
        "scripts/dev_employee_openclaw_enable/model_tool_diagnostic_result.py"
    ),
    "classify_model_tool_diagnostic": (
        "scripts/dev_employee_openclaw_enable/model_tool_diagnostic_result.py"
    ),
    "run_model_tool_diagnostic": (
        "scripts/dev_employee_openclaw_enable/model_tool_diagnostic_runtime.py"
    ),
    "endpoint_from_config": (
        "scripts/dev_employee_openclaw_enable/free_mesh_protocol.py"
    ),
    "validate_health_payload": (
        "scripts/dev_employee_openclaw_enable/free_mesh_protocol.py"
    ),
    "probe_free_mesh_protocol": (
        "scripts/dev_employee_openclaw_enable/free_mesh_protocol.py"
    ),
    "is_write_capable_tool": "scripts/dev_employee_openclaw_enable/tool_authority.py",
    "_native_support_tools": "scripts/dev_employee_openclaw_enable/task_contract.py",
    "evaluate_native_support_outcomes": "scripts/dev_employee_openclaw_enable/telemetry_analysis.py",
    "parse_chat_request": "oris_vnext/openai_chat_contract.py",
    "normalize_assistant_message": "oris_vnext/openai_chat_contract.py",
    "model_to_role": "oris_vnext/free_mesh_compat.py",
    "chat_payload": "oris_vnext/free_mesh_compat.py",
    "build_handler": "oris_vnext/free_mesh_http.py",
    "FreeMeshInference": "oris_vnext/free_mesh_inference.py",
    "InferRefresh": "oris_vnext/infer_refresh.py",
    "execute_provider": "oris_vnext/runtime_provider_client.py",
    "RuntimeExecutionState": "oris_vnext/runtime_execution_state.py",
    "RuntimeExecutionEngine": "oris_vnext/runtime_execution_engine.py",
}


def _effective_authorities() -> dict[str, str]:
    authorities = dict(AUTHORITIES)
    authorities.pop("run", None)
    authorities.update(_ADDITIONAL_AUTHORITIES)
    return authorities


def _oversized_target_modules(
    repo_root: Path,
    paths: tuple[Path, ...],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in paths:
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 240:
            findings.append(
                {
                    "file": path.relative_to(repo_root).as_posix(),
                    "line_count": line_count,
                    "limit": 240,
                }
            )
    return findings


def _deduplicate_oversized(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    unique: dict[tuple[object, object], dict[str, Any]] = {}
    for item in findings:
        path = item.get("file") or item.get("path")
        size = item.get("line_count") or item.get("value")
        unique[(path, size)] = item
    return list(unique.values())


def _routing_contract_error(repo_root: Path) -> str:
    for relative in (
        Path("orchestration/routing_policy.yaml"),
        Path("orchestration/runtime_policy.yaml"),
    ):
        text = (repo_root / relative).read_text(encoding="utf-8")
        if "tool_calling:" not in text:
            return f"tool_calling role missing from {relative.as_posix()}"
    return ""


def _combined_contract_error(repo_root: Path) -> str:
    existing = contract_error(repo_root)
    if existing:
        return existing
    try:
        load_standalone_evidence_target(repo_root, _POLICY_EVIDENCE_CONFIG)
        load_code_audit_scope(repo_root)
    except Exception as exc:
        return str(exc) or type(exc).__name__
    return _routing_contract_error(repo_root)


def scan_repository_sources(repo_root: Path) -> dict[str, Any]:
    policy = load_policy(repo_root)
    scope = load_code_audit_scope(repo_root)
    audit_paths = source_paths(repo_root, scope, policy.source_extensions)
    architecture_files = architecture_paths(repo_root, scope)
    quality_findings, quality_file_count = scan_repository(
        repo_root,
        policy,
        audit_paths,
    )
    architecture = scan_python_architecture(
        repo_root,
        _effective_authorities(),
        architecture_files,
    )
    duplicate_bindings = [
        item.to_dict()
        for item in quality_findings
        if item.rule_id in {"duplicate_symbol", "duplicate_json_key", "python_syntax"}
    ]
    oversized = [
        item.to_dict()
        for item in quality_findings
        if item.rule_id == "large_file"
    ]
    oversized.extend(_oversized_target_modules(repo_root, architecture_files))
    oversized = _deduplicate_oversized(oversized)
    hardcoding = [
        item.to_dict()
        for item in quality_findings
        if item.rule_id
        not in {"duplicate_symbol", "duplicate_json_key", "python_syntax", "large_file"}
    ]
    legacy = [
        *legacy_path_findings(repo_root),
        *active_path_findings(repo_root),
    ]
    contract = _combined_contract_error(repo_root)
    failures = (
        duplicate_bindings,
        architecture["authority_violations"],
        architecture["duplicate_function_bodies"],
        architecture["import_cycles"],
        oversized,
        hardcoding,
        legacy,
        contract,
    )
    return {
        "ok": not any(failures),
        "files_scanned": quality_file_count,
        "python_architecture_files_scanned": architecture["files_scanned"],
        "duplicate_bindings": duplicate_bindings,
        "authority_violations": architecture["authority_violations"],
        "duplicate_function_bodies": architecture["duplicate_function_bodies"],
        "import_cycles": architecture["import_cycles"],
        "oversized_modules": oversized,
        "forbidden_hardcoding": hardcoding,
        "legacy_path_findings": legacy,
        "contract_error": contract or None,
        "quality_findings_total": len(quality_findings),
    }


def scan_engineering_sources(context: RuntimeContext) -> dict[str, Any]:
    return scan_repository_sources(context.repo_root)
