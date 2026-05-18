#!/usr/bin/env python3
"""Export the latest Dev Employee commercial readiness report.

This script reads current Dev Employee cycle artifacts and writes JSON/Markdown
readiness reports under logs/dev_employee/. It does not run Codex and does not
perform git operations.
"""

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
    json_out = Path("logs/dev_employee/latest_commercial_readiness.json")
    md_out = Path("logs/dev_employee/latest_commercial_readiness.md")
    write_readiness_json(json_out, report)
    write_readiness_markdown(md_out, report)
    payload = report.to_dict()
    print(
        json.dumps(
            {
                "ok": True,
                "readiness_ok": payload.get("ok"),
                "status": payload.get("status"),
                "json_out": str(json_out),
                "md_out": str(md_out),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
