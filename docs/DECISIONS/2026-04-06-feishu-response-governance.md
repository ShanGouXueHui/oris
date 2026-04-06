# Decision: add Feishu response governance for latency and internal-output safety
Date: 2026-04-06

## Context
Direct Feishu messaging is already working, but two product issues appeared:
1. general Chinese replies were slower than expected
2. some model responses exposed internal/tool-like text such as code fragments

## Decision
1. Add Feishu channel profile in config/bridge_runtime.json
2. Route Feishu default general queries to cn_candidate_pool
3. Add config-driven meta-question reply rules
4. Add unsafe-output guard to block tool/code-like reply leakage
5. Keep exact short-reply rule for deterministic testing

## Outcome
Feishu direct chat is now governed as a consumer-facing bot channel rather than a raw model passthrough.
