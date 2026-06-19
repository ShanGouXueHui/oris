# Current AI Dev Employee Task

Status: `diagnostic_remediation_published_pending_runtime_execution`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `execute_github_hosted_pre_activation_policy_diagnostic`

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

Native OpenClaw is the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the plugin. Keep the internal ORIS listeners loopback-only. Keep product code in product repositories. `main` is the only mainstream branch.

## Completed prerequisites

### Native plugin installation

- plugin: `oris-dev-employee` `0.1.0`
- result: `INSTALLED_TOOLS_DENIED`
- source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

The installed baseline verified exactly three read-only tools, exactly three typed hooks, zero plugin errors, no write tools and scoped conversation access only for the ORIS plugin.

### Read-only readiness

- result: `READY`
- checks: `26/26 PASS`
- evidence commit: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`

Readiness did not modify config, restart Gateway, enable tools or submit a product task.

## Previously proved

- all three ORIS tools passed direct contract-valid read-only calls;
- managed Skill `oris-readonly-status` was runtime-visible to Agent `main`;
- native Agent turns completed through the existing Gateway with a persisted session;
- earlier telemetry contained `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`.

Therefore direct invocation success and Skill visibility did not prove model tool materialization or invocation.

## Latest failed attempt

- result: `FAILED`
- failure: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- selected policy: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- candidate `tools.allow`: 13 entries
- candidate `tools.alsoAllow`: 3 entries
- rollback: healthy
- product task submitted: no
- write tools added: no
- secrets printed: no
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The failure happened after candidate activation and Gateway restart, before runtime plugin inventory, direct calls, native Agent acceptance and telemetry acceptance.

False values for those unreached stages in the historical evidence mean `NOT_CHECKED`, not an observed regression.

## Diagnostic remediation now published

Implementation ancestor commit:

`090e815d7649a92054d5cc5cbe6036b8ad3fd2c7`

Entrypoint:

`scripts/dev_employee_diagnose_openclaw_readonly_policy.sh`

Implementation document:

`docs/DEV_EMPLOYEE_OPENCLAW_READONLY_POLICY_DIAGNOSTIC_IMPLEMENTATION_2026-06-19.md`

The implementation now provides:

1. source authority, duplicate-definition and hardcoding scan;
2. layered candidate, runtime validation, service control, plugin inventory, acceptance and evidence modules;
3. a mode-0700 private temporary candidate directory;
4. sensitive-value redaction before candidate validation;
5. reuse of the existing authoritative tool-profile and Skill policy transforms;
6. static validation of `tools.profile`, `tools.allow`, `tools.alsoAllow`, `tools.deny`, group selectors, optional tools and Skill visibility;
7. safe discovery of installed OpenClaw validators that explicitly accept an alternate candidate path;
8. pre-diagnostic Gateway PID presence and health capture;
9. exact active-config hash, queue and product invariants;
10. `PASS`, `FAIL` and `NOT_CHECKED` semantics;
11. detached-worktree evidence publication;
12. bounded, sanitized `systemctl` and `journalctl` capture before rollback when a future controlled activation fails;
13. exact tools-denied rollback health verification through the shared service controller.

## Diagnostic-only safety boundary

The next run does not activate the candidate and does not restart Gateway.

It must not:

- run the enablement entrypoint;
- invoke an ORIS tool;
- submit a product task;
- add a write tool;
- replace active OpenClaw configuration;
- touch the production host.

Activation, runtime inventory, direct calls, native Agent acceptance, telemetry acceptance and rollback will be reported as `NOT_CHECKED` during this diagnostic-only run.

## Current blocker

Source remediation is complete and published. The remaining blocker is installed-runtime evidence:

- whether the installed OpenClaw CLI exposes a safe alternate-config validator;
- whether that validator accepts or rejects the candidate policy shape;
- which exact policy field or selector is rejected if validation fails.

No enablement retry is authorized until the GitHub evidence from the diagnostic run is read.

## Next required action

Run once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Engineering rules

- no broad prompt-keyword task creation;
- no hardcoded provider or model in shared code;
- one rule has one authoritative implementation;
- scripts and modules remain layered by responsibility;
- no long heredoc;
- user-facing Linux scripts do not use `set -e`;
- every execution prints one final summary;
- never print or commit credentials, raw config or private marker content;
- evidence is committed once through a detached worktree;
- no competing long-lived branch;
- do not touch production host `8.136.28.6`;
- do not add write tools.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
