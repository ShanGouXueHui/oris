# Skill Candidate Policy Decision — 2026-05-25

Third-party skills remain quarantine-only. No candidate is approved for production install by this report.

| Candidate | Decision | Rough risk | Main reasons |
|---|---:|---:|---|
| ClawHub | `blocked_no_install` | `100` | network_write=50, package_hooks=50, process_exec=50, shell_download_exec=16 |
| Awesome OpenClaw Skills | `blocked_no_install` | `100` | package_hooks=5, shell_download_exec=4 |
| Awesome OpenClaw Skills ZH | `intelligence_only_reviewable` | `0` | no risk indicators in coarse scan; still not approved for runtime install |
| Awesome Agent Skills | `blocked_no_install` | `100` | network_write=15, package_hooks=6, process_exec=50, shell_download_exec=3 |
| Awesome MCP Servers | `intelligence_only` | `74` | credential_keywords=37, sensitive_paths=37 |

## Promotion rule

Promotion requires a separate review against the source repository, exact commit SHA, license, manifest, install behavior, filesystem/network access, and rollback path.

## Immediate use allowed

Only use these repositories as read-only intelligence sources for discovering candidate names, categories, and ecosystem patterns. Do not install or execute them.
