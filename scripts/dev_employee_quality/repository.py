from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Iterable

from . import hardcoding
from .duplicates import scan_json, scan_python, scan_text_symbols
from .models import Finding, ScanPolicy, SourceFile


def iter_source_files(repo_root: Path, policy: ScanPolicy) -> Iterable[SourceFile]:
    for root_name in policy.scan_roots:
        scan_root = repo_root / root_name
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in policy.source_extensions:
                continue
            relative = path.relative_to(repo_root)
            if any(part in policy.excluded_directory_names for part in relative.parts):
                continue
            yield SourceFile(path, relative.as_posix(), path.suffix.lower(), path.read_text(encoding="utf-8", errors="replace"))


def scan_large_file(source: SourceFile, policy: ScanPolicy) -> list[Finding]:
    if "large_file" not in policy.detectors:
        return []
    limit = policy.large_file_line_limits.get(source.suffix)
    line_count = len(source.text.splitlines())
    if not limit or line_count <= limit:
        return []
    return [Finding("large_file", source.relative_path, 1, f"split this {line_count}-line file by responsibility; limit is {limit}", str(line_count))]


def _scan_definitions(source: SourceFile) -> tuple[list[Finding], list[tuple[str, str, int]]]:
    if source.suffix == ".py":
        return scan_python(source)
    if source.suffix in {".sh", ".ts", ".tsx", ".js", ".mjs", ".cjs"}:
        return scan_text_symbols(source)
    if source.suffix == ".json":
        return scan_json(source), []
    return [], []


def scan_repository(repo_root: Path, policy: ScanPolicy) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    constants: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    file_count = 0
    for source in iter_source_files(repo_root, policy):
        file_count += 1
        findings.extend(hardcoding.scan(source, policy))
        findings.extend(scan_large_file(source, policy))
        definition_findings, source_constants = _scan_definitions(source)
        findings.extend(definition_findings)
        for name, value, line in source_constants:
            constants[name].append((source.relative_path, value, line))
    if "duplicate_constant" in policy.detectors:
        for name, rows in sorted(constants.items()):
            if len({path for path, _, _ in rows}) < policy.duplicate_constant_min_occurrences:
                continue
            locations = "; ".join(f"{path}:{line}" for path, _, line in rows[:12])
            for path, value, line in rows:
                findings.append(Finding("duplicate_constant", path, line, f"move constant {name} to one authoritative source; also found at {locations}", value[:160]))
    findings.sort(key=lambda item: (item.path, item.line, item.rule_id, item.message))
    return findings, file_count
