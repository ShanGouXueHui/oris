# 2026-04-06 Download rewrite fix

## Symptom
公网签名下载链接不再返回 401，但返回 404。

## Root cause
nginx 将 `/oris-download/<artifact_code>` 改写成了 `/<artifact_code>`，
而下载服务实际要求的本地路径前缀是 `/download/<artifact_code>`。

## Fix
rewrite rule updated to:

- external: `/oris-download/<artifact_code>`
- internal: `/download/<artifact_code>`

## Result expectation
- 管理面继续 Basic Auth
- 签名下载链接公网可访问
- 下载认证仍由 artifact_code + expires + sig 控制
