# Decision: identify free model routing issue as policy-plan contract drift, not full free API failure

## Date
2026-04-09

## Context
ORIS already has a free model chain, provider secret mapping, runtime execution, and failover behavior.
However, during report generation, the system still selected `openrouter/auto` as `execution_primary`, and earlier had hit `402 Payment Required` before fallback.

## Facts
1. `free_eligibility.json` currently contains:
   - `verified_free_models = ["qwen3.6-plus"]`
2. `runtime_execute.py` already maps secrets for:
   - openrouter
   - gemini
   - zhipu
   - alibaba_bailian
   - tencent_hunyuan
3. Current observed behavior:
   - `free_fallback -> qwen3.6-plus`
   - `cn_candidate_pool -> qwen3.6-plus`
   - `report_generation -> openrouter/auto`

## Decision
Treat the current failure primarily as:
- **policy-plan contract drift**

Do not treat it primarily as:
- universal free provider outage
- universal secret mapping failure
- total failover failure

## Why
Because:
- free chain exists and works for some roles
- failover exists
- the system can already execute `qwen3.6-plus`
- the failure is that some roles still do not obey strict free-only routing

## Required next step
Prioritize:
1. enforce `allow_free_candidates_only` in runtime planning for any role, not just dedicated free role names
2. ensure report-generation style roles do not silently fall back to paid default candidates
3. then extend automatic refresh of free eligibility / scoreboard / health into the pre-execution path
