# Strict Autonomous Schema Test Plan — 2026-05-26

## Purpose

Validate that ORIS Dev Employee can complete a real product change under strict autonomous result schema enforcement.

The bridge now blocks autonomous tasks if Codex returns an incomplete result JSON when `strict_result_schema=true`.

## Test target

Product repository:

`ShanGouXueHui/oris-final-acceptance-api`

Product path:

`/home/admin/projects/oris-final-acceptance-api`

## Task

Add optional filters to the in-memory task-board API list endpoint.

Current endpoint:

```text
GET /tasks
```

Required behavior:

- keep existing `GET /tasks` behavior unchanged when no query params are provided;
- support optional `status` query param using existing task status enum values;
- support optional `assignee` query param;
- allow both filters together;
- return only matching tasks;
- preserve all existing endpoints and response models;
- add tests for status filter, assignee filter, and combined filters.

## Expected autonomous evidence

The Codex result JSON must include:

- `plan`
- `design_summary`
- `skill_resolution`
- `changed_files`
- `check_logs`
- `iteration_summary`
- `blockers`
- `notes`

The bridge should reject incomplete results with:

`blocked_result_schema_invalid`

## Enqueue command

```bash
cd /home/admin/projects/oris

git fetch origin main
git reset --hard origin/main

python3 scripts/dev_employee_autonomous_enqueue.py \
  --task-id autonomous-api-list-filters-20260526 \
  --objective "为 in-memory task-board API 的 GET /tasks 增加可选过滤能力：支持 status 查询参数，支持 assignee 查询参数，两个参数可以同时使用；没有参数时保持现有行为不变；补充必要测试，旧测试继续通过。" \
  --constraint "不要引入数据库，继续使用 in-memory 存储。" \
  --constraint "不要改变现有 endpoint 路径和现有响应结构。" \
  --constraint "由 ORIS 自主决定最小实现方案、测试覆盖点和修复步骤。" \
  --check "python3 -m py_compile app/main.py" \
  --check "PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q" \
  --check "PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q -W error::DeprecationWarning" \
  --product-path /home/admin/projects/oris-final-acceptance-api \
  --product-repo ShanGouXueHui/oris-final-acceptance-api \
  --commit-message "feat(api): add task list filters" \
  --note "Strict autonomous schema test: add task list filters"
```

## Verification

```bash
sleep 180

python3 scripts/dev_employee_task_status.py --task-id autonomous-api-list-filters-20260526
git log -1 --oneline
```

Then verify the ORIS evidence commit from GitHub.
