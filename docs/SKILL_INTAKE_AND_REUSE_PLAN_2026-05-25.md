# ORIS Skill Intake and Reuse Plan — 2026-05-25

## Purpose

Add reusable agent capabilities to ORIS without blindly installing third-party OpenClaw/ClawHub skills into the production host.

The immediate goal is discovery and controlled reuse: find useful high-signal skills or MCP-style tools from GitHub/OpenClaw ecosystems, inspect them, quarantine them, and only promote safe, narrowly scoped capabilities into ORIS.

## Current ecosystem findings

### OpenClaw / ClawHub

- `openclaw/clawhub` is the public skill registry for OpenClaw. It supports `SKILL.md` plus supporting files, search, install, inspect, pin, update, package catalog, and CLI workflows such as `clawhub search`, `clawhub inspect`, `clawhub install`, `clawhub pin`, and `clawhub list`.
- `VoltAgent/awesome-openclaw-skills` indexes thousands of community OpenClaw skills and explicitly filters out spam, duplicate/similar names, low-quality descriptions, crypto/blockchain/finance/trade skills, and skills identified as malicious by published security audits.
- Public reports and research indicate that ClawHub/OpenClaw skills have meaningful supply-chain risk. Therefore ORIS must not use popularity alone as an install criterion.

### GitHub / MCP adjacent ecosystem

Candidate discovery sources from GitHub search include:

- `VoltAgent/awesome-openclaw-skills`
- `openclaw/clawhub`
- `clawdbot-ai/awesome-openclaw-skills-zh`
- `libukai/awesome-agent-skills`
- `punkpeye/awesome-mcp-servers`
- `appcypher/awesome-mcp-servers`
- `wong2/awesome-mcp-servers`

These are discovery/index sources, not automatically trusted runtime dependencies.

## ORIS adoption policy

### Default stance

Third-party skills are untrusted until proven otherwise.

ORIS may download a skill for inspection, but must not execute installer scripts, shell snippets, postinstall hooks, package scripts, or arbitrary tool code until the skill passes review.

### Quarantine locations

Use these directories only:

- candidate source mirror: `/home/admin/projects/oris/vendor/skill_candidates/`
- audit output: `/home/admin/projects/oris/logs/dev_employee/skill_audit/`
- promoted internal skills: `/home/admin/projects/oris/skills/`

Do not install directly into global OpenClaw skill directories such as `~/.openclaw/skills/` during discovery.

### Minimum acceptance gate

A skill can be promoted only if all are true:

1. source repo and exact commit SHA are recorded;
2. license is recorded;
3. `SKILL.md` or equivalent manifest is present and reviewed;
4. no obfuscated curl/wget/bash/powershell one-liners;
5. no credential harvesting patterns;
6. no automatic access to `.ssh`, browser profiles, crypto wallets, `.env`, tokens, or OpenClaw config;
7. no network write/exfiltration behavior unless explicitly required and isolated;
8. no install/postinstall execution during discovery;
9. capability is needed by ORIS and not already covered by built-in tools;
10. a rollback/uninstall path exists.

### Capability priorities for ORIS

Priority 1 — useful now:

- GitHub repo/file/PR/issue operations and evidence management.
- Shell-safe execution wrappers and task-run logging.
- Test automation and code-quality runners.
- Documentation and markdown summarization.
- Web research / source capture with citation metadata.

Priority 2 — later:

- Browser automation in isolated container.
- Package/security scanning.
- Lightweight RAG/indexing for repo docs.
- Calendar/Gmail only through explicit account-scoped connectors.

Avoid by default:

- crypto/trading/finance automation skills;
- credential managers or browser-profile readers;
- skills that request broad filesystem/network execution;
- social/media automation that can post externally without approval;
- abandoned repos with recent ownership changes.

## Immediate next step

Implement a skill discovery/audit helper that:

1. reads a candidate list;
2. clones or downloads candidates into quarantine only;
3. records repo URL, commit SHA, files, detected `SKILL.md`, install instructions, shell/network/credential risk indicators;
4. emits JSON and Markdown reports;
5. never executes candidate code.

After that, run it against a small allowlisted candidate set:

- `openclaw/clawhub`
- `VoltAgent/awesome-openclaw-skills`
- `clawdbot-ai/awesome-openclaw-skills-zh`
- `libukai/awesome-agent-skills`
- `punkpeye/awesome-mcp-servers`

No production install until audit evidence is committed to GitHub.
