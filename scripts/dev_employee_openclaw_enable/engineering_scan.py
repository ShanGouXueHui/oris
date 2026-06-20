from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.dev_employee_quality.policy import load_policy
from scripts.dev_employee_quality.repository import scan_repository

from .engineering_scan_ast import scan_python_architecture, target_python_files
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
_AUDIT_DIRECTORY_ROOTS = (
    Path("scripts/dev_employee_openclaw_enable"),
    Path("scripts/dev_employee_quality"),
    Path("config/dev_employee"),
)
_AUDIT_AUTHORITY_FILES = (
    Path("scripts/dev_employee_activate_free_mesh_tool_calling_and_diagnose.sh"),
    Path("scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh"),
    Path("scripts/dev_employee_diagnose_openclaw_model_tool_call_routing.sh"),
    Path("scripts/dev_employee_diagnose_openclaw_readonly_policy.sh"),
    Path("scripts/dev_employee_enable_openclaw_readonly_tools.sh"),
    Path("scripts/oris_free_mesh_api.py"),
    Path("scripts/oris_infer.py"),
    Path("scripts/runtime_execute.py"),
    Path("oris_vnext/free_mesh_compat.py"),
    Path("oris_vnext/free_mesh_http.py"),
    Path("oris_vnext/free_mesh_inference.py"),
    Path("oris_vnext/infer_refresh.py"),
    Path("oris_vnext/openai_chat_contract.py"),
    Path("oris_vnext/runtime_execution_engine.py"),
    Path("oris_vnext/runtime_execution_state.py"),
    Path("oris_vnext/runtime_provider_client.py"),
    Path("tests/test_free_mesh_tool_calling.py"),
    Path("tests/test_free_mesh_protocol.py"),
    Path("tests/test_script_entrypoint_bootstrap.py"),
    Path("orchestration/routing_policy.yaml"),
    Path("orchestration/runtime_policy.yaml"),
    Path("memory/dev_employee/current_task.json"),
    Path("memory/dev_employee/current_task.md"),
    Path("docs/DEV_EMPLOYEE_CODE_FIRST_CONTINUATION_GATE_2026-06-20.md"),
    Path("docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md"),
    Path("docs/DEV_EMPLOYEE_MODEL_TOOL_CALL_AND_HARNESS_DIAGNOSTIC_2026-06-20.md"),
    Path("docs/DEV_EMPLOYEE_FREE_MESH_TOOL_CALLING_FIX_2026-06-20.md"),
    Path("docs/DEV_EMPLOYEE_FREE_MESH_TOOL_PROTOCOL_ACTIVATION_2026-06-20.md"),
    Path("docs/DEV_EMPLOYEE_NATIVE_SKILL_SUPPORT_TOOL_CONTRACT_2026-06-20.md"),
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


def _audit_source_paths(repo_root: Path, suffixes: set[str]) -> tuple[Path, ...]:
    paths = {
        path.relative_to(repo_root)
        for relative_root in _AUDIT_DIRECTORY_ROOTS
        for path in (repo_root / relative_root).rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    }
    paths.update(
        relative
        for relative in _AUDIT_AUTHORITY_FILES
        if (repo_root / relative).is_file()
    )
    return tuple(sorted(paths))


def _oversized_target_modules(repo_root: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in target_python_files(repo_root):
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
    except Exception as exc:
        return str(exc) or type(exc).__name__
    return _routing_contract_error(repo_root)


def scan_repository_sources(repo_root: Path) -> dict[str, Any]:
    policy = load_policy(repo_root)
    audit_paths = _audit_source_paths(repo_root, policy.source_extensions)
    quality_findings, quality_file_count = scan_repository(
        repo_root,
        policy,
        audit_paths,
    )
    architecture = scan_python_architecture(repo_root, _effective_authorities())
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
    oversized.extend(_oversized_target_modules(repo_root))
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
