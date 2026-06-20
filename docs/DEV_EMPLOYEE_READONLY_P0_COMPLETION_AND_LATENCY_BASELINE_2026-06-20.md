# Dev Employee Read-only P0 Completion and Latency Baseline — 2026-06-20

## 1. Decision

The native OpenClaw read-only P0 is complete and accepted.

Authoritative evidence commit:

`65217d4bb81f4ac3cd8c6d917af95425d2b47529`

Evidence files:

- `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260620T213307Z.json`;
- `logs/dev_employee/openclaw_readonly_tool_enablement/openclaw-readonly-automatic-enablement-20260620T213307Z.log`.

Result:

`ENABLED_READONLY_AUTOMATIC_ACCEPTED`

Check result:

- total: 26;
- pass: 26;
- fail: 0;
- not checked: 0.

## 2. Accepted business capabilities

The only accepted ORIS business tools are:

- `oris_queue_status`;
- `oris_task_status`;
- `oris_latest_task_status`.

All three were:

- present in the native effective surface;
- owned by Plugin `oris-dev-employee`;
- directly invokable;
- invoked through native OpenClaw natural language;
- correlated to a persisted native session;
- successful in privacy-safe typed-hook telemetry.

## 3. Native support tool boundary

One native `read` call was accepted only as bounded Skill hydration support.

Contract:

- maximum one call;
- must occur before the first ORIS business-tool call;
- must succeed;
- is not an ORIS business capability;
- does not expand the effective tool surface;
- does not authorize arbitrary filesystem fallback.

Every undeclared, excessive, failed, late, overlapping or write-capable support tool remains rejected.

## 4. Retained runtime state

The validated read-only policy was retained.

Policy mode:

`profile-authority-preserved+created-profile-also-allow+skill-unrestricted`

Tool-policy facts:

- `tools.profile` authority preserved;
- `tools.allow` remains absent;
- exactly three ORIS tools were added through profile `alsoAllow`;
- single authorization scope validated.

Routing Skill:

- name: `oris-readonly-status`;
- installed: yes;
- agent: `main`;
- runtime-visible: yes.

Rollback:

- count: 0;
- status: not required.

## 5. Final invariants

The accepted run verified:

- Gateway healthy;
- native public route healthy;
- internal ORIS listeners loopback-only;
- Free Mesh protocol version 2 with tool calling;
- queue unchanged;
- active task count remained zero;
- product repository unchanged;
- ORIS source worktree invariant passed;
- write tools absent;
- no product task submitted;
- no OpenClaw reinstall or upgrade;
- no secrets, prompts, conversation content, tool arguments/results or raw session identifiers recorded.

## 6. Initial latency baseline v1

### 6.1 Model duration

| Metric | Value |
|---|---:|
| Samples | 8 |
| Minimum | 2,661 ms |
| P50 | 5,478 ms |
| Maximum | 49,734 ms |

### 6.2 Agent total duration

| Metric | Value |
|---|---:|
| Samples | 3 |
| Minimum | 8,538 ms |
| P50 | 9,029 ms |
| Maximum | 69,134 ms |

### 6.3 ORIS tool duration

| Tool | Samples | Minimum | P50 | Maximum |
|---|---:|---:|---:|---:|
| `oris_queue_status` | 1 | 13 ms | 13 ms | 13 ms |
| `oris_task_status` | 1 | 42 ms | 42 ms | 42 ms |
| `oris_latest_task_status` | 2 | 13 ms | 27 ms | 41 ms |

### 6.4 Native support tool duration

| Tool | Samples | Minimum | P50 | Maximum |
|---|---:|---:|---:|---:|
| `read` | 1 | 92 ms | 92 ms | 92 ms |

## 7. Baseline interpretation

- ORIS read-only tool execution is millisecond-scale.
- Model and Agent orchestration dominate observed end-to-end latency.
- `oris_latest_task_status` had two attempts in the accepted run; both were non-failed and the overall execution outcome passed.
- TTFT is unavailable because the approved typed hooks do not expose a first-token timestamp.
- Observed provider/model identifiers are bounded runtime facts only and are not configuration authority.
- This dataset is an initial observed baseline, not an SLO or SLA.

## 8. Future measurement requirements

A commercial latency baseline must later add:

- repeated accepted samples over time;
- cold/warm separation where observable without privacy loss;
- per provider/model runtime-fact grouping without hardcoding;
- Agent total duration percentiles beyond P50;
- tool error and retry rates;
- queue wait, executor start and product-delivery duration for write tasks;
- load/concurrency dimensions;
- cost and token metrics only through approved bounded telemetry;
- retention limits and aggregation windows;
- alerts based on SLOs, not one-run maxima.

TTFT may be added only if a supported typed hook exposes a safe first-token timestamp. It must not be reconstructed from conversation content or raw streaming traces.

## 9. Completion statement

The following original commercialization items are complete:

- effective tool materialization;
- provider/model tool-call capability diagnosis;
- Agent Harness ORIS routing;
- native three-tool natural-language acceptance;
- approved-only typed-hook telemetry acceptance;
- persistent read-only P0 enablement;
- initial privacy-safe latency baseline.

Write actions remain absent and unauthorized.
