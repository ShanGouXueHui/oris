# Current AI Dev Employee Task

Status: `diagnostic_patch_dry_run_published_pending_runtime_execution`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `execute_native_config_patch_dry_run_diagnostic`

## Objective

Enable only these three read-only ORIS typed tools through the installed native OpenClaw plugin:

- `oris_queue_status`
- `oris_task_status`
- `oris_latest_task_status`

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

## Completed prerequisites

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- plugin source: `8f174b49196aac90b505846200ce260f75355b41`;
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`;
- readiness: `26/26 PASS`;
- readiness evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`.

Previously proved:

- all three tools pass direct read-only calls;
- Skill `oris-readonly-status` was visible to Agent `main`;
- native Gateway transport and persisted sessions work;
- prior telemetry contained `model_call_ended=3`, `agent_end=3`, `after_tool_call=0`.

Direct invocation and Skill visibility still do not prove model tool materialization or invocation.

## Latest enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The candidate policy was activated, the existing Gateway failed its health gate, and rollback restored the tools-denied baseline. Runtime inventory, direct calls, native Agent acceptance and telemetry acceptance were not reached.

## Diagnostic history

### First run

Evidence commit:

`df9d21839974e4adcc6bde9b62db0fe468b3cc76`

The run stopped safely at the engineering source gate because `skill.py` had 261 lines against a 240-line module limit. Duplicate authorities and hardcoding findings were zero. The Skill implementation was then split into a compatibility facade, installation lifecycle module and runtime inventory module without changing its public API.

### Second run

Evidence commit:

`7c01b72a8ae71c2cbf62a0ae4032ab245b09335c`

Result:

`DIAGNOSTIC_VALIDATOR_UNAVAILABLE`

Checks:

- `9 PASS`;
- `0 FAIL`;
- `7 NOT_CHECKED`.

Passed:

- diagnostic selftests;
- source authority, hardcoding and module-size gate;
- exact tools-denied baseline;
- Gateway PID and HTTP health;
- private candidate build;
- candidate policy and Skill compatibility;
- final Gateway/config invariant;
- queue invariant;
- product invariant.

Candidate facts:

- policy mode: `materialized-profile-plus-approved+created-profile-also-allow+skill-unrestricted`;
- `tools.allow`: 13 entries;
- `tools.alsoAllow`: 3 entries;
- `tools.deny`: 0 entries;
- all candidate compatibility checks passed;
- active config unchanged;
- Gateway not restarted;
- product task not submitted;
- write tools not added.

The installed CLI exposes `config validate` and `config check`, but neither command accepts `--config` or `--config-path`. This was not a policy rejection; those commands simply cannot validate a private candidate path.

## Runtime-compatible dry-run path

Installed runtime:

`OpenClaw 2026.5.19 (a185ca2)`

The matching OpenClaw source and CLI reference define:

```text
openclaw config patch --file <patch> --dry-run
```

This command validates the post-change in-memory configuration and does not write the active config.

ORIS now generates a mode-0600 private patch containing only policy paths changed by the authoritative transforms:

- `tools.profile`;
- `tools.allow`;
- `tools.alsoAllow`;
- `tools.deny`;
- Skill allowlist paths only when changed.

Unrelated tools configuration, Gateway configuration, credentials and Provider/Model configuration are not copied into the patch.

The validator hashes active config before and after the dry run. A result can pass only when the OpenClaw command succeeds and the hash remains unchanged.

Implementation:

- `scripts/dev_employee_openclaw_enable/runtime_policy_patch.py`;
- `scripts/dev_employee_openclaw_enable/runtime_validation.py`;
- `docs/DEV_EMPLOYEE_OPENCLAW_POLICY_DRY_RUN_VALIDATION_ADDENDUM_2026-06-20.md`.

Relevant commits:

- `12392337ba8f33eda5228f3d87e5b6961d255e72`;
- `3a9259c44e2f3f92672a52b85441a15c6a8967a8`;
- `2690501651ca2bd45637460a2dc5d0d9b2ab3501`;
- `061fb475e0f5e7abf4411f71888e81cd74bbabf5`;
- `5452d3faf0c2a27c7991ee85b81545d87f38955d`.

## Current blocker

The candidate has passed ORIS static compatibility checks, but the installed OpenClaw runtime has not yet executed its native `config patch --dry-run` against the minimal policy delta.

Candidate activation remains prohibited until the resulting GitHub evidence is read.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

This remains diagnostic-only. It must not:

- execute the enablement entrypoint;
- replace active config;
- restart Gateway;
- install the routing Skill;
- invoke ORIS tools;
- submit a product task;
- add write tools.

A dry-run `PASS` authorizes evidence review only, not automatic activation.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
