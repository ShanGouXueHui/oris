# Current AI Dev Employee Task

Status: `blocked_after_dual_stage_policy_gateway_health_failure_rollback_complete`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `diagnose_gateway_rejection_of_dual_stage_readonly_policy_before_retry`

## Objective

Enable only these three read-only ORIS typed tools through the installed native OpenClaw plugin:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Then prove:

- native natural-language use;
- no ORIS-specific command syntax;
- no task submission or queue mutation;
- no write tool;
- privacy-safe `model_call_ended`, `after_tool_call` and `agent_end` telemetry;
- real model/tool/agent latency baseline;
- automatic rollback to tools-denied state on any failure.

This task does not authorize submit, cancel, retry or product-mutation actions.

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
- evidence JSON: `logs/dev_employee/openclaw_readonly_tool_readiness/openclaw-readonly-tool-readiness-20260618T212757Z.json`

Readiness did not modify config, restart Gateway, enable tools or submit a product task.

### Quality target

- repository scan: `FINDINGS`, 865 total repository findings
- active remediation target gate: `PASS`
- active target findings: `0`

The repository-wide count still includes legacy debt. It is not considered fully resolved.

## What has been proved

### Direct tools

All three ORIS tools passed direct contract-valid read-only calls in earlier controlled attempts.

### Skill routing

The managed `oris-readonly-status` skill was runtime-visible to Agent `main` in earlier attempts. It requires the matching typed tool and prohibits exec, shell, filesystem, browser, HTTP and write-action fallback.

### Native Agent transport

OpenClaw native Agent turns completed through the existing Gateway with a persisted session and without embedded fallback.

### Missing model tool invocation

Earlier evidence showed:

- `model_call_ended=3`
- `agent_end=3`
- `after_tool_call=0`

Therefore direct tool success and skill visibility did not prove model tool availability.

## Current source implementation

A reversible dual-stage tool-policy implementation now exists:

1. optional-tool materialization through `tools.allow`;
2. profile extension through `tools.alsoAllow`;
3. removal of only the approved three names from `tools.deny`;
4. exact config-scope validation;
5. automatic restoration of the prior tools-denied config.

Relevant source commits:

- `741f24687c751ebfa405d8ea74c8a45a53a09161`
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323`
- `c48a8741645cfd57ba24530a6dc4da767612568a`
- `d650a0f9e4686df4b46157ace680e9bb08e396ff`

## Latest attempt

Latest evidence:

- result: `FAILED`
- failure: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- selected policy: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- candidate `tools.allow` count: 13
- candidate `tools.alsoAllow` count: 3
- rollback: healthy
- product task submitted: no
- write tools added: no
- secrets printed: no
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`
- evidence JSON: `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260619T200933Z.json`

The failure happened after candidate policy activation and before runtime inventory, direct calls, Agent acceptance and telemetry acceptance.

Rollback restored the tools-denied baseline.

## Evidence interpretation correction

In the latest early-abort JSON, false values for direct calls, write-tool absence, queue unchanged and product unchanged mean those checks were not reached. They do not prove a write tool appeared or a repository changed.

Future evidence must use `PASS`, `FAIL` and `NOT_CHECKED` semantics.

## Current blocker

The exact reason the installed OpenClaw Gateway rejects or fails under the candidate dual-stage policy is not yet captured.

The current evidence contains the health timeout and rollback result, but not the runtime config-validator error or bounded service journal reason.

## Next required action

Do not rerun the same enablement script blindly.

First update the GitHub-hosted workflow to:

1. scan the target source for duplicate definitions, existing helpers and hardcoded values;
2. build the candidate config in a private temporary path;
3. run installed OpenClaw config/schema validation where supported;
4. test whether `tools.profile`, `tools.allow`, `tools.alsoAllow`, group selectors and optional tools may coexist in OpenClaw `2026.5.19`;
5. capture pre-mutation Gateway PID and health;
6. capture bounded sanitized `systemctl` and `journalctl` diagnostics on failure before rollback;
7. represent unreached checks as `NOT_CHECKED`;
8. restore the exact tools-denied config and prove Gateway health;
9. commit sanitized evidence through a detached worktree;
10. only then choose and rerun the minimal runtime-accepted enablement policy.

Authoritative diagnostic plan:

`docs/DEV_EMPLOYEE_OPENCLAW_READONLY_ENABLEMENT_DIAGNOSTIC_PLAN_2026-06-19.md`

## Engineering rules

- scan for duplicate definitions before every edit;
- no hardcoded environment/project/provider/model/acceptance behavior in shared code;
- reuse one authoritative implementation;
- split large files by responsibility;
- long scripts and documents go directly to GitHub;
- user receives one short pull-and-run command;
- no long heredoc;
- user-facing shell scripts do not use `set -e`;
- every run ends with one `===== SUMMARY =====`;
- detailed evidence is inspected from GitHub;
- never print or commit secrets;
- `main` is the only mainstream branch;
- backups allowed, competing long-lived branches prohibited;
- do not touch production host `8.136.28.6` without an explicit task;
- do not reinstall/upgrade OpenClaw or reinstall the plugin;
- do not add write tools.

## Commercial sequence after P0

1. complete read-only tool and telemetry acceptance;
2. design explicit typed write actions with approval, project authorization, idempotency and audit;
3. add generic project onboarding and capability discovery;
4. move routine provider/policy management to controlled Admin UI;
5. add monitoring, privacy/retention, backup/restore and disaster recovery;
6. add multi-tenant identity, quotas, metering and commercial packaging.
