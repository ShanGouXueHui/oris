#!/usr/bin/env python3
"""Patch ORIS routing policy for latency-aware free routing.

This keeps the existing ORIS provider orchestration pipeline intact. It only
changes role candidate ordering so chat/general traffic prefers faster free
models, while report/coding roles keep quality-oriented choices.
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
  latency_bias: high
  availability_bias: high
  cost_bias: no_cost_candidates
  prefer_secret_managed_credentials: true

roles:
  primary_general:
    ordered_candidates:
      - models/gemini-2.0-flash-lite
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - hunyuan-large-role-latest
      - hunyuan-turbos-latest
      - qwen3.6-plus
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      avoid_status: [down]
      allow_free_candidates_only: true

  free_fallback:
    ordered_candidates:
      - models/gemini-2.0-flash-lite
      - models/gemini-2.5-flash-lite
      - models/gemini-flash-lite-latest
      - hunyuan-large-role-latest
      - hunyuan-turbos-latest
      - qwen3.6-plus
      - openrouter/free
    rules:
      require_health_status: [healthy, degraded, unknown]
      allow_free_candidates_only: true

  report_generation:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-large-role-latest
      - hunyuan-turbos-latest
      - models/gemini-2.0-flash-lite
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
      - qwen/qwen3-coder:free
      - openrouter/free
      - models/gemini-2.0-flash-lite
      - models/gemini-2.5-flash-lite
    rules:
      require_health_status: [healthy, degraded, unknown]
      prefer_tool_capable: true
      allow_free_candidates_only: true

  cn_candidate_pool:
    ordered_candidates:
      - qwen3.6-plus
      - hunyuan-large-role-latest
      - hunyuan-turbos-latest
      - glm-4.7-flash
      - models/gemini-2.0-flash-lite
      - models/gemini-2.5-flash-lite
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
    if "models/gemini-2.0-flash-lite" in old and "latency_bias: high" in old:
        print("apply_latency_aware_free_routing: already patched")
        return 0
    POLICY.write_text(POLICY_TEXT, encoding="utf-8")
    print(f"apply_latency_aware_free_routing: wrote {POLICY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
