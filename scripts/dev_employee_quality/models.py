from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    rule_id: str
    path: str
    line: int
    message: str
    value: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScanPolicy:
    scan_roots: tuple[str, ...]
    excluded_directory_names: frozenset[str]
    source_extensions: frozenset[str]
    authoritative_literal_files: frozenset[str]
    detectors: frozenset[str]
    environment_ports: tuple[int, ...]
    public_domains: tuple[str, ...]
    acceptance_project_names: tuple[str, ...]
    large_file_line_limits: dict[str, int]
    duplicate_constant_min_occurrences: int
    evidence_directory: str


@dataclass(frozen=True)
class SourceFile:
    absolute_path: Path
    relative_path: str
    suffix: str
    text: str
