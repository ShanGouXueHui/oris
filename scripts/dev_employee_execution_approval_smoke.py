#!/usr/bin/env python3
"""Smoke test for Dev Employee execution approval contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.execution_approval import (
    evaluate_approval,
    load_approval,
    load_execution_packet,
    write_approval_result,
)


def main() -> int:
    approval = load_approval("config/dev_employee_execution_approval.json")
    packet = load_execution_packet("logs/dev_employee/latest_execution_packet.json")
    result = evaluate_approval(approval=approval, execution_packet=packet)
    out = Path("run/dev_employee/execution_approval_smoke/result.json")
    write_approval_result(out, result)
    ok = result.get("allowed") is False and result.get("enabled") is False
    print(json.dumps({"ok": ok, "allowed": result.get("allowed"), "enabled": result.get("enabled"), "out": str(out)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
