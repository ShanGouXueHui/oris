# ORIS Dev Employee Next Chat Handoff — 2026-05-26

## Read this first in the next chat

Required GitHub context, in order:

1. `memory/dev_employee/CURRENT_STATE_2026-05-26.md`
2. `memory/dev_employee/NEXT_CHAT_HANDOFF_2026-05-26.md`
3. `memory/dev_employee/current_task.json`
4. `memory/dev_employee/current_task.md`
5. `docs/DEV_EMPLOYEE_AUTONOMOUS_DECISION_DOCTRINE_2026-05-26.md`
6. `docs/DEV_EMPLOYEE_AUTONOMOUS_CAPABILITY_TARGET_2026-05-26.md`
7. `docs/SKILL_RESOLVER_INTEGRATION_2026-05-26.md`
8. `docs/DEV_EMPLOYEE_FAILURE_EVIDENCE_PLAN_2026-05-26.md`
9. `scripts/dev_employee_supervised_bridge_v2.py`
10. `scripts/dev_employee_autonomous_enqueue.py`
11. `scripts/dev_employee_skill_resolver.py`
12. `scripts/dev_employee_failure_triage.py`
13. `scripts/dev_employee_repair_from_triage.py`
14. `scripts/dev_employee_acceptance_harness.py`
15. `orchestration/project_registry.json`

## Current objective

Continue toward the target:

> ORIS acts as an autonomous AI development employee. Human provides goals and constraints; ORIS decides plan, capabilities, skills, implementation, tests, repair loops, acceptance checks, and evidence. Routine engineering decisions should not require human prompts.

## Current validated architecture

```text
human objective
  -> scripts/dev_employee_autonomous_enqueue.py or acceptance harness
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
  -> ORIS success evidence commit
  -> optional scenario acceptance report commit
  -> ORIS tracked working tree remains clean after bridge commit
```

Failure/repair chain validated:

```text
failure occurs
  -> bridge commits failure_result.json/logs/resolver evidence
  -> bridge runs deterministic failure triage automatically
  -> triage commits JSON/Markdown report
  -> repair-from-triage generates a guarded repair plan
  -> target guard validates product_path/product_repo
  -> repair task is enqueued through loopback API
  -> bridge/Codex repairs real product code
  -> host checks pass
  -> product commit/push and ORIS evidence commit complete
```

## Most recent verified product capability

Task id:

`goal-readyz-endpoint-clean-check-20260529-r1`

Result:

- Status: `completed`
- Product commit and remote SHA: `714dc53b239ad9ab2d7f408cef40b5c594e47181`
- Product feature: `GET /readyz` returns `{"ready": true}`.
- Full pytest: `20 passed in 0.30s`
- Full pytest with `-W error::DeprecationWarning`: `20 passed in 0.31s`
- Acceptance harness report: `logs/dev_employee/acceptance_harness/readyz-goal-driven-clean-check-20260529-r1.json`
- Harness report commit: `bf85937b75c809a090752fce6c6cabde9f0bccb5`
- `final_oris_tracked_status`: empty string, proving bridge post-commit clean behavior after restart.

Earlier product milestones:

- `goal-api-info-endpoint-20260526-r1`
  - Product commit: `d2d577e3476320f3a35d88c0870e31befd032ecc`
  - ORIS evidence: `ad9463326dffc551fd4ecd720e060c9875a75402`
  - Acceptance report: `9dfd847c5b5ac774bb24311f441b9b712d8c78a8`
  - Feature: `GET /info`.
- `goal-version-endpoint-clean-check-20260526-r1`
  - Product commit: `044ac0f1dd6f13766338f17e31e067bed2a9b372`
  - ORIS evidence: `adf8ea0102a26831848b11aa7208135a2d84caea`
  - Acceptance report: `d5beb709fee01b089f52d50bb80809eef295d085`
  - Feature: `GET /version`.
  - Note: this run occurred before bridge service restart and still observed dirty tracked task-run evidence.
- `repair-real-product-healthz-20260526-r1`
  - ORIS evidence commit: `5b6710bd1390e0b96c8a2dc64be24bb5f748d86f`
  - Product commit and remote SHA: `58fb03fe2020f6d044e837a4626ff050fe90d2d9`
  - Product feature: `GET /healthz`.
- `autonomous-api-stats-skill-resolution-20260526`
  - ORIS evidence commit: `6a6d19e33b71da50fce06a1f5d4c382b12a7d7ad`
  - Product commit and remote SHA: `7853ab0a27e1266789af7c97d900db171176d228`
  - Product feature: `GET /stats`.

## Verified failure/evidence/repair milestones

- `404d44ecad8150709089263e2e6c763e02fc5e30`: controlled `bridge_exception` failure evidence committed.
- `fe58abe15fb55158f8bb5a717411dcf9dd29a7ab`: controlled `blocked_skill_resolution_invalid` failure evidence committed.
- `8c079bab5abfc5914a5dbd7f14142cbb13738211`: controlled `blocked_host_checks_failed` failure evidence committed.
- `c0815b2`: manual failure triage report committed.
- `f2ebb8d`: bridge patched to run failure triage automatically.
- `671daad1a4a9a5968f67dab02f088be94105f56d`: end-to-end auto triage verified.
- `88b336dccaff1ed698ed0b79b0cc7d448c40320b`: triage-driven repair helper added.
- `9d1096a66ea86c96a79b900b56798708c39259bf`: repair plan generated from triage.
- `af219e0`: repair target path/repo guard added.
- `95e23b0`: guard validation passed; mismatch enqueue rejected and no queue task created.
- `a77d534`: real target repair plan guard positive path verified.
- `8d7be20`: real target repair enqueue positive path verified while preventing bridge/Codex from consuming synthetic task.
- `963f16d`: real product repair E2E precheck relaxed to ignore old untracked ORIS runtime noise while keeping product precheck strict.
- `930cc89`: bridge fixed to avoid rewriting committed task-run evidence JSON after ORIS evidence commit.
- `bf85937`: readyz acceptance report proves clean ORIS tracked state after bridge restart.

## Acceptance harness state

Reusable harness:

- `scripts/dev_employee_acceptance_harness.py`

Scenario directory:

- `acceptance_scenarios/`

Verified scenarios:

- `healthz-repair-seed-20260526-r1`: dry-run repair_seed schema validation.
- `api-info-goal-driven-20260526-r1`: normal goal-driven full run, `ok=true`.
- `version-goal-driven-clean-check-20260526-r1`: normal goal-driven full run, `ok=true`, but before bridge restart.
- `readyz-goal-driven-clean-check-20260529-r1`: normal goal-driven full run, `ok=true`, clean ORIS tracked state.

## Current immediate next task

The core loop is proven across repair execution, normal goal-driven development, scenario-driven acceptance, and clean post-commit working-tree behavior. The next useful task is productizing the AI development employee interface:

1. Add a thin OpenClaw/Web-to-Dev-Employee intake contract around the goal-driven enqueue path.
2. Define a small persistent task catalog/status API for non-shell users to submit goals and inspect GitHub evidence.
3. Keep GitHub as source of truth for evidence; avoid asking humans to paste logs.
4. Keep acceptance harness as regression suite for new platform changes.

## Interaction rules

- Use Chinese.
- Be professional, direct, and structured.
- Prefer direct GitHub file updates through tools instead of printing long scripts or logs in chat.
- The user prefers reading evidence from GitHub. Do not ask them to paste long logs.
- If shell commands are needed for the user, keep them copy-paste ready and short.
- Do not use `set -e` in Linux command blocks.
- Only `main` is the long-lived branch.
- Do not commit `.env`, credentials, private keys, `.venv`, caches, queue runtime JSON, browser profiles, or runtime noise.
- Product code must not be written into `/home/admin/projects/oris`.

## Current services

On host:

- `oris-dev-employee-enqueue.service` should be active.
- `oris-dev-employee-bridge.service` should be active and should already be restarted after `930cc89`.
- Enqueue API: `127.0.0.1:18891`.
- Token local file: `~/.config/oris/dev_employee_enqueue.env`.

Check if needed:

```bash
systemctl --user status oris-dev-employee-enqueue.service --no-pager
systemctl --user status oris-dev-employee-bridge.service --no-pager
```

## Important implementation notes

- `dev_employee_autonomous_enqueue.py` annotates local queued descriptors with `strict_result_schema=true`, `autonomy_mode=goal_driven`, `task_objective`, `constraints`, and `expected_checks`.
- `dev_employee_supervised_bridge_v2.py` validates result schema and skill resolver evidence before host checks.
- `dev_employee_supervised_bridge_v2.py` commits failure evidence and automatically runs `dev_employee_failure_triage.py --commit`.
- Since `930cc89`, `dev_employee_supervised_bridge_v2.py` does not rewrite committed task-run evidence JSON after ORIS evidence commit.
- `dev_employee_failure_triage.py` writes JSON/Markdown triage reports under `logs/dev_employee/failure_triage/`.
- `dev_employee_repair_from_triage.py` writes repair plans under `logs/dev_employee/repair_plans/` and only enqueues when `--enqueue` is passed.
- `dev_employee_repair_from_triage.py` blocks enqueue by default if `product_path` basename does not match `product_repo` slug.
- `dev_employee_skill_resolver.py` prefers ORIS-owned capabilities and only quarantines allowlisted external intelligence repos when requested.
- Third-party skills must not be installed or executed in runtime. Use quarantine/audit/internalization only.

## Do not regress

Do not return to pseudo-exec behavior. Completion requires GitHub-verifiable evidence:

- product SHA;
- product remote SHA;
- ORIS evidence SHA;
- task run JSON;
- check logs;
- skill resolution report for strict autonomous tasks;
- failure evidence and triage report for failed tasks;
- repair plans must preserve original evidence references and enforce target guard before enqueue;
- repair execution must prove product remote SHA and ORIS evidence commit;
- acceptance harness reports must record final product status and ORIS tracked status.
