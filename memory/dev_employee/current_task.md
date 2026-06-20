# Current AI Dev Employee Task

Status: `controlled_activation_jit_gate_published_pending_execution`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `execute_controlled_readonly_enablement_once`

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
- latest source governance: `CODE_AUDIT_PASS` across 43 target modules;
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

The previous dual-scope candidate was activated, the existing Gateway failed its health gate, and rollback restored the tools-denied baseline. Runtime inventory, direct calls, native Agent acceptance and telemetry acceptance were not reached.

## Diagnostic run 3

Evidence commit:

`366c8b441e8adff5fa684b2255339ad32832cc31`

Result:

`DIAGNOSTIC_RUNTIME_VALIDATION_FAILED`

The installed OpenClaw `config patch --dry-run` rejected the candidate because it contained both non-empty `tools.allow` and non-empty `tools.alsoAllow` in the same scope.

OpenClaw `2026.5.19 (a185ca2)` permits either:

- an explicit `allow` policy; or
- a tool profile plus additive `alsoAllow` entries.

## Single-scope remediation

Authoritative document:

`docs/DEV_EMPLOYEE_OPENCLAW_SINGLE_SCOPE_TOOL_POLICY_REMEDIATION_2026-06-20.md`

The corrected candidate uses:

- `tools.profile = coding` unchanged;
- no materialized `tools.allow`;
- only the three approved ORIS tools in `tools.alsoAllow`;
- the approved ORIS tools removed from `tools.deny`.

ORIS now rejects any candidate with both non-empty `allow` and `alsoAllow` before runtime validation.

## Diagnostic run 4 — accepted candidate

Evidence commit:

`2eb0e06c4dee75486e3f3859337867d638941901`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

Checks:

- `10 PASS`;
- `0 FAIL`;
- `6 NOT_CHECKED`.

Verified:

- engineering scan passed across 43 target modules;
- candidate authorization scope is exactly `profile-plus-alsoAllow`;
- `tools.allow` count is 0;
- `tools.alsoAllow` count is 3;
- `tools.deny` count is 0;
- native `config patch --dry-run` returned success;
- patch changed only `tools.alsoAllow` and `tools.deny`;
- schema and resolvability checks passed with zero errors;
- active config remained unchanged and unwritten;
- Gateway remained healthy without restart;
- queue and product repository remained unchanged;
- no product task was submitted;
- no write tool was added.

The GitHub evidence has been reviewed and accepted for one controlled activation attempt.

## Just-in-time controlled activation gate

Authoritative document:

`docs/DEV_EMPLOYEE_CONTROLLED_ACTIVATION_GATE_2026-06-20.md`

Before any active mutation, the enablement transaction now must:

1. re-run source governance;
2. rebuild the candidate in a private temporary directory;
3. reject dual authorization scopes or unexpected policy paths;
4. repeat installed OpenClaw native dry-run;
5. require schema and resolvability completion with zero errors;
6. prove the active config was not written;
7. create the private tools-denied backup;
8. prove the backup hash exactly matches the validated config hash.

Only after those gates pass may the transaction install the routing Skill, apply the policy and restart the existing Gateway.

Any failure after mutation begins must restore the exact tools-denied config, marker and Skill state and prove rollback health.

## Current blocker

The one authorized controlled activation transaction has not yet executed. The active runtime remains on the healthy tools-denied baseline.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_enable_openclaw_readonly_tools.sh
```

Do not execute a second attempt before the resulting GitHub evidence is reviewed.

The transaction must either:

- finish native read-only tool, telemetry and invariance acceptance; or
- automatically restore the exact tools-denied baseline and publish failure evidence.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
