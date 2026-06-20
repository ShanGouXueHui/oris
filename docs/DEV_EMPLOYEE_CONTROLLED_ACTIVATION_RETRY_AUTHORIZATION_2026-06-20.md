# Controlled Read-Only Activation Retry Authorization — 2026-06-20

## Reviewed evidence

Latest diagnostic-only evidence commit:

`30a32ba761418d0e7bcbb04ac2b4e0a9ac0c8e82`

Result:

`DIAGNOSTIC_CANDIDATE_VALIDATED_PENDING_EVIDENCE_REVIEW`

## Verified remediation

The diagnostic-only run proved all required preconditions for a single retry:

- diagnostic selftests passed, including the remediated single-scope policy tests;
- source authority, duplicate-definition, import-cycle, oversized-module, hardcoding, legacy-path and contract gates passed across 46 modules;
- the active runtime remained on the exact tools-denied baseline;
- Gateway PID, service state and HTTP health were good before and after validation;
- the private candidate used exactly one authorization scope: `profile-plus-alsoAllow`;
- `tools.allow` count was 0;
- `tools.alsoAllow` count was 3;
- the approved tools were removed from `tools.deny` in the candidate;
- candidate patch paths were exactly `tools.alsoAllow` and `tools.deny`;
- installed OpenClaw `config patch --dry-run` passed schema and complete resolvability checks with zero errors;
- the active configuration was neither written nor changed;
- Gateway was not restarted;
- queue and product repository remained unchanged;
- no routing Skill was installed;
- no ORIS tool was invoked;
- no product task or write tool was created;
- no secret, raw config, conversation content or private marker content was retained.

## Retry authorization

One controlled retry of the existing read-only enablement transaction is authorized on development/control host `43.106.55.255` only.

The retry must use:

`scripts/dev_employee_enable_openclaw_readonly_tools.sh`

The retry must not:

- reinstall or upgrade OpenClaw;
- reinstall the plugin;
- add write tools;
- submit a product task;
- expose internal listeners;
- change the product repository;
- touch production host `8.136.28.6`;
- run more than once before the resulting evidence is reviewed.

## Mandatory transaction gates

Before mutation, the transaction must:

1. compile the enablement package in an isolated temporary cache;
2. re-run source governance;
3. run the named automatic selftests;
4. rebuild the private candidate;
5. repeat native OpenClaw dry-run validation;
6. require the single-scope policy and exact approved patch paths;
7. require the validated active-config hash to equal the private backup hash.

After mutation, the transaction must verify:

1. Gateway health and native route boundaries;
2. routing Skill visibility to Agent `main`;
3. exact plugin read-only tool and typed-hook inventory;
4. direct calls for all three approved ORIS read-only tools;
5. three native natural-language Agent turns using one persisted session;
6. approved-tool-only `after_tool_call` telemetry plus `model_call_ended` and `agent_end`;
7. privacy-safe latency metadata;
8. unchanged queue, product repository and loopback-only listeners;
9. absence of write tools and product task submission.

Any failure after mutation begins must restore the exact tools-denied configuration, marker and routing Skill state, restart the existing Gateway when required, prove final Gateway health, and publish sanitized evidence.

## Completion rule

Success advances to persistence of completion state and the real privacy-safe model/tool/agent latency baseline.

Failure returns to evidence review. A third attempt is not authorized by this document.
