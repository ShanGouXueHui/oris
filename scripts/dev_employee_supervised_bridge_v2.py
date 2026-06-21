#!/usr/bin/env python3
"""Compatibility entrypoint for ORIS Dev Employee supervised bridge v2."""

from __future__ import annotations

from dev_employee_runtime.bridge_codex import final_check, invoke_codex, validate_codex_result
from dev_employee_runtime.bridge_context import claim_task, run, safe_path, select_python, strict_result_schema
from dev_employee_runtime.bridge_evidence import fail_task
from dev_employee_runtime.bridge_runner import main, run_once, run_task

__all__ = [
    "claim_task",
    "fail_task",
    "final_check",
    "invoke_codex",
    "main",
    "run",
    "run_once",
    "run_task",
    "safe_path",
    "select_python",
    "strict_result_schema",
    "validate_codex_result",
]


if __name__ == "__main__":
    raise SystemExit(main())
