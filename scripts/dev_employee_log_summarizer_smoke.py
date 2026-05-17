#!/usr/bin/env python3
"""Smoke test for Dev Employee cycle log summarizer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.log_summarizer import summarize_cycle_log, write_summary_json, write_summary_markdown


def main() -> int:
    sample_dir = Path("run/dev_employee/log_summarizer_smoke")
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample = sample_dir / "sample.summary.md"
    sample.write_text(
        "# Dev Employee Cycle Summary\n\n"
        "- timestamp_utc: 20260517T000000Z\n"
        "- branch: main\n\n"
        "## Validation report\n\n"
        "- ok: true\n"
        "- check_count: 2\n\n"
        "| Check | Return code | Result |\n"
        "| --- | ---: | --- |\n"
        "| `compile` | 0 | pass |\n"
        "| `smoke` | 0 | pass |\n\n"
        "## Key result\n\n"
        "```json\n"
        "{\"ok\":true,\"timestamp_utc\":\"20260517T000000Z\",\"compile_rc\":0,\"smoke_rc\":0,\"validation_rc\":0}\n"
        "```\n",
        encoding="utf-8",
    )
    summary = summarize_cycle_log(sample)
    write_summary_json(sample_dir / "latest.json", summary)
    write_summary_markdown(sample_dir / "latest.md", summary)
    payload = summary.to_dict()
    ok = payload["ok"] is True and payload["check_count"] == 2
    payload["smoke_ok"] = ok
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
