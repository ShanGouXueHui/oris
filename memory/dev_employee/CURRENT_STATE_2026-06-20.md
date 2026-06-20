# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`controlled_activation_retry_authorized_pending_execution`

Current step:

`execute_single_controlled_readonly_activation_retry`

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the plugin. Do not expose internal listeners. Do not add write tools in this task. Do not touch production host `8.136.28.6`.

## Installed baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- active product task: none;
- current runtime: exact healthy tools-denied baseline.

## Previous activation failure and remediation

Activation evidence:

`2c5c33adfd04f2c6a2312465c198aa18ceac41c1`

The candidate, Gateway restart, routing Skill visibility, plugin runtime inventory and all three direct ORIS read-only calls passed. Failure occurred before the first native Agent turn because a stale automatic test still asserted the obsolete dual-scope policy.

Rollback restored the exact tools-denied configuration and routing Skill state and returned Gateway to healthy status. No task, product mutation or write tool occurred.

The remediation now:

- aligns tests with single-scope `profile + alsoAllow` policy;
- executes named automatic selftests before mutation;
- removes the redundant post-mutation test rerun;
- reports blocked stages as `NOT_CHECKED`.

## Latest diagnostic verification

Evidence commit:

`30a32ba761418d0e7bcbb04ac2b4e0a9ac0c8e82`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

Checks:

- 10 PASS;
- 0 FAIL;
- 6 intentional NOT_CHECKED post-activation stages.

Verified:

- diagnostic selftests passed;
- source governance passed across 46 modules with all structural findings at zero;
- exact tools-denied baseline remained active;
- Gateway remained healthy and was not restarted;
- private candidate used exactly `profile-plus-alsoAllow`;
- `tools.allow=0`, `tools.alsoAllow=3`, candidate `tools.deny=0`;
- patch paths were exactly `tools.alsoAllow` and `tools.deny`;
- native OpenClaw dry-run passed schema and complete resolvability checks with zero errors;
- active config was unchanged and unwritten;
- queue and product remained unchanged;
- no Skill, ORIS tool, product task or write tool was created or invoked.

## Controlled retry authorization

Authoritative document:

`docs/DEV_EMPLOYEE_CONTROLLED_ACTIVATION_RETRY_AUTHORIZATION_2026-06-20.md`

The diagnostic evidence has been reviewed and authorizes exactly one controlled read-only activation retry on development/control host `43.106.55.255`.

The transaction must run all pre-mutation gates, complete native Agent and telemetry acceptance, or automatically restore the exact tools-denied baseline and prove final Gateway health.

A third attempt is not authorized.

## Next action

Run exactly once:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_enable_openclaw_readonly_tools.sh
```

Do not run it again before the resulting GitHub evidence is reviewed. Return only the final `===== SUMMARY =====` block.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish privacy-safe real model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
