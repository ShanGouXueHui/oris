# Decision: add Feishu send executor skeleton
Date: 2026-04-06

## Context
Feishu integration already had:
- bridge core
- ingress skeleton
- transport skeleton

The next missing piece was a real sender-side execution skeleton.

## Decision
1. Add scripts/feishu_send_executor_skeleton.py
2. Fetch tenant_access_token using app credentials
3. Build reply/send API request from send envelope
4. Default to dry-run
5. Allow explicit real execution later through --execute

## Outcome
Feishu integration now has an end-to-end executable send-side skeleton while still keeping production send disabled by default.
