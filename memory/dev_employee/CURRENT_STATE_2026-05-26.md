# ORIS Dev Employee Current State — 2026-05-26

## Executive status

ORIS Dev Employee has moved from smoke testing into a working autonomous development loop.

The current proven chain is:

```text
human goal and constraints
  -> autonomous enqueue helper
  -> local loopback enqueue API
  -> local queue descriptor
  -> systemd supervised bridge
  -> Codex CLI execution
  -> runtime task contract injection
  -> skill/capability resolver requirement
  -> strict autonomous result schema gate
  -> host-side final checks
  -> product GitHub push and remote SHA verification
  -> ORIS evidence commit and task status
```

## Core services on host

- ORIS repo: `/home/admin/projects/oris`
- Product acceptance repo: `/home/admin/projects/oris-final-acceptance-api`
- Enqueue API service: `oris-dev-employee-enqueue.service`
- Supervised bridge service: `oris-dev-employee-bridge.service`
- Enqueue API bind: `127.0.0.1:18891`
- Enqueue token: local only in `~/.config/oris/dev_employee_enqueue.env`; never paste or commit it.
- Codex CLI: `/home/admin/.npm-global/lib/node_modules/@openai/codex/bin/codex.js`
- GitHub CLI is authenticated as `ShanGouXueHui` on host.

## Important repositories

- Platform: `ShanGouXueHui/oris`
- Final acceptance product: `ShanGouXueHui/oris-final-acceptance-api`
- Product local path: `/home/admin/projects/oris-final-acceptance-api`

Do not put product code in `/home/admin/projects/oris`; ORIS is platform/orchestration/evidence only.

## Verified product state

`oris-final-acceptance-api` is a FastAPI + pytest + httpx in-memory task-board API.

Implemented and verified capabilities:

1. base task CRUD;
2. Pydantic v2 cleanup with no deprecation warnings;
3. `tags` support on create/update/list/detail responses;
4. `GET /tasks` optional filters by `status` and `assignee`.

Latest verified product commit before this handoff:

- `343600d47794d56c06bcf2735ac2355865484c19`

Latest verified test evidence before this handoff:

- `14 passed in 0.32s`
- `14 passed in 0.30s` with `-W error::DeprecationWarning`

## Verified ORIS evidence commits

Key milestones:

- `7c861d3f2db084a8ac9724e954d51d2d79a8667d`: HTTP enqueue smoke completed.
- `776b7bb90666e562dc5b3e15fa6a902ff1790d38`: runtime task contract injection completed.
- `f1161efa323cc764ca7ef2ac56da69640a6f06ee`: enqueue client smoke completed.
- `29a64168f916a691d1e505c6bcd8af8ce2f65bbc`: autonomous `tags` feature completed.
- `2205e03d1549a8e039a86ba82a004dc04dd407c2`: strict schema autonomous `GET /tasks` filters completed.

## Current ORIS capabilities

### Task intake

- `scripts/dev_employee_enqueue_server.py`: loopback HTTP enqueue/status API.
- `scripts/dev_employee_enqueue_client.py`: local API client wrapper.
- `scripts/dev_employee_autonomous_enqueue.py`: creates runtime prompt from goal/constraints and enqueues task.
- `scripts/dev_employee_task_status.py`: reads latest/queue/task status from local API.

### Execution

- `scripts/dev_employee_supervised_bridge_v2.py`: watches queue, invokes Codex, enforces runtime descriptor, validates result schema, runs final checks, commits/pushes product, verifies remote SHA, commits ORIS evidence.
- `scripts/dev_employee_result_validator.py`: validates autonomous result contract.
- `scripts/dev_employee_recover_stale_tasks.py`: stale task recovery helper.

### Skill/capability handling

- `scripts/dev_employee_skill_resolver.py`: maps task objective to ORIS-owned capabilities, flags risk keywords, optionally mirrors allowlisted intelligence repos into quarantine only.
- Quarantine location: `vendor/skill_candidates/`.
- Resolver reports: `logs/dev_employee/skill_resolution/<task_id>.json` and `.md`.

## Strict autonomous gate

For `strict_result_schema=true`, bridge must enforce:

1. Codex result JSON passes schema validation.
2. `logs/dev_employee/skill_resolution/<task_id>.json` exists.
3. Codex result `skill_resolution` exactly matches resolver report `skill_resolution`.
4. If invalid, task fails before host checks/Git operations with `blocked_result_schema_invalid` or `blocked_skill_resolution_invalid`.

## Current next test

A test plan has been committed but not yet confirmed as executed in this chat:

- `docs/SKILL_RESOLVER_ENFORCEMENT_TEST_PLAN_2026-05-26.md`
- Commit: `e5b4e328d4c9432f6d160180bd49a6b09a1b6de4`

Planned task:

- `autonomous-api-stats-skill-resolution-20260526`
- Goal: add `GET /stats` returning `total_tasks` and counts by status.
- This should verify that skill resolver evidence is enforced and included in final ORIS evidence.

## Operating rule

For future work, do not ask the human for routine engineering decisions. The human gives goals and constraints; ORIS decides design, capabilities, files, tests, retries, and evidence, stopping only at explicit safety/compliance/secret/paid-resource/destructive boundaries.
