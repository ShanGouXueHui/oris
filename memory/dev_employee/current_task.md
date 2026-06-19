# Current AI Dev Employee Task

Status: `diagnostic_source_gate_remediated_pending_safe_rerun`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `rerun_github_hosted_pre_activation_policy_diagnostic_after_skill_module_split`

## Objective

Enable only these three read-only ORIS typed tools through the installed native OpenClaw plugin:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Then prove native natural-language tool use, no task or product mutation, no write tool, privacy-safe typed-hook telemetry, a real model/tool/agent latency baseline and automatic rollback to the tools-denied state on failure.

This task does not authorize submit, cancel, retry or product-mutation actions.

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only. Do not reinstall or upgrade OpenClaw, reinstall the plugin, expose internal listeners, add write tools or touch the production host.

## Completed prerequisites

- plugin: `oris-dev-employee` `0.1.0`
- installation result: `INSTALLED_TOOLS_DENIED`
- installed source: `8f174b49196aac90b505846200ce260f75355b41`
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`
- read-only readiness: `26/26 PASS`
- readiness evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`

Previously proved:

- all three tools pass direct read-only calls;
- Skill `oris-readonly-status` was visible to Agent `main`;
- native Gateway transport and persisted sessions work;
- prior telemetry contained `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`.

Direct invocation and Skill visibility still do not prove model tool materialization or invocation.

## Latest enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The candidate policy was activated, the existing Gateway failed its health gate, and rollback restored the tools-denied baseline. Runtime inventory, direct calls, native Agent acceptance and telemetry acceptance were not reached.

## First diagnostic run

Evidence commit:

`df9d21839974e4adcc6bde9b62db0fe468b3cc76`

Result:

`DIAGNOSTIC_FAILED`

Executed stages:

- diagnostic selftests: `PASS`;
- source authority and hardcoding scan: `FAIL`;
- all later stages: `NOT_CHECKED`.

Exact finding:

- duplicate authority definitions: `0`;
- forbidden hardcoding findings: `0`;
- oversized modules: `1`;
- file: `scripts/dev_employee_openclaw_enable/skill.py`;
- observed line count: `261`;
- permitted layered-module maximum: `240`.

This was an engineering source-gate failure, not an OpenClaw policy or Gateway runtime failure.

Safety result:

- active config mutated: no;
- Gateway restarted: no;
- ORIS tool invoked: no;
- product task submitted: no;
- write tool added: no;
- rollback required: no;
- evidence remotely verified: yes.

## Source-gate remediation

The Skill implementation has been split without changing its public API:

- compatibility facade: `scripts/dev_employee_openclaw_enable/skill.py` — 22 lines;
- installation, backup and restore authority: `scripts/dev_employee_openclaw_enable/skill_installation.py` — 181 lines;
- runtime inventory authority: `scripts/dev_employee_openclaw_enable/skill_runtime.py` — 85 lines.

The existing callers may continue importing from `.skill`.

A diagnostic selftest now proves that every public type and function exported by the facade is the same object as the corresponding split-module authority.

Relevant remediation commits include:

- `b3e7518c5afdfdc150e81c6c6d0cd0a844aa0d2e`
- `079e009a4d9b0ac99194ddd5a31abd25058d1090`
- `6b6fbfa7ea585e8de27e002d23dd573341480a98`
- `a4c1c04befeccc45c48ce55c901c87e9b0df1a70`

Additional evidence improvements:

- top-level `check_summary` now includes `not_checked`;
- diagnostic failures now preserve the stable internal reason code instead of only `RuntimeError`.

## Current blocker

The source-gate finding has been remediated, but the diagnostic must run again on the installed environment before reaching the actual OpenClaw validator question.

The remaining runtime questions are:

1. whether OpenClaw `2026.5.19` exposes a safe alternate-config validator;
2. whether that validator accepts the private candidate;
3. which policy field is rejected if validation fails.

Do not execute enablement before reading the next diagnostic evidence.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

The run must remain diagnostic-only:

- do not execute the enablement entrypoint;
- do not replace active config;
- do not restart Gateway;
- do not invoke ORIS tools;
- do not submit a product task;
- do not add write tools.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
