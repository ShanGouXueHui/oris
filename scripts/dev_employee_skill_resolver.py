#!/usr/bin/env python3
"""Resolve capabilities/skills for ORIS Dev Employee tasks.

This resolver is deliberately conservative. It prefers ORIS-owned scripts and
patterns. External repositories are treated as untrusted intelligence sources
and may only be mirrored into quarantine when explicitly requested.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
LOG_DIR = ORIS_DIR / "logs" / "dev_employee" / "skill_resolution"
QUARANTINE_DIR = ORIS_DIR / "vendor" / "skill_candidates"

INTERNAL_CAPABILITIES: dict[str, dict[str, Any]] = {
    "github_evidence": {
        "keywords": ["github", "commit", "push", "remote", "evidence", "sha", "repo"],
        "owned_assets": [
            "scripts/dev_employee_supervised_bridge_v2.py",
            "scripts/dev_employee_task_status.py",
            "docs/OPENCLAW_WEB_TO_DEV_EMPLOYEE_ENQUEUE_INTEGRATION_2026-05-26.md",
        ],
        "decision": "use_existing",
    },
    "fastapi_pytest": {
        "keywords": ["fastapi", "api", "endpoint", "pytest", "httpx", "pydantic", "tests"],
        "owned_assets": [
            "prompts/dev_employee_autonomous_development_task_template_20260526.md",
            "schemas/dev_employee_task_result.schema.json",
        ],
        "decision": "use_existing",
    },
    "safe_execution": {
        "keywords": ["execute", "codex", "cli", "shell", "test", "run", "bridge"],
        "owned_assets": [
            "scripts/dev_employee_supervised_bridge_v2.py",
            "scripts/dev_employee_recover_stale_tasks.py",
        ],
        "decision": "use_existing",
    },
    "skill_audit": {
        "keywords": ["skill", "skills", "openclaw", "clawhub", "mcp", "download", "quarantine", "audit"],
        "owned_assets": [
            "docs/SKILL_INTAKE_AND_REUSE_PLAN_2026-05-25.md",
            "docs/SKILL_INTERNALIZATION_SHORTLIST_2026-05-25.md",
        ],
        "decision": "use_existing_then_quarantine_if_needed",
    },
    "docs_reports": {
        "keywords": ["doc", "docs", "markdown", "report", "runbook", "summary"],
        "owned_assets": [
            "docs/RUNBOOKS/DEV_EMPLOYEE_BRIDGE_SERVICE.md",
            "docs/RUNBOOKS/DEV_EMPLOYEE_ENQUEUE_API.md",
        ],
        "decision": "use_existing",
    },
}

ALLOWLISTED_INTELLIGENCE_REPOS: dict[str, str] = {
    "awesome-openclaw-skills": "https://github.com/VoltAgent/awesome-openclaw-skills.git",
    "clawhub": "https://github.com/openclaw/clawhub.git",
    "awesome-mcp-servers": "https://github.com/punkpeye/awesome-mcp-servers.git",
}

RISK_KEYWORDS = [
    "credential",
    "password",
    "private key",
    "browser profile",
    "wallet",
    "crypto",
    "trading",
    "postinstall",
    "curl |",
    "wget |",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize(text: str) -> str:
    return text.lower()


def match_capabilities(objective: str) -> list[dict[str, Any]]:
    text = normalize(objective)
    matches: list[dict[str, Any]] = []
    for name, spec in INTERNAL_CAPABILITIES.items():
        hit_keywords = [kw for kw in spec["keywords"] if kw in text]
        if hit_keywords:
            matches.append(
                {
                    "name": name,
                    "decision": spec["decision"],
                    "hit_keywords": hit_keywords,
                    "owned_assets": spec["owned_assets"],
                }
            )
    if not matches:
        matches.append(
            {
                "name": "generic_autonomous_development",
                "decision": "use_existing",
                "hit_keywords": [],
                "owned_assets": [
                    "prompts/dev_employee_autonomous_development_task_template_20260526.md",
                    "scripts/dev_employee_supervised_bridge_v2.py",
                ],
            }
        )
    return matches


def risk_flags(objective: str) -> list[str]:
    text = normalize(objective)
    return [kw for kw in RISK_KEYWORDS if kw in text]


def mirror_repo(name: str, url: str) -> dict[str, Any]:
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    target = QUARANTINE_DIR / name
    if target.exists():
        proc = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
        return {
            "name": name,
            "url": url,
            "path": str(target),
            "already_present": True,
            "return_code": proc.returncode,
            "commit_sha": proc.stdout.strip() if proc.returncode == 0 else None,
            "stderr": proc.stderr,
        }
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(target)],
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    sha = None
    if proc.returncode == 0:
        rev = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
        sha = rev.stdout.strip() if rev.returncode == 0 else None
    return {
        "name": name,
        "url": url,
        "path": str(target),
        "already_present": False,
        "return_code": proc.returncode,
        "commit_sha": sha,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def resolve(objective: str, task_id: str, quarantine: bool) -> dict[str, Any]:
    capabilities = match_capabilities(objective)
    flags = risk_flags(objective)
    needed = [item["name"] for item in capabilities]
    used_existing = [asset for item in capabilities for asset in item["owned_assets"]]
    blocked = []
    if flags:
        blocked.append("Risk keywords require policy review before runtime execution: " + ", ".join(flags))

    quarantine_results = []
    should_quarantine = quarantine and any(item["name"] == "skill_audit" for item in capabilities) and not blocked
    if should_quarantine:
        for name, url in ALLOWLISTED_INTELLIGENCE_REPOS.items():
            try:
                quarantine_results.append(mirror_repo(name, url))
            except Exception as exc:
                quarantine_results.append({"name": name, "url": url, "error": repr(exc)})

    result = {
        "task_id": task_id,
        "resolved_at": now_iso(),
        "objective": objective,
        "skill_resolution": {
            "needed": needed,
            "used_existing": used_existing,
            "downloaded_quarantine": [item.get("path", item.get("name")) for item in quarantine_results],
            "blocked": blocked,
        },
        "capability_matches": capabilities,
        "quarantine_results": quarantine_results,
        "policy": {
            "third_party_runtime_install_allowed": False,
            "quarantine_only": True,
            "promote_by_internalization_only": True,
        },
    }
    return result


def write_reports(result: dict[str, Any]) -> dict[str, str]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    task_id = result["task_id"]
    json_path = LOG_DIR / f"{task_id}.json"
    md_path = LOG_DIR / f"{task_id}.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"# Skill Resolution — {task_id}",
        "",
        f"Resolved at: `{result['resolved_at']}`",
        "",
        "## Needed capabilities",
    ]
    for item in result["skill_resolution"]["needed"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Existing ORIS assets to use"])
    for item in result["skill_resolution"]["used_existing"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Quarantine mirrors"])
    for item in result["skill_resolution"]["downloaded_quarantine"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Blockers"])
    blockers = result["skill_resolution"]["blocked"]
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve ORIS task capabilities and safe skill policy")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--quarantine", action="store_true", help="mirror allowlisted intelligence repos into quarantine only")
    args = parser.parse_args()
    result = resolve(args.objective, args.task_id, args.quarantine)
    paths = write_reports(result)
    output = {"ok": True, "reports": paths, "result": result}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
