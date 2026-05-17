#!/usr/bin/env python3
"""Smoke test for Dev Employee append-only ledger events."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.ledger_events import append_event, build_state_event


def main() -> int:
    output_dir = Path("run/dev_employee/ledger_event_smoke")
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = output_dir / "events.jsonl"
    event = build_state_event(
        task_run_id="dev-smoke-ledger-event",
        previous_state="planned",
        state="validated",
        reason="smoke_validation_passed",
        metadata={"dry_run": True},
    )
    append_event(ledger_path, event)
    lines = ledger_path.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[-1])
    ok = payload.get("event_type") == "task_state_event" and payload.get("state") == "validated"
    result = {"ok": ok, "ledger_path": str(ledger_path), "event": payload}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
