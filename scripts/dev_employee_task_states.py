#!/usr/bin/env python3
"""Canonical ORIS Dev Employee task-state classification.

This module is the single authoritative source for terminal-state decisions used
by the bridge, intake/status API, Web E2E finishers, and operational scripts.
Legacy detailed statuses remain observable, but consumers must use
``canonical_status`` and ``is_terminal_status`` for lifecycle decisions.
"""

from __future__ import annotations

import argparse
from typing import Any

CANONICAL_TERMINAL_STATES = frozenset(
    {
        "completed",
        "preflight_failed",
        "local_checks_failed",
        "remote_verification_failed",
        "blocked",
        "cancelled",
        "failed",
        "error",
    }
)

LEGACY_STATUS_CANONICAL_MAP = {
    "codex_failed": "failed",
    "host_checks_failed": "local_checks_failed",
    "blocked_host_checks_failed": "local_checks_failed",
    "blocked_product_push_failed": "remote_verification_failed",
    "blocked_oris_push_failed": "remote_verification_failed",
    "bridge_exception": "failed",
    "enqueue_failed": "failed",
    "blocked_result_schema_invalid": "blocked",
    "blocked_skill_resolution_invalid": "blocked",
    "blocked_missing_codex_result": "blocked",
    "blocked_codex_result_not_passed": "blocked",
}


def normalize_status(status: Any) -> str:
    value = str(status or "").strip().lower()
    return value or "unknown"


def canonical_status(status: Any) -> str:
    value = normalize_status(status)
    if value in LEGACY_STATUS_CANONICAL_MAP:
        return LEGACY_STATUS_CANONICAL_MAP[value]
    if value.startswith("blocked_"):
        return "blocked"
    if value.endswith("_failed"):
        return "failed"
    return value


def is_terminal_status(status: Any) -> bool:
    return canonical_status(status) in CANONICAL_TERMINAL_STATES


def extract_failure_code(status: Any, payload: dict[str, Any] | None = None) -> str | None:
    data = payload or {}
    candidates = [
        data.get("failure_code"),
        (data.get("failure_details") or {}).get("failure_code")
        if isinstance(data.get("failure_details"), dict)
        else None,
        (data.get("last_error") or {}).get("type")
        if isinstance(data.get("last_error"), dict)
        else None,
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)
    value = normalize_status(status)
    if value in LEGACY_STATUS_CANONICAL_MAP and value not in CANONICAL_TERMINAL_STATES:
        return value
    return None


def classify(status: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_status(status)
    canonical = canonical_status(normalized)
    return {
        "status": normalized,
        "canonical_status": canonical,
        "terminal": canonical in CANONICAL_TERMINAL_STATES,
        "failure_code": extract_failure_code(normalized, payload),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify an ORIS Dev Employee task status")
    parser.add_argument("status")
    parser.add_argument(
        "--field",
        choices=["status", "canonical_status", "terminal", "failure_code", "json"],
        default="json",
    )
    args = parser.parse_args()
    result = classify(args.status)
    if args.field == "json":
        import json

        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        value = result.get(args.field)
        if isinstance(value, bool):
            print("true" if value else "false")
        elif value is None:
            print("")
        else:
            print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
