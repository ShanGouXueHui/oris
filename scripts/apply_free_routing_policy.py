#!/usr/bin/env python3
"""Patch ORIS routing_policy.yaml to keep runtime roles on no-cost candidates.

This script is intentionally narrow: it updates only the routing policy text and
then lets the existing quota/score/selector/runtime-plan chain do its normal work.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "orchestration" / "routing_policy.yaml"

POLICY_TEXT = """version: 1
updated_at: 2026-05-20

global:
  strategy: weighted-fallback
  fail_open_to_free_pool: true
  max_probe_age_minutes: 1440
  latency_bias: medium
  availability_bias: high
  cost_bias: no_cost_candidates
  prefer_secret_managed_credentials: true

roles:
  primary_general:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-turbos-latest
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      avoid_status: [down]
      allow_free_candidates_only: true

  free_fallback:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-turbos-latest
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      allow_free_candidates_only: true

  report_generation:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-turbos-latest
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      minimum_context_window: null
      allow_free_candidates_only: true

  coding:
    ordered_candidates:
      - qwen-coder-turbo-0919
      - qwen3.6-plus
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      prefer_tool_capable: true
      allow_free_candidates_only: true

  cn_candidate_pool:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-turbos-latest
      - glm-4.7-flash
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      allow_unconfigured: false
      allow_free_candidates_only: true

replacement_policy:
  auto_replace_when:
    last_probe_failed_consecutive: 3
    success_rate_24h_below: 0.7
    median_latency_ms_above: 15000
  notification_only_when:
    provider_not_configured: true
    free_policy_changed: true
"""


def main() -> int:
    old = POLICY.read_text(encoding="utf-8") if POLICY.exists() else ""
    if "openrouter/auto" not in old and "allow_free_candidates_only: false" not in old:
        print("apply_free_routing_policy: already patched")
        return 0
    POLICY.write_text(POLICY_TEXT, encoding="utf-8")
    print(f"apply_free_routing_policy: wrote {POLICY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
