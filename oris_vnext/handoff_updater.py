"""Handoff updater for ORIS Dev Employee vNext state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_latest_index(path: str | Path = "logs/dev_employee/latest_cycle_index.json") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, dict):
        raise ValueError("latest index must be a JSON object")
    return raw


def render_handoff(index: dict[str, Any]) -> str:
    checks = index.get("checks", [])
    check_lines = []
    for item in checks:
        if isinstance(item, dict):
            check_lines.append(
                f"| `{item.get('name')}` | {item.get('returncode')} | {item.get('result')} |"
            )

    key_result = index.get("key_result", {}) if isinstance(index.get("key_result"), dict) else {}
    source_file = index.get("source_file", "")
    generated_at = utc_now()
    ok = index.get("ok")
    timestamp_utc = index.get("timestamp_utc")

    lines = [
        "# ORIS vNext Dev Employee Latest Handoff",
        "",
        "This file is generated from the latest Dev Employee cycle index.",
        "It is intended as the first short entry point after the larger project handoff files.",
        "",
        "## Latest cycle",
        "",
        f"- generated_at: `{generated_at}`",
        f"- cycle_timestamp_utc: `{timestamp_utc}`",
        f"- ok: `{ok}`",
        f"- source_file: `{source_file}`",
        f"- summary_file: `{key_result.get('summary_file', '')}`",
        f"- validation_file: `{key_result.get('validation_file', '')}`",
        "",
        "## Validation checks",
        "",
        "| Check | Return code | Result |",
        "| --- | ---: | --- |",
        *check_lines,
        "",
        "## Current Dev Employee kernel capabilities",
        "",
        "- Task Kernel scaffold",
        "- Worker Registry / Dev Employee profile",
        "- DevTask schema",
        "- Execution Ledger JSONL contract",
        "- Bootstrap document reader",
        "- CodexExecutor dry-run and execution gate smoke",
        "- Validation markdown summary",
        "- Append-only ledger event helper",
        "- Latest GitHub cycle index",
        "",
        "## Next recommended implementation step",
        "",
        "Add a repo-aware planning packet builder that combines bootstrap doc status, task_run metadata, validation status, and current dirty-worktree policy into a single Dev Employee planning input.",
        "",
        "## Fixed constraints",
        "",
        "- OpenClaw remains the access/channel layer.",
        "- ORIS Native Task Kernel remains the Dev Employee orchestration layer.",
        "- Real Codex execution remains gated and disabled by default.",
        "- Stable rules live in config/.",
        "- Secrets remain env/secrets only.",
        "- No set -e in user-facing shell flows.",
        "- Provider orchestration is reused, not rewritten.",
        "",
    ]
    return "\n".join(lines)


def write_handoff(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
