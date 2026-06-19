# ORIS Dev Employee — Session Archive 2026-06-19

## Purpose

This archive captures the continuation of the ORIS/OpenClaw commercialization work after the native plugin installation completed on 2026-06-18.

It records the quality scan, readiness verification, repeated controlled enablement attempts, policy corrections, evidence interpretation and the latest Gateway-health blocker.

Current operational truth is in:

- `memory/dev_employee/CURRENT_STATE_2026-06-19.md`
- `memory/dev_employee/current_task.json`
- `memory/dev_employee/current_task.md`

Historical failed evidence must remain unchanged.

## Starting state

The session started from this verified baseline:

- native OpenClaw UI was the commercial main UI;
- `oris-dev-employee` `0.1.0` was installed and enabled;
- runtime tools were exactly `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime typed hooks were exactly `model_call_ended`, `after_tool_call`, `agent_end`;
- plugin error count was zero;
- all three ORIS tools were in `tools.deny`;
- write tools were absent;
- scoped conversation access was enabled only for the ORIS plugin;
- Gateway authentication was token-based;
- OpenClaw was not to be reinstalled or upgraded;
- the completed product baseline was `bcb93e17ea88704548101f5e4a5c460e15a80ec7`.

The active task was to enable only the three read-only tools, prove native natural-language use, and establish latency/privacy telemetry.

## User-required engineering corrections

During the session the user established additional mandatory rules:

1. Normal interaction must complete automatically; it must not merely print a command for a human to copy into the conversation flow.
2. Required skills may be installed, upgraded or removed when justified, but daily engineering details are decided automatically.
3. The entire ORIS engineering tree must be checked for duplicate definitions and hardcoded behavior.
4. Before modifying any file, scan the relevant scope for duplicate definitions and existing authoritative implementations.
5. Hardcoded environment, project, host, port, provider, model, branch, credential or acceptance-only behavior is prohibited in shared code.
6. Large files must be split into layered modules with clear responsibilities.
7. Long scripts and documents go directly to GitHub; terminal heredocs are avoided.

These rules are now formalized in the 2026-06-19 engineering-standard addendum.

## Repository quality scan sequence

### Initial scanner failure

The first repository-wide quality scan reported:

- files scanned: 471
- findings: 6030
- result: scanner execution failure, then findings after rerun

Evidence commits included:

- `6111bec8562e39d124023e65396d974f5a5a1940`
- `8d57908857dba0b07ae511f996f7fb7105f11f59`

Triage identified:

- generated/runtime artifact findings: 1505
- initially actionable engineering findings: 4525

The count was not accepted at face value because scanner policy incorrectly treated generated/runtime evidence and legacy operational artifacts as current source defects.

### Scanner-policy correction

After correcting scanner exclusions and triage policy, a rescan produced:

- scan findings: 831
- generated/runtime artifact findings: 0
- legacy operational-script findings: 465
- actionable engineering findings: 366
- scan evidence commit: `dbd1a41ace26ffcc8a145be057dddcc44789973f`
- triage evidence commit: `b2ee7b10f196b8bf82927364946c49d3009fef85`

Later orchestration summaries reported 865 repository findings while the active remediation target quality gate passed with zero findings.

Correct interpretation:

- the full repository still contains legacy quality debt;
- the active OpenClaw enablement source scope passed its target gate;
- the full 865 count must not be described as fully fixed;
- generated/runtime noise must not be reintroduced into source-quality counts.

## Read-only readiness

A read-only readiness workflow was created and run before any enablement mutation.

Final readiness result:

- result: `READY`
- checks: 26/26 pass
- config mutated: no
- Gateway restarted/reloaded: no
- tools enabled: no
- product task submitted: no
- write tools present: no
- evidence commit: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`

The readiness evidence verified:

- private install marker and backup;
- config ownership/mode and token-auth presence without reading secret values;
- exact plugin tools and typed hooks;
- zero plugin errors;
- exact tools-denied baseline;
- scoped conversation-access policy;
- Gateway/public root/restricted routes;
- loopback-only 18891, 18892 and 18893 listeners;
- telemetry location, rotation and content-safety contract;
- zero active tasks and queue fingerprint;
- product HEAD, remote main and clean worktree;
- no write tool and no task submission;
- no config or Gateway PID drift.

## Preflight and source-worktree failures

The automatic orchestrator initially failed preflight because the ORIS source worktree contained many generated task-run and event artifacts.

The first dirty count was 33. After runtime-artifact cleanup and policy correction it reduced to 8, then to 0.

Evidence included:

- preflight evidence commit `3e348b0d09ecffa3cb8e2bc3354c768379dcd5b9`

The durable lesson is:

- runtime-generated artifacts must be ignored or intentionally promoted;
- source preflight must distinguish runtime drift from source drift;
- a clean main source worktree is required before controlled platform mutation;
- detached worktrees are used for evidence commits.

## Database security workflow

The orchestration also ran the insight database credential-security workflow.

The database was already secure on later runs, so credentials were not repeatedly rotated.

Latest session result:

- `ALREADY_SECURE_AND_VERIFIED`
- latest evidence commit: `bc799a640138a19800270ecab1a656f09d70252a`

The PostgreSQL `oris_insight` database and `insight` schema remain separate from the Dev Employee task-state system.

## First enablement and browser acceptance failure

The first reversible enablement run passed direct tool checks but failed browser/native natural-language acceptance.

Representative evidence:

- result: failed
- failure: browser natural-language acceptance timeout or failure
- direct tool calls: pass
- browser acceptance: fail
- rollback healthy: yes
- evidence commit: `4a4610b13094a7299e51e171cbfe51af01ceac23`

This exposed the need for fully automatic native-agent acceptance rather than printing browser commands for the operator.

## Automatic native-agent acceptance implementation

The workflow was changed to run native OpenClaw Agent turns automatically through the existing Gateway.

It added:

- automatic CLI capability discovery;
- explicit Agent `main` targeting where supported;
- one persisted native session;
- structured JSON output parsing;
- Gateway-fallback rejection;
- telemetry correlation using hashed session/run identifiers;
- privacy and file-mode checks;
- automatic rollback on any failure.

## Skill installation and routing investigation

A managed skill `oris-readonly-status` was added.

Its contract:

- model-visible;
- not user-invocable;
- always included in the agent prompt;
- live queue requests map to `oris_queue_status`;
- live latest-task requests map to `oris_latest_task_status`;
- named task requests map to `oris_task_status`;
- no exec, shell, filesystem, browser or direct HTTP fallback;
- no write action.

The workflow was updated to:

- install the skill atomically;
- remove higher-priority shadow copies;
- validate frontmatter and tool names;
- resolve the default Agent;
- update an existing Agent skill allowlist only when required;
- verify skill runtime visibility through OpenClaw skill inventory;
- back up and restore skill paths transactionally.

Evidence later proved:

- routing skill runtime visible: yes
- Agent: `main`
- `after_tool_call`: still zero

Therefore skill visibility was necessary but insufficient.

## Telemetry evidence: model answered without tools

Repeated automatic acceptance evidence showed:

- three successful model calls;
- three successful agent ends;
- zero `after_tool_call` events;
- no ORIS tools reported in structured output;
- persisted native session present;
- no embedded fallback;
- privacy/schema checks otherwise safe.

Key evidence commits:

- `cbe95ee2d9b4241e5a8ade39e2404af32bedfab0`
- `a2fbf2248ef71a47ddd1396ecb77a8093183464f`
- `dd74d4db2b20e185c6f1492c550c3fa6a7f13db1`
- `2564ac3f47c1fdebb985084964e4aacaa57f81c1`

This established that the model was not receiving or invoking the ORIS typed tools even though:

- the plugin registered them;
- direct calls succeeded;
- the routing skill was visible;
- the Gateway and native Agent transport worked.

## OpenClaw optional-tool and profile-policy investigation

The plugin manifest and registration mark the three ORIS tools as optional.

The investigation separated two policy stages:

1. optional plugin tool materialization;
2. active profile authorization.

### First policy shape

An earlier attempt used explicit allow behavior but did not correctly preserve/extend the active `coding` profile. It still produced no model tool calls.

### Second policy shape

The next attempt used:

- `tools.profile=coding`
- `tools.alsoAllow=[three ORIS tools]`
- removal of the three names from `tools.deny`

Evidence commit `2564ac3f47c1fdebb985084964e4aacaa57f81c1` showed:

- policy application passed;
- skill visible;
- direct calls passed;
- three model turns completed;
- `after_tool_call=0`.

The conclusion was that profile extension alone did not reliably materialize optional plugin tools in the installed runtime.

## Dual-stage authorization implementation

The policy implementation was refactored into a dedicated module and covered by regression tests.

Current intended candidate policy:

- if no `tools.allow` exists, materialize the configured `coding` profile expansion plus the three approved ORIS tools into `tools.allow`;
- if an allowlist exists, preserve it and append only missing approved ORIS tools;
- append the three tools to `tools.alsoAllow`;
- remove only the three tools from `tools.deny`;
- preserve all unrelated config;
- restore the exact original config on failure.

Source commits:

- `741f24687c751ebfa405d8ea74c8a45a53a09161`
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323`
- `c48a8741645cfd57ba24530a6dc4da767612568a`

Telemetry was also extended to persist only bounded provider/model identifiers for future diagnostics:

- commit: `d650a0f9e4686df4b46157ace680e9bb08e396ff`

No prompt, assistant text, tool argument/result, header, token or credential is recorded.

## Latest failure: candidate config prevented Gateway health

Latest execution summary:

- result: failed
- failure code: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- selected policy mode: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`
- rollback count: 1
- rollback healthy: yes
- no product task submitted
- no write tools added
- no secrets printed
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The run proved the candidate policy was generated as intended:

- 13 `tools.allow` entries after materializing the configured coding profile and ORIS tools;
- 3 `tools.alsoAllow` entries;
- Agent `main` skill policy unrestricted.

But the existing Gateway failed to become healthy after the candidate config was activated.

The failure occurred before:

- runtime skill visibility check;
- runtime plugin inventory;
- direct tool calls;
- native Agent natural-language turns;
- telemetry acceptance;
- final queue/product invariant checks.

Rollback restored service health and the tools-denied baseline.

## Evidence interpretation correction

The latest JSON records several booleans as false because execution stopped early:

- `direct_tool_calls_pass=false`
- `write_tools_absent=false`
- `queue_unchanged=false`
- `product_unchanged=false`

These values are not proof of a mutation or security regression. They mean those checks were not reached before the exception.

The explicit safety record is authoritative:

- product task submitted: false
- write tools added: false
- OpenClaw reinstalled/upgraded: false
- secret values recorded: false
- rollback healthy: yes

Future evidence schemas should distinguish `false` from `not_checked` where an early abort is possible.

## Current blocker and next diagnostic

The current blocker is the installed OpenClaw runtime rejecting or failing under the dual-stage candidate tool policy.

The exact rejection reason is not present in sanitized evidence.

The next action is not another blind enablement retry. It is a diagnostic update that:

1. builds the candidate config privately;
2. validates it against the installed OpenClaw runtime before replacement;
3. scans for duplicate entries and unsupported schema combinations;
4. identifies whether `profile`, `allow`, `alsoAllow`, group selectors and explicit plugin tools may coexist in this OpenClaw version;
5. captures bounded sanitized Gateway status/journal output on failure;
6. restores the exact tools-denied config;
7. proves Gateway health and private listener invariants;
8. commits evidence from a detached worktree.

## Durable technical conclusions

1. Direct tool success does not prove model tool availability.
2. Skill visibility does not prove tool materialization.
3. Optional plugin-tool materialization and profile authorization must be treated as distinct runtime stages.
4. Python-side config-diff tests do not replace validation by the installed OpenClaw runtime.
5. A service restart health failure must capture config-validator and journal evidence before rollback erases the failing runtime context.
6. Early-abort evidence must use tri-state or explicit `not_checked` semantics.
7. Rollback health is a first-class acceptance gate.
8. Do not reinstall OpenClaw or the plugin to work around a policy/configuration defect.

## Environment and operating contract retained

- ORIS host: `43.106.55.255`, user `admin`;
- ORIS path: `/home/admin/projects/oris`;
- production host `8.136.28.6`, user `deploy`, untouched without an explicit production task;
- OpenClaw Gateway: `127.0.0.1:18789`;
- enqueue/status: `127.0.0.1:18891`;
- intake: `127.0.0.1:18892`;
- Web Console: `127.0.0.1:18893`;
- Codex CLI is the real coding executor;
- PostgreSQL `oris_insight`, schema `insight`, remains separate research storage;
- long changes go directly to GitHub;
- user executes one short GitHub-hosted script command;
- detailed logs are inspected from GitHub;
- no `set -e` in user-facing scripts;
- one final Summary per script;
- no secrets in logs or chat;
- `main` is the only mainstream branch;
- backups allowed, competing long-lived branches prohibited;
- generic commercial design, layered decoupling and configuration separation are mandatory.
