# ORIS Dev Employee — Authoritative Context Index

Last updated: 2026-06-20

## Purpose

This is the stable entry point for every new ORIS / OpenClaw / Codex-backed AI Dev Employee conversation.

Do not reconstruct current project truth from chat history when these GitHub files are available.

## Mandatory read order

Read the current authoritative set first:

1. `memory/dev_employee/CURRENT_STATE_2026-06-20.md`
2. `memory/dev_employee/current_task.json`
3. `memory/dev_employee/current_task.md`
4. latest failed-enablement evidence commit `2c5c33adfd04f2c6a2312465c198aa18ceac41c1`
5. `docs/DEV_EMPLOYEE_CONTROLLED_ACTIVATION_GATE_2026-06-20.md`
6. `docs/DEV_EMPLOYEE_OPENCLAW_SINGLE_SCOPE_TOOL_POLICY_REMEDIATION_2026-06-20.md`
7. latest accepted-candidate diagnostic evidence commit `2eb0e06c4dee75486e3f3859337867d638941901`
8. `docs/DEV_EMPLOYEE_OPENCLAW_POLICY_DRY_RUN_VALIDATION_ADDENDUM_2026-06-20.md`
9. `docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`
10. `docs/DEV_EMPLOYEE_OPENCLAW_READONLY_POLICY_DIAGNOSTIC_IMPLEMENTATION_2026-06-19.md`
11. `docs/DEV_EMPLOYEE_ENVIRONMENT_AND_OPERATING_MODEL_ADDENDUM_2026-06-19.md`
12. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_2026-06-16.md`
13. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-17.md`
14. `docs/DEV_EMPLOYEE_ENGINEERING_STANDARD_ADDENDUM_2026-06-19.md`
15. `memory/dev_employee/OPENCLAW_NATIVE_PLUGIN_INSTALL_COMPLETION_2026-06-18.md`
16. `docs/DEV_EMPLOYEE_OPENCLAW_AGENT_END_POLICY_ADDENDUM_2026-06-18.md`
17. `docs/DEV_EMPLOYEE_OPENCLAW_PLUGIN_RUNTIME_HOOK_INSPECTION_ADDENDUM_2026-06-18.md`
18. `docs/DEV_EMPLOYEE_COMMERCIALIZATION_PRIORITY_2026-06-18.md`
19. `orchestration/project_registry.json`
20. historical Gateway-failure evidence commit `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

Use earlier dated files only for historical background.

## Authority hierarchy

When documents conflict, use this order:

1. latest dated file under `memory/dev_employee/`;
2. `memory/dev_employee/current_task.json`;
3. `memory/dev_employee/current_task.md`;
4. latest dated architecture, diagnostic, engineering or environment addendum;
5. current machine-readable configuration and `orchestration/project_registry.json`;
6. latest sanitized evidence under `logs/dev_employee/` and its remote evidence commit;
7. older dated state, handoff and architecture documents.

Historical evidence must never be rewritten to hide failures. Correct current truth with a newer authoritative document or explicit correction addendum.

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Fixed decisions:

- native OpenClaw is the commercial primary UI;
- custom ORIS UI remains restricted diagnostics and rollback only;
- do not reinstall or upgrade OpenClaw during the active task;
- reuse `openclaw-gateway.service` on `127.0.0.1:18789`;
- expose ORIS through stable typed tools/actions/plugins;
- do not restore broad prompt-keyword task creation;
- keep 18891 and 18892 loopback-only;
- keep product code in product repositories;
- `main` is the only mainstream branch;
- do not touch production host `8.136.28.6` without an explicit production task.

## Current active task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`automatic_selftest_remediation_published_pending_diagnostic_verification`

Current step:

`verify_selftest_remediation_without_mutation`

## Current observed facts

Completed baseline:

- plugin `oris-dev-employee` `0.1.0` is installed;
- installation result is `INSTALLED_TOOLS_DENIED`;
- exactly three read-only tools and three typed hooks were runtime-verified;
- readiness result is `26/26 PASS`;
- no write tool is authorized;
- no product task is active.

Accepted-candidate diagnostic evidence `2eb0e06c4dee75486e3f3859337867d638941901` proved the single-scope candidate passes installed OpenClaw native dry-run without active mutation.

Latest controlled activation evidence `2c5c33adfd04f2c6a2312465c198aa18ceac41c1` records:

- 18 PASS and 1 FAIL;
- just-in-time candidate validation passed;
- Gateway restart and health passed;
- routing Skill visibility passed;
- plugin runtime inventory passed;
- all three direct ORIS read-only calls passed;
- queue-after-direct-call check passed;
- failure occurred as `AssertionError` before native Agent acceptance;
- rollback restored the exact tools-denied baseline and healthy Gateway;
- no task, product mutation or write tool occurred.

Source inspection identified a stale automatic policy selftest which still asserted the removed dual-scope behavior. The runtime policy itself was not defective.

The remediation on `main` now aligns selftests with the single-scope contract, runs them before any mutation, removes the late rerun, and records blocked later stages as `NOT_CHECKED`.

A controlled activation retry is not authorized until a new diagnostic-only run verifies this remediation and its GitHub evidence is reviewed.

## Immediate next action

Run once on development/control host `43.106.55.255` as user `admin`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

This run is diagnostic-only. Do not execute enablement, install the Skill, replace active config, restart Gateway, invoke ORIS tools, submit a task or add write tools.

## Environment

- ORIS development/control/execution: `43.106.55.255`, user `admin`;
- ORIS repository: `/home/admin/projects/oris`;
- separate production host: `8.136.28.6`, user `deploy`; do not touch;
- OpenClaw Gateway: `127.0.0.1:18789`;
- enqueue/status: `127.0.0.1:18891`;
- intake: `127.0.0.1:18892`;
- Web Console: `127.0.0.1:18893`;
- OpenClaw: `2026.5.19 (a185ca2)`;
- Node: `v22.22.2`;
- npm: `10.9.7`;
- Codex CLI: real coding executor;
- provider/model identities are runtime facts and must not be hardcoded;
- ZenMux remains excluded unless explicitly reopened.

## Engineering and interaction contract

- Chinese, professional, direct and structured;
- do not ask the user to decide routine engineering details;
- write long scripts, documents and patches directly to GitHub;
- give one short pull-and-run command only when host execution is required;
- no long heredocs;
- detailed logs go under `logs/dev_employee/` and are read from GitHub;
- every user-run script ends with exactly one `===== SUMMARY =====`;
- never print or commit secrets, raw config or private marker content;
- user-facing shell scripts do not use `set -e`;
- scan for duplicate definitions and hardcoded values before every edit;
- reuse one authoritative definition per rule;
- split large files by responsibility;
- configuration and code remain separated;
- generic commercial implementation only;
- evidence is committed once through a detached worktree;
- competing long-lived branches are prohibited;
- do not append to tracked logs after commit.

## Commercial priority order

1. verify the selftest remediation through diagnostic-only evidence;
2. complete controlled read-only enablement and native natural-language acceptance;
3. establish privacy-safe real model/tool/agent latency telemetry;
4. design explicit typed write actions only after P0 passes;
5. add generic project onboarding and capability discovery;
6. add controlled Admin Provider/Model/Policy management;
7. add monitoring, privacy/retention, backup/restore and disaster recovery;
8. add multi-tenant quotas, metering and commercial packaging.
