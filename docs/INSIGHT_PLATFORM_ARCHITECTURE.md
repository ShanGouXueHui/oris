# ORIS 洞察中台架构（Insight Platform Architecture）

## 1. 文档目的
本文件定义 ORIS 在“AI 员工产品化阶段”的企业竞争力洞察架构，作为后续数据库落地、skill 开发、报告交付、下载分发、评测与审计的统一设计基线。

ORIS 的定位不是“会联网总结的聊天机器人”，而是：
- 可持续积累证据的研究中台
- 可复用、可审计、可回溯的分析交付系统
- 面向 Feishu / Qbot / Word / Excel / PPT 的正式业务输出引擎

## 2. 总体原则
### 2.1 正确性优先于速度
- 回答慢一点可以接受
- 结论错误不可接受
- 在正确性、稳定性、速度冲突时，优先级固定为：
  1. 正确性
  2. 稳定性
  3. 速度

### 2.2 证据优先于观点
- 结论必须由数据支撑
- 数据必须说明是什么
- 数据必须说明出处
- 出处必须尽量附带链接、公告名、报告名、页面名、接口名中的一种或多种
- 必须区分：事实 / 推断 / 假设 / 风险

### 2.3 技能是原子能力，不是最终系统
OpenClaw / ClawHub 生态中的 community skill 可以作为辅助原子能力接入，但 ORIS 的核心竞争力放在：
- 自有 schema
- 自有证据协议
- 自有报告协议
- 自有调度与审计流程
- 自有配置治理规则

### 2.4 常量治理
- 业务常量不得散落在脚本中
- 可变参数进入 config/*.json 或数据库
- 渠道、报告模板、提示词规则、输出协议、下载策略均配置化
- 后续若脚本中再次出现新增常量，默认视为待治理项

---

## 3. 目标能力分层
### 3.1 渠道层
当前与规划中的业务入口：
- Feishu：已打通 direct webhook callback 路径
- OpenClaw：可作为独立入口与调度辅助
- Qbot：后续作为下载与报告分发渠道
- HTTPS API：作为统一推理与报告服务层

### 3.2 编排层
ORIS 统一负责编排：
- 路由不同任务到合适模型与工具
- 执行外部检索 / 抓取 / 文档处理 / 分析 / 报告生成
- 记录 execution log / evidence log / report log / alert log
- 形成可追踪 request_id 与 artifact_id

### 3.3 洞察技能层
分为两类：

#### A. 外部原子能力 skill（可接入 / 可参考）
- Web Search / Browser / Search Assistant
- Competitor Teardown
- Competitive Intelligence / Market Research
- Metrics Dashboard
- Slide / Document generation

#### B. ORIS 自建业务 skill（必须沉淀）
1. source-collector  
   采集网页、PDF、公告、财报、新闻、价格、评论、社媒等原始材料

2. source-normalizer  
   统一来源口径、清洗元数据、去重、打标签

3. evidence-extractor  
   抽取数字、日期、主体、结论、引用句段、证据片段

4. metric-observer  
   将结构化数字转为可比较的观测值，形成时间序列

5. snapshot-diff  
   对官网、价格页、产品页、公告页做时间点差异对比

6. competitive-analyzer  
   生成竞争矩阵、产品能力对标、价格对标、渠道对标、财务对标、组织能力对标

7. report-assembler  
   组装 Word 正式报告、Excel 辅助底表、后续 PPT

8. alert-monitor  
   定时监控变化，触发 Feishu / Qbot 告警与定期简报

---

## 4. 数据层架构
## 4.1 为什么必须落库
如果不把洞察数据持久化，ORIS 每次都会像第一次做研究，无法形成：
- 时间序列
- 差异监控
- 证据复用
- 报告复盘
- 可审计的结论链路

因此，洞察数据存储不是可选优化，而是产品化基础设施。

### 4.2 数据层拆分
建议采用三层：

#### A. PostgreSQL 主库
用于存放结构化与半结构化核心数据：
- 企业主体
- 来源元数据
- 证据
- 指标观测
- 分析运行记录
- 报告 artifact 元数据
- 下载任务
- 监控任务
- 告警事件

#### B. 文件 / 对象存储层
用于保存：
- 原始网页快照
- PDF 原文件
- HTML / 文本快照
- Word 报告
- Excel 评分表 / 证据底表
- 后续 PPT
- ZIP 打包下载件

#### C. 可选缓存 / 队列层
后续按需增加 Redis，用于：
- 去重键
- 队列
- 限流
- 临时会话缓存
- 下载任务状态

---

## 5. 交付物架构
### 5.1 Word
定位：
- 面向终端用户的正式交付报告
- 对外可下载、可转发、可留档

内容结构遵循 evidence-first protocol：
- 结论
- 核心数据
- 数据出处
- 分析与推断
- 主要风险
- 待验证点

### 5.2 Excel
定位：
- 证据底表
- 评分结果
- 可比矩阵
- 指标明细
- 引用清单
- 评测结果

### 5.3 PPT
定位：
- 管理层简报
- 项目汇报
- 对外策略演示
- 竞品快照图示版交付

### 5.4 渠道分发
下载分发以渠道能力为准：
- Feishu：文件 / 链接分发
- Qbot：文件 / 链接分发
- HTTPS：artifact 下载接口
- ZIP：统一打包下载

---

## 6. 与现有 ORIS 体系的关系
当前 ORIS 已完成：
- provider orchestration
- runtime plan
- unified infer
- v1 api contract
- Feishu direct callback
- Word / Excel eval artifact 基础路径

下一阶段不是继续堆单点脚本，而是进入：
- 洞察中台 schema 固化
- 证据链规范化
- 研究型 skill 体系化
- 报告交付产品化
- 下载与审计闭环化

---

## 7. 当前建议的实施顺序
### Phase 1：洞察底座
- 落 PostgreSQL
- 建 insight schema
- 建 artifact 元数据表
- 把配置治理规则写入 docs + config

### Phase 2：证据链
- source snapshot
- evidence item
- citation link
- metric observation
- analysis run

### Phase 3：技能产品化
- source-collector
- source-normalizer
- evidence-extractor
- snapshot-diff
- competitive-analyzer

### Phase 4：报告交付
- Word 正式报告模板
- Excel 辅助底表模板
- Feishu / Qbot 下载分发
- artifact package / manifest

### Phase 5：监控告警
- watch task
- alert event
- scheduled diff
- weekly / monthly digest

---

## 8. 非目标
当前阶段暂不追求：
- 一上来就做全量 BI 平台
- 一上来就接太多社区 skill
- 把所有行业都一起做深
- 把数据库、队列、搜索、向量、缓存一次性全部堆满

原则：
- 先打通企业竞争力洞察最短闭环
- 再扩展行业深度与多渠道交付
