from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TARGET_PREFIXES = (
    "scripts/dev_employee_openclaw_enable/",
    "scripts/security/",
    "scripts/lib/insight_db",
    "skills/oris-readonly-status/",
)
TARGET_FILES = {
    "scripts/lib/secret_refs.py",
    "scripts/dev_employee_enable_openclaw_readonly_tools.sh",
    "scripts/dev_employee_rotate_insight_db_credential.sh",
    "scripts/dev_employee_remediate_and_enable_openclaw_readonly.sh",
    "config/insight_storage.json",
    "config/dev_employee/openclaw_readonly_acceptance.json",
    "config/dev_employee/repository_quality_policy.json",
}


def _is_target(path: str) -> bool:
    return path in TARGET_FILES or any(path.startswith(prefix) for prefix in TARGET_PREFIXES)


def evaluate(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    target_findings = [
        {
            "rule_id": item.get("rule_id"),
            "path": item.get("path"),
            "line": item.get("line"),
            "message": item.get("message"),
        }
        for item in findings
        if isinstance(item, dict) and _is_target(str(item.get("path") or ""))
    ]
    return {
        "result": "PASS" if not target_findings else "FAILED",
        "target_finding_count": len(target_findings),
        "target_findings": target_findings,
        "source_report_checked_at": report.get("checked_at"),
        "secret_values_recorded": False,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: target_gate.py <scan-report.json> <result.json>", file=sys.stderr)
        return 64
    report_path = Path(sys.argv[1]).resolve()
    result_path = Path(sys.argv[2]).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = evaluate(report)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
