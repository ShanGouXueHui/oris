from __future__ import annotations

import ast
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any

from scripts.dev_employee_quality.duplicates import scan_python
from scripts.dev_employee_quality.models import SourceFile

from .models import RuntimeContext
from .task_contract import load_json_object, load_runtime_contract, load_task_id


_AUTHORITIES = {
    "load_context": "context.py",
    "load_runtime_contract": "task_contract.py",
    "load_json_object": "task_contract.py",
    "apply_readonly_policy": "policy.py",
    "enable_profile_tools": "profile_tool_policy.py",
    "ensure_skill_visible": "agent_skill_policy.py",
    "run_activation_candidate_gate": "activation_candidate_gate.py",
    "run_enablement_rollback": "enablement_rollback.py",
    "probe_effective_tool_surface": "effective_tool_surface.py",
    "run_effective_surface_diagnostic": "effective_surface_diagnostic.py",
    "restart_service_and_wait": "service_control.py",
    "verify_plugin_runtime": "plugin_runtime.py",
    "write_and_commit_evidence": "evidence.py",
    "run_enablement": "runner.py",
    "run_policy_diagnostic": "diagnostic.py",
    "build_policy_validation_patch": "runtime_policy_patch.py",
    "validate_candidate_with_installed_runtime": "runtime_validation.py",
    "install_routing_skill": "skill_installation.py",
    "verify_routing_skill_runtime": "skill_runtime.py",
    "run": "process.py",
}
_LEGACY_LIBS = (
    "dev_employee_openclaw_readonly_enable_common_20260618.sh",
    "dev_employee_openclaw_readonly_enable_preflight_20260618.sh",
    "dev_employee_openclaw_readonly_enable_policy_direct_20260618.sh",
    "dev_employee_openclaw_readonly_enable_browser_telemetry_20260618.sh",
    "dev_employee_openclaw_readonly_enable_finalize_20260618.sh",
)
_ABSOLUTE_HOME_PREFIX = "/" + "home" + "/"


def _cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    found: set[tuple[str, ...]] = set()

    def visit(node: str, path: list[str]) -> None:
        for child in graph.get(node, set()):
            if child not in graph:
                continue
            if child in path:
                core = path[path.index(child) :]
                rotations = [tuple(core[index:] + core[:index]) for index in range(len(core))]
                found.add(min(rotations))
            elif len(path) <= len(graph):
                visit(child, path + [child])

    for node in graph:
        visit(node, [node])
    return [list(item) for item in sorted(found)]


def _digest(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    if node.name == "main" or node.name.startswith("_"):
        return None
    if len(list(ast.walk(node))) < 12:
        return None
    normalized = ast.FunctionDef(
        name="function",
        args=node.args,
        body=node.body,
        decorator_list=[],
        returns=node.returns,
        type_comment=node.type_comment,
    )
    return hashlib.sha256(ast.dump(normalized).encode("utf-8")).hexdigest()


def _legacy_findings(repo_root: Path) -> list[dict[str, str]]:
    root = repo_root / "scripts" / "lib"
    findings: list[dict[str, str]] = []
    forbidden = ("function ", "() {", "python3", "openclaw", "systemctl", "curl ", "git ")
    allowed = {"return 64 2>/dev/null || exit 64"}
    for name in _LEGACY_LIBS:
        path = root / name
        if not path.is_file():
            findings.append({"file": name, "kind": "missing"})
            continue
        code = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if any(any(token in line for token in forbidden) for line in code):
            findings.append({"file": name, "kind": "executable_logic"})
        if set(code) - allowed:
            findings.append({"file": name, "kind": "unapproved_statement"})
    return findings


def _unsafe_env_calls(tree: ast.Module, relative: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if any(keyword.arg == "env" for keyword in node.keywords):
            findings.append({"file": relative, "kind": "subprocess_env_override"})
    return findings


def scan_repository_sources(repo_root: Path) -> dict[str, Any]:
    package = repo_root / "scripts" / "dev_employee_openclaw_enable"
    files = sorted(package.glob("*.py"))
    duplicate_bindings: list[dict[str, Any]] = []
    oversized: list[dict[str, Any]] = []
    hardcoding: list[dict[str, str]] = []
    definitions: dict[str, list[str]] = defaultdict(list)
    bodies: dict[str, list[tuple[str, str]]] = defaultdict(list)
    graph: dict[str, set[str]] = {}

    for path in files:
        relative = path.name
        text = path.read_text(encoding="utf-8")
        duplicate_bindings.extend(
            item.to_dict() for item in scan_python(SourceFile(path, relative, ".py", text))
        )
        if len(text.splitlines()) > 240:
            oversized.append({"file": relative, "line_count": len(text.splitlines())})
        tree = ast.parse(text, filename=str(path))
        hardcoding.extend(_unsafe_env_calls(tree, relative))
        imports: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                definitions[node.name].append(relative)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                digest = _digest(node)
                if digest:
                    bodies[digest].append((relative, node.name))
            if isinstance(node, ast.ImportFrom) and node.level == 1:
                if node.module:
                    imports.add(node.module.split(".")[0])
                else:
                    imports.update(item.name.split(".")[0] for item in node.names)
        graph[path.stem] = imports - {path.stem}
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _ABSOLUTE_HOME_PREFIX in node.value:
                    hardcoding.append({"file": relative, "kind": "absolute_home_path"})

    authority = {
        name: definitions.get(name, [])
        for name, expected in _AUTHORITIES.items()
        if definitions.get(name, []) != [expected]
    }
    duplicate_bodies = [values for values in bodies.values() if len(values) > 1]
    contract_error = ""
    try:
        contract = load_runtime_contract(
            repo_root / "config/dev_employee/openclaw_readonly_acceptance.json"
        )
        load_task_id(repo_root / "memory/dev_employee/current_task.json")
        projects = load_json_object(
            repo_root / "orchestration/project_registry.json"
        ).get("projects")
        if not isinstance(projects, dict) or contract["baseline"]["project_key"] not in projects:
            raise RuntimeError("baseline project is missing from project registry")
    except Exception as exc:
        contract_error = str(exc) or type(exc).__name__

    legacy = _legacy_findings(repo_root)
    import_cycles = _cycles(graph)
    failures = (
        duplicate_bindings,
        authority,
        duplicate_bodies,
        import_cycles,
        oversized,
        hardcoding,
        legacy,
        contract_error,
    )
    return {
        "ok": not any(failures),
        "files_scanned": len(files),
        "duplicate_bindings": duplicate_bindings,
        "authority_violations": authority,
        "duplicate_function_bodies": duplicate_bodies,
        "import_cycles": import_cycles,
        "oversized_modules": oversized,
        "forbidden_hardcoding": hardcoding,
        "legacy_path_findings": legacy,
        "contract_error": contract_error or None,
    }


def scan_engineering_sources(context: RuntimeContext) -> dict[str, Any]:
    return scan_repository_sources(context.repo_root)
