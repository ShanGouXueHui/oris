# Decision: ORIS 洞察中台采用 PostgreSQL 主库 + 自建 skill 中台路线

## 日期
2026-04-06

## 背景
ORIS 已从“多模型编排 + Feishu 通道打通”的原型阶段，进入“AI 员工产品化”阶段。  
该阶段需要：
- 长期积累企业竞争力洞察数据
- 把证据、快照、引用、报告沉淀下来
- 把 Word / Excel / PPT 变成正式业务交付件
- 支持 Feishu / Qbot 下载分发
- 保证后续对话与开发可持续续接

## 决策
1. 洞察数据必须落库，不再视为可选能力
2. 默认采用 PostgreSQL 作为洞察主库
3. 文件类 artifact 单独保存，不直接塞入数据库大字段
4. community skill 只作为原子能力参考，不作为 ORIS 核心方法论替代
5. ORIS 自建 insight skill 体系
6. 常量治理继续执行：可变规则进入 config 或数据库
7. Word 作为正式交付主件，Excel 作为辅助底表，后续再接 PPT
8. Feishu 与后续 Qbot 作为下载分发渠道

## 原因
- 研究系统若不落库，无法形成证据复用、时间序列、差异监控、可审计回溯
- PostgreSQL 更适合洞察中台后续的 JSON、引用链、结构化分析与扩展
- skill 生态可用，但 ORIS 的竞争力应放在 schema、证据协议与交付协议
- 当前阶段优先形成“证据 -> 分析 -> 报告 -> 下载”的完整闭环

## 影响
### 正面
- 后续所有企业竞争力分析有统一底座
- 报告可以正式产品化
- 后续对话可继续依赖 GitHub 文档而非短期聊天上下文

### 代价
- 需要先建库和 schema
- 需要治理脚本中的散落常量
- 需要把 artifact 元数据纳入统一管理

## 后续动作
1. 建 PostgreSQL
2. 建 insight schema
3. 建 report_artifact / citation_link / evidence_item 等核心表
4. 建第一批 ORIS 自建 skill scaffold
5. 把下载链路并入 Feishu / Qbot
