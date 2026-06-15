#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ORIS = Path("/home/admin/projects/oris")
BRIDGE = ORIS / "scripts/dev_employee_supervised_bridge_v2.py"
INTAKE = ORIS / "scripts/dev_employee_intake_api.py"
QUEUE = ORIS / "orchestration/dev_employee_queue"

REPLACEMENTS = {
    BRIDGE: [
        (
            '    claimed = path.with_suffix(".running.json")\n',
            '    claimed = QUEUE_DIR / f"{task[\'task_id\']}.running.json"\n',
            "canonical_running_path",
        ),
        (
            '    failed_path = task_path.with_suffix(".failed.json")\n',
            '    failed_path = QUEUE_DIR / f"{task[\'task_id\']}.failed.json"\n',
            "canonical_failed_path",
        ),
        (
            '        done_path = task_path.with_suffix(".done.json")\n',
            '        done_path = QUEUE_DIR / f"{task_id}.done.json"\n',
            "canonical_done_path",
        ),
    ],
    INTAKE: [
        (
            '''    queue = []
    for suffix in ["queued", "running", "done", "failed"]:
        path = QUEUE_DIR / f"{task_id}.{suffix}.json"
        if path.exists():
            queue.append({"suffix": suffix, "path": str(path), "data": read_json(path)})
''',
            '''    queue = []
    seen_queue_paths: set[Path] = set()
    for suffix in ["queued", "running", "done", "failed"]:
        candidates = [QUEUE_DIR / f"{task_id}.{suffix}.json"]
        candidates.extend(sorted(QUEUE_DIR.glob(f"{task_id}*.{suffix}.json")))
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen_queue_paths or not path.exists():
                continue
            seen_queue_paths.add(resolved)
            queue.append({"suffix": suffix, "path": str(path), "data": read_json(path)})
''',
            "legacy_queue_discovery",
        ),
    ],
}


def replace_once(path: Path, old: str, new: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return False
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}:{label}: expected one match, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def migrate_task(task_id: str) -> dict[str, str]:
    QUEUE.mkdir(parents=True, exist_ok=True)
    result: dict[str, str] = {}
    for suffix in ["running", "done", "failed"]:
        canonical = QUEUE / f"{task_id}.{suffix}.json"
        if canonical.exists():
            result[suffix] = f"canonical_exists:{canonical}"
            continue
        legacy = [
            path
            for path in sorted(QUEUE.glob(f"{task_id}*.{suffix}.json"))
            if path != canonical
        ]
        if not legacy:
            result[suffix] = "not_found"
            continue
        if len(legacy) > 1:
            raise RuntimeError(f"multiple legacy {suffix} files for {task_id}: {legacy}")
        legacy[0].rename(canonical)
        result[suffix] = f"migrated:{legacy[0]}->{canonical}"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()

    changed: list[str] = []
    for path, replacements in REPLACEMENTS.items():
        for old, new, label in replacements:
            if replace_once(path, old, new, label):
                changed.append(f"{path.name}:{label}")

    migration = migrate_task(args.task_id)
    print(f"SOURCE_PATCHES={','.join(changed) if changed else 'already'}")
    for suffix, value in migration.items():
        print(f"MIGRATION_{suffix.upper()}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
