from __future__ import annotations

from pathlib import Path

from .task_contract import load_json_object, load_runtime_contract, load_task_id


AUTHORITIES = {
    "load_context": "scripts/dev_employee_openclaw_enable/context.py",
    "load_runtime_contract": "scripts/dev_employee_openclaw_enable/task_contract.py",
    "load_json_object": "scripts/dev_employee_openclaw_enable/task_contract.py",
    "apply_readonly_policy": "scripts/dev_employee_openclaw_enable/policy.py",
    "enable_profile_tools": "scripts/dev_employee_openclaw_enable/profile_tool_policy.py",
    "ensure_skill_visible": "scripts/dev_employee_openclaw_enable/agent_skill_policy.py",
    "run_activation_candidate_gate": (
        "scripts/dev_employee_openclaw_enable/activation_candidate_gate.py"
    ),
    "activate_validated_candidate": (
        "scripts/dev_employee_openclaw_enable/activation_transaction.py"
    ),
    "run_enablement_rollback": (
        "scripts/dev_employee_openclaw_enable/enablement_rollback.py"
    ),
    "summarize_effective_tool_payload": (
        "scripts/dev_employee_openclaw_enable/effective_tool_contract.py"
    ),
    "probe_effective_tool_surface": (
        "scripts/dev_employee_openclaw_enable/effective_tool_surface.py"
    ),
    "run_effective_surface_diagnostic": (
        "scripts/dev_employee_openclaw_enable/effective_surface_diagnostic.py"
    ),
    "evaluate_readonly_invariants": (
        "scripts/dev_employee_openclaw_enable/readonly_invariants.py"
    ),
    "record_readonly_invariants": (
        "scripts/dev_employee_openclaw_enable/readonly_invariants.py"
    ),
    "restart_service_and_wait": (
        "scripts/dev_employee_openclaw_enable/service_control.py"
    ),
    "verify_plugin_runtime": "scripts/dev_employee_openclaw_enable/plugin_runtime.py",
    "publish_evidence": "scripts/dev_employee_openclaw_enable/evidence.py",
    "publish_evidence_artifacts": (
        "scripts/dev_employee_openclaw_enable/git_evidence.py"
    ),
    "run_enablement": "scripts/dev_employee_openclaw_enable/runner.py",
    "run_policy_diagnostic": "scripts/dev_employee_openclaw_enable/diagnostic.py",
    "build_policy_validation_patch": (
        "scripts/dev_employee_openclaw_enable/runtime_policy_patch.py"
    ),
    "validate_candidate_with_installed_runtime": (
        "scripts/dev_employee_openclaw_enable/runtime_validation.py"
    ),
    "install_routing_skill": (
        "scripts/dev_employee_openclaw_enable/skill_installation.py"
    ),
    "verify_routing_skill_runtime": (
        "scripts/dev_employee_openclaw_enable/skill_runtime.py"
    ),
    "run": "scripts/dev_employee_openclaw_enable/process.py",
}
_LEGACY_LIBS = (
    "dev_employee_openclaw_readonly_enable_common_20260618.sh",
    "dev_employee_openclaw_readonly_enable_preflight_20260618.sh",
    "dev_employee_openclaw_readonly_enable_policy_direct_20260618.sh",
    "dev_employee_openclaw_readonly_enable_browser_telemetry_20260618.sh",
    "dev_employee_openclaw_readonly_enable_finalize_20260618.sh",
)
_ACTIVE_FORBIDDEN_FILES = (
    "scripts/dev_employee_openclaw_enable/agent_surface.py",
)
_ACTIVE_FORBIDDEN_TOKENS = (
    "system" + "PromptReport",
    "approved_tools_missing_from_" + "effective_model_surface",
)


def legacy_path_findings(repo_root: Path) -> list[dict[str, str]]:
    root = repo_root / "scripts" / "lib"
    findings: list[dict[str, str]] = []
    forbidden = (
        "function ",
        "() {",
        "python3",
        "openclaw",
        "systemctl",
        "curl ",
        "git ",
    )
    allowed = {"return 64 2>/dev/null || exit 64"}
    for name in _LEGACY_LIBS:
        path = root / name
        relative = path.relative_to(repo_root).as_posix()
        if not path.is_file():
            findings.append({"file": relative, "kind": "missing"})
            continue
        code = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if any(any(token in line for token in forbidden) for line in code):
            findings.append({"file": relative, "kind": "executable_logic"})
        if set(code) - allowed:
            findings.append({"file": relative, "kind": "unapproved_statement"})
    return findings


def active_path_findings(repo_root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for relative in _ACTIVE_FORBIDDEN_FILES:
        if (repo_root / relative).exists():
            findings.append({"file": relative, "kind": "forbidden_competing_path"})

    package = repo_root / "scripts" / "dev_employee_openclaw_enable"
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(repo_root).as_posix()
        for token in _ACTIVE_FORBIDDEN_TOKENS:
            if token in text:
                findings.append(
                    {
                        "file": relative,
                        "kind": f"forbidden_active_token:{token}",
                    }
                )

    diagnostic = (
        repo_root / "scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh"
    )
    relative = diagnostic.relative_to(repo_root).as_posix()
    if not diagnostic.is_file():
        findings.append({"file": relative, "kind": "missing_diagnostic_entrypoint"})
    else:
        text = diagnostic.read_text(encoding="utf-8")
        audit_index = text.find("code_audit_cli")
        diagnostic_index = text.find("effective_surface_cli")
        if audit_index < 0 or diagnostic_index < 0 or audit_index > diagnostic_index:
            findings.append(
                {"file": relative, "kind": "code_gate_not_before_runtime_diagnostic"}
            )
        if "dev_employee_enable_openclaw_readonly_tools.sh" in text:
            findings.append(
                {"file": relative, "kind": "full_enablement_entrypoint_referenced"}
            )

    authority_doc = (
        repo_root
        / "docs/DEV_EMPLOYEE_NATIVE_MODEL_TOOL_SURFACE_DIAGNOSTIC_2026-06-20.md"
    )
    if authority_doc.is_file() and "Status: SUPERSEDED" not in authority_doc.read_text(
        encoding="utf-8"
    ):
        findings.append(
            {
                "file": authority_doc.relative_to(repo_root).as_posix(),
                "kind": "competing_document_authority",
            }
        )
    return findings


def contract_error(repo_root: Path) -> str:
    try:
        contract = load_runtime_contract(
            repo_root / "config/dev_employee/openclaw_readonly_acceptance.json"
        )
        load_task_id(repo_root / "memory/dev_employee/current_task.json")
        projects = load_json_object(
            repo_root / "orchestration/project_registry.json"
        ).get("projects")
        project_key = contract["baseline"]["project_key"]
        if not isinstance(projects, dict) or project_key not in projects:
            raise RuntimeError("baseline project is missing from project registry")
        targets = contract["evidence_targets"]
        if targets["enablement"] == targets["effective_surface_diagnostic"]:
            raise RuntimeError("enablement and diagnostic evidence targets must differ")
    except Exception as exc:
        return str(exc) or type(exc).__name__
    return ""
