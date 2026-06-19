# Next Chat Handoff — 2026-06-19

## Mandatory first read

Read these GitHub files in order before changing design or code:

1. `memory/dev_employee/CONTEXT_INDEX.md`
2. `memory/dev_employee/CURRENT_STATE_2026-06-19.md`
3. `memory/dev_employee/SESSION_ARCHIVE_2026-06-19.md`
4. `memory/dev_employee/current_task.json`
5. `memory/dev_employee/current_task.md`
6. `docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`
7. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
8. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
9. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
10. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
11. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
12. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
13. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
14. `orchestration/project_registry.json`
15. latest evidence commit `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

Do not reconstruct project truth from chat history after these files are available.

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`blocked_after_dual_stage_policy_gateway_health_failure_rollback_complete`

Current step:

`diagnose_gateway_rejection_of_dual_stage_readonly_policy_before_retry`

## Current runtime state

The latest enablement attempt failed after candidate policy activation because the existing OpenClaw Gateway did not become healthy.

Rollback was successful and healthy.

Treat the runtime as restored to the prior tools-denied baseline:

- plugin remains the installed `oris-dev-employee` `0.1.0` baseline;
- exactly three approved read-only tools are registered;
- exactly three typed hooks are registered;
- the three tools remain denied after rollback;
- no write tool was added;
- no product task was submitted;
- OpenClaw was not reinstalled or upgraded;
- no secret was printed.

## Latest evidence

Latest result:

- `FAILED`
- failure: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- selected policy: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- rollback: `YES`
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`
- evidence JSON: `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260619T200933Z.json`

The attempt generated:

- 13 entries in candidate `tools.allow`;
- 3 entries in candidate `tools.alsoAllow`;
- unrestricted skill policy for Agent `main`.

It failed before runtime inventory, direct tool calls, native Agent acceptance or telemetry acceptance.

False post-stage fields in this early-abort evidence mean `NOT_CHECKED`; they do not prove write tools appeared or repositories changed.

## Previously completed proof

- read-only readiness: 26/26 pass, evidence `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`;
- direct calls to all three ORIS tools passed in earlier controlled attempts;
- routing skill was runtime-visible to Agent `main`;
- native Agent transport and persisted sessions worked;
- earlier model turns produced `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`;
- repository active target quality gate passed with zero target findings;
- repository-wide legacy findings remain 865 and are not declared fully fixed;
- insight database security result is `ALREADY_SECURE_AND_VERIFIED`, latest evidence `bc799a640138a19800270ecab1a656f09d70252a`.

## Source changes already on main

Dual-stage policy and diagnostics:

- `741f24687c751ebfa405d8ea74c8a45a53a09161`
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323`
- `c48a8741645cfd57ba24530a6dc4da767612568a`
- `d650a0f9e4686df4b46157ace680e9bb08e396ff`

Do not add another parallel parser, tool-policy implementation or service controller without first scanning for existing definitions.

## First action in the new chat

Do not rerun enablement immediately.

First inspect the current enablement modules for:

- duplicate config/JSON parsers;
- duplicate tool-name/profile-expansion definitions;
- existing OpenClaw validation helpers;
- existing systemd/Gateway status and journal helpers;
- hardcoded host/port/project/provider/model values;
- modules that need decomposition before more code is added.

Then implement the diagnostic plan from:

`docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`

Required diagnostic behavior:

1. build the candidate config privately;
2. run installed OpenClaw config/schema validation where supported;
3. determine which candidate field/combination prevents Gateway health;
4. capture bounded sanitized service status/journal evidence before rollback;
5. use `PASS`/`FAIL`/`NOT_CHECKED` evidence semantics;
6. restore and prove the exact tools-denied baseline;
7. publish evidence through a detached worktree;
8. only after reading evidence, choose the minimal runtime-accepted policy and rerun enablement.

## Fixed restrictions

- do not reinstall or upgrade OpenClaw;
- do not reinstall the plugin;
- do not manually edit `openclaw.json`;
- do not add write tools;
- do not submit a product task;
- do not expose 18891 or 18892;
- do not touch production host `8.136.28.6`;
- do not copy product code into ORIS;
- do not print or commit secrets/raw config/private marker content;
- do not ask the user to paste long logs;
- do not introduce acceptance-project hardcoding.

## Fixed engineering and interaction contract

- Chinese, professional, direct and structured;
- routine engineering decisions are automatic;
- long scripts/docs/patches go directly to GitHub;
- user receives one short pull-and-run command only when host execution is required;
- no long heredoc;
- no `set -e` in user-facing scripts;
- every run ends with exactly one `===== SUMMARY =====`;
- inspect detailed evidence from GitHub;
- scan for duplicate definitions and hardcoded values before every edit;
- reuse one authoritative implementation;
- split large files by responsibility;
- `main` is the only mainstream branch;
- backups and detached evidence worktrees are allowed;
- competing long-lived branches are prohibited;
- completion requires real tests, commit SHA, remote SHA and evidence.

## Commercial order after this blocker

1. complete Gateway-safe read-only enablement;
2. prove native natural-language invocation of all three tools;
3. establish privacy-safe real latency telemetry;
4. design explicit typed write actions with approval/RBAC/idempotency/audit;
5. add generic project onboarding;
6. move routine provider/policy controls into Admin UI;
7. add monitoring, privacy/retention, backup/restore and disaster recovery;
8. add multi-tenant quotas, metering and packaging.
