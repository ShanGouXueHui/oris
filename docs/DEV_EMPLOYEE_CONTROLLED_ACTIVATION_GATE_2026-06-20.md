# Controlled Activation Gate — 2026-06-20

## Evidence reviewed

Diagnostic evidence commit:

`2eb0e06c4dee75486e3f3859337867d638941901`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

Verified facts:

- engineering scan passed across 43 target modules;
- duplicate bindings, competing authorities, duplicate function bodies, import cycles, oversized modules, forbidden hardcoding, legacy path findings and contract errors were all zero;
- active baseline remained `tools.profile = coding` with the three approved ORIS tools denied;
- candidate authorization scope was exactly `profile-plus-alsoAllow`;
- candidate had no `tools.allow` entries and exactly three `tools.alsoAllow` entries;
- candidate removed the three approved tools from `tools.deny`;
- installed OpenClaw accepted the private candidate through `config patch --dry-run`;
- the minimal patch changed only `tools.alsoAllow` and `tools.deny`;
- schema and resolvability checks passed with zero errors;
- active config was not written or changed;
- Gateway stayed healthy without restart;
- queue and product repository stayed unchanged;
- no product task or write tool was created.

## Activation authorization

The evidence authorizes one controlled enablement execution on the development/control host only.

It does not authorize:

- production deployment;
- OpenClaw reinstall or upgrade;
- plugin reinstall;
- broad prompt-keyword task creation;
- write tools;
- public exposure of internal listeners;
- touching host `8.136.28.6`.

## Just-in-time validation

Before any Skill installation, active configuration write or Gateway restart, the enablement transaction must:

1. re-run the complete source governance scan;
2. rebuild the candidate in a private temporary directory;
3. verify one authorization scope only;
4. run installed OpenClaw `config patch --dry-run` again;
5. require schema and resolvability completion with zero errors;
6. require the active config hash to remain unchanged;
7. require the patch paths to match the policy evidence exactly;
8. create the tools-denied backup;
9. verify the backup hash exactly matches the configuration validated by the dry-run.

Failure at any point before mutation must stop without Gateway restart or rollback.

## Controlled mutation and acceptance

After the just-in-time gate passes, the existing transaction may:

1. install the managed read-only routing Skill;
2. apply the validated single-scope policy;
3. restart the existing `openclaw-gateway.service`;
4. verify Gateway health and public/restricted route boundaries;
5. verify the exact three read-only plugin tools and typed hooks;
6. run direct read-only tool probes;
7. run three native natural-language Agent turns in one persisted session;
8. verify `after_tool_call`, `model_call_ended` and `agent_end` telemetry;
9. verify privacy, approved-tool-only behavior, queue invariance, product invariance and absence of write tools;
10. commit sanitized evidence once through a detached worktree.

Any failure after mutation begins must restore the exact tools-denied config, private marker and routing Skill state, restart Gateway, and prove rollback health.

## Completion sequence

A successful read-only enablement does not begin write-action development immediately.

The next commercial step is to persist completion and establish the real privacy-safe model/tool/agent latency baseline. Typed write actions remain P0-gated behind completed read-only acceptance and latency measurement.
