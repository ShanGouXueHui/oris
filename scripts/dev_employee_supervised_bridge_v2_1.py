#!/usr/bin/env python3
"""ORIS Dev Employee supervised bridge v2.1.

This wrapper patches the v2 host-side final-check phase to use the product
virtualenv Python when available. It avoids relying on a bare `python` binary
that may not exist on Ubuntu hosts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import dev_employee_supervised_bridge_v2 as bridge


def select_python(product_path: Path) -> str:
    venv_python = product_path / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return "python3"


def final_check(product_path: Path, task_id: str) -> dict[str, Any]:
    python_bin = select_python(product_path)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(product_path)
    py_compile_log = bridge.LOG_DIR / f"{task_id}_host_py_compile.txt"
    pytest_log = bridge.LOG_DIR / f"{task_id}_host_pytest.txt"
    pytest_werror_log = bridge.LOG_DIR / f"{task_id}_host_pytest_werror.txt"
    checks = [
        ([python_bin, "-m", "py_compile", "app/main.py"], py_compile_log, env),
        ([python_bin, "-m", "pytest", "-q"], pytest_log, env),
        ([python_bin, "-m", "pytest", "-q", "-W", "error::DeprecationWarning"], pytest_werror_log, env),
    ]
    results = []
    for cmd, log_path, check_env in checks:
        proc = bridge.run(cmd, cwd=product_path, log_path=log_path, env=check_env)
        results.append({"cmd": " ".join(cmd), "return_code": proc.returncode, "log": str(log_path)})
    ok = all(item["return_code"] == 0 for item in results)
    return {"ok": ok, "python_bin": python_bin, "results": results}


bridge.final_check = final_check


if __name__ == "__main__":
    raise SystemExit(bridge.main())
