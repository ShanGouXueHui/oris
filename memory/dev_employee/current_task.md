# Current AI Dev Employee Task

Status: in progress

Task id: `oris-dev-employee-autonomous-loop-20260526`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Current objective

Build ORIS into an autonomous AI development employee.

Human gives goals and constraints. ORIS should autonomously decide design, capabilities, skills, implementation, tests, ordinary repair loops, failure diagnosis, repair planning, repair execution, acceptance validation, and GitHub evidence. Human should not decide routine engineering steps.

## Verified milestones

- Final acceptance product `oris-final-acceptance-api` created and verified.
- Loopback enqueue API verified.
- systemd supervised bridge verified.
- Codex CLI real execution verified.
- Runtime task contract injection verified.
- Enqueue client verified.
- Goal-driven autonomous `tags` feature completed.
- Strict-schema autonomous `GET /tasks` filters feature completed.
- Autonomous decision doctrine committed.
- Skill resolver added.
- Autonomous prompt now requires skill resolver.
- Bridge enforces strict result schema.
- Bridge enforces skill resolver evidence for strict tasks.
- `GET /stats` endpoint completed with strict schema and skill resolver evidence.
- Failure evidence persistence implemented and verified for `bridge_exception`, `blocked_skill_resolution_invalid`, and `blocked_host_checks_failed`.
- Failure triage helper added and verified.
- Bridge now automatically runs failure triage after failure evidence commit.
- Auto triage end-to-end verified.
- Triage-driven repair plan helper added.
- Repair plan generated from failure triage.
- Repair target path/repo mismatch guard added.
- Repair target guard validation passed: mismatch enqueue rejected and no queue task created.
- Real target repair plan guard positive path verified.
- Real target repair enqueue positive path verified.
- Real product repair E2E precheck relaxed to allow old untracked ORIS runtime noise while keeping product precheck strict.
- Real product repair execution E2E verified: ORIS repaired the real product by adding `GET /healthz` and committed product + ORIS evidence.
- Reusable acceptance harness added at `scripts/dev_employee_acceptance_harness.py`.
- `api_info` normal goal-driven acceptance verified.
- `version` normal goal-driven acceptance verified.
- Bridge post-commit clean fix added at `930cc89`.
- `readyz` normal goal-driven clean-state acceptance verified: final ORIS tracked status remained clean.

## Last verified product state

Product repository: `ShanGouXueHui/oris-final-acceptance-api`

Product local path: `/home/admin/projects/oris-final-acceptance-api`

Last verified product commit SHA: `714dc53b239ad9ab2d7f408cef40b5c594e47181`

Latest verified product capability: `GET /readyz -> {"ready": true}`

Latest verified checks:

- targeted `/readyz` check: passed
- full pytest: `20 passed in 0.30s`
- full pytest with `-W error::DeprecationWarning`: `20 passed in 0.31s`

Latest verified acceptance report:

- `logs/dev_employee/acceptance_harness/readyz-goal-driven-clean-check-20260529-r1.json`
- report commit: `bf85937b75c809a090752fce6c6cabde9f0bccb5`
- `final_product_status`: empty
- `final_oris_tracked_status`: empty

## Current platform evidence state

Key recent platform commits:

- `5b6710bd1390e0b96c8a2dc64be24bb5f748d86f`: real product repair ORIS evidence committed.
- `f8f98f8`: real product repair execution E2E report committed with `ok=true`.
- `cdadb9a`: reusable acceptance harness added.
- `b5af5aa`: healthz repair-seed scenario added.
- `a5a70c3`: API info goal-driven scenario added.
- `9dfd847c5b5ac774bb24311f441b9b712d8c78a8`: API info goal-driven acceptance report committed with `ok=true`.
- `d5beb709fee01b089f52d50bb80809eef295d085`: version goal-driven acceptance report committed with `ok=true`; it still observed dirty tracked task-run evidence because bridge process was not restarted yet.
- `930cc89`: bridge fixed to avoid rewriting committed task-run evidence JSON after ORIS evidence commit.
- `1359c7a02489a2422e864ccdc1cdb848ee758994`: readyz clean-state scenario added.
- `bf85937b75c809a090752fce6c6cabde9f0bccb5`: readyz acceptance report committed with `ok=true` and clean ORIS tracked state.

## Next action

Productize the AI development employee intake and status interface.

Requirements:

1. Add a thin OpenClaw/Web-to-Dev-Employee intake contract around the goal-driven enqueue path.
2. Define a small persistent task catalog/status API for non-shell users to submit goals and inspect GitHub evidence.
3. Keep GitHub as the source of truth for evidence; do not ask humans to paste logs.
4. Keep the acceptance harness as the regression suite for platform changes.

## Operating rule

Do not ask the human for routine engineering decisions. Inspect GitHub evidence and decide the next smallest safe action. Stop only at explicit safety/compliance/secret/paid-resource/destructive boundaries.
