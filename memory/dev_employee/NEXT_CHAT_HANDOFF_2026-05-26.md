# ORIS Dev Employee Next Chat Handoff — 2026-05-26

## Read this first in the next chat

Required GitHub context, in order:

1. `memory/dev_employee/CURRENT_STATE_2026-05-26.md`
2. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-05-26.md`
3. `docs/DEV_EMPLOYEE_AUTONOMOUS_DECISION_DOCTRINE_2026-05-26.md`
4. `docs/DEV_EMPLOYEE_AUTONOMOUS_CAPABILITY_TARGET_2026-05-26.md`
5. `docs/SKILL_RESOLVER_INTEGRATION_2026-05-26.md`
6. `docs/SKILL_RESOLVER_ENFORCEMENT_TEST_PLAN_2026-05-26.md`
7. `scripts/dev_employee_supervised_bridge_v2.py`
8. `scripts/dev_employee_autonomous_enqueue.py`
9. `scripts/dev_employee_skill_resolver.py`
10. `orchestration/project_registry.json`

## Current objective

Continue toward the target:

> ORIS acts as an autonomous AI development employee. Human provides goals and constraints; ORIS decides plan, capabilities, skills, implementation, tests, repair loops, and evidence. Routine engineering decisions should not require human prompts.

## Immediate next task

Run and verify the skill resolver enforcement test.

Task id:

`autonomous-api-stats-skill-resolution-20260526`

Goal:

Add `GET /stats` to `oris-final-acceptance-api`, returning `total_tasks` and counts by status, with tests.

Use the command in:

`docs/SKILL_RESOLVER_ENFORCEMENT_TEST_PLAN_2026-05-26.md`

After execution, read evidence from GitHub, not pasted long logs.

Expected success:

- ORIS evidence commit exists.
- Product commit SHA equals product remote SHA.
- pytest passes.
- strict result schema is true.
- ORIS evidence includes `skill_resolver_report_json` and `autonomous_result.skill_resolution`.
- `logs/dev_employee/skill_resolution/autonomous-api-stats-skill-resolution-20260526.json` exists and is committed.

Expected failure if Codex skips resolver:

- `blocked_skill_resolution_invalid`.

If failure occurs, do not ask user what to do. Inspect GitHub evidence/log files, update prompt/bridge/resolver as needed, and rerun with a new task id.

## Interaction rules

- Use Chinese.
- Be professional, direct, and structured.
- Prefer direct GitHub file updates through tools instead of printing long scripts or logs in chat.
- The user prefers reading evidence from GitHub. Do not ask them to paste long logs.
- If shell commands are needed for the user, keep them copy-paste ready and short.
- Do not use `set -e` in Linux command blocks.
- Only `main` is the long-lived branch.
- Do not commit `.env`, credentials, private keys, `.venv`, caches, queue runtime JSON, or runtime noise.
- Product code must not be written into `/home/admin/projects/oris`.

## Current services

On host:

- `oris-dev-employee-enqueue.service` should be active.
- `oris-dev-employee-bridge.service` should be active.
- Enqueue API: `127.0.0.1:18891`.
- Token local file: `~/.config/oris/dev_employee_enqueue.env`.

Check if needed:

```bash
systemctl --user status oris-dev-employee-enqueue.service --no-pager
systemctl --user status oris-dev-employee-bridge.service --no-pager
```

## Current validated architecture

```text
human objective
  -> scripts/dev_employee_autonomous_enqueue.py
  -> generated runtime prompt under run/dev_employee_prompts/
  -> local enqueue API
  -> queue descriptor
  -> supervised bridge
  -> Codex CLI
  -> runtime contract injection
  -> skill resolver before coding
  -> strict result schema validation
  -> skill resolver evidence validation
  -> host final checks
  -> product commit/push/remote verification
  -> ORIS evidence commit
```

## Important implementation notes

- `dev_employee_autonomous_enqueue.py` annotates local queued descriptors with `strict_result_schema=true`, `autonomy_mode=goal_driven`, `task_objective`, `constraints`, and `expected_checks`.
- `dev_employee_supervised_bridge_v2.py` validates result schema and skill resolver evidence before host checks.
- `dev_employee_skill_resolver.py` prefers ORIS-owned capabilities and only quarantines allowlisted external intelligence repos when requested.
- Third-party skills must not be installed or executed in runtime. Use quarantine/audit/internalization only.

## Do not regress

Do not return to pseudo-exec behavior. Completion requires GitHub-verifiable evidence:

- product SHA;
- product remote SHA;
- ORIS evidence SHA;
- task run JSON;
- check logs;
- skill resolution report for strict autonomous tasks.
