#!/usr/bin/env python3
"""Smoke test for ORIS vNext Dev Employee Phase 2 scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from oris_vnext.codex_executor import CodexExecutor, write_executor_result
from oris_vnext.task_kernel import DevTask, TaskKernel
from oris_vnext.validation import load_runtime_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Dev Employee scaffold smoke test.")
    parser.add_argument("--config", default="config/dev_employee_runtime.json")
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke external executors.")
    parser.add_argument("--output-dir", default="run/dev_employee/smoke")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    kernel = TaskKernel(args.config)
    task_run = kernel.create_dev_task_run(
        DevTask(
            request_summary="Dev Employee Phase 2 scaffold smoke",
            repo="ShanGouXueHui/oris",
            objective="Verify task kernel, worker registry, execution ledger, and CodexExecutor dry-run contract.",
            constraints=["no_secrets", "no_external_write", "dry_run"],
            source="smoke",
        )
    )

    prompt_path = output_dir / "codex_prompt.md"
    prompt_path.write_text(
        "# ORIS Dev Employee Dry Run\n\n"
        "Validate repository state, propose a minimal plan, and do not modify files.\n",
        encoding="utf-8",
    )

    runtime_config = load_runtime_config(args.config)
    executor = CodexExecutor(runtime_config)
    executor_result = executor.run(prompt_path, dry_run=True)
    write_executor_result(output_dir / "codex_executor_result.json", executor_result)

    result = {
        "ok": True,
        "task_run_id": task_run.task_run_id,
        "worker_profile": task_run.worker_profile,
        "model_role": task_run.model_role,
        "executor_plan": task_run.executor_plan,
        "codex_dry_run": executor_result.dry_run,
        "ledger_path": str(kernel.ledger.path),
    }
    (output_dir / "smoke_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
