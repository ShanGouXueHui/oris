# ORIS Integration Contract

## Target
All upper-layer integrations should converge on the same ORIS external HTTPS endpoint:

- POST /oris-api/v1/infer

## Unified upstream-to-ORIS mapping

### 1. Feishu bridge
Input source:
- Feishu p2p message
- Feishu group message if later enabled

Bridge behavior:
- extract plain text content
- choose an ORIS role
- call ORIS HTTPS API
- return ORIS text answer back to Feishu

Recommended payload:
{
  "role": "primary_general",
  "prompt": "<cleaned user text>",
  "source": "feishu_bridge"
}

### 2. OpenClaw bridge
Input source:
- OpenClaw operator action
- OpenClaw workflow or tool wrapper

Bridge behavior:
- normalize user request
- choose role according to task type
- call ORIS HTTPS API
- return structured result to OpenClaw workflow

Recommended payload:
{
  "role": "coding | report_generation | primary_general | cn_candidate_pool | free_fallback",
  "prompt": "<normalized task text>",
  "source": "openclaw_bridge"
}

### 3. WeChat service-account backend
Input source:
- WeChat text message event

Bridge behavior:
- parse inbound XML
- extract user text
- choose ORIS role
- call ORIS HTTPS API
- send ORIS text back as passive or active reply

Recommended payload:
{
  "role": "primary_general",
  "prompt": "<wechat user text>",
  "source": "wechat_mp_backend"
}

## Role guidance

### primary_general
General assistant / broad Q&A / non-specialized tasks

### free_fallback
Cost-controlled fallback path

### report_generation
Structured report / insight generation

### coding
Code generation / debugging / engineering tasks

### cn_candidate_pool
Chinese-provider-oriented task routing

## External calling rule
For all external HTTPS integrations, use:
- Basic Auth
- X-ORIS-API-Key

Do not mix external Basic Auth with application bearer token in the same Authorization header.
