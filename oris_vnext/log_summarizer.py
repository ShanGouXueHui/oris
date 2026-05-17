"""GitHub log summarizer for ORIS Dev Employee cycles."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KEY_RESULT_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
CHECK_ROW_RE = re.compile(r"\| `([^`]+)` \|\s*(-?\d+)\s*\|\s*([^|]+?)\s*\|")
META_RE = re.compile(r"^- ([a-zA-Z0-9_]+):\s*(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class CycleCheckSummary:
    name: str
    returncode: int
    result: str


@dataclass(frozen=True)
class CycleLogSummary:
    source_file: str
    generated_at: str
    timestamp_utc: str | None
    ok: bool | None
    check_count: int
    checks: list[CycleCheckSummary]
    key_result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "generated_at": self.generated_at,
            "timestamp_utc": self.timestamp_utc,
            "ok": self.ok,
            "check_count": self.check_count,
            "checks": [asdict(check) for check in self.checks],
            "key_result": self.key_result,
            "metadata": self.metadata,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_key_result(text: str) -> dict[str, Any]:
    matches = KEY_RESULT_RE.findall(text)
    for raw in reversed(matches):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if "ok" in parsed and "timestamp_utc" in parsed:
            return parsed
    return {}


def parse_metadata(text: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in META_RE.finditer(text)}


def parse_checks(text: str) -> list[CycleCheckSummary]:
    checks: list[CycleCheckSummary] = []
    for name, returncode, result in CHECK_ROW_RE.findall(text):
        checks.append(CycleCheckSummary(name=name, returncode=int(returncode), result=result.strip()))
    return checks


def summarize_cycle_log(path: str | Path) -> CycleLogSummary:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    key_result = parse_key_result(text)
    checks = parse_checks(text)
    metadata = parse_metadata(text)
    ok_value = key_result.get("ok")
    ok = ok_value if isinstance(ok_value, bool) else None
    timestamp_utc = key_result.get("timestamp_utc") or metadata.get("timestamp_utc")
    return CycleLogSummary(
        source_file=str(source),
        generated_at=utc_now(),
        timestamp_utc=str(timestamp_utc) if timestamp_utc else None,
        ok=ok,
        check_count=len(checks),
        checks=checks,
        key_result=key_result,
        metadata=metadata,
    )


def write_summary_json(path: str | Path, summary: CycleLogSummary) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_summary_markdown(path: str | Path, summary: CycleLogSummary) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dev Employee Latest Cycle Index",
        "",
        f"- source_file: `{summary.source_file}`",
        f"- generated_at: `{summary.generated_at}`",
        f"- timestamp_utc: `{summary.timestamp_utc}`",
        f"- ok: `{summary.ok}`",
        f"- check_count: `{summary.check_count}`",
        "",
        "| Check | Return code | Result |",
        "| --- | ---: | --- |",
    ]
    for check in summary.checks:
        lines.append(f"| `{check.name}` | {check.returncode} | {check.result} |")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
