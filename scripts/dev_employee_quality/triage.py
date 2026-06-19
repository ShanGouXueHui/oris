from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GENERATED_NAME_PARTS = {
    "dev_employee_chat_sessions",
    "dev_employee_intake_catalog",
    "dev_employee_queue",
    "dev_employee_runs",
    "dev_employee_evidence",
    "dev_employee_approvals",
    "dev_employee_cancel_requests",
    "dev_employee_retry_requests",
    "dev_employee_status",
}
TIMESTAMPED_JSON = re.compile(r"(?:^|[-_])20\d{6,12}(?:[-_.]|$)")
SOURCE_SUFFIXES = {".py", ".sh", ".ts", ".tsx", ".js", ".mjs", ".cjs"}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml"}


def classify_path(path_value: str) -> str:
    path = Path(path_value)
    if any(part in GENERATED_NAME_PARTS for part in path.parts):
        return "generated_runtime_artifact"
    if path.suffix.lower() == ".json" and TIMESTAMPED_JSON.search(path.name):
        return "generated_runtime_artifact"
    if path.suffix.lower() in SOURCE_SUFFIXES:
        return "source_code"
    if path.suffix.lower() in CONFIG_SUFFIXES:
        return "configuration"
    return "other"


def top_items(counter: Counter[str], limit: int = 30) -> list[dict[str, Any]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def sanitize_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": finding.get("rule_id"),
        "path": finding.get("path"),
        "line": finding.get("line"),
        "message": finding.get("message"),
    }


def build_triage(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    rule_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    file_counts: Counter[str] = Counter()
    directory_counts: Counter[str] = Counter()
    rule_by_class: dict[str, Counter[str]] = defaultdict(Counter)
    actionable: list[dict[str, Any]] = []
    generated_count = 0

    seen: set[tuple[Any, ...]] = set()
    for raw in findings:
        if not isinstance(raw, dict):
            continue
        key = (raw.get("rule_id"), raw.get("path"), raw.get("line"), raw.get("message"), raw.get("value"))
        if key in seen:
            continue
        seen.add(key)
        path_value = str(raw.get("path") or "")
        rule = str(raw.get("rule_id") or "unknown")
        category = classify_path(path_value)
        rule_counts[rule] += 1
        class_counts[category] += 1
        file_counts[path_value] += 1
        directory_counts[str(Path(path_value).parent)] += 1
        rule_by_class[category][rule] += 1
        if category == "generated_runtime_artifact":
            generated_count += 1
            continue
        actionable.append(sanitize_finding(raw))

    actionable_by_rule: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in actionable:
        actionable_by_rule[str(item.get("rule_id"))].append(item)

    priority_order = {
        "duplicate_symbol": 0,
        "duplicate_json_key": 1,
        "python_syntax": 2,
        "json_syntax": 3,
        "forbidden_set_e": 4,
        "large_file": 5,
        "absolute_host_path": 6,
        "environment_loopback_port": 7,
        "public_oris_domain": 8,
        "embedded_commit_sha": 9,
        "embedded_commercial_task_id": 10,
        "acceptance_project_name": 11,
        "duplicate_constant": 12,
    }
    actionable.sort(key=lambda item: (
        priority_order.get(str(item.get("rule_id")), 99),
        str(item.get("path")),
        int(item.get("line") or 0),
    ))

    return {
        "schema_version": 1,
        "source_report": {
            "checked_at": report.get("checked_at"),
            "files_scanned": report.get("files_scanned"),
            "reported_findings": report.get("finding_count"),
        },
        "deduplicated_findings": len(seen),
        "generated_runtime_artifact_findings": generated_count,
        "actionable_engineering_findings": len(actionable),
        "counts_by_rule": dict(sorted(rule_counts.items())),
        "counts_by_class": dict(sorted(class_counts.items())),
        "counts_by_rule_and_class": {
            category: dict(sorted(counter.items()))
            for category, counter in sorted(rule_by_class.items())
        },
        "top_files": top_items(file_counts),
        "top_directories": top_items(directory_counts),
        "actionable_counts_by_rule": {
            rule: len(items) for rule, items in sorted(actionable_by_rule.items())
        },
        "actionable_sample": actionable[:300],
        "triage_policy": {
            "generated_runtime_artifacts_are_not_source_code": True,
            "no_source_files_modified": True,
            "full_actionable_list_truncated_to": 300,
        },
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: triage.py <input-report.json> <output-triage.json>", file=sys.stderr)
        return 64
    source = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    report = json.loads(source.read_text(encoding="utf-8"))
    triage = build_triage(report)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(triage, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
