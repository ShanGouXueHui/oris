# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`controlled_activation_jit_gate_published_pending_execution`

Current step:

`execute_controlled_readonly_enablement_once`

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

The latest diagnostic scanned 43 target modules and passed all tracked gates:

- duplicate bindings: 0;
- competing authorities: 0;
- duplicate function bodies: 0;
- import cycles: 0;
- oversized modules: 0;
- forbidden hardcoding: 0;
- legacy path findings: 0;
- contract errors: 0.

The enablement transaction now re-runs this governance gate before any mutation.

## Historical enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The previous dual-scope candidate was activated, the existing Gateway did not pass its health gate, and rollback restored the exact tools-denied baseline. Runtime inventory, direct tool calls, native Agent acceptance and telemetry acceptance were not reached.

This historical result does not authorize blind activation.

## Diagnostic run 3

Evidence commit:

`366c8b441e8adff5fa684b2255339ad32832cc31`

Result:

`DIAGNOSTIC_RUNTIME_VALIDATION_FAILED`

The installed native `config patch --dry-run` rejected the candidate because it contained both non-empty `tools.allow` and non-empty `tools.alsoAllow`.

OpenClaw `2026.5.19 (a185ca2)` requires one authorization scope:

1. explicit `allow`; or
2. profile plus additive `alsoAllow`.

## Single-scope remediation

Authoritative document:

`docs/DEV_EMPLOYEE_OPENCLAW_SINGLE_SCOPE_TOOL_POLICY_REMEDIATION_2026-06-20.md`

The corrected policy is:

- preserve `tools.profile = coding`;
- do not create `tools.allow`;
- add only the three approved ORIS tools to `tools.alsoAllow`;
- remove those three tools from `tools.deny`.

ORIS rejects non-empty `allow` plus non-empty `alsoAllow` before runtime validation.

## Diagnostic run 4 — candidate accepted

Evidence commit:

`2eb0e06c4dee75486e3f3859337867d638941901`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

Checks:

- 10 PASS;
- 0 FAIL;
- 6 NOT_CHECKED.

Verified:

- engineering scan passed across 43 target modules;
- authorization scope was exactly `profile-plus-alsoAllow`;
- `tools.allow` count was 0;
- `tools.alsoAllow` count was 3;
- `tools.deny` count was 0;
- installed OpenClaw accepted `config patch --dry-run`;
- patch paths were exactly `tools.alsoAllow` and `tools.deny`;
- schema and resolvability checks passed with zero errors;
- active config was unchanged and unwritten;
- Gateway stayed healthy without restart;
- queue and product repository stayed unchanged;
- no product task was submitted;
- no write tool was added.

The evidence has been read from GitHub and accepted for one controlled activation transaction.

## Controlled activation gate

Authoritative document:

`docs/DEV_EMPLOYEE_CONTROLLED_ACTIVATION_GATE_2026-06-20.md`

Before any Skill installation, active config write or Gateway restart, enablement now must:

1. re-run source governance;
2. rebuild the private single-scope candidate;
3. repeat installed OpenClaw native dry-run;
4. reject unexpected policy paths, dual scopes, incomplete schema/resolvability checks, raw output retention or SecretRef retention;
5. prove the active config hash is unchanged;
6. create the private tools-denied backup;
7. prove the backup hash exactly matches the validated config hash.

Only after these checks pass may the transaction install the routing Skill, apply the policy and restart the existing Gateway.

Any failure after mutation begins must restore the exact tools-denied config, private marker and Skill state, restart Gateway, and prove rollback health.

## Current blocker

The one authorized controlled activation transaction has not yet executed. The runtime remains on the healthy tools-denied baseline.

## Next action

Run exactly once on development/control host `43.106.55.255` as user `admin`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_enable_openclaw_readonly_tools.sh
```

Do not execute a second enablement attempt before the resulting GitHub evidence is reviewed.

The transaction must either complete native read-only tool, telemetry and invariance acceptance or automatically restore the exact tools-denied baseline.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
