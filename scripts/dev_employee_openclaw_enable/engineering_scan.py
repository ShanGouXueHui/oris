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
from .models import RuntimeContext


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


def scan_repository_sources(repo_root: Path) -> dict[str, Any]:
    policy = load_policy(repo_root)
    quality_findings, quality_file_count = scan_repository(repo_root, policy)
    architecture = scan_python_architecture(repo_root, AUTHORITIES)

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
    contract = contract_error(repo_root)

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
