# ORIS Dev Employee Commercialization Session Archive — 2026-06-17

This document preserves the decision-useful timeline from the long commercialization conversation. It is not a substitute for machine-readable task/evidence files. Current operational truth remains `CURRENT_STATE_2026-06-17.md` and `current_task.json`.

## 1. Starting condition

The conversation began with task:

`goal-oris-final-acceptance-api-20260616-031022`

Public Web submission, Console Token, allowlist, intake, queue and bridge claim had succeeded. Codex failed before product mutation because authentication refresh returned `refresh_token_reused`.

Failure evidence:

- failure evidence commit: `ea2089c5344c67e016601de8993ef365591daa06`
- diagnostic commit: `6fbc0ba1636ca01865b9565e68fdf6689ed6cae5`

## 2. Codex authentication and terminal-state repair

Completed:

- code hardening commit: `57cf6eccb1bbf7cc4e6ddd79eab94e7530d3fe5c`
- device-code login: passed
- admin non-interactive preflight: passed
- systemd bridge-context preflight: passed
- bridge auth context: passed
- evidence commit: `6397fa315d4172a92fbdcdc6d95e429f2dec2b53`

No real project task was submitted until authentication passed.

## 3. Full public commercial-chain acceptance

A new public task was submitted:

`goal-oris-final-acceptance-api-readonly-e2e-20260616-044030`

Initial verification script incorrectly reported failure because evidence readiness and local product verification logic were incomplete. After inspection and repair, final acceptance passed.

Final evidence:

- product commit/remote SHA: `3207f20a2afdf109beac9a4a95523e7792e0ae33`
- ORIS evidence commit: `188a17eeba4acb43f5b922560ad98c3d8d28c587`
- ORIS evidence index: `4425edbe8e29912ff44d41da2a5e458bdac292d3`
- independent final verification: `f1bb1cfcefbd7a3b5abb2a4f3bf6b4c00707605e`

Conclusion: the real public Web -> Codex -> product GitHub -> ORIS evidence chain works.

## 4. Queue and lifecycle commercial hardening

P1-A was implemented and accepted.

First run failed on platform regression tests:

- evidence commit: `5954932cd39a34e08224c541411b93d63805af0b`

Final server acceptance passed:

- evidence commit: `7540e90f54c0b397477c014305e6101d9513a647`

Capabilities accepted:

- transaction-safe filesystem queue;
- atomic claim and lock;
- canonical lifecycle states;
- lease and heartbeat;
- timeout;
- cancellation and rollback;
- explicit retry with new Task ID;
- worker concurrency slots;
- stale task policy without automatic duplicate execution;
- browser lifecycle controls.

## 5. Conversation-first custom shell experiment

The first browser-facing engineering console exposed forms/raw task detail and was rejected by the operator as not conversational.

The lifecycle test task was safely cancelled and product SHA remained unchanged:

- evidence commit: `9def6001a6488296b9ec79a08aa74a9741d24888`

Existing OpenClaw runtime discovery passed:

- evidence commit: `7e110e8c9ee24c37d53295e5faf59028e34aaa4f`

OpenClaw was not reinstalled.

A custom ORIS conversation shell was then developed using:

- OpenClaw as provider/inference backend;
- Agent Harness as policy/structured-output layer;
- ORIS as task control plane.

The custom shell initially failed an admin route contract and later passed application tests, but runtime stash restoration failed.

## 6. Runtime/Git boundary recovery

The custom shell deployment exposed historical tracked/untracked runtime-state problems.

Sequence:

- initial stash reconciliation failed because file count differed;
- read-only inspection found six files: five runtime files and one source file;
- three-way source merge attempts initially failed;
- source was eventually proven to match origin;
- runtime ignore boundary was corrected;
- historical stash was privately archived and safely dropped.

Final recovery evidence:

- evidence commit: `db38c220c41709da959c9e7add13888216d99ccb`
- private archive manifest: `5a6872aff7280634576a3a97329c40485cec99d25453fd27b70246cb553ebf15`

OpenClaw, bridge, intake and Web Console remained active. Product repository remained unchanged.

## 7. Public chat POST 403 repair

Browser chat loaded but message POST returned HTTP 403.

Diagnosis:

- direct Web Console POST passed;
- application CSRF/session logic was not the source;
- Nginx was blocking POST;
- the first attempted config patch modified a duplicate ignored server block;
- `nginx -T` showed four matching blocks and identified the effective file:
  `/etc/nginx/conf.d/oris-dev-employee-web-console.readonly.conf`;
- the effective config contained four location-level request-method guards.

The final structural patcher preserved all existing location guards and added only the exact chat POST route.

Final evidence:

- log commit: `6e992978146bd8686d450638753acad098d22fc0`

Verified:

- authenticated chat POST reaches the application;
- other public write routes remain blocked;
- product SHA/worktree unchanged;
- all services active.

## 8. Safe browser chat acceptance

The operator verified:

- `帮助` returned normal-language guidance;
- `查看进度` returned no current task;
- no HTTP 403;
- no task was created during the safe smoke.

Browser acceptance record:

- commit: `fed4fc9ad2e3aca30263b4fab6fdfc60527b0f58`

## 9. Intent-boundary defect and repair

A controlled product goal containing `接口状态码` was incorrectly interpreted as a status command because the custom deterministic router matched the substring `状态`.

The same message also contained `不要修改任何密钥`, which the original risk classifier could incorrectly treat as a request to operate on secrets.

The repair changed control intent to exact short-command matching and treated negative secret language as a safety constraint.

Testing was complicated by:

- system Python lacking pytest;
- unittest modules requiring `scripts/` in `PYTHONPATH`;
- tracked evidence logs being appended after commit;
- repeated log drift caused by nested resume scripts.

Final repair passed:

- code commit: `d7ba5754ff1295432b8771e908418c99719f42ee`
- evidence commit: `467ff998b6687d35d52c4afacbaddf09fb0f448a`

Verified:

- exact original message routes to create-task;
- `状态码` does not trigger status;
- polite exact control commands still work;
- negative secret constraint is not risky;
- unittest passes;
- Web Console restart/health passes;
- product repository unchanged.

## 10. Controlled `/capabilities` task

The operator submitted a real task through the custom shell:

`chat-oris-final-acceptance-api-20260617-051313-c802347ff17c`

The UI progressed from queued to executing to completed.

Product commit:

`927f1968cc86bfd5213670f4eaa171fc1a3be620`

The commit added:

- `GET /capabilities`;
- required response fields/features;
- pytest coverage.

Acceptance gap:

- the requested README API-list update was not included.

Lesson: canonical `completed` and a commit are insufficient; every requested deliverable must be checked independently.

## 11. Final product UX decision

The operator explicitly stated that the custom interface is inferior to the native OpenClaw/Harness experience because it lacks standard conversation lifecycle capabilities and requires special prompt rules.

Decision:

- stop developing the custom shell as the commercial primary UI;
- use existing native OpenClaw UI;
- keep Agent Harness as a backend policy/tool layer;
- integrate ORIS through stable tools/actions;
- move the custom shell to a restricted rollback/diagnostic route;
- do not reinstall or upgrade OpenClaw during migration.

Decision documents:

- `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_DECISION_2026-06-17.md`
- `docs/DEV_EMPLOYEE_NATIVE_OPENCLAW_UI_MIGRATION_PLAN_2026-06-17.md`

## 12. Current next action

Do not submit another product task.

First perform read-only discovery of:

- native OpenClaw UI and history/session behavior;
- HTTP/static/WebSocket paths;
- authentication and device pairing;
- effective Nginx load order and routes;
- service/task/product baseline.

Then prepare a reversible migration of the public root to OpenClaw, preserving `/admin`, intake privacy and a rollback route.
