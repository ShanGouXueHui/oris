#!/usr/bin/env python3
"""Smoke test for Dev Employee handoff updater."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.handoff_updater import render_handoff, write_handoff


def main() -> int:
    sample_index = {
        "source_file": "logs/dev_employee/sample.summary.md",
        "timestamp_utc": "20260517T000000Z",
        "ok": True,
        "checks": [
            {"name": "compile", "returncode": 0, "result": "pass"},
            {"name": "smoke", "returncode": 0, "result": "pass"},
        ],
        "key_result": {
            "summary_file": "logs/dev_employee/sample.summary.md",
            "validation_file": "logs/dev_employee/sample.validation.txt",
        },
    }
    content = render_handoff(sample_index)
    output = Path("run/dev_employee/handoff_updater_smoke/HANDOFF.md")
    write_handoff(output, content)
    ok = "ORIS vNext Dev Employee Latest Handoff" in content and "compile" in content
    print(json.dumps({"ok": ok, "output": str(output)}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
