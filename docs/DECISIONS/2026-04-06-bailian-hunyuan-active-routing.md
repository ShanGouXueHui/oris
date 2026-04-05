# Decision: promote Bailian into active routing after successful direct probe
Date: 2026-04-06

## Context
Alibaba Bailian and Tencent Hunyuan direct probes are both healthy.
After fixing routing policy, ORIS can now automatically select these providers in the active routing layer.

## Outcome
Current routing state:
- `primary_general` -> `openrouter/auto`
- `free_fallback` -> `qwen3.6-plus`
- `coding` -> `qwen-coder-turbo-0919`
- `cn_candidate_pool` -> `qwen3.6-plus`

## Interpretation
- Bailian is now the preferred free fallback provider
- Bailian is also the preferred coding and CN candidate provider at the moment
- Hunyuan is healthy and available in the pool, but current ordered policy still prefers Bailian for the affected roles
- Gemini remains healthy and continues to serve as an automatic fallback candidate when higher-priority CN/direct models are unavailable

## Operating rule
This selection is automatic.
Human intervention should only happen later through explicit override UI or exceptional risk/compliance handling.
