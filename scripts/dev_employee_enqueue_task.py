#!/usr/bin/env python3
"""Create local ORIS Dev Employee queued task descriptors.

Queue JSON files are local runtime state and ignored by Git. This helper is the
safe handoff point for OpenClaw Web or a human operator: create a descriptor,
then the systemd bridge service will claim and execute it.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ORIS_DIR = Path("/home/admin/projects/oris")
PROJECTS_DIR = Path("/home/admin/projects")
QUEUE_DIR = ORIS_DIR / "orchestration" / "dev_employee_queue"
DEFAULT_CODEX = Path("/home/admin/.npm-global/bin/codex")

TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{2,120}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def safe_resolve(path_value: str, roots: list[Path], must_exist: bool = False) -> Path:
    path = Path(path_value).expanduser().resolve()
    resolved_roots = [root.resolve() for root in roots]
    if not any(path == root or root in path.parents for root in resolved_roots):
        raise SystemExit(f"ERROR: path outside allowed roots: {path}")
    if must_exist and not path.exists():
        raise SystemExit(f"ERROR: path does not exist: {path}")
    return path


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a local ORIS Dev Employee queued task descriptor")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--product-path", required=True)
    parser.add_argument("--product-repo", required=True)
    parser.add_argument("--commit-message", required=True)
    parser.add_argument("--workdir", default=str(PROJECTS_DIR))
    parser.add_argument("--codex-bin", default=str(DEFAULT_CODEX))
    parser.add_argument("--sandbox", default="workspace-write")
    parser.add_argument("--note", default="Queued by dev_employee_enqueue_task.py")
    args = parser.parse_args()

    if not TASK_ID_RE.match(args.task_id):
        raise SystemExit("ERROR: invalid task id; use 3-120 chars: letters, digits, dot, underscore, dash")

    prompt_path = safe_resolve(args.prompt_path, [ORIS_DIR, PROJECTS_DIR], must_exist=True)
    product_path = safe_resolve(args.product_path, [PROJECTS_DIR], must_exist=True)
    workdir = safe_resolve(args.workdir, [PROJECTS_DIR], must_exist=True)
    codex_bin = safe_resolve(args.codex_bin, [Path("/home/admin")], must_exist=True)

    target = QUEUE_DIR / f"{args.task_id}.queued.json"
    for suffix in ["queued", "running", "done", "failed"]:
        existing = QUEUE_DIR / f"{args.task_id}.{suffix}.json"
        if existing.exists():
            raise SystemExit(f"ERROR: task descriptor already exists: {existing}")

    descriptor = {
        "task_id": args.task_id,
        "status": "queued",
        "created_at": now_iso(),
        "prompt_path": str(prompt_path),
        "workdir": str(workdir),
        "codex_bin": str(codex_bin),
        "sandbox": args.sandbox,
        "extra_write_dirs": [str(ORIS_DIR)],
        "expected_product_repo": args.product_repo,
        "expected_product_path": str(product_path),
        "product_commit_message": args.commit_message,
        "notes": args.note,
    }
    write_json(target, descriptor)
    print(f"QUEUED_TASK={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
