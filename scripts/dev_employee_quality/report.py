from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .policy import load_policy
from .repository import scan_repository


def write_report(repo_root: Path, output: Path | None = None) -> tuple[dict[str, object], Path]:
    policy = load_policy(repo_root)
    findings, file_count = scan_repository(repo_root, policy)
    checked_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = output or repo_root / policy.evidence_directory / f"repository-quality-scan-{checked_at}.json"
    if not target.is_absolute():
        target = repo_root / target
    target.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(item.rule_id for item in findings)
    report: dict[str, object] = {
        "schema_version": 1,
        "checked_at": checked_at,
        "repository": repo_root.name,
        "result": "PASS" if not findings else "FINDINGS",
        "files_scanned": file_count,
        "finding_count": len(findings),
        "findings_by_rule": dict(sorted(counts.items())),
        "findings": [item.to_dict() for item in findings],
        "scan_only": True,
    }
    target.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report, target
