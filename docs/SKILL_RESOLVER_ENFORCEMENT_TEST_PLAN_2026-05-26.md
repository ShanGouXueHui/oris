# Skill Resolver Enforcement Test Plan — 2026-05-26

## Purpose

Verify that strict autonomous tasks cannot pass unless Codex runs the ORIS skill resolver and copies its `skill_resolution` output into the final result JSON.

The bridge now enforces:

1. strict autonomous result schema;
2. existence of `logs/dev_employee/skill_resolution/<task_id>.json`;
3. exact match between resolver report `skill_resolution` and Codex result `skill_resolution`.

## Test product

- Repository: `ShanGouXueHui/oris-final-acceptance-api`
- Local path: `/home/admin/projects/oris-final-acceptance-api`

## Product task

Add a small non-breaking API capability:

- Add `GET /stats` endpoint.
- Return total number of tasks and counts by status.
- Keep all existing endpoints compatible.
- Add tests for empty board and mixed status counts.

## Skill/capability expectation

Because the objective mentions FastAPI, pytest, GitHub evidence, and OpenClaw skill policy, the resolver should select at least:

- `fastapi_pytest`
- `github_evidence`
- `skill_audit`

If quarantine is triggered, external repositories must only be mirrored into `vendor/skill_candidates/`; no third-party skill may be installed or executed.

## Enqueue command

```bash
cd /home/admin/projects/oris

git fetch origin main
git reset --hard origin/main

python3 scripts/dev_employee_autonomous_enqueue.py \
  --task-id autonomous-api-stats-skill-resolution-20260526 \
  --objective "为 in-memory task-board API 增加 GET /stats 端点，返回 total_tasks 以及按 status 分组的计数；保持现有 API 兼容；补充必要 pytest。任务开始前必须解析所需 FastAPI、pytest、GitHub evidence 与 OpenClaw skills/capability policy；如需要外部 skills，只能 quarantine audit，不能安装执行。" \
  --constraint "不要引入数据库，继续使用 in-memory 存储。" \
  --constraint "不要改变现有 endpoint 路径和现有响应结构。" \
  --constraint "由 ORIS 自主决定最小实现方案、测试覆盖点和修复步骤。" \
  --check "python3 -m py_compile app/main.py" \
  --check "PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q" \
  --check "PYTHONPATH=/home/admin/projects/oris-final-acceptance-api /home/admin/projects/oris-final-acceptance-api/.venv/bin/python -m pytest -q -W error::DeprecationWarning" \
  --product-path /home/admin/projects/oris-final-acceptance-api \
  --product-repo ShanGouXueHui/oris-final-acceptance-api \
  --commit-message "feat(api): add task stats endpoint" \
  --note "Strict autonomous task with enforced skill resolver evidence"
```

## Verify

```bash
sleep 240

python3 scripts/dev_employee_task_status.py --task-id autonomous-api-stats-skill-resolution-20260526
git log -1 --oneline
```

Expected success:

- `status=completed`
- product remote SHA equals product commit SHA
- host tests pass
- ORIS evidence contains `skill_resolver_report_json`
- ORIS evidence contains `autonomous_result.skill_resolution`
- resolver report exists under `logs/dev_employee/skill_resolution/`

Expected failure if Codex skips resolver:

- `status=blocked_skill_resolution_invalid`
