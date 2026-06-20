# ORIS Dev Employee Current State — 2026-06-20

## Current task

Task id:

`commercial-openclaw-readonly-tool-enable-20260618`

Status:

`effective_tool_surface_diagnostic_published_pending_execution`

Current step:

`diagnose_model_effective_tool_surface_without_model_turns`

## Fixed commercial architecture

```text
user
  -> native OpenClaw UI and native sessions
  -> native ORIS plugin / Agent Harness
  -> ORIS task governance and evidence
  -> Codex real code execution
  -> product commit, tests and ORIS evidence returned through OpenClaw
```

Native OpenClaw remains the commercial primary UI. The custom ORIS Web Console remains restricted diagnostics and rollback only.

Do not reinstall or upgrade OpenClaw. Do not reinstall the plugin. Do not expose internal listeners. Do not add write tools in this task. Do not touch production host `8.136.28.6`.

## Installed baseline

- plugin: `oris-dev-employee` `0.1.0`;
- installation result: `INSTALLED_TOOLS_DENIED`;
- runtime tools: `oris_queue_status`, `oris_task_status`, `oris_latest_task_status`;
- runtime hooks: `model_call_ended`, `after_tool_call`, `agent_end`;
- readiness: `26/26 PASS`;
- active product task: none;
- current runtime after rollback: exact healthy tools-denied baseline.

## Latest controlled activation

Evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

Result:

`FAILED / RuntimeError`

Passed before the failure:

- source governance and named automatic selftests;
- private single-scope candidate native dry-run;
- validated configuration and private backup hash equality;
- routing Skill installation and visibility to Agent `main`;
- single-scope policy activation;
- existing Gateway restart and health;
- exact plugin read-only tool and typed-hook inventory;
- direct invocation of all three approved ORIS tools;
- queue invariance after direct calls.

Three native Agent turns completed through Gateway in one persisted session. Every turn returned zero, produced structured output and avoided embedded fallback.

Observed telemetry:

- `model_call_ended=3`;
- `agent_end=3`;
- `after_tool_call=0`;
- approved tools seen: none;
- unexpected tools seen: none.

Native Agent acceptance failed because no tool invocation occurred.

Rollback completed successfully:

- exact tools-denied config restored;
- routing Skill state restored;
- Gateway restarted and remained healthy;
- rollback failure codes: none;
- no product task, product mutation or write tool occurred.

## Current unresolved boundary

Direct typed invocation proves the plugin endpoint works. Plugin inventory proves registration. Skill visibility proves the instructions are visible.

These facts do not prove the three optional plugin tools were present in the selected Agent session's effective model-facing tool inventory.

Two explanations remain:

1. the approved tools were absent from the effective inventory;
2. the approved tools were present, but the runtime provider/model did not issue tool calls.

A third full enablement attempt is prohibited until this distinction is proven.

## Effective tool surface diagnostic

Authoritative plan:

`docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`

Entrypoint:

`scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh`

The diagnostic:

- compiles and re-runs source governance and automatic selftests;
- repeats the private candidate native dry-run;
- temporarily activates only the validated read-only policy;
- calls native Gateway RPC `tools.effective` for the configured persisted Agent session;
- does not run a model turn;
- does not invoke an ORIS tool;
- retains only sanitized effective-inventory counts and the three approved names;
- always restores the exact tools-denied config, marker and Skill state;
- proves final Gateway, queue, product and listener invariants;
- publishes detached-worktree evidence.

## Next action

Run exactly once:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh
```

Do not run `scripts/dev_employee_enable_openclaw_readonly_tools.sh`.

Return only the final `===== SUMMARY =====` block. Detailed evidence will be read from GitHub before choosing the materialization or provider/model remediation path.

## Commercial sequence after P0

1. resolve effective tool materialization or provider/model tool-call capability;
2. complete native read-only tool and telemetry acceptance;
3. establish privacy-safe real model/tool/agent latency baselines;
4. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
5. add generic project onboarding and capability discovery;
6. move routine Provider, Model and Policy management to controlled Admin UI;
7. add monitoring, privacy/retention, backup/restore and disaster recovery;
8. add multi-tenant identity, quotas, metering and commercial packaging.
