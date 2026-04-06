# Decision: freeze config governance and prioritize OpenClaw production cutover
Date: 2026-04-06

## Context
Bridge/runtime code had started to accumulate hardcoded operational constants.
At the same time, ORIS already had a practical lower-risk production path through OpenClaw.

## Decision
1. Freeze a config-governance rule:
   - secrets -> ~/.openclaw/secrets.json
   - non-secret runtime constants -> repository config
   - frequently adjusted rules -> database/admin UI later
2. Keep direct script execution compatible with the current copy-paste workflow
3. Prioritize OpenClaw as the first production traffic path
4. Keep direct Feishu transport in staged/dry-run mode for now

## Outcome
The project now has a clearer maintainability rule and a more disciplined rollout path.
