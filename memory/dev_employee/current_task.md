# Current AI Dev Employee Task

Status: `single_scope_policy_remediation_published_pending_runtime_dry_run`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `execute_single_scope_native_config_patch_dry_run_diagnostic`

## Objective

Enable only these three read-only ORIS typed tools through the installed native OpenClaw plugin:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Then prove native natural-language tool use, no task or product mutation, no write tool, privacy-safe typed-hook telemetry, a real model/tool/agent latency baseline and automatic rollback to the tools-denied state on failure.

This task does not authorize submit, cancel, retry or product-mutation actions.

## Fixed architecture and boundaries

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw, reinstall the plugin, expose internal listeners, add write tools or touch production host `8.136.28.6`.

## Completed prerequisites

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- plugin source: `8f174b49196aac90b505846200ce260f75355b41`;
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`;
- readiness: `26/26 PASS`;
- readiness evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`;
- source code governance: `CODE_AUDIT_PASS` across 42 target modules;
- duplicate bindings, competing authorities, duplicate function bodies, import cycles, oversized modules, forbidden hardcoding, legacy path findings and contract errors: all zero.

Previously proved:

- all three tools pass direct read-only calls;
- Skill `oris-readonly-status` was visible to Agent `main`;
- native Gateway transport and persisted sessions work;
- prior telemetry contained `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`.

Direct invocation and Skill visibility still do not prove model tool materialization or invocation.

## Historical enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The candidate policy was activated, the existing Gateway failed its health gate, and rollback restored the tools-denied baseline. Runtime inventory, direct calls, native Agent acceptance and telemetry acceptance were not reached.

## Diagnostic run 2

Evidence commit:

`7c01b72a8ae71c2cbf62a0ae4032ab245b09335c`

Result:

`DIAGNOSTIC_VALIDATOR_UNAVAILABLE`

The installed CLI exposed `config validate` and `config check`, but neither accepted an alternate candidate path. No policy rejection was observed.

## Diagnostic run 3

Evidence commit:

`366c8b441e8adff5fa684b2255339ad32832cc31`

Result:

`DIAGNOSTIC_RUNTIME_VALIDATION_FAILED`

Checks:

- `9 PASS`;
- `1 FAIL`;
- `6 NOT_CHECKED`.

Verified:

- all diagnostic selftests and source governance checks passed;
- exact tools-denied baseline remained active;
- Gateway remained active and HTTP healthy;
- private candidate build passed without active mutation;
- active config, queue and product repository remained unchanged;
- Gateway was not restarted;
- no product task was submitted;
- no write tool was added.

The installed OpenClaw `config patch --dry-run` rejected the candidate because the candidate contained both non-empty `tools.allow` and non-empty `tools.alsoAllow` in the same scope.

OpenClaw `2026.5.19 (a185ca2)` explicitly requires either:

- an explicit `allow` policy; or
- a tool profile plus additive `alsoAllow` entries.

It does not permit both non-empty lists together.

## Single-scope remediation

Authoritative remediation document:

`docs/DEV_EMPLOYEE_OPENCLAW_SINGLE_SCOPE_TOOL_POLICY_REMEDIATION_2026-06-20.md`

The active baseline has `tools.profile = coding` and no existing non-empty `tools.allow`. Therefore the corrected candidate uses:

- `tools.profile = coding` unchanged;
- no materialized `tools.allow`;
- only the three approved ORIS tools in `tools.alsoAllow`;
- the approved ORIS tools removed from `tools.deny`.

The expected policy patch now changes only:

- `tools.alsoAllow`;
- `tools.deny`.

Code enforcement now includes:

- ORIS rejects any candidate with both non-empty `allow` and `alsoAllow`;
- the policy transformer selects exactly one authorization scope;
- positive selftests cover `profile + alsoAllow`;
- negative selftests cover the rejected dual-scope policy;
- dry-run JSON output is converted into sanitized rule codes and hashes without preserving raw messages or SecretRef identifiers.

## Current blocker

The corrected single-scope candidate has not yet passed the installed OpenClaw native dry-run.

Candidate activation remains prohibited until the resulting GitHub evidence is read.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

This remains diagnostic-only. It must not:

- execute the enablement entrypoint;
- replace active config;
- restart Gateway;
- install the routing Skill;
- invoke ORIS tools;
- submit a product task;
- add write tools.

The run must first pass the source governance and selftest gates. A native dry-run `PASS` authorizes evidence review only, not automatic activation.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
