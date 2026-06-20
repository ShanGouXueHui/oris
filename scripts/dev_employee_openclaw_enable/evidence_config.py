from __future__ import annotations

from pathlib import Path

from .models import EvidenceTarget
from .task_contract import load_json_object


def load_standalone_evidence_target(
    repo_root: Path,
    relative_path: Path,
) -> EvidenceTarget:
    value = load_json_object(repo_root / relative_path)
    if value.get("schema_version") != 1:
        raise RuntimeError("unsupported evidence target schema")
    fields = ("directory", "filename_prefix", "commit_message_prefix")
    if any(
        not isinstance(value.get(field), str) or not str(value[field]).strip()
        for field in fields
    ):
        raise RuntimeError("evidence target fields are invalid")
    return EvidenceTarget(
        directory=repo_root / str(value["directory"]),
        filename_prefix=str(value["filename_prefix"]),
        commit_message_prefix=str(value["commit_message_prefix"]),
    )
