# OpenClaw Bridge

## Current status
A reusable OpenClaw-to-ORIS bridge is available in:

- scripts/openclaw_bridge_to_oris.py

## Responsibility
The bridge:
1. accepts OpenClaw-like text input
2. selects an ORIS role
3. calls local ORIS v1 infer
4. applies reply shaping for exact short-answer prompts
5. outputs normalized reply text
6. writes bridge logs

## Input
Required arguments:
- --session-id
- --user-id
- --text

Optional:
- --role
- --source

## Output
JSON:
- bridge metadata
- reply_text
- oris_result

## Log
- orchestration/openclaw_bridge_log.jsonl

## Recommended production role
OpenClaw should be treated as the first real production transport path for ORIS while direct Feishu transport remains in dry-run / staged mode.
