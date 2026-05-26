# Current AI Dev Employee Task

Status: in progress

Task id: `oris-dev-employee-autonomous-loop-20260526`

Target project: `oris`

Target repository: `ShanGouXueHui/oris`

Target local path: `/home/admin/projects/oris`

## Current objective

Build ORIS into an autonomous AI development employee.

Human gives goals and constraints. ORIS should autonomously decide design, capabilities, skills, implementation, tests, ordinary repair loops, failure diagnosis, repair planning, and GitHub evidence. Human should not decide routine engineering steps.

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

## Last verified product state

Product repository: `ShanGouXueHui/oris-final-acceptance-api`

Product local path: `/home/admin/projects/oris-final-acceptance-api`

Last verified product commit SHA: `7853ab0a27e1266789af7c97d900db171176d228`

Last verified ORIS evidence SHA for product task: `6a6d19e33b71da50fce06a1f5d4c382b12a7d7ad`

Latest verified product checks:

- `16 passed in 0.30s`
- `16 passed in 0.30s` with `-W error::DeprecationWarning`

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

## Next action

Verify positive repair enqueue behavior with a real product target pair.

Requirements:

1. Use a failure whose product target is actually `/home/admin/projects/oris-final-acceptance-api` and `ShanGouXueHui/oris-final-acceptance-api`, or pass both explicitly.
2. Run `scripts/dev_employee_repair_from_triage.py` and confirm generated `target_guard.enqueue_allowed=true`.
3. Only then use `--enqueue` to submit a repair task.
4. Verify the repair task uses a new task id, preserves original failure evidence, runs skill resolver, passes strict schema, and commits GitHub evidence.

Do not enqueue synthetic fixture failures into the real product repo unless explicitly running a controlled fixture test with `--allow-path-repo-mismatch`.

## Operating rule

Do not ask the human for routine engineering decisions. Inspect GitHub evidence and decide the next smallest safe action. Stop only at explicit safety/compliance/secret/paid-resource/destructive boundaries.
