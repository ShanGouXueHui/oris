#!/usr/bin/env python3
"""Generate ORIS skill promotion policy decisions from audit reports.

This script consumes the quarantine-only audit summary and emits deterministic
policy decisions. It does not download, install, import, or execute candidate
skill code.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
SUMMARY_PATH = ORIS_DIR / "logs" / "dev_employee" / "skill_audit" / "summary_20260525.json"
OUT_JSON = ORIS_DIR / "logs" / "dev_employee" / "skill_audit" / "policy_decision_20260525.json"
OUT_MD = ORIS_DIR / "logs" / "dev_employee" / "skill_audit" / "policy_decision_20260525.md"

HIGH_RISK_FINDINGS = {
    "shell_download_exec",
    "package_hooks",
    "process_exec",
    "network_write",
    "credential_keywords",
    "sensitive_paths",
}

BLOCK_FINDINGS = {
    "shell_download_exec",
    "package_hooks",
    "process_exec",
    "network_write",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def decide(item: dict[str, Any]) -> dict[str, Any]:
    finding_counts = item.get("finding_counts") or {}
    risk_score = item.get("risk_score_rough")
    reasons: list[str] = []

    if risk_score is None:
        decision = "blocked_missing_audit"
        reasons.append("audit summary did not include a risk score")
    elif any(finding_counts.get(kind, 0) > 0 for kind in BLOCK_FINDINGS):
        decision = "blocked_no_install"
        for kind in sorted(BLOCK_FINDINGS):
            count = finding_counts.get(kind, 0)
            if count:
                reasons.append(f"{kind}={count}")
    elif finding_counts.get("credential_keywords", 0) or finding_counts.get("sensitive_paths", 0):
        decision = "intelligence_only"
        if finding_counts.get("credential_keywords", 0):
            reasons.append(f"credential_keywords={finding_counts['credential_keywords']}")
        if finding_counts.get("sensitive_paths", 0):
            reasons.append(f"sensitive_paths={finding_counts['sensitive_paths']}")
    elif risk_score == 0:
        decision = "intelligence_only_reviewable"
        reasons.append("no risk indicators in coarse scan; still not approved for runtime install")
    else:
        decision = "intelligence_only"
        reasons.append(f"risk_score_rough={risk_score}")

    return {
        "name": item["name"],
        "repo": item["repo"],
        "commit_sha": item.get("commit_sha"),
        "risk_score_rough": risk_score,
        "finding_counts": finding_counts,
        "decision": decision,
        "reasons": reasons,
        "allowed_uses": [
            "read-only intelligence extraction",
            "directory/category discovery",
            "manual source review in quarantine",
        ],
        "forbidden_uses": [
            "direct production install",
            "global OpenClaw skill install",
            "running installer scripts or package hooks",
            "granting credential or browser-profile access",
        ],
    }


def main() -> int:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    decisions = [decide(item) for item in summary.get("reports", [])]
    payload = {
        "generated_at": now_iso(),
        "source_summary": str(SUMMARY_PATH),
        "policy": "third_party_skills_are_quarantine_only_until_explicitly_promoted",
        "decisions": decisions,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Skill Candidate Policy Decision — 2026-05-25",
        "",
        "Third-party skills remain quarantine-only. No candidate is approved for production install by this report.",
        "",
        "| Candidate | Decision | Rough risk | Main reasons |",
        "|---|---:|---:|---|",
    ]
    for item in decisions:
        reasons = ", ".join(item["reasons"]) or "none"
        lines.append(f"| {item['name']} | `{item['decision']}` | `{item['risk_score_rough']}` | {reasons} |")
    lines.extend([
        "",
        "## Promotion rule",
        "",
        "Promotion requires a separate review against the source repository, exact commit SHA, license, manifest, install behavior, filesystem/network access, and rollback path.",
        "",
        "## Immediate use allowed",
        "",
        "Only use these repositories as read-only intelligence sources for discovering candidate names, categories, and ecosystem patterns. Do not install or execute them.",
    ])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"POLICY_JSON={OUT_JSON}")
    print(f"POLICY_MD={OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
