# ORIS Dev Employee Current State — 2026-05-26

## Executive status

ORIS Dev Employee has progressed from autonomous feature execution into a GitHub-evidence-backed autonomous development loop with failure evidence, failure triage, repair-plan generation, repair-target safety guards, and a verified real product repair execution E2E.

The current proven success chain is:

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
  -> skill resolver evidence gate
  -> host-side final checks
  -> product GitHub push and remote SHA verification
  -> ORIS success evidence commit
```

The current proven failure/repair chain is:

```text
failure occurs
  -> bridge writes failure_result.json and related logs
  -> bridge commits GitHub-verifiable failure evidence
  -> bridge automatically runs deterministic failure triage
  -> triage commits JSON/Markdown report
  -> repair-from-triage generates guarded repair plan
  -> target guard validates product_path/product_repo before enqueue
  -> repair task is enqueued through loopback API
  -> bridge/Codex performs repair
  -> host checks pass
  -> product commit/push and ORIS evidence commit complete
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
4. `GET /tasks` optional filters by `status` and `assignee`;
5. `GET /stats` returns `total_tasks` and status-grouped counts;
6. `GET /healthz` returns `{"status": "ok"}` and was added by the verified repair execution loop.

Latest verified product commit:

- `58fb03fe2020f6d044e837a4626ff050fe90d2d9`

Latest verified product checks for `repair-real-product-healthz-20260526-r1`:

- targeted health check: `1 passed in 0.25s`
- full pytest: `17 passed in 0.30s`
- full pytest with `-W error::DeprecationWarning`: `17 passed in 0.31s`

## Verified ORIS evidence commits

Key success milestones:

- `7c861d3f2db084a8ac9724e954d51d2d79a8667d`: HTTP enqueue smoke completed.
- `776b7bb90666e562dc5b3e15fa6a902ff1790d38`: runtime task contract injection completed.
- `f1161efa323cc764ca7ef2ac56da69640a6f06ee`: enqueue client smoke completed.
- `29a64168f916a691d1e505c6bcd8af8ce2f65bbc`: autonomous `tags` feature completed.
- `2205e03d1549a8e039a86ba82a004dc04dd407c2`: strict schema autonomous `GET /tasks` filters completed.
- `6a6d19e33b71da50fce06a1f5d4c382b12a7d7ad`: `GET /stats` completed with strict schema and skill resolver evidence.
- `5b6710bd1390e0b96c8a2dc64be24bb5f748d86f`: real product repair task `repair-real-product-healthz-20260526-r1` completed with product commit/remote verification and ORIS evidence.
- `f8f98f8`: real product repair execution E2E report committed with `ok=true`.

Key platform/negative-path milestones:

- `f0e6f17688fb57db110307e434d82006bb6eb10f`: failure evidence persistence plan documented.
- `ab779dbd865231a6067e19f019033e3e2da8dce6`: bridge persists failure evidence.
- `404d44ecad8150709089263e2e6c763e02fc5e30`: controlled `bridge_exception` failure evidence verified.
- `fe58abe15fb55158f8bb5a717411dcf9dd29a7ab`: controlled `blocked_skill_resolution_invalid` failure evidence verified.
- `8c079bab5abfc5914a5dbd7f14142cbb13738211`: controlled `blocked_host_checks_failed` failure evidence verified.
- `98a8eaab3a66a50fabf4f14dd13733823d3456d0`: failure triage helper added.
- `c0815b2`: manual triage report verified for host-check failure.
- `f2ebb8d`: bridge automatically runs failure triage.
- `671daad1a4a9a5968f67dab02f088be94105f56d`: auto triage end-to-end verified.
- `88b336dccaff1ed698ed0b79b0cc7d448c40320b`: repair-from-triage helper added.
- `9d1096a66ea86c96a79b900b56798708c39259bf`: repair plan generated from triage.
- `af219e0`: repair target path/repo mismatch guard added.
- `95e23b0`: repair target guard validation passed.
- `a77d534`: real target repair plan guard positive path verified.
- `8d7be20`: real target repair enqueue positive path verified while preventing bridge/Codex from consuming synthetic task.
- `963f16d`: real product repair E2E precheck relaxed to ignore old untracked ORIS runtime noise while keeping product precheck strict.

## Current ORIS capabilities

### Task intake

- `scripts/dev_employee_enqueue_server.py`: loopback HTTP enqueue/status API.
- `scripts/dev_employee_enqueue_client.py`: local API client wrapper.
- `scripts/dev_employee_autonomous_enqueue.py`: creates runtime prompt from goal/constraints and enqueues task.
- `scripts/dev_employee_task_status.py`: reads latest/queue/task status from local API.

### Execution

- `scripts/dev_employee_supervised_bridge_v2.py`: watches queue, invokes Codex, enforces runtime descriptor, validates result schema, validates skill resolver evidence, runs final checks, commits/pushes product, verifies remote SHA, commits ORIS evidence.
- The bridge also persists failure evidence and automatically runs failure triage.
- `scripts/dev_employee_result_validator.py`: validates autonomous result contract.
- `scripts/dev_employee_recover_stale_tasks.py`: stale task recovery helper.

### Skill/capability handling

- `scripts/dev_employee_skill_resolver.py`: maps task objective to ORIS-owned capabilities, flags risk keywords, optionally mirrors allowlisted intelligence repos into quarantine only.
- Quarantine location: `vendor/skill_candidates/`.
- Resolver reports: `logs/dev_employee/skill_resolution/<task_id>.json` and `.md`.

### Failure evidence and triage

- `scripts/dev_employee_failure_triage.py`: reads failure evidence and writes deterministic triage reports under `logs/dev_employee/failure_triage/`.
- Failure triage classifies at least: `blocked_skill_resolution_invalid`, `blocked_result_schema_invalid`, `blocked_host_checks_failed`, `codex_failed`, `bridge_exception`, product/ORIS Git push failures, and unknown failures.
- Triage reports include `root_cause`, `recommended_action`, `repair_scope`, `routine_autonomous_repair_allowed`, evidence paths, and next-step contract.

### Repair planning and repair execution

- `scripts/dev_employee_repair_from_triage.py`: reads failure evidence + triage and generates a repair contract under `logs/dev_employee/repair_plans/`.
- Default mode only writes a plan; `--enqueue` is required to submit a repair task.
- Product target guard checks that `product_path` basename matches `product_repo` slug before enqueue.
- Mismatches are blocked by default. `--allow-path-repo-mismatch` exists only for controlled fixture tests.
- Validation report: `logs/dev_employee/repair_guard_tests/repair-target-guard-20260526-r1.json`, with `ok=true`.
- Real product repair execution E2E report: `logs/dev_employee/repair_execution_tests/real-product-healthz-repair-e2e-20260526-r1.json`, with `ok=true`.

## Strict autonomous gate

For `strict_result_schema=true`, bridge must enforce:

1. Codex result JSON passes schema validation.
2. `logs/dev_employee/skill_resolution/<task_id>.json` exists.
3. Codex result `skill_resolution` exactly matches resolver report `skill_resolution`.
4. If invalid, task fails before host checks/Git operations with `blocked_result_schema_invalid` or `blocked_skill_resolution_invalid`.

This was verified by `failure-evidence-skill-resolution-invalid-20260526-r1`, which failed as expected with `blocked_skill_resolution_invalid`.

## Current next task

The core autonomous repair loop is now proven end-to-end on a real product repository. The next useful step is hardening/generalization rather than another one-off acceptance test:

- Promote the repair execution E2E runner from one-off validation into a reusable acceptance harness.
- Add a small post-run sanity helper that records local tracked clean state after report commit/reset so future reports do not confuse transient report-file modifications with product failure.
- Validate one additional routine feature/repair task using the normal goal-driven enqueue path, not a synthetic failure seed, to confirm the system behaves as an AI development employee under normal objectives.

## Operating rule

For future work, do not ask the human for routine engineering decisions. The human gives goals and constraints; ORIS decides design, capabilities, files, tests, retries, failure diagnosis, repair planning, repair execution, and evidence, stopping only at explicit safety/compliance/secret/paid-resource/destructive boundaries.
