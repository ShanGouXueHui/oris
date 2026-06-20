# Current AI Dev Employee Task

Status: `effective_tool_surface_diagnostic_published_pending_execution`

Task id: `commercial-openclaw-readonly-tool-enable-20260618`

Current step: `diagnose_model_effective_tool_surface_without_model_turns`

## Objective

Determine whether these three approved ORIS tools are actually present in the selected Agent session's model-facing OpenClaw tool inventory:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

A third natural-language enablement attempt is prohibited until this boundary is resolved.

## Latest controlled activation evidence

Evidence commit:

`d5cea6980ad46a51cb4f26f8e6229c11539ea2d5`

Passed before the failure:

- source governance and named automatic selftests;
- private single-scope candidate native dry-run;
- exact validated-config-to-backup hash equality;
- managed routing Skill installation and visibility to Agent `main`;
- single-scope policy activation;
- existing Gateway restart and health;
- exact plugin read-only tool and typed-hook inventory;
- all three direct ORIS read-only calls;
- queue invariance after direct calls.

Three native Agent turns then completed successfully through Gateway in one persisted session:

- all return codes were zero;
- all outputs were structured and present;
- no embedded fallback occurred;
- `model_call_ended=3`;
- `agent_end=3`.

However:

- `after_tool_call=0`;
- no approved tool name was reported;
- no approved tool appeared in telemetry;
- native Agent acceptance failed.

Rollback restored the exact tools-denied config, marker and routing Skill state and left Gateway healthy. No task, product mutation or write tool occurred.

## Unresolved boundary

Direct `/tools/invoke` success proves that the plugin endpoints work. Plugin inventory proves registration. Skill visibility proves instruction visibility.

None of those facts proves that the selected Agent session and runtime model received the ORIS tools in its effective model-facing tool set.

Two explanations remain:

1. the optional ORIS tools were absent from the effective Agent inventory;
2. the tools were present, but the runtime provider/model did not issue tool calls.

## Effective tool surface diagnostic

Authoritative plan:

`docs/DEV_EMPLOYEE_EFFECTIVE_TOOL_SURFACE_DIAGNOSTIC_PLAN_2026-06-20.md`

The new diagnostic uses OpenClaw's native `tools.effective` Gateway RPC. It temporarily activates the already validated read-only policy, inspects the effective inventory for the configured persisted Agent session, then always restores the exact tools-denied baseline.

It retains only:

- effective profile and counts;
- the names of the three approved ORIS tools only;
- whether each approved tool is owned by `oris-dev-employee`;
- safe command fingerprints and invariants.

It does not retain raw RPC output, unrelated tool names, tool descriptions, raw session identifiers, config content, secrets or conversation content.

The diagnostic does not run model turns and does not invoke an ORIS tool.

## Next required action

Run exactly once on the ORIS development/control/execution host:

```bash
cd /home/admin/projects/oris && git pull --ff-only origin main && bash scripts/dev_employee_diagnose_openclaw_effective_tool_surface.sh
```

Do not run `scripts/dev_employee_enable_openclaw_readonly_tools.sh`.

The diagnostic must restore the tools-denied baseline whether the approved tools are present, absent or the RPC fails. Return only the final `===== SUMMARY =====` block. Detailed evidence will be read directly from GitHub.

## Decision after evidence review

- approved tools absent: remediate OpenClaw effective materialization or session-policy resolution;
- approved tools present: diagnose provider/model tool-call capability and Harness routing without hardcoding a provider or model;
- native RPC unavailable: stop and remediate the diagnostic path; do not substitute direct calls or catalog inventory.

## Commercial sequence after P0

1. resolve the effective tool surface or provider/model capability boundary;
2. complete native read-only tool and telemetry acceptance;
3. establish real privacy-safe model/tool/agent latency baselines;
4. design typed write actions with approval, RBAC, project authorization, idempotency and audit;
5. add generic project onboarding and capability discovery;
6. move routine Provider, Model and Policy management to controlled Admin UI;
7. add monitoring, privacy/retention, backup/restore and disaster recovery;
8. add multi-tenant identity, quotas, metering and commercial packaging.
