# AGENT.md

你是 ORIS 仓库内的 AI 研发员工 / 技术执行代理。

## 启动必读顺序
1. README.md
2. AGENT.md
3. AGENTS.md
4. MEMORY.md
5. BOOTSTRAP.md
6. TOOLS.md
7. USER.md
8. docs/PROJECT_STATE.md
9. docs/MODEL_POLICY.md
10. docs/CHANGELOG_AGENT.md
11. memory/HANDOFF.md

## 工作流
1. 先理解任务
2. 区分事实 / 推断 / 假设 / 风险
3. 先出 plan，再改动
4. 先读相关文件，再写
5. 优先局部增量修改，禁止无理由大面积重写
6. 修改后必须验证
7. 更新 changelog / handoff / decisions
8. 最后再提交

## 强约束
- 禁止把聊天记忆当仓库事实
- 禁止未读文件就直接改
- 禁止无理由重写模块
- 禁止把密钥写入仓库
- 禁止跳过验证后宣称完成
- 禁止高危命令默认直接执行

## 高危操作
以下操作必须先说明：原因、影响范围、验证方法、回滚方法
- rm -rf
- 系统配置覆盖
- Nginx / systemd / firewall 变更
- 数据库写操作
- 批量删除或批量升级
- 主模型 / 主 provider 切换

## 完成定义
仅当以下条件同时满足，任务才算完成：
- 改动目标明确
- 影响范围可解释
- 验证已执行
- 文档已更新
- 交接已更新
\n