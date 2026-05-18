#!/usr/bin/env python3
"""Smoke test for Dev Employee commercial readiness evaluator."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.commercial_readiness import (
    build_readiness_report,
    write_readiness_json,
    write_readiness_markdown,
)


def main() -> int:
    report = build_readiness_report()
    json_out = Path("run/dev_employee/commercial_readiness_smoke/report.json")
    md_out = Path("run/dev_employee/commercial_readiness_smoke/report.md")
    write_readiness_json(json_out, report)
    write_readiness_markdown(md_out, report)
    payload = report.to_dict()
    ok = isinstance(payload.get("ok"), bool) and payload.get("status") in {"green", "red"}
    print(json.dumps({"ok": ok, "status": payload.get("status"), "report_ok": payload.get("ok"), "json_out": str(json_out)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
