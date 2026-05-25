#!/usr/bin/env python3
"""Recover stale ORIS Dev Employee queue tasks.

Moves old `*.running.json` task descriptors back to `*.queued.json` or to
`*.failed.json` depending on age and whether a matching task run has completed.
This script does not execute Codex or mutate product repos.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
RUN_DIR = ORIS_DIR / "orchestration" / "task_runs"
LOG_DIR = ORIS_DIR / "logs" / "dev_employee"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recover(max_age_minutes: int, fail_completed_running: bool) -> dict[str, Any]:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = now() - timedelta(minutes=max_age_minutes)
    summary: dict[str, Any] = {
        "checked_at": now().isoformat(timespec="seconds"),
        "max_age_minutes": max_age_minutes,
        "recovered": [],
        "failed": [],
        "skipped": [],
    }

    for path in sorted(QUEUE_DIR.glob("*.running.json")):
        try:
            task = read_json(path)
        except Exception as exc:
            summary["skipped"].append({"path": str(path), "reason": f"invalid_json:{exc!r}"})
            continue
        task_id = task.get("task_id") or path.name.replace(".running.json", "")
        claimed_at = parse_dt(task.get("claimed_at") or task.get("started_at"))
        run_path = RUN_DIR / f"{task_id}.json"
        run_status = None
        if run_path.exists():
            try:
                run_status = read_json(run_path).get("status")
            except Exception:
                run_status = None
        if run_status == "completed" and fail_completed_running:
            task["status"] = "failed_stale_descriptor_after_completed_run"
            task["recovered_at"] = now().isoformat(timespec="seconds")
            target = path.with_suffix(".failed.json")
            write_json(target, task)
            path.unlink(missing_ok=True)
            summary["failed"].append({"task_id": task_id, "from": str(path), "to": str(target), "reason": "run_already_completed"})
            continue
        if claimed_at is None or claimed_at > cutoff:
            summary["skipped"].append({"task_id": task_id, "path": str(path), "reason": "not_stale_or_missing_time"})
            continue
        task["status"] = "queued"
        task["requeued_at"] = now().isoformat(timespec="seconds")
        task["requeue_reason"] = "stale_running_task_recovered"
        target = path.with_name(path.name.replace(".running.json", ".queued.json"))
        write_json(target, task)
        path.unlink(missing_ok=True)
        summary["recovered"].append({"task_id": task_id, "from": str(path), "to": str(target)})

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover stale ORIS Dev Employee running queue tasks")
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument("--fail-completed-running", action="store_true")
    args = parser.parse_args()
    summary = recover(args.max_age_minutes, args.fail_completed_running)
    out = LOG_DIR / "stale_task_recovery_latest.json"
    write_json(out, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
