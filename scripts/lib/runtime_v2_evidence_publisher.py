from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from runtime_v2_run_store import utc_now


class EvidencePublisherError(Exception):
    pass


class MissingEvidenceError(EvidencePublisherError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_index_id(module: str, artifacts: List[Dict[str, Any]]) -> str:
    stable = {
        "module": module,
        "artifacts": [
            {"path": artifact["path"], "sha256": artifact["sha256"], "size_bytes": artifact["size_bytes"]}
            for artifact in artifacts
        ],
    }
    raw = json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


class RuntimeV2EvidencePublisher:
    def __init__(self, repo_root: Path | str = ".") -> None:
        self.repo_root = Path(repo_root)

    def collect_artifacts(self, paths: Iterable[str]) -> List[Dict[str, Any]]:
        artifacts: List[Dict[str, Any]] = []
        for raw_path in sorted(paths):
            path = self.repo_root / raw_path
            if not path.exists() or not path.is_file():
                raise MissingEvidenceError(f"missing evidence artifact: {raw_path}")
            artifacts.append({
                "path": raw_path,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            })
        return artifacts

    def build_index(self, module: str, status: str, artifact_paths: Iterable[str], commit_sha: Optional[str] = None) -> Dict[str, Any]:
        artifacts = self.collect_artifacts(artifact_paths)
        return {
            "index_id": deterministic_index_id(module, artifacts),
            "module": module,
            "status": status,
            "artifacts": artifacts,
            "created_at": utc_now(),
            "commit_sha": commit_sha,
        }

    def write_index(self, index: Dict[str, Any], output_path: str) -> str:
        path = self.repo_root / output_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(index, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        return output_path

    def create_publish_plan(self, branch: str, commit_message: str, files: Iterable[str], evidence_index_ref: str, issue_number: Optional[int] = None) -> Dict[str, Any]:
        file_list = sorted(files)
        issue_update = self.create_issue_update_payload(issue_number, commit_message, evidence_index_ref) if issue_number is not None else {}
        return {
            "branch": branch,
            "commit_message": commit_message,
            "files": file_list,
            "evidence_index_ref": evidence_index_ref,
            "issue_update": issue_update,
        }

    def create_issue_update_payload(self, issue_number: Optional[int], summary: str, evidence_index_ref: str) -> Dict[str, Any]:
        return {
            "issue_number": issue_number,
            "summary": summary,
            "evidence_index_ref": evidence_index_ref,
            "body": f"Runtime v2 evidence updated: {summary}\n\nEvidence index: `{evidence_index_ref}`",
        }
