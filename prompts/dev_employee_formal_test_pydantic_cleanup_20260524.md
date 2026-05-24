# ORIS Formal Test Prompt — Pydantic v2 Cleanup

You are ORIS / OpenClaw / Codex-backed AI Dev Employee. This is a formal autonomous execution test after final acceptance.

## Required context first

Before coding, read durable GitHub/local context from the ORIS repo:

1. `docs/DEV_EMPLOYEE_AUTONOMOUS_EXECUTION_POLICY.md`
2. `docs/DEV_EMPLOYEE_FINAL_ACCEPTANCE_RETROSPECTIVE_2026-05-24.md`
3. `orchestration/project_registry.json`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`

Do not redesign ORIS. Continue from current policy and architecture.

## Test objective

Perform a small real maintenance task on the accepted product repo:

- Product repo: `ShanGouXueHui/oris-final-acceptance-api`
- Product local path: `/home/admin/projects/oris-final-acceptance-api`
- ORIS repo local path: `/home/admin/projects/oris`

Task: remove Pydantic v2 deprecation warnings from the product API without changing public API behavior.

Expected product changes:

- Replace class-based Pydantic config with `ConfigDict`.
- Replace `.dict()` calls with `.model_dump()`.
- Preserve all existing endpoints and tests.
- Do not add a database or new architecture.

## Hard boundaries

- Product code must stay in `/home/admin/projects/oris-final-acceptance-api`.
- Do not write product code into `/home/admin/projects/oris`.
- ORIS changes are limited to logs/state/evidence.
- Do not commit `.env`, secrets, private keys, `.venv`, caches, pyc files, pytest cache, or runtime noise.
- Do not use pseudo exec/write output. Use real filesystem, commands, Git commits, and GitHub remote verification.
- Use only `main` as the mainstream branch.
- Do not print long logs in chat. Commit logs to GitHub and return commit/file refs.

## Required checks

From `/home/admin/projects/oris-final-acceptance-api`, run:

```bash
python3 -m py_compile app/main.py
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api python -m pytest -q
PYTHONPATH=/home/admin/projects/oris-final-acceptance-api python -m pytest -q -W error::DeprecationWarning
```

The third command is the stricter formal-test gate. It must pass.

Write exact outputs to ORIS logs:

- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_py_compile_20260524.txt`
- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_pytest_20260524.txt`
- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_pytest_werror_20260524.txt`
- `/home/admin/projects/oris/logs/dev_employee/formal_test_pydantic_git_20260524.txt`

## Git / GitHub requirements

1. Commit and push product repo changes to `main`.
2. Update ORIS durable evidence after product tests pass.
3. Commit and push ORIS evidence/log updates to `main`.
4. Verify both commits from GitHub remote, not only local terminal output.

Suggested ORIS evidence files:

- `logs/dev_employee/latest_task_progress.json`
- `logs/dev_employee/latest_task_progress.md`
- `orchestration/task_runs/formal-test-pydantic-cleanup-20260524.json`

## Final response requirements

Return only a concise completion summary with:

- Product commit SHA.
- ORIS evidence commit SHA.
- Changed files in product repo.
- Changed files in ORIS repo.
- Exact outputs of the three checks.
- GitHub remote verification result.
- Known dirty files intentionally left uncommitted.
- Confirmation that no product code was written into `/home/admin/projects/oris`.

If blocked, do not fake completion. Record blocker in ORIS logs/state and return exact blocker evidence.
