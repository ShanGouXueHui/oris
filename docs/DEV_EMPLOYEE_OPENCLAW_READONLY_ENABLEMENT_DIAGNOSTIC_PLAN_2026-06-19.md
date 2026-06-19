# ORIS Dev Employee — OpenClaw Read-Only Enablement Diagnostic Plan 2026-06-19

## 1. Scope

This plan governs the next action for task:

`commercial-openclaw-readonly-tool-enable-20260618`

It does not authorize any ORIS write tool or product task.

## 2. Current verified facts

Verified before the latest failure:

- OpenClaw `2026.5.19 (a185ca2)` is the installed runtime;
- the existing Gateway is `openclaw-gateway.service` on `127.0.0.1:18789`;
- `oris-dev-employee` `0.1.0` is installed and enabled;
- exactly three approved read-only tools and three typed hooks are registered;
- direct calls to all three tools have passed in earlier controlled attempts;
- the managed skill is runtime-visible to Agent `main` in earlier attempts;
- prior model turns completed but produced no `after_tool_call` events;
- the full read-only readiness check passed 26/26;
- every failed attempt restored the tools-denied baseline.

Latest candidate policy evidence:

- `tools.allow` was materialized with the configured coding-profile expansion plus the three ORIS tools;
- `tools.alsoAllow` contained the three ORIS tools;
- the three tools were removed from `tools.deny`;
- the routing skill policy was unrestricted for Agent `main`;
- after activation, Gateway did not become healthy;
- rollback succeeded.

Authoritative failure evidence:

- commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`
- JSON: `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260619T200933Z.json`

## 3. Problem statement

The current script proves that the candidate JSON is internally consistent according to ORIS-side policy logic. It does not yet prove that the installed OpenClaw runtime accepts the candidate combination.

The exact Gateway failure cause is unknown because the evidence records only the health timeout and rollback result, not the bounded runtime validation or systemd journal reason.

No further enablement retry is permitted until that diagnostic gap is closed.

## 4. Diagnostic architecture

The next implementation must be split into these layers:

### 4.1 Candidate builder

Pure logic only:

- load the current tools-denied config;
- derive the candidate policy from the versioned profile expansion and approved tool set;
- reject duplicate entries;
- reject unknown OpenClaw versions;
- produce a private candidate file;
- produce a redacted structural diff, not raw config content.

### 4.2 Runtime validator adapter

Responsible only for invoking installed OpenClaw validation surfaces:

- discover supported config/check/doctor commands from CLI help;
- run supported non-mutating validation against the candidate when the CLI permits an alternate config path;
- record command identity, return code and bounded sanitized error classification;
- never print credentials or raw config.

If the installed CLI cannot validate an alternate config, record that limitation explicitly.

### 4.3 Service controller

Responsible only for:

- pre-mutation Gateway PID/health capture;
- exact config backup;
- atomic candidate activation;
- restart of the existing Gateway only;
- bounded health wait;
- immediate status/journal capture on failure;
- exact rollback and post-rollback health proof.

### 4.4 Runtime inventory verifier

Runs only after Gateway health passes:

- plugin enabled/error count;
- exact three read-only tools;
- exact three typed hooks;
- no write tools;
- routing skill visible to Agent `main`;
- effective tool policy evidence.

### 4.5 Acceptance runner

Runs only after runtime inventory passes:

- direct tool calls;
- native Agent natural-language queue/latest/task prompts;
- exact expected tool-call telemetry;
- no unexpected tools;
- queue/product invariants;
- privacy-safe latency metrics.

### 4.6 Evidence publisher

Responsible only for:

- tri-state check results;
- sanitized JSON/log generation;
- detached-worktree evidence commit;
- remote SHA verification;
- final Summary.

## 5. Required pre-edit scan

Before modifying the diagnostic or enablement source, scan the target files and adjacent modules for:

- duplicate JSON/config parsers;
- duplicate tool-name constants;
- duplicate OpenClaw profile-expansion definitions;
- hardcoded server/port/project/model values;
- oversized modules with mixed policy/process/evidence responsibility;
- existing config-validator and journal-capture helpers.

Reuse authoritative helpers. Do not introduce another parser or service-control implementation if one already exists.

## 6. Candidate policy hypotheses to test

The diagnostic must distinguish, without assuming the answer:

1. whether `tools.profile` and `tools.allow` may coexist in OpenClaw `2026.5.19`;
2. whether group selectors such as `group:fs`, `group:runtime` or `group:web` are valid inside `tools.allow`;
3. whether explicit plugin-tool names in `tools.allow` materialize optional tools;
4. whether `tools.alsoAllow` is accepted together with a materialized `tools.allow`;
5. whether an empty baseline `tools.allow` should remain absent rather than be materialized;
6. whether optional tool activation must be plugin-qualified or use another policy surface;
7. whether any Agent-specific tool policy overrides the global candidate;
8. whether the candidate is rejected by schema validation, plugin initialization or later Gateway startup.

The next code change should be driven by the observed installed-runtime failure, not by another speculative policy combination.

## 7. Sanitized failure evidence

On candidate validation or Gateway failure, evidence may contain:

- validation command name;
- exit code;
- error category;
- JSON field path;
- bounded error message after secret-pattern rejection;
- systemd active/sub state;
- PID presence/change;
- port bind result;
- bounded recent journal line count and hashes/categories;
- rollback result.

Evidence must not contain:

- raw `openclaw.json`;
- token/password/credential values;
- environment files;
- full journal dumps;
- prompts, messages or assistant responses;
- tool arguments or tool results;
- private marker contents.

## 8. Acceptance gates

A successful P0 enablement requires all of the following:

1. candidate accepted by installed OpenClaw runtime;
2. Gateway healthy after controlled restart;
3. public root and restricted routes unchanged;
4. plugin enabled with zero errors;
5. exact three approved read-only tools visible;
6. exact three typed hooks visible;
7. no write tools;
8. routing skill visible to the selected Agent;
9. direct queue/latest/task calls pass;
10. native Agent natural-language prompts invoke each matching typed tool;
11. telemetry includes `model_call_ended`, `after_tool_call` and `agent_end`;
12. telemetry contains no conversation or secret content;
13. queue fingerprint unchanged;
14. product repository unchanged;
15. evidence commit and remote SHA verified.

Any failure restores the tools-denied state.

## 9. Evidence-state semantics

Every post-stage invariant must be one of:

- `PASS`;
- `FAIL`;
- `NOT_CHECKED`.

An early Gateway failure must not emit `false` in a way that implies a write tool appeared or the queue/product changed when the check was never executed.

## 10. Immediate implementation order

1. inspect current enablement/service-control modules for duplicate definitions and existing helpers;
2. add tri-state evidence support;
3. add candidate-config runtime validation discovery;
4. add bounded sanitized Gateway status/journal capture;
5. add regression tests for config rejection and early-abort semantics;
6. run repository target quality gate;
7. run a diagnostic-only workflow first;
8. read evidence from GitHub;
9. only then update and rerun enablement.

## 11. Prohibited shortcuts

- do not reinstall or upgrade OpenClaw;
- do not reinstall the plugin;
- do not manually edit `openclaw.json`;
- do not disable the `coding` profile without runtime evidence and an explicit design update;
- do not expose 18891/18892 publicly;
- do not add submit/cancel/retry tools;
- do not submit a product task;
- do not touch the production host;
- do not ask the user to paste long logs.
