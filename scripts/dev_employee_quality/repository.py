from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from . import hardcoding
from .duplicates import scan_json, scan_python, scan_text_symbols
from .models import Finding, ScanPolicy, SourceFile
from .secrets import scan_json_secrets


TIMESTAMPED_JSON = re.compile(r"(?:^|[-_])20\d{6,12}(?:[-_.]|$)")


def _is_excluded(relative: Path, policy: ScanPolicy) -> bool:
    relative_text = relative.as_posix()
    if any(part in policy.excluded_directory_names for part in relative.parts):
        return True
    if relative.name in policy.excluded_file_names:
        return True
    if any(relative_text == prefix or relative_text.startswith(prefix + "/") for prefix in policy.excluded_path_prefixes):
        return True
    return bool(
        policy.exclude_timestamped_json
        and relative.suffix.lower() == ".json"
        and TIMESTAMPED_JSON.search(relative.name)
    )


def iter_source_files(repo_root: Path, policy: ScanPolicy) -> Iterable[SourceFile]:
    for root_name in policy.scan_roots:
        scan_root = repo_root / root_name
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in policy.source_extensions:
                continue
            relative = path.relative_to(repo_root)
            if _is_excluded(relative, policy):
                continue
            yield SourceFile(
                path,
                relative.as_posix(),
                path.suffix.lower(),
                path.read_text(encoding="utf-8", errors="replace"),
            )


def scan_large_file(source: SourceFile, policy: ScanPolicy) -> list[Finding]:
    if "large_file" not in policy.detectors or source.suffix not in policy.code_extensions:
        return []
    limit = policy.large_file_line_limits.get(source.suffix)
    line_count = len(source.text.splitlines())
    if not limit or line_count <= limit:
        return []
    return [
        Finding(
            "large_file",
            source.relative_path,
            1,
            f"split this {line_count}-line source file by responsibility; limit is {limit}",
            str(line_count),
        )
    ]


def scan_definitions(source: SourceFile, policy: ScanPolicy) -> list[Finding]:
    if source.suffix == ".py":
        return scan_python(source)
    if source.suffix in {".sh", ".ts", ".tsx", ".js", ".mjs", ".cjs"}:
        return scan_text_symbols(source)
    if source.suffix == ".json":
        findings = scan_json(source)
        if "plaintext_secret" in policy.detectors:
            findings.extend(scan_json_secrets(source))
        return findings
    return []


def scan_repository(repo_root: Path, policy: ScanPolicy) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    file_count = 0
    for source in iter_source_files(repo_root, policy):
        file_count += 1
        if source.suffix in policy.code_extensions:
            findings.extend(hardcoding.scan(source, policy))
        findings.extend(scan_large_file(source, policy))
        findings.extend(scan_definitions(source, policy))
    findings.sort(key=lambda item: (item.path, item.line, item.rule_id, item.message))
    return findings, file_count
