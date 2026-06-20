# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`automatic_selftest_remediation_published_pending_diagnostic_verification`

Current step:

`verify_selftest_remediation_without_mutation`

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

## Installed and safety baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- no write tool is authorized;
- no product task is active;
- production host remains untouched.

## Accepted single-scope candidate

Diagnostic evidence:

`2eb0e06c4dee75486e3f3859337867d638941901`

The installed OpenClaw runtime accepted the private candidate through native `config patch --dry-run`:

- authorization scope: `profile-plus-alsoAllow`;
- `tools.allow=0`;
- `tools.alsoAllow=3`;
- patch paths: `tools.alsoAllow`, `tools.deny`;
- schema and resolvability checks passed;
- active config, Gateway, queue and product remained unchanged.

## Latest controlled activation attempt

Evidence commit:

`2c5c33adfd04f2c6a2312465c198aa18ceac41c1`

Result:

`FAILED / AssertionError`

Passed before failure:

- source governance;
- readiness and tools-denied baseline;
- Gateway/public/restricted route health;
- loopback-only internal listeners;
- queue and product baselines;
- just-in-time native candidate dry-run;
- exact validated-config-to-backup hash match;
- routing Skill installation and visibility to Agent `main`;
- single-scope policy activation;
- controlled Gateway restart and HTTP health;
- exact plugin tool and typed-hook inventory;
- safe built-in direct probe;
- all three ORIS direct read-only calls;
- queue fingerprint after direct calls.

Native Agent acceptance and telemetry acceptance were not reached.

Rollback result:

- rollback count: 1;
- rollback healthy: yes;
- exact tools-denied policy restored;
- routing Skill state restored;
- Gateway restarted and remained healthy;
- rollback failure codes: none;
- no task submission, product mutation or write tool occurred.

## Root cause

The runtime policy implementation was correct. The failure came from a stale automatic policy selftest that still expected the obsolete dual-scope transform which materialized both non-empty `tools.allow` and `tools.alsoAllow`.

The current policy deliberately preserves one authorization scope only. The obsolete assertion therefore raised `AssertionError` in this deterministic path:

```text
run_native_acceptance
  -> run_automatic_acceptance
  -> discover_agent_cli
  -> run_selftests
  -> test_profile_tool_policy
```

The evidence intentionally retained no traceback or conversation content. The root cause was determined by source-path inspection against the exact evidence boundary.

## Remediation now on `main`

The code now:

- aligns automatic policy selftests with the single-scope contract;
- covers profile-plus-`alsoAllow`, existing explicit-`allow`, and existing-`alsoAllow` baselines;
- retains negative coverage for dual scopes and duplicate entries;
- converts failures into named `AutomaticSelftestFailure` results;
- executes automatic selftests during transaction preflight before any mutation;
- removes post-mutation selftest reruns from Agent CLI discovery;
- executes the same automatic tests in the diagnostic core gate;
- records blocked later stages as `NOT_CHECKED` in future failure evidence.

Implementation commits:

- `24909447199697410e721e0e62da41fa855c5f58`;
- `bd762cd2354c115368e9c4f8685f433a0ba2ff7c`;
- `2f57bc2b5cc35288a550d9ebebd4cdf994f3c35c`;
- `6d7d0f146a99816cb9fc1046d96eb4bbaa28bdb4`;
- `d72a5a239e486bae6618b31476bf1714543eeac9`;
- `fd6c1926b18ef81ff1f6e28ec2dd165a513654ab`.

## Current blocker

The first controlled activation authorization was consumed. A retry is not authorized until one new diagnostic-only run verifies the remediation and its GitHub evidence is reviewed.

The runtime is currently healthy on the exact tools-denied baseline.

## Next action

Run exactly once on development/control host `43.106.55.255` as user `admin`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

This is diagnostic-only. It must re-pass automatic selftests, source governance, native candidate dry-run and final no-mutation invariants. It must not execute enablement, install the Skill, replace active config, restart Gateway, invoke ORIS tools, submit a task or add write tools.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read from GitHub before any controlled retry decision.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
