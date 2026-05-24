# Codex Task Prompt — ORIS Final Acceptance API

Task id: `oris-final-acceptance-api-20260523`

You are executing as the real coding backend for ORIS AI Dev Employee. Do not simulate work. Use the real host filesystem, Git, GitHub CLI, Python, and pytest.

## Target

- Product repo: `ShanGouXueHui/oris-final-acceptance-api`
- Product local path: `/home/admin/projects/oris-final-acceptance-api`
- Stack: FastAPI + pytest + httpx
- Function: in-memory task-board API
- Main branch only: `main`

## Hard boundaries

- Do not write product code into `/home/admin/projects/oris`.
- Product implementation must live only in `/home/admin/projects/oris-final-acceptance-api`.
- ORIS repo changes are limited to durable logs/state and `orchestration/project_registry.json` after product tests pass.
- Do not commit `.env`, secrets, private keys, venvs, caches, pyc files, pytest cache, or runtime noise.
- Do not use `set -e` in generated shell commands or scripts.

## Product API requirements

Implement a small in-memory task-board API with FastAPI.

Minimum endpoints:

- `GET /health` returns service status.
- `GET /tasks` lists all tasks.
- `POST /tasks` creates a task.
- `GET /tasks/{task_id}` reads a task by id.
- `PATCH /tasks/{task_id}` partially updates title, description, status, or assignee.
- `DELETE /tasks/{task_id}` deletes a task and returns a deletion result.

Minimum task fields:

- `id`: integer, assigned by API.
- `title`: required non-empty string.
- `description`: optional string, default empty.
- `status`: enum-like string, default `todo`, allowed `todo`, `doing`, `done`.
- `assignee`: optional string.

Expected behavior:

- Unknown task id returns 404.
- Invalid status returns 422.
- Empty title on creation returns 422.
- In-memory storage is acceptable; no database.

## Required project files

Create or maintain at least:

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `requirements.txt`
- `app/main.py`
- `tests/test_tasks_api.py`

## Required checks

From `/home/admin/projects/oris-final-acceptance-api`, run and capture exact output:

```bash
python3 -m py_compile app/main.py
pytest -q
```

Write command outputs to files under the ORIS repo path:

- `/home/admin/projects/oris/logs/dev_employee/final_acceptance_py_compile_20260524.txt`
- `/home/admin/projects/oris/logs/dev_employee/final_acceptance_pytest_20260524.txt`
- `/home/admin/projects/oris/logs/dev_employee/final_acceptance_git_20260524.txt`

## GitHub and registry

If the product GitHub repo does not exist, create it as `ShanGouXueHui/oris-final-acceptance-api` using the authenticated GitHub CLI. Keep it public unless existing account policy says otherwise.

Commit and push the product repo on `main`.

After product tests pass and push succeeds, update `/home/admin/projects/oris/orchestration/project_registry.json` by adding project key `oris-final-acceptance-api` with:

- name: `ORIS Final Acceptance API`
- type: `test_project`
- repo: `git@github.com:ShanGouXueHui/oris-final-acceptance-api.git`
- github: `https://github.com/ShanGouXueHui/oris-final-acceptance-api`
- local_path: `/home/admin/projects/oris-final-acceptance-api`
- default_branch: `main`
- allowed_scope: `README.md`, `AGENTS.md`, `docs/`, `app/`, `tests/`, `requirements.txt`, `.gitignore`
- forbidden_scope: `.env`, `secrets`, `private_keys`, `production_credentials`
- notes: standalone final acceptance project for validating Codex-backed ORIS AI dev employee execution.

Also update ORIS durable task state files to completion only after product commit and registry commit exist:

- `memory/dev_employee/current_task.json`
- `memory/dev_employee/current_task.md`
- `logs/dev_employee/latest_task_progress.json`
- `logs/dev_employee/latest_task_progress.md`
- `orchestration/task_runs/oris-final-acceptance-api-20260523.json`

## Final response requirements

Return exact:

- Product repo URL.
- Product local path.
- Product commit SHA.
- ORIS registry commit SHA.
- Changed files in product repo.
- Changed files in ORIS repo.
- Exact `python3 -m py_compile app/main.py` output.
- Exact `pytest -q` output.
- Git push result.
- Known dirty files intentionally left uncommitted.
- Confirmation that no product code was written inside `/home/admin/projects/oris`.
