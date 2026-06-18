from __future__ import annotations

import json
from pathlib import Path

from .models import ScanPolicy


DEFAULT_POLICY_PATH = Path("config/dev_employee/repository_quality_policy.json")


def load_policy(repo_root: Path, policy_path: Path | None = None) -> ScanPolicy:
    target = policy_path or repo_root / DEFAULT_POLICY_PATH
    if not target.is_absolute():
        target = repo_root / target
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("unsupported repository quality policy schema")
    return ScanPolicy(
        scan_roots=tuple(data["scan_roots"]),
        excluded_directory_names=frozenset(data["excluded_directory_names"]),
        source_extensions=frozenset(data["source_extensions"]),
        authoritative_literal_files=frozenset(data["authoritative_literal_files"]),
        detectors=frozenset(data["detectors"]),
        environment_ports=tuple(int(value) for value in data["environment_ports"]),
        public_domains=tuple(data["public_domains"]),
        acceptance_project_names=tuple(data["acceptance_project_names"]),
        large_file_line_limits={str(key): int(value) for key, value in data["large_file_line_limits"].items()},
        duplicate_constant_min_occurrences=int(data["duplicate_constant_min_occurrences"]),
        evidence_directory=str(data["evidence_directory"]),
    )
