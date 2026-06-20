# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`diagnostic_patch_dry_run_published_pending_runtime_execution`

Current step:

`execute_native_config_patch_dry_run_diagnostic`

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

## Installed baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- plugin source: `8f174b49196aac90b505846200ce260f75355b41`;
- installation evidence: `b831470063bc640e498d2061fdaeb2bf8bc9639c`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- readiness evidence: `a63dd823ac4d5b3fa0fa867771f94904d0b4ceee`.

## Historical enablement failure

Evidence commit:

`c68e7d2f50a84f6e68199d2fada9a244f31e4f41`

The dual-stage candidate was activated, the existing Gateway did not pass its health gate, and rollback restored the exact tools-denied baseline. Runtime inventory, direct tool calls, native Agent acceptance and telemetry acceptance were not reached.

This historical result does not authorize another blind activation.

## Diagnostic run 1

Evidence commit:

`df9d21839974e4adcc6bde9b62db0fe468b3cc76`

The run stopped at the engineering source gate because `skill.py` exceeded the 240-line module limit. Duplicate authorities and hardcoding findings were zero. The module was split without changing its public API.

## Diagnostic run 2

Evidence commit:

`7c01b72a8ae71c2cbf62a0ae4032ab245b09335c`

Result:

`DIAGNOSTIC_VALIDATOR_UNAVAILABLE`

Checks:

- 9 PASS;
- 0 FAIL;
- 7 NOT_CHECKED.

Verified:

- diagnostic selftests pass;
- source authority, hardcoding and module-size checks pass;
- exact approved tools remain denied in the active baseline;
- Gateway is active and HTTP healthy;
- candidate is built privately without active mutation;
- candidate profile, allow, alsoAllow, deny, group selectors and Skill visibility are internally valid;
- active config remains unchanged;
- queue remains unchanged;
- product repository remains unchanged;
- Gateway is not restarted;
- no product task is submitted;
- no write tool is added.

The installed CLI exposes `config validate` and `config check`, but neither accepts an alternate candidate path. This is not a policy rejection.

## Native dry-run remediation

Installed runtime:

`OpenClaw 2026.5.19 (a185ca2)`

The matching OpenClaw implementation supports:

```text
openclaw config patch --file <patch> --dry-run
```

ORIS now generates a private mode-0600 patch containing only the actual policy delta. The dry run validates the post-change in-memory config and must leave the active config hash unchanged.

Implementation:

- `scripts/dev_employee_openclaw_enable/runtime_policy_patch.py`;
- `scripts/dev_employee_openclaw_enable/runtime_validation.py`;
- `docs/DEV_EMPLOYEE_OPENCLAW_POLICY_DRY_RUN_VALIDATION_ADDENDUM_2026-06-20.md`.

The patch does not include unrelated Gateway, Provider/Model or credential configuration. Evidence does not include patch content, candidate content or raw CLI output.

## Current blocker

The installed OpenClaw runtime has not yet executed `config patch --dry-run` against the minimal policy delta.

Candidate activation remains prohibited until the next diagnostic evidence is read.

## Next action

Run exactly once on development/control host `43.106.55.255` as user `admin`:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_readonly_policy.sh
```

The run remains diagnostic-only. It must not activate the candidate, replace active config, restart Gateway, install the routing Skill, invoke ORIS tools, submit a product task or add write tools.

Return only the final `===== SUMMARY =====` block. Read detailed evidence from GitHub before any enablement retry.

## Commercial sequence after P0

1. complete native read-only tool and telemetry acceptance;
2. establish real privacy-safe model/tool/agent latency baselines;
3. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
4. add generic project onboarding and capability discovery;
5. move routine Provider, Model and Policy management to controlled Admin UI;
6. add monitoring, privacy/retention, backup/restore and disaster recovery;
7. add multi-tenant identity, quotas, metering and commercial packaging.
