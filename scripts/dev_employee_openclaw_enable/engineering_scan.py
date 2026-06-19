from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import Any

from .models import RuntimeContext


_AUTHORITY_NAMES = {
    "load_context",
    "apply_readonly_policy",
    "enable_profile_tools",
    "restart_gateway",
    "restart_service_and_wait",
    "write_and_commit_evidence",
    "verify_plugin_runtime",
}
_LITERAL_TARGET_TERMS = {
    "host",
    "port",
    "provider",
    "model",
    "version",
    "project",
    "branch",
    "path",
}


def _source_files(context: RuntimeContext) -> list[Path]:
    package = context.repo_root / "scripts" / "dev_employee_openclaw_enable"
    files = sorted(package.glob("*.py"))
    for name in (
        "dev_employee_enable_openclaw_readonly_tools.sh",
        "dev_employee_diagnose_openclaw_readonly_policy.sh",
    ):
        entry = context.repo_root / "scripts" / name
        if entry.is_file():
            files.append(entry)
    return files


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, (ast.Tuple, ast.List)):
        values: list[str] = []
        for child in node.elts:
            values.extend(_target_names(child))
        return values
    return []


def _name_terms(name: str) -> set[str]:
    return {part for part in name.lower().split("_") if part}


def _literal_kind(name: str, value: object) -> str | None:
    terms = _name_terms(name)
    matched = terms.intersection(_LITERAL_TARGET_TERMS)
    if not matched:
        return None
    if "path" in matched:
        if isinstance(value, str) and (value.startswith("/") or value.startswith("~")):
            return "absolute_path_literal"
        return None
    if "branch" in matched and value == "main":
        return None
    if "host" in matched and value in {"localhost", "127" + ".0.0.1"}:
        return None
    if "project" in matched:
        if isinstance(value, str) and "acceptance" in value.lower():
            return "acceptance_project_literal"
        return None
    if "version" in matched:
        if isinstance(value, str) and value[:1].isdigit() and "." in value:
            return "runtime_version_literal"
        return None
    if "port" in matched and isinstance(value, int):
        return "port_literal"
    if "host" in matched and isinstance(value, str) and value:
        return "host_literal"
    if ("provider" in matched or "model" in matched) and isinstance(value, str) and value:
        return "provider_or_model_literal"
    if "branch" in matched and isinstance(value, str) and value:
        return "branch_literal"
    return None


def _record_literal(
    findings: list[dict[str, str]],
    relative: str,
    name: str,
    value: object,
) -> None:
    kind = _literal_kind(name, value)
    if kind:
        findings.append({"file": relative, "kind": kind})


def _python_findings(path: Path, root: Path) -> list[dict[str, str]]:
    relative = path.relative_to(root).as_posix()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            for target in node.targets:
                for name in _target_names(target):
                    _record_literal(findings, relative, name, node.value.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Constant):
            for name in _target_names(node.target):
                _record_literal(findings, relative, name, node.value.value)
        elif isinstance(node, ast.keyword) and node.arg and isinstance(node.value, ast.Constant):
            _record_literal(findings, relative, node.arg, node.value.value)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and isinstance(value, ast.Constant)
                ):
                    _record_literal(findings, relative, key.value, value.value)
    return findings


def _shell_findings(path: Path, root: Path) -> list[dict[str, str]]:
    relative = path.relative_to(root).as_posix()
    findings: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        name, raw = line.split("=", 1)
        value = raw.strip().strip("'\"")
        if value.startswith("$") or "$(" in value:
            continue
        _record_literal(findings, relative, name.strip(), value)
    return findings


def scan_engineering_sources(context: RuntimeContext) -> dict[str, Any]:
    definitions: dict[str, list[str]] = defaultdict(list)
    hardcoding: list[dict[str, str]] = []
    oversized: list[dict[str, Any]] = []
    files = _source_files(context)

    for path in files:
        relative = path.relative_to(context.repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        line_count = len(text.splitlines())
        if line_count > 240:
            oversized.append({"file": relative, "line_count": line_count})
        if path.suffix == ".py":
            tree = ast.parse(text, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name in _AUTHORITY_NAMES:
                        definitions[node.name].append(relative)
            hardcoding.extend(_python_findings(path, context.repo_root))
        else:
            hardcoding.extend(_shell_findings(path, context.repo_root))

    duplicates = {name: paths for name, paths in definitions.items() if len(paths) > 1}
    return {
        "ok": not duplicates and not hardcoding and not oversized,
        "files_scanned": len(files),
        "duplicate_authorities": duplicates,
        "forbidden_hardcoding": hardcoding,
        "oversized_modules": oversized,
        "oversized_modules_require_layered_remediation": bool(oversized),
    }
