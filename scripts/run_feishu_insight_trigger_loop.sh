#!/usr/bin/env bash
cd "$(dirname "$0")/.."
python3 scripts/feishu_insight_trigger.py --start-at-end --poll-seconds "${GENERIC_INSIGHT_TRIGGER_POLL_SECONDS:-2}"
