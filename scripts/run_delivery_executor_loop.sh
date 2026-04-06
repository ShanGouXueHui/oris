#!/usr/bin/env bash
cd "$(dirname "$0")/.."
python3 scripts/delivery_executor.py --max-tasks "${DELIVERY_MAX_TASKS_PER_CYCLE:-20}" --poll-seconds "${DELIVERY_POLL_SECONDS:-10}"
