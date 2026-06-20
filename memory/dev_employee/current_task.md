# Current AI Dev Employee Task

Status: `controlled_activation_retry_authorized_pending_execution`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `execute_single_controlled_readonly_activation_retry`

## Objective

Enable only these three read-only ORIS typed tools through the installed native OpenClaw plugin:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

Then prove native natural-language tool use, no task or product mutation, no write tool, privacy-safe typed-hook telemetry, a real model/tool/agent latency baseline and automatic rollback to the tools-denied state on failure.

## Latest diagnostic review

Evidence commit:

`30a32ba761418d0e7bcbb04ac2b4e0a9ac0c8e82`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

Verified:

- diagnostic selftests passed, including the remediated single-scope policy selftests;
- source governance passed across 46 modules with zero duplicate bindings, competing authorities, duplicate function bodies, import cycles, oversized modules, forbidden hardcoding, legacy findings or contract errors;
- active runtime remained on the exact tools-denied baseline;
- Gateway was healthy before and after validation and was not restarted;
- candidate authorization scope was exactly `profile-plus-alsoAllow`;
- `tools.allow=0`, `tools.alsoAllow=3`, candidate `tools.deny=0`;
- patch paths were exactly `tools.alsoAllow` and `tools.deny`;
- installed OpenClaw native `config patch --dry-run` passed schema and complete resolvability checks with zero errors;
- active config was neither written nor changed;
- queue and product repository remained unchanged;
- no Skill installation, ORIS tool invocation, task submission or write tool occurred.

## Retry authorization

Authoritative document:

`docs/DEV_EMPLOYEE_CONTROLLED_ACTIVATION_RETRY_AUTHORIZATION_2026-06-20.md`

Exactly one controlled read-only activation retry is authorized on development/control host `43.106.55.255`.

Before mutation, the transaction must re-run compilation, source governance, named automatic selftests, private candidate construction, native dry-run validation and exact config-hash-to-backup matching.

After mutation, it must verify Gateway health, Skill visibility, exact plugin inventory, direct read-only calls, three native natural-language Agent turns in one persisted session, typed-hook telemetry, privacy-safe latency metadata and all queue/product/listener invariants.

Any failure after mutation begins must restore the exact tools-denied policy, marker and Skill state and prove final Gateway health.

A further retry is prohibited until the resulting evidence is reviewed.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_enable_openclaw_readonly_tools.sh
```

Do not execute the command a second time. Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
