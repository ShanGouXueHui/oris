# ORIS Bridge Service HTTP Enqueue Smoke Prompt — 2026-05-25

You are ORIS / OpenClaw / Codex-backed AI Dev Employee. This task is executed by the host supervised bridge service after being queued through the local HTTP enqueue API.

## Required context first

Read these files from `/home/admin/projects/oris`:

1. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
2. `docs/DEV_EMPLOYEE_SUPERVISED_BRIDGE_V2_2026-05-25.md`
3. `docs/DEV_EMPLOYEE_SUPERVISED_BRIDGE_V2_1_RETROSPECTIVE_2026-05-25.md`
4. `orchestration/project_registry.json`

## Task

Perform a no-op service smoke verification on:

- Product repo: `/home/admin/projects/oris-final-acceptance-api`
- ORIS repo: `/home/admin/projects/oris`
- Task id: `bridge-service-smoke-http-20260525`

Do not change product behavior. Do not add architecture. If product code already satisfies the checks, leave it unchanged.

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
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q -W error::DeprecationWarning
```

Write exact outputs to:

- `/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_py_compile_20260525.txt`
- `/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_pytest_20260525.txt`
- `/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_pytest_werror_20260525.txt`

## Required structured result

After local checks pass, write exactly this file:

`/home/admin/projects/oris/orchestration/task_runs/bridge-service-smoke-http-20260525.codex_result.json`

with JSON:

```json
{
  "task_id": "bridge-service-smoke-http-20260525",
  "status": "local_checks_passed",
  "product_path": "/home/admin/projects/oris-final-acceptance-api",
  "changed_files": [],
  "check_logs": {
    "py_compile": "/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_py_compile_20260525.txt",
    "pytest": "/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_pytest_20260525.txt",
    "pytest_werror": "/home/admin/projects/oris/logs/dev_employee/bridge_service_smoke_http_pytest_werror_20260525.txt"
  },
  "notes": "Local HTTP enqueue smoke checks passed; outer supervised bridge must verify host checks, push if needed, verify remote, and update ORIS evidence."
}
```

If blocked, write the same path with `status=blocked` and exact error evidence.

## Final response

Return concise local result only. Do not claim final completion. The outer bridge will decide final completion.
