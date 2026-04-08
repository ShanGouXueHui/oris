# DECISION — 2026-04-08 GitHub sync and entity-detection governance

## Status
Accepted

## Context
ORIS 已进入可商用 AI 员工阶段。当前主阻塞不是 Feishu 发送，而是：
- 本地 worktree 被 runtime 日志/lock/out 污染
- GitHub 与部署环境之间存在未分类漂移
- company entity detection 仍可能把行业词、竞品、合作方误判为主实体
- 识别失败时，聊天链路仍有发送占位内容的风险

## Decision
1. GitHub 作为 ORIS 的权威长期记忆与主链路代码源
2. 新增 GitHub 同步治理文档
3. 新增实体识别治理文档
4. 新增洞察投递治理文档
5. 增强 routing / config / provider orchestration 文档
6. `.gitignore` 正式接管 runtime 噪音文件
7. 把 runtime `jsonl` 日志从 Git 索引中移除
8. `active_routing.json` 保留为可跟踪的“已验证基线快照”，但不再按每次运行自动提交
9. 本轮主线优先级固定为：
   - 通用公司识别主链路
   - 失败阻断
   - 真实正文投递
   - 最后再扩展高级 case

## Consequences
### Positive
- GitHub 可重新成为可靠续航底座
- 部署环境与主线代码边界更清晰
- 运行噪音不再污染代码库
- company_profile 的目标公司识别拥有正式治理框架
- Feishu 聊天版结果质量可控

### Trade-offs
- 需要对当前未提交漂移做一次正式分类
- 需要把历史专用 trigger 与实验路径逐步退出主链路

## Follow-up
1. 审核并正式接入 `company_entity_detector.py` 相关配置与脚本
2. 清理旧 direct send / placeholder 路径
3. 做本地自检
4. 做 Feishu 真实回传验证
5. 更新 `docs/PROJECT_STATE.md` 与 `memory/HANDOFF.md`
