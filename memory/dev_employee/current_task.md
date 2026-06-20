# Current AI Dev Employee Task

Status: `automatic_selftest_remediation_published_pending_diagnostic_verification`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `verify_selftest_remediation_without_mutation`

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

## Validated candidate baseline

Diagnostic evidence commit:

`2eb0e06c4dee75486e3f3859337867d638941901`

The installed runtime accepted the single-scope private candidate:

- `tools.profile = coding` remains unchanged;
- `tools.allow` is not materialized;
- the three approved tools are added through `tools.alsoAllow` only;
- those tools are removed from `tools.deny`;
- native `config patch --dry-run` passed;
- active config, Gateway, queue and product remained unchanged.

## Controlled activation attempt — failed after direct calls

Evidence commit:

`2c5c33adfd04f2c6a2312465c198aa18ceac41c1`

Result:

`FAILED / AssertionError`

The following stages passed:

- source governance;
- readiness and tools-denied baseline;
- Gateway and route health;
- private listener boundaries;
- queue and product baselines;
- just-in-time candidate dry-run;
- validated-config-to-backup hash equality;
- routing Skill installation and runtime visibility;
- single-scope policy activation;
- Gateway restart and health;
- plugin runtime inventory;
- all three ORIS direct read-only calls;
- queue fingerprint after direct calls.

The failure occurred before the first native Agent acceptance turn. No native Agent telemetry acceptance was reached.

Rollback completed successfully:

- policy restored to the exact tools-denied baseline;
- routing Skill state restored;
- Gateway restarted and remained HTTP healthy;
- rollback failure codes were empty;
- no product task was submitted;
- no write tool was added.

## Root cause

The production policy implementation was correct. The failure was caused by a stale automatic policy selftest that still asserted the removed dual-scope behavior: materializing both `tools.allow` and `tools.alsoAllow`.

The corrected policy deliberately uses only one authorization scope. Therefore the obsolete test assertion raised `AssertionError` after mutation and direct-call checks but before native Agent execution.

The sanitized evidence intentionally did not retain a traceback. The exact root cause was determined by deterministic source-path inspection of `run_native_acceptance -> run_automatic_acceptance -> discover_agent_cli -> run_selftests -> test_profile_tool_policy`.

## Remediation now on `main`

The code now:

1. aligns runtime policy selftests with the single-scope contract;
2. covers profile-plus-`alsoAllow`, existing explicit `allow`, and existing `alsoAllow` baselines;
3. rejects dual non-empty authorization scopes;
4. converts assertion failures into named `AutomaticSelftestFailure` checks;
5. runs all automatic selftests during transaction preflight, before Skill installation, config write or Gateway restart;
6. removes the redundant post-mutation selftest execution from native Agent discovery;
7. includes the same automatic selftests in diagnostic core validation;
8. records blocked later stages as `NOT_CHECKED` rather than reporting a misleading zero count.

Relevant implementation commits:

- `24909447199697410e721e0e62da41fa855c5f58`;
- `bd762cd2354c115368e9c4f8685f433a0ba2ff7c`;
- `2f57bc2b5cc35288a550d9ebebd4cdf994f3c35c`;
- `6d7d0f146a99816cb9fc1046d96eb4bbaa28bdb4`;
- `d72a5a239e486bae6618b31476bf1714543eeac9`;
- `fd6c1926b18ef81ff1f6e28ec2dd165a513654ab`.

## Current blocker

A controlled enablement retry is not yet authorized. The code remediation must first pass one new diagnostic-only run and publish no-mutation evidence.

The active runtime remains on the healthy tools-denied baseline.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

This run is diagnostic-only. It must not:

- execute the enablement entrypoint;
- install the routing Skill;
- replace active config;
- restart Gateway;
- invoke ORIS tools;
- submit a product task;
- add write tools.

It must verify automatic selftests, source governance, native candidate dry-run and final no-mutation invariants. Return only the final `===== SUMMARY =====` block. Detailed evidence will be read from GitHub before any retry decision.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
