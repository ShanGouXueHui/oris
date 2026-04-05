# Decision: create provider orchestration skeleton before adding more channels or expert workflows
Date: 2026-04-06

## Context
Feishu is already working.
QQ Bot is waiting for platform approval.
The next highest-value work is to reduce model-cost risk and free-tier fragility.

## Decision
Create a provider orchestration skeleton first, including:
- provider registry
- routing policy
- runtime health snapshot
- quota probe script

## Why
This becomes the shared substrate for:
- free token allocation
- fallback routing
- expert-role execution
- future automatic provider replacement
