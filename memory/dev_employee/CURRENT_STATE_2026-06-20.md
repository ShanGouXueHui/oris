# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`single_scope_policy_remediation_published_pending_runtime_dry_run`

Current step:

`execute_single_scope_native_config_patch_dry_run_diagnostic`

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

Do not reinstall or upgrade OpenClaw. Do not reinstall the plugin. Do not expose internal listeners. Do not add write tools in the current task. Do not touch production host `8.136.28.6`.

## Installed baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- plugin source: `8f174b49196aac90b505846200ce260f75355b41`;
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- readiness evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`.

## Code governance state

The target package code audit passed across 42 modules before the latest runtime diagnostic:

- duplicate bindings: 0;
- competing authorities: 0;
- duplicate function bodies: 0;
- import cycles: 0;
- oversized modules: 0;
- forbidden hardcoding: 0;
- legacy path findings: 0;
- contract errors: 0.

The structural source-code blocker is closed. Any later code change must pass the same gate again before runtime work.

## Historical enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The dual-stage candidate was activated, the existing Gateway did not pass its health gate, and rollback restored the exact tools-denied baseline. Runtime inventory, direct tool calls, native Agent acceptance and telemetry acceptance were not reached.

This historical result does not authorize another blind activation.

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

- 9 PASS;
- 1 FAIL;
- 6 NOT_CHECKED.

Verified:

- source governance and diagnostic selftests passed;
- exact approved tools remained denied in the active baseline;
- Gateway baseline and final health passed;
- private candidate build passed;
- ORIS candidate compatibility passed under the previous internal rules;
- active configuration remained unchanged;
- Gateway was not restarted;
- queue and product repository remained unchanged;
- no product task was submitted;
- no write tool was added.

The installed native `config patch --dry-run` rejected the candidate because it contained both non-empty `tools.allow` and non-empty `tools.alsoAllow`.

OpenClaw `2026.5.19 (a185ca2)` requires one authorization scope:

1. explicit `allow`; or
2. profile plus additive `alsoAllow`.

## Single-scope remediation

Authoritative document:

`docs/DEV_EMPLOYEE_OPENCLAW_SINGLE_SCOPE_TOOL_POLICY_REMEDIATION_2026-06-20.md`

The corrected current-baseline policy is:

- preserve `tools.profile = coding`;
- do not create `tools.allow`;
- add only the three approved ORIS tools to `tools.alsoAllow`;
- remove those three tools from `tools.deny`.

The expected minimal patch changes only:

- `tools.alsoAllow`;
- `tools.deny`.

The code now:

- rejects non-empty `allow` plus non-empty `alsoAllow` before runtime validation;
- supports existing explicit-allow baselines without creating `alsoAllow`;
- supports current profile baselines through `alsoAllow` only;
- verifies rollback scope reconstruction for the selected mode;
- records sanitized OpenClaw validation rule codes and message hashes without raw messages or SecretRef values.

## Current blocker

The corrected single-scope candidate has not yet passed the installed OpenClaw native dry-run.

Candidate activation remains prohibited until the next GitHub diagnostic evidence is read.

## Next action

Run exactly once on development/control host `43.106.55.255` as user `admin`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

The run remains diagnostic-only. It must not activate the candidate, replace active config, restart Gateway, install the routing Skill, invoke ORIS tools, submit a product task or add write tools.

The diagnostic must first re-pass the source governance and selftest gates. A runtime dry-run `PASS` permits evidence review only.

Return only the final `===== SUMMARY =====` block. Read detailed evidence from GitHub before any activation decision.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
