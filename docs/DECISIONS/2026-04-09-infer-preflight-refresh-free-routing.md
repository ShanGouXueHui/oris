# Decision: make infer preflight refresh active routing and free pool before execution

## Date
2026-04-09

## Context
ORIS free routing was available but not consistently applied to `report_generation`.
The root cause was that `oris_infer.py` refreshed `runtime_plan.py` only, without first refreshing `model_selector.py` output (`active_routing.json`).
As a result, stale routing could keep `report_generation` on `openrouter/auto`.

## Final fix
`oris_infer.py` now performs:

### Preflight
- `quota_probe.py` (best-effort)
- `provider_scoreboard.py` (best-effort)
- `model_selector.py` (required)
- `runtime_plan.py` (required)

### Execute
- `runtime_execute.py`

### Postflight
- refresh the same chain again in best-effort mode
- capture warnings instead of failing an already successful request

## Verified result
Manual smoke confirms:
- `report_generation -> qwen3.6-plus`
- provider -> `alibaba_bailian`
- `preflight_warnings = []`
- `post_refresh_warnings = []`

## Impact
This turns the free model chain from manual correction into automatic routing refresh at inference time.
