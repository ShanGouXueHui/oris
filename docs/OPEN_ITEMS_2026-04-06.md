# OPEN ITEMS / ROADMAP (2026-04-06)

## Summary
The runtime baseline is working.
Public dashboard works.
Feishu works.
QQ Bot is still pending external approval.

The remaining work is now mainly productization, provider routing, and expert-skill formalization.

---

## P0 - External dependency
### 1. QQ Bot integration
Status:
- Not implemented yet
- Waiting for platform approval
- Resume only after correct QQ Bot platform credentials (`AppID` + `AppSecret`) become available

Important note:
- `q.qq.com` is the correct QQ Bot platform
- `chatbot.weixin.qq.com` is WeChat dialogue platform and is not the same integration target

---

## P1 - High-value internal work
### 2. Free token / free quota orchestration module
Goal:
Create a provider orchestration layer that continuously allocates the best currently-available free or low-cost model source.

Proposed module outputs:
- `provider_registry.json`
- `provider_health_snapshot.json`
- `routing_policy.yaml`
- `quota_probe.py`
- scheduled refresh via cron

Functional requirements:
- Track provider, model, region, free policy, expiry, RPM/TPM, latency, availability
- Distinguish:
  - primary model
  - free fallback
  - coding model
  - report-writing model
  - web-research model
- Auto-replace degraded or expiring free providers
- Keep a ranked candidate pool instead of a hardcoded single fallback

Candidate providers to evaluate dynamically:
- Gemini free tier
- OpenRouter free router and free models
- Zhipu free quotas
- Alibaba Bailian newcomer quotas
- Tencent Hunyuan free package
- MiniMax temporary free / signup free quota
- Kimi free / Tier0 path
- `mimo` remains unconfirmed and should not enter the pool until the exact provider is identified

### 3. Necessary skill installation
Goal:
Install only high-value skills; avoid bloating the workspace with low-value community skills.

Rule:
- Built-in tools already cover shell, browser, web search, file I/O, cron, gateway, image, and subagents.
- Additional skills should mainly provide workflow guidance and domain-specific operating procedures.

Planned actions:
1. run skills readiness check
2. search only for research / report / development / testing related skills
3. install a very small set first
4. validate before keeping them

---

## P2 - Expert employee formalization
### 4. ORIS expert roles
ORIS should be formalized as five workspace skills plus standard operating templates.

#### Expert-01 Insight Analyst
Use case:
- company intelligence
- competitive intelligence
- market map
- report generation
- source registry and citation discipline

#### Expert-02 Coding Engineer
Use case:
- GitHub-first commercial software development
- continuity across chats
- patch / verify / commit workflow
- repo memory as source of truth

#### Expert-03 QA / Test Engineer
Use case:
- regression tests
- business-rule validation
- theory-driven validation for apps such as Nolly
- test plans, cases, and failure summaries

#### Expert-04 Information Concierge
Use case:
- current events digests
- people / company / industry dossiers
- timeline building
- long-horizon structured knowledge summaries

#### Expert-05 Self-Upgrade / Ops Engineer
Use case:
- version watch
- provider watch
- skill / plugin watch
- upgrade recommendations
- health checks and fallback policy

Recommended implementation order:
1. Expert-01
2. Expert-02
3. Expert-04
4. Expert-03
5. Expert-05

---

## P3 - Deferred hardening
### 5. Feishu App Secret rotation
Status:
- Secret was exposed during setup
- Rotation is required before final production hardening
- Do after current productization work is stabilized

---

## Recommended next sequence
1. Build free token orchestration skeleton
2. Formalize Expert-01 and Expert-02 as workspace skills
3. Install a minimal set of additional skills
4. Wait for QQ Bot approval
5. Integrate QQ Bot using the same unified secrets architecture
6. Rotate Feishu App Secret before final hardening
