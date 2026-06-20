# Dev Employee Model Tool-Call and Agent Harness Diagnostic — 2026-06-20

## Status

Execution authority after effective-surface evidence commit `57636946573e149028fc5d180db75c3cecb316ba`.

## Proven boundary

The native Gateway `tools.effective` RPC proved that all three approved ORIS read-only typed tools are present and owned by Plugin `oris-dev-employee`. Plugin runtime, required hooks, routing Skill visibility, rollback, queue, product repository, and private listener invariants also passed.

Therefore this diagnostic must not repeat tool materialization work. It distinguishes:

1. provider/model plus generic Agent Harness tool-call capability;
2. ORIS-specific natural-language routing through the Agent Harness.

## Rules

- Do not hardcode provider or model identifiers.
- Read provider/model only from privacy-safe runtime telemetry.
- Use one persisted native Agent session.
- Dynamically select an approved safe built-in control tool from runtime configuration.
- Run one control turn for the safe built-in tool.
- Run one ORIS turn for `oris_queue_status`.
- Do not invoke ORIS tools directly.
- Do not submit a product task.
- Do not add write tools.
- Do not record prompts, responses, conversation content, tool arguments/results, raw config, secrets, or session identifiers.
- Restore exact tools-denied config, marker, and Skill state on every outcome.
- Verify Gateway, queue, product repository, and internal listener final invariants.
- Publish only sanitized evidence through a detached worktree.

## Decision matrix

| Safe built-in called | ORIS queue tool called | Conclusion | Next action |
|---|---|---|---|
| No | No | Generic tool-call capability not demonstrated | Diagnose runtime provider/model capability or generic Agent Harness tool-call pipeline |
| Yes | No | Generic capability works; ORIS routing fails | Fix ORIS Skill/Agent Harness routing without changing provider/model |
| Yes | Yes | Provider/model and ORIS routing both work | Run the full three-tool native natural-language acceptance |
| No | Yes | Inconsistent control result | Stop and inspect telemetry correlation and control-tool selection |

## Required final invariants

- exact tools-denied baseline restored;
- Gateway healthy;
- queue unchanged and zero active tasks;
- product repository unchanged;
- internal listeners loopback-only;
- no product task submitted;
- no write tool added;
- evidence commit remote-verified.
