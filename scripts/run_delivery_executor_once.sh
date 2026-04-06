#!/usr/bin/env bash
cd "$(dirname "$0")/.."
python3 scripts/delivery_executor.py --once --max-tasks "${DELIVERY_MAX_TASKS_PER_CYCLE:-20}"
