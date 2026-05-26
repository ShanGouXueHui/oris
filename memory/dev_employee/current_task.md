# Current AI Dev Employee Task

Status: in progress

Task id: `oris-dev-employee-autonomous-loop-20260526`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Current objective

Build ORIS into an autonomous AI development employee.

Human gives goals and constraints. ORIS should autonomously decide design, capabilities, skills, implementation, tests, ordinary repair loops, failure diagnosis, repair planning, repair execution, and GitHub evidence. Human should not decide routine engineering steps.

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

## Last verified product state

Product repository: `ShanGouXueHui/oris-final-acceptance-api`

Product local path: `/home/admin/projects/oris-final-acceptance-api`

Last verified product commit SHA: `58fb03fe2020f6d044e837a4626ff050fe90d2d9`

Last verified ORIS evidence SHA for real repair task: `5b6710bd1390e0b96c8a2dc64be24bb5f748d86f`

Latest verified product checks:

- targeted `/healthz` test: `1 passed in 0.25s`
- full pytest: `17 passed in 0.30s`
- full pytest with `-W error::DeprecationWarning`: `17 passed in 0.31s`

## Current platform evidence state

Key recent platform commits:

- `f0e6f17688fb57db110307e434d82006bb6eb10f`: failure evidence persistence plan.
- `ab779dbd865231a6067e19f019033e3e2da8dce6`: bridge failure evidence persistence implementation.
- `404d44ecad8150709089263e2e6c763e02fc5e30`: `bridge_exception` failure evidence verified.
- `fe58abe15fb55158f8bb5a717411dcf9dd29a7ab`: `blocked_skill_resolution_invalid` failure evidence verified.
- `8c079bab5abfc5914a5dbd7f14142cbb13738211`: `blocked_host_checks_failed` failure evidence verified.
- `98a8eaab3a66a50fabf4f14dd13733823d3456d0`: failure triage helper added.
- `f2ebb8d`: bridge auto failure triage integration.
- `671daad1a4a9a5968f67dab02f088be94105f56d`: auto triage end-to-end verified.
- `88b336dccaff1ed698ed0b79b0cc7d448c40320b`: repair-from-triage helper added.
- `9d1096a66ea86c96a79b900b56798708c39259bf`: repair plan generated from triage.
- `af219e0`: repair target guard added.
- `95e23b0`: repair target guard validation passed.
- `a77d534`: real target repair plan guard positive path verified.
- `8d7be20`: real target repair enqueue positive path verified.
- `963f16d`: real product repair E2E precheck relaxed.
- `5b6710bd1390e0b96c8a2dc64be24bb5f748d86f`: real product repair ORIS evidence committed.
- `f8f98f8`: real product repair execution E2E report committed with `ok=true`.

## Next action

Harden/generalize the verified repair execution loop.

Requirements:

1. Promote `scripts/dev_employee_run_real_product_repair_e2e.py` from one-off healthz validation into a reusable acceptance harness.
2. Add post-run local tracked clean-state reporting after report commit/reset so future reports do not confuse transient report-file modifications with product failure.
3. Validate one additional routine product feature or repair task using the normal goal-driven enqueue path, not a synthetic failure seed.

## Operating rule

Do not ask the human for routine engineering decisions. Inspect GitHub evidence and decide the next smallest safe action. Stop only at explicit safety/compliance/secret/paid-resource/destructive boundaries.
