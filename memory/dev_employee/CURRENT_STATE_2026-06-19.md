# ORIS Dev Employee — Current State 2026-06-19

## 1. Executive state

ORIS is in the P0 commercialization phase for native OpenClaw read-only status tools.

The commercial primary interface is the native OpenClaw UI and native session system at:

`https://control.orisfy.com`

The approved chain remains:

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness policy adapter
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

The custom ORIS Web Console is not the commercial main UI. It remains restricted to `/admin` and rollback/diagnostic paths.

## 2. Fixed product decisions

These decisions are not open for routine redesign:

1. Native OpenClaw is the commercial UI and conversation/session system.
2. Do not reinstall or upgrade OpenClaw during the current task.
3. Reuse `openclaw-gateway.service` on `127.0.0.1:18789`.
4. ORIS integrates through stable typed tools/actions/plugins, not broad prompt keyword matching.
5. `127.0.0.1:18891` and `127.0.0.1:18892` remain loopback-only.
6. Product code, tests and product documentation stay in product repositories.
7. `main` is the only mainstream branch.
8. The current task authorizes read-only status tools only. No submit, cancel, retry or other write tool may be added.

## 3. Completed capabilities

### 3.1 Native OpenClaw UI migration

Completed and browser-accepted:

- native OpenClaw root UI;
- token-authenticated access;
- new conversations;
- multiple sessions;
- session history switching;
- refresh persistence;
- session deletion while preserving another session;
- restricted `/admin` and `/_oris-chat-shell` paths.

### 3.2 Final acceptance product

Repository:

`ShanGouXueHui/oris-final-acceptance-api`

Local path:

`/home/admin/projects/oris-final-acceptance-api`

Completed product commit and remote `main`:

`bcb93e17ea88704548101f5e4a5c460e15a80ec7`

Do not reopen this product task without regression evidence.

### 3.3 Native ORIS plugin

Installed plugin:

- id: `oris-dev-employee`
- version: `0.1.0`
- installed source commit: `8f174b49196aac90b505846200ce260f75355b41`
- artifact SHA-256: `976377c2e5ffbf6932d5e43bed17c4d07cfcb16fefb7383b5ab593d4ed1eecda`
- installation evidence commit: `b831470063bc640e498d2061fdaeb2bf8bc9639c`

Runtime-verified read-only tools:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

Runtime-verified typed hooks:

- `model_call_ended`
- `after_tool_call`
- `agent_end`

Plugin errors were zero at the verified installed baseline. Scoped `allowConversationAccess=true` is enabled only for `oris-dev-employee`, because OpenClaw requires it for the non-bundled `agent_end` hook.

## 4. Current active task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Current status:

`blocked_after_dual_stage_policy_gateway_health_failure_rollback_complete`

Current step:

`diagnose_gateway_rejection_of_dual_stage_readonly_policy_before_retry`

Objective:

Enable only the three approved read-only ORIS tools in native OpenClaw, prove natural-language tool use and privacy-safe telemetry, and preserve automatic rollback to the tools-denied baseline.

## 5. Readiness and quality progress

### 5.1 Read-only readiness

Readiness completed with 26/26 checks passing.

- result: `READY`
- evidence commit: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`
- evidence JSON: `logs/dev_employee/openclaw_readonly_tool_readiness/openclaw-readonly-tool-readiness-20260618T212757Z.json`

The readiness run made no config changes, did not restart Gateway, did not enable tools and did not submit a product task.

### 5.2 Repository quality work

The first scanner produced 6030 findings, dominated by generated/runtime artifacts and scanner-policy noise. The scanner and triage policy were corrected.

Latest observed repository scan state:

- total findings: `865`
- active remediation target gate: `PASS`
- active target findings: `0`

The 865 repository findings are not equivalent to 865 current blocking defects. They include legacy operational-script findings outside the active P0 remediation scope. They remain technical debt and must not be reported as fully resolved.

The mandatory engineering rule is now:

- before editing a file, scan the target scope for duplicate definitions and duplicated authoritative rules;
- check for hardcoded environment, project, host, port, branch, provider, model, credential or acceptance-only values;
- shared code may not introduce hardcoded acceptance-project behavior;
- large files must be split by responsibility before further growth.

## 6. Enablement attempts and corrected conclusions

### 6.1 Direct plugin tools work

Multiple controlled runs proved that direct invocation of all three read-only tools succeeds against the loopback ORIS status API and returns contract-valid sanitized results.

This proves the plugin tool implementation and ORIS status endpoints work. It does not by itself prove that the model receives and invokes the tools.

### 6.2 Skill routing works

The managed routing skill `oris-readonly-status` was installed and shown as runtime-visible to Agent `main` during controlled runs.

The skill is:

- model-visible;
- not user-invocable;
- always included;
- explicit that live status requests must use the matching typed tool;
- prohibited from falling back to exec, shell, filesystem, browser or direct HTTP.

Skill visibility alone did not produce tool calls.

### 6.3 Model calls originally had no tool calls

Evidence commits including `dd74d4db2b20e185c6f1492c550c3fa6a7f13db1` and `2564ac3f47c1fdebb985084964e4aacaa57f81c1` showed:

- `model_call_ended=3`;
- `agent_end=3`;
- `after_tool_call=0`;
- no approved ORIS tool observed in model output or telemetry.

This established that prompt/skill visibility was not the only issue. Tool policy had to be evaluated at both optional-plugin materialization and profile authorization stages.

### 6.4 Dual-stage authorization implementation

The current source implementation applies a reversible dual-stage policy:

1. materialization stage: `tools.allow` receives the configured coding-profile expansion plus the three approved ORIS tools when no allowlist previously existed, or only the approved tools when an allowlist already existed;
2. profile stage: `tools.alsoAllow` receives the three approved ORIS tools;
3. deny stage: only the three approved names are removed from `tools.deny`;
4. all unrelated config must remain identical after the authorized additions are stripped;
5. failure restores the exact prior tools-denied configuration.

Relevant source commits:

- `741f24687c751ebfa405d8ea74c8a45a53a09161` — dual-stage profile/materialization policy model;
- `0182858e58fefdb267f7cb3cf8b76bf6a8064323` — policy application and rollback validation;
- `c48a8741645cfd57ba24530a6dc4da767612568a` — regression tests;
- `d650a0f9e4686df4b46157ace680e9bb08e396ff` — privacy-safe provider/model diagnostics.

## 7. Latest execution result

Latest controlled execution:

- result: `FAILED`
- failure: `RuntimeError:existing OpenClaw Gateway did not become healthy`
- evidence commit: `c68e7d2f50a84f6e68199d2fada9a244f31e4f41`
- evidence JSON: `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260619T200933Z.json`

The run reached:

- readiness verification;
- tools-denied baseline verification;
- Gateway/public route precheck;
- private listener checks;
- queue and product baseline checks;
- private backup;
- routing skill installation;
- dual-stage policy materialization.

The policy evidence recorded:

- mode: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`;
- `tools.allow`: 13 authorized entries after materializing the configured coding profile plus the 3 ORIS tools;
- `tools.alsoAllow`: 3 ORIS tools;
- skill target: Agent `main`, unrestricted skill policy.

After applying this candidate config, the existing Gateway did not become healthy. The run failed before runtime plugin inspection, direct tool calls or native Agent acceptance.

Rollback completed successfully:

- rollback count: `1`;
- rollback healthy: `YES`;
- no product task submitted;
- no write tool added;
- no secret printed;
- no OpenClaw reinstall or upgrade.

Current runtime must therefore be treated as restored to the prior tools-denied baseline.

Important evidence interpretation correction:

Fields such as `direct_tool_calls_pass=false`, `write_tools_absent=false`, `queue_unchanged=false` and `product_unchanged=false` in this early-abort evidence mean those post-mutation checks were not reached. They are not evidence that write tools appeared, the queue changed or the product changed. The explicit safety fields and healthy rollback remain authoritative for what the failed run did.

## 8. Current blocker

The P0 blocker is no longer read-only readiness, plugin installation, skill visibility or direct tool implementation.

The blocker is:

`The candidate dual-stage OpenClaw tool policy causes the existing Gateway to fail its post-restart health gate, and the sanitized evidence does not yet capture the exact config-validation or service-journal reason.`

Do not rerun the same enablement workflow blindly.

## 9. Next minimum safe action

Before another enablement attempt, create a GitHub-hosted diagnostic/remediation update that:

1. reproduces the candidate policy in a private temporary config without replacing the active config;
2. runs every available OpenClaw config/schema validation command against the candidate where supported;
3. verifies whether `tools.profile`, `tools.allow` and `tools.alsoAllow` may coexist in OpenClaw `2026.5.19` and whether group/profile expansion entries are accepted in `tools.allow`;
4. scans the candidate for duplicate tool entries and unsupported/hardcoded values;
5. records the existing Gateway PID and health before mutation;
6. if a controlled restart is attempted, captures sanitized `systemctl status` and bounded `journalctl` diagnostics immediately on failure;
7. records only error class, field path, exit status and bounded non-secret messages;
8. restores the exact tools-denied config and proves Gateway health;
9. does not invoke a product task or any write tool;
10. commits sanitized evidence through a detached worktree and prints one final Summary.

The next implementation must not guess that dual-stage authorization is valid merely because the Python-side policy tests pass. It must validate against the installed OpenClaw runtime before restart.

## 10. Environment truth

### Hosts

- ORIS development/control/execution host: `43.106.55.255`, user `admin`
- ORIS repository: `/home/admin/projects/oris`
- separate production host: `8.136.28.6`, user `deploy`
- production rule: do not touch without an explicit production/deployment task

### Services and ports

- native OpenClaw Gateway: `openclaw-gateway.service`, `127.0.0.1:18789`
- ORIS enqueue/status: `127.0.0.1:18891`
- ORIS intake: `127.0.0.1:18892`
- ORIS Web Console: `127.0.0.1:18893`
- supervised bridge: `oris-dev-employee-bridge.service`

### Runtime

- OpenClaw: `2026.5.19 (a185ca2)`
- Node: `v22.22.2`
- npm: `10.9.7`
- Codex CLI: real coding executor

### Storage and database

- Dev Employee queue/state: filesystem-backed, transaction-hardened
- intentional evidence: `logs/dev_employee/`
- durable context: `memory/dev_employee/` and `docs/`
- project registry: `orchestration/project_registry.json`
- separate insight/research database: PostgreSQL `oris_insight`, schema `insight`
- latest database security workflow result: `ALREADY_SECURE_AND_VERIFIED`
- latest database evidence commit: `bc799a640138a19800270ecab1a656f09d70252a`

The insight database is not the Dev Employee task-state database and must remain decoupled unless a separate architecture decision changes that.

### Models and providers

- OpenClaw owns conversation/model execution;
- Codex CLI owns real code execution;
- model/provider availability, identity, quota, latency and price are runtime facts and must be probed rather than hardcoded;
- telemetry may record bounded provider/model identifiers, but never prompts, responses, tool arguments, tool results or credentials;
- ZenMux remains excluded unless the user explicitly reopens it.

## 11. Working and interaction contract

- use Chinese, professional, direct and structured communication;
- do not delegate routine engineering decisions to the user;
- write long scripts, patches and documents directly to GitHub;
- give the user one short pull-and-run command;
- do not provide long heredocs because terminal input can be truncated;
- write detailed logs under `logs/dev_employee/` and inspect them from GitHub;
- every user-run script ends with exactly one `===== SUMMARY =====` block;
- the user sends only the Summary;
- never print or commit tokens, passwords, keys, credentials, private marker contents or raw config;
- user-facing shell scripts must not use `set -e`;
- use detached worktrees for evidence commits when needed;
- do not append to a tracked evidence log after its commit;
- maintain one mainstream branch: `main`;
- backups are allowed, competing long-lived branches are not;
- preserve layered decoupling, configuration separation and one authoritative source per rule;
- build generic commercial mechanisms, never acceptance-project special cases;
- before editing, scan for duplicate definitions and hardcoded values;
- split large files by responsibility;
- completion requires actual deliverables, tests, commit SHA, remote SHA and durable evidence.

## 12. Commercial priority order

1. Diagnose and resolve the Gateway rejection of the candidate read-only policy.
2. Complete direct and native natural-language acceptance of exactly three read-only tools.
3. Establish privacy-safe model/tool/agent latency telemetry from real samples.
4. Only after P0 passes, design explicit typed write actions with approval, project authorization, idempotency and audit.
5. Add generic project onboarding and capability discovery.
6. Move routine provider/policy management into controlled Admin UI.
7. Complete monitoring, retention/privacy, backup/restore and disaster-recovery gates.
8. Add multi-tenant identity, quotas, metering and commercial packaging.
