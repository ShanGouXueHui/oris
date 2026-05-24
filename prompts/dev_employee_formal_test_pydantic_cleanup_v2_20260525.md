# ORIS Formal Test Prompt v2 — Pydantic Cleanup Local Work Only

You are ORIS / OpenClaw / Codex-backed AI Dev Employee. This prompt is executed by the host supervised bridge v2.

## Required context first

Read these files from `/home/admin/projects/oris` before making changes:

1. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
2. `docs/DEV_EMPLOYEE_FINAL_ACCEPTANCE_RETROSPECTIVE_2026-05-24.md`
3. `docs/DEV_EMPLOYEE_SUPERVISED_BRIDGE_V2_2026-05-25.md`
4. `orchestration/project_registry.json`

## Task

Perform a small local maintenance task on:

- Product repo: `/home/admin/projects/oris-final-acceptance-api`
- ORIS repo: `/home/admin/projects/oris`
- Task id: `formal-test-pydantic-cleanup-v2-20260525`

Remove Pydantic v2 deprecation warnings from the product API without changing public API behavior.

Expected product changes:

- Replace class-based Pydantic config with `ConfigDict`.
- Replace `.dict()` calls with `.model_dump()`.
- Preserve all existing endpoints and tests.
- Do not add a database or new architecture.

## Boundaries

- Product code must stay in `/home/admin/projects/oris-final-acceptance-api`.
- Do not write product implementation into `/home/admin/projects/oris`.
- Do not perform GitHub push or remote verification. The outer bridge owns that.
- Do not commit secrets, `.env`, private keys, `.venv`, caches, pyc files, or pytest cache.
- Do not fake completion.

## Required local checks

From `/home/admin/projects/oris-final-acceptance-api`, run:

```bash
python3 -m py_compile app/main.py
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api python -m pytest -q
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api python -m pytest -q -W error::DeprecationWarning
```

Write exact outputs to:

- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_py_compile_20260525.txt`
- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_20260525.txt`
- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_werror_20260525.txt`

## Required structured result

After local checks pass, write:

`/home/admin/projects/oris/orchestration/task_runs/formal-test-pydantic-cleanup-v2-20260525.codex_result.json`

with JSON:

```json
{
  "task_id": "formal-test-pydantic-cleanup-v2-20260525",
  "status": "local_checks_passed",
  "product_path": "/home/admin/projects/oris-final-acceptance-api",
  "changed_files": ["app/main.py"],
  "check_logs": {
    "py_compile": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_py_compile_20260525.txt",
    "pytest": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_20260525.txt",
    "pytest_werror": "/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_v2_pytest_werror_20260525.txt"
  },
  "notes": "Local checks passed; outer supervised bridge must commit, push, verify remote, and update ORIS evidence."
}
```

If blocked, write the same path with `status=blocked` and exact error evidence.

## Final response

Return concise local result only. Do not claim final completion. The outer bridge will decide final completion.
