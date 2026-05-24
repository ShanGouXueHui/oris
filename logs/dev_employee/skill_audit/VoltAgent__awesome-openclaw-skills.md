# Skill Candidate Audit — Awesome OpenClaw Skills

- Repo: `https://github.com/VoltAgent/awesome-openclaw-skills.git`
- Commit: `bf943408a62c7e16d477c95f40a17f8f4d21a72a`
- Audit time: `2026-05-25T05:29:41+08:00`
- Rough risk score: `100`

## Manifest files

- `README.md`

## Finding counts

- `credential_keywords`: 50
- `package_hooks`: 5
- `sensitive_paths`: 50
- `shell_download_exec`: 4

## Sample findings

- `credential_keywords` `README.md:89` — `OpenClaw agents can interact with external services like GitHub, Slack, Gmail, and more. You can build integrations yourself with Skills or Plugins, or use a managed service to handle auth, token refresh, and permissions across all your con`
- `credential_keywords` `README.md:123` — `openclaw onboard --auth-choice openai-api-key`
- `sensitive_paths` `README.md:177` — `| [Browser & Automation](#browser--automation) (323) | [AI & LLMs](#ai--llms) (176) | [Smart Home & IoT](#smart-home--iot) (41) |`
- `credential_keywords` `README.md:182` — `| [Search & Research](#search--research) (345) | [iOS & macOS Development](#ios--macos-development) (29) | [Security & Passwords](#security--passwords) (54) |`
- `credential_keywords` `README.md:221` — `- [0protocol](https://clawskills.sh/skills/0isone-0protocol) - Agents can sign plugins, rotate credentials without losing identity, and publicly attest to behavior.`
- `sensitive_paths` `README.md:253` — `<summary><h3 style="display:inline">Browser & Automation</h3></summary>`
- `sensitive_paths` `README.md:263` — `- [Agent Browser](https://clawskills.sh/skills/thesethrose-agent-browser) - A fast Rust-based headless browser automation CLI.`
- `sensitive_paths` `README.md:264` — `- [agent-browser](https://clawskills.sh/skills/murphykobe-agent-browser-2) - Automates browser interactions for web testing, form.`
- `sensitive_paths` `README.md:281` — `- [adspower-browser](https://github.com/openclaw/skills/tree/main/skills/adspower/adspower-browser) - Use when the user asks to create or manage AdsPower browsers, groups, tags, proxies, or check status via AdsPower Local API.`
- `sensitive_paths` `README.md:284` — `> **[View all 323 skills in Browser & Automation →](categories/browser-and-automation.md)**`
- `sensitive_paths` `README.md:293` — `- [actionbook](https://clawskills.sh/skills/adcentury-actionbook) - Activate when the user needs to interact with any website — browser automation, web scraping, screenshots, form.`
- `sensitive_paths` `README.md:314` — `- [agentic-browser-0-1-2](https://clawskills.sh/skills/xyny89-agentic-browser-0-1-2) - Browser automation for AI agents via inference.sh.`
- `sensitive_paths` `README.md:328` — `- [abstract-searcher](https://clawskills.sh/skills/easonc13-abstract-searcher) - Add abstracts to .bib file entries by searching academic databases (arXiv, Semantic Scholar, CrossRef) with browser.`
- `credential_keywords` `README.md:345` — `- [agentkeys](https://clawskills.sh/skills/alexandr-belogubov-agentkeys) - Secure credential proxy for AI agents.`
- `sensitive_paths` `README.md:470` — `- [agent-browser](https://clawskills.sh/skills/matrixy-agent-browser-clawdbot) - Headless browser automation CLI optimized for AI agents.`
- `credential_keywords` `README.md:519` — `- [audit-code](https://clawskills.sh/skills/itsnishi-audit-code) - Security-focused code review for hardcoded secrets, dangerous calls, and common vulnerabilities.`
- `credential_keywords` `README.md:574` — `- [adaptlypost](https://clawskills.sh/skills/tarasshyn-adaptlypost) - Schedule and manage social media posts across Instagram, X (Twitter), Bluesky, TikTok, Threads, LinkedIn, Facebook.`
- `credential_keywords` `README.md:580` — `- [agent-earner](https://clawskills.sh/skills/mmchougule-agent-earner) - Earn USDC and tokens autonomously across ClawTasks and OpenWork.`
- `credential_keywords` `README.md:622` — `- [agent-registry](https://clawskills.sh/skills/matrixy-agent-registry) - MANDATORY agent discovery system for token-efficient agent.`
- `sensitive_paths` `README.md:977` — `- [checkers-sixty60](https://clawskills.sh/skills/snopoke-checkers-sixty60) - Shop on Checkers.co.za Sixty60 delivery service via browser.`
- `credential_keywords` `README.md:1056` — `- [confidant](https://clawskills.sh/skills/ericsantos-confidant) - Secure secret handoff from human to AI.`
- `credential_keywords` `README.md:1089` — `- [nas-master](https://clawskills.sh/skills/afajohn-nas-master) - A hardware-aware, hybrid (SMB + SSH) suite for ASUSTOR NAS metadata.`
- `credential_keywords` `README.md:1102` — `<summary><h3 style="display:inline">Security & Passwords</h3></summary>`
- `credential_keywords` `README.md:1104` — `- [1password](https://clawskills.sh/skills/steipete-1password) - Set up and use 1Password CLI (op).`
- `credential_keywords` `README.md:1105` — `- [1claw](https://clawskills.sh/skills/kmjones1979-1claw) - HSM-backed vault for agent secrets; store, rotate, share securely.`
- `credential_keywords` `README.md:1113` — `- [bitwarden](https://clawskills.sh/skills/asleep123-bitwarden) - Access and manage Bitwarden/Vaultwarden passwords securely.`
- `credential_keywords` `README.md:1122` — `- [credential-manager](https://clawskills.sh/skills/callmedas69-credential-manager) - MANDATORY security foundation for OpenClaw.`
- `credential_keywords` `README.md:1123` — `- [dashlane](https://clawskills.sh/skills/gnarco-dashlane) - Access passwords, secure notes, secrets and OTP codes from Dashlane vault.`
- `credential_keywords` `README.md:1131` — `- [trentclaw](https://github.com/openclaw/skills/tree/main/skills/trent-ai-release/trentclaw/SKILL.md) - Finds chained attack paths across config, secrets, and permissions.`
- `credential_keywords` `README.md:1133` — `> **[View all 54 skills in Security & Passwords →](categories/security-and-passwords.md)**`
- `credential_keywords` `categories/calendar-and-scheduling.md:51` — `- [office-secretary](https://clawskills.sh/skills/cenralsolution-office-secretary) - Secure M365 Assistant for Triage, Calendar coordination, and Governance.`
- `sensitive_paths` `categories/web-and-frontend-development.md:10` — `- [actionbook](https://clawskills.sh/skills/adcentury-actionbook) - Activate when the user needs to interact with any website — browser automation, web scraping, screenshots, form.`
- `sensitive_paths` `categories/web-and-frontend-development.md:31` — `- [agentic-browser-0-1-2](https://clawskills.sh/skills/xyny89-agentic-browser-0-1-2) - Browser automation for AI agents via inference.sh.`
- `sensitive_paths` `categories/web-and-frontend-development.md:64` — `- [apechain-reader](https://clawskills.sh/skills/luigi08001-apechain-reader) - Advanced multi-chain wallet analyzer with USD pricing, collection names, ENS support, and sophisticated bot.`
- `sensitive_paths` `categories/web-and-frontend-development.md:72` — `- [approvals-ui](https://clawskills.sh/skills/fizzy2390-approvals-ui) - A web dashboard for managing OpenClaw device pairings, channel approvals, and a live terminal — all from your browser.`
- `sensitive_paths` `categories/web-and-frontend-development.md:94` — `- [b0tresch-stealth-browser](https://clawskills.sh/skills/b0tresch-b0tresch-stealth-browser) - Anti-detection web browsing that bypasses bot detection, CAPTCHAs, and IP blocks using puppeteer-extra with stealth.`
- `package_hooks` `categories/web-and-frontend-development.md:122` — `- [build-warden-agent](https://clawskills.sh/skills/kryptopaid-build-warden-agent) - Build original LangGraph agents for Warden Protocol and prepare them for publishing in Warden Studio.`
- `credential_keywords` `categories/web-and-frontend-development.md:127` — `- [cacheforge](https://clawskills.sh/skills/tkuehnl-cacheforge) - CacheForge primary skill — bootstrap onboarding + ops + stats for the OpenAI-compatible token optimization gateway.`
- `sensitive_paths` `categories/web-and-frontend-development.md:134` — `- [camofox-mcp](https://clawskills.sh/skills/redf0x1-camofox-mcp) - Anti-detection browser automation MCP skill for OpenClaw agents with 41 tools for navigation, interaction.`
- `sensitive_paths` `categories/web-and-frontend-development.md:142` — `- [chia-walletconnect](https://clawskills.sh/skills/koba42corp-chia-walletconnect) - Telegram Web App for Chia wallet verification via WalletConnect and Sage.`
- `sensitive_paths` `categories/web-and-frontend-development.md:144` — `- [chrome-devtools](https://clawskills.sh/skills/podcasting101-chrome-devtools) - Uses Chrome DevTools via MCP for efficient debugging, troubleshooting and browser automation.`
- `credential_keywords` `categories/web-and-frontend-development.md:147` — `- [claude-code-pro](https://clawskills.sh/skills/swaylq-claude-code-pro) - Token-efficient Claude Code workflow.`
- `credential_keywords` `categories/web-and-frontend-development.md:182` — `- [context-viz](https://clawskills.sh/skills/furukama-context-viz) - Visualize the current context window usage — token estimates per component (system prompt, tools, workspace files.`
- `credential_keywords` `categories/web-and-frontend-development.md:243` — `- [domain-email-forwarding](https://clawskills.sh/skills/brandonwadepackard-cell-domain-email-forwarding) - Set up email forwarding for custom domains to receive verification codes, password resets, and other emails.`
- `credential_keywords` `categories/web-and-frontend-development.md:251` — `- [elite-tools](https://clawskills.sh/skills/bezkom-elite-tools) - Elite CLI tooling for efficient shell operations with optimized token usage.`
- `credential_keywords` `categories/web-and-frontend-development.md:256` — `- [emily](https://clawskills.sh/skills/mavremu-emily) - Query Radix DLT blockchain data including wallet balances and performance, token prices and market movers.`
- `sensitive_paths` `categories/web-and-frontend-development.md:256` — `- [emily](https://clawskills.sh/skills/mavremu-emily) - Query Radix DLT blockchain data including wallet balances and performance, token prices and market movers.`
- `credential_keywords` `categories/web-and-frontend-development.md:257` — `- [emily-radix-assistant](https://clawskills.sh/skills/mavremu-emily-radix-assistant) - Query Radix DLT blockchain data including wallet balances and performance, token prices and market movers.`
- `sensitive_paths` `categories/web-and-frontend-development.md:257` — `- [emily-radix-assistant](https://clawskills.sh/skills/mavremu-emily-radix-assistant) - Query Radix DLT blockchain data including wallet balances and performance, token prices and market movers.`
- `credential_keywords` `categories/web-and-frontend-development.md:270` — `- [expiring-local-fileshare](https://clawskills.sh/skills/tradmangh-expiring-local-fileshare) - Lets OpenClaw safely share single files from its local workspace via expiring, tokenized HTTP links.`
- `sensitive_paths` `categories/web-and-frontend-development.md:272` — `- [external-ai-integration](https://clawskills.sh/skills/konscious0beast-external-ai-integration) - Leverage external AI models (ChatGPT, Claude, Hugging Face, etc.) as tools via browser automation (Chrome Relay)`
- `sensitive_paths` `categories/web-and-frontend-development.md:290` — `- [food-cal-order](https://clawskills.sh/skills/thisisjeron-food-cal-order) - Order food delivery via browser automation, triggered by calendar events.`
- `sensitive_paths` `categories/web-and-frontend-development.md:325` — `- [google-maps-api-skill](https://clawskills.sh/skills/phheng-google-maps-api-skill) - This skill helps users automatically scrape business data from Google Maps using the BrowserAct Google Maps API.`
- `credential_keywords` `categories/web-and-frontend-development.md:329` — `- [google-workspace-byok](https://clawskills.sh/skills/kyesh-google-workspace-byok) - Google Calendar and Gmail integration using your own GCP project credentials (BYoK — Bring Your Own Key)`
- `sensitive_paths` `categories/web-and-frontend-development.md:341` — `- [handsfree-windows-control](https://clawskills.sh/skills/lijinlar-handsfree-windows-control) - Guide skill for controlling native Windows apps (UIA) and web browsers (Playwright) via the handsfree-windows CLI.`
- `sensitive_paths` `categories/web-and-frontend-development.md:342` — `- [harpa-ai](https://clawskills.sh/skills/alxsharuk-harpa-ai) - Automate web browsers, scrape pages, search the web, and run AI prompts on live websites via HARPA AI Grid REST API.`
- `credential_keywords` `categories/web-and-frontend-development.md:345` — `- [heurist-mesh](https://clawskills.sh/skills/wjw12-heurist-mesh) - Real-time crypto token data, DeFi analytics, blockchain data, Twitter/X social intelligence, enhanced web search.`
- `sensitive_paths` `categories/web-and-frontend-development.md:364` — `- [human-browser](https://clawskills.sh/skills/al1enjesus-human-browser) - The default browser for AI agents.`
- `sensitive_paths` `categories/web-and-frontend-development.md:382` — `- [iyeque-unified-web-search](https://clawskills.sh/skills/iyeque-iyeque-unified-web-search) - Pick the best source (Tavily, Web Search Plus, Browser, or local files) for a query, run the search, and return.`
- `sensitive_paths` `categories/web-and-frontend-development.md:390` — `- [js-eyes](https://clawskills.sh/skills/imjszhang-js-eyes) - Browser automation for AI agents — control tabs, extract content, execute scripts and manage cookies via WebSocket.`
- `sensitive_paths` `categories/web-and-frontend-development.md:396` — `- [kaspa](https://clawskills.sh/skills/manyfestation-kaspa) - Simple wallet for Kaspa blockchain.`
- `package_hooks` `categories/web-and-frontend-development.md:428` — `- [lex](https://clawskills.sh/skills/kulotzkih-lex) - Build original LangGraph agents for Warden Protocol and prepare them for publishing in Warden Studio.`
- `sensitive_paths` `categories/web-and-frontend-development.md:448` — `- [m44-internal-testing](https://clawskills.sh/skills/tuleyko-m44-internal-testing) - Install and set up DataHive in a deterministic headless-friendly flow: (1) check/install browser (Chrome or Chromium)`
- `sensitive_paths` `categories/web-and-frontend-development.md:453` — `- [manikantasai-playwright-automation](https://clawskills.sh/skills/manikantasai1987-manikantasai-playwright-automation) - Browser automation using Playwright API directly.`
- `sensitive_paths` `categories/web-and-frontend-development.md:454` — `- [markdown-browser](https://clawskills.sh/skills/2233admin-markdown-browser) - Wrapper skill for OpenClaw web_fetch results.`
- `credential_keywords` `categories/web-and-frontend-development.md:456` — `- [markdown-fetch](https://clawskills.sh/skills/howtimeschange-markdown-fetch) - Optimizes web fetching by using Cloudflare's Markdown for Agents, reducing token consumption by ~80%.`
- `sensitive_paths` `categories/web-and-frontend-development.md:478` — `- [midscene-computer-browser](https://clawskills.sh/skills/quanru-midscene-computer-browser) - Vision-driven browser automation using Midscene.`
- `credential_keywords` `categories/web-and-frontend-development.md:482` — `- [minimax-cli-web-search](https://clawskills.sh/skills/biggersun-minimax-cli-web-search) - Web search via MiniMax MCP using a local CLI wrapper (mcporter), with environment preflight, API-key/config checks.`
- `credential_keywords` `categories/web-and-frontend-development.md:486` — `- [mirage-proxy](https://clawskills.sh/skills/chandika-mirage-proxy) - Install and configure mirage-proxy as a transparent PII/secrets filter for OpenClaw LLM API calls.`
- `sensitive_paths` `categories/web-and-frontend-development.md:503` — `- [my-play-music-from-yt](https://clawskills.sh/skills/whodidthese-my-play-music-from-yt) - Play music on YouTube via browser automation with playwright-cli.`
- `credential_keywords` `categories/web-and-frontend-development.md:564` — `- [pandora](https://clawskills.sh/skills/kleberbaum-pandora) - Pandora namespace for Netsnek e.U. secrets and configuration management vault.`
- `sensitive_paths` `categories/web-and-frontend-development.md:568` — `- [pascal-playwright-mcp](https://clawskills.sh/skills/ramspan-pascal-playwright-mcp) - Browser automation via Playwright MCP server.`
- `credential_keywords` `categories/web-and-frontend-development.md:569` — `- [password-gen](https://clawskills.sh/skills/ouyangabel-password-gen) - Secure password generator with multiple character sets and strength analysis.`
- `credential_keywords` `categories/web-and-frontend-development.md:579` — `- [personality-backup](https://clawskills.sh/skills/civilainominee-personality-backup) - Create encrypted backups of agent personality files, memory, config, secrets, and projects.`
- `sensitive_paths` `categories/web-and-frontend-development.md:584` — `- [pinchtab](https://clawskills.sh/skills/luigi-agosti-pinchtab) - Control a headless or headed Chrome browser via Pinchtab's HTTP API.`
- `sensitive_paths` `categories/web-and-frontend-development.md:587` — `- [playwright-browser-automation](https://clawskills.sh/skills/spiceman161-playwright-browser-automation) - Browser automation using Playwright API directly.`
- `sensitive_paths` `categories/web-and-frontend-development.md:588` — `- [playwright-headless-browser](https://clawskills.sh/skills/maverick-software-playwright-headless-browser) - Set up headless browser automation in Clawdbot using Playwright Chromium.`
- `sensitive_paths` `categories/web-and-frontend-development.md:589` — `- [playwright-mcp](https://clawskills.sh/skills/spiceman161-playwright-mcp) - Browser automation via Playwright MCP server.`
- `sensitive_paths` `categories/web-and-frontend-development.md:590` — `- [playwright-mcp-1-0-0](https://clawskills.sh/skills/itsjustfred-playwright-mcp-1-0-0) - Browser automation via Playwright MCP server.`
- `sensitive_paths` `categories/web-and-frontend-development.md:591` — `- [playwright-npx](https://clawskills.sh/skills/mahone-bot-playwright-npx) - Fast browser automation using Node.js scripts with Playwright (run via `node script.mjs`)`
