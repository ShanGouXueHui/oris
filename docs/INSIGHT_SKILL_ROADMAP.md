# ORIS 洞察 Skill 路线图（Insight Skill Roadmap）

## 1. 目标
本文件定义 ORIS 在企业竞争力洞察方向的 skill 分层、引入原则与实施顺序。

## 2. Skill 选择原则
### 2.1 原子能力优先
优先引入可独立复用的原子能力：
- 搜索
- 抓取
- 浏览器访问
- PDF 读取
- 差异比对
- 指标分析
- 文档生成
- 幻灯片生成
- 自动化调度

### 2.2 方法论不得外包
第三方 skill 可以辅助执行，但 ORIS 的以下部分必须自建：
- 证据协议
- 引用协议
- 事实 / 推断 / 假设 / 风险分层
- 报告结构协议
- 下载交付协议
- 配置治理规则

### 2.3 config-first
- skill 的路由规则、来源优先级、输出协议、报告模板，不得直接写死在业务脚本中
- 所有可变规则进入 config 或数据库

---

## 3. 外部 skill 分层
## 3.1 直接参考 / 可优先纳入
### A. 搜索与竞品研究
- competitor-teardown
- competitive-intelligence-market-research
- competitor-analysis

### B. 文档 / 演示生成
- 2slides-skills
- 文档 / PDF 相关 skill
- 指标仪表盘类 skill

### C. 自动化
- n8n / workflow 类能力
- 定时监控与告警分发能力

---

## 4. ORIS 自建 skill 列表
## 4.1 P0（立即做）
1. insight-source-collector
2. insight-source-normalizer
3. insight-evidence-extractor
4. insight-report-assembler
5. insight-download-packager

## 4.2 P1（很快做）
6. insight-snapshot-diff
7. insight-metric-observer
8. insight-competitor-matrix
9. insight-delivery-router

## 4.3 P2（第二阶段）
10. insight-watch-monitor
11. insight-alert-notifier
12. insight-executive-briefing-ppt
13. insight-industry-template-pack

---

## 5. 各 skill 的职责边界
### 5.1 insight-source-collector
输入：
- 公司
- 主题
- 来源范围
- 时间范围

输出：
- 原始快照
- 原始来源元数据
- storage path

### 5.2 insight-source-normalizer
输入：
- source snapshot

输出：
- 标准化 source
- 去重后的快照记录
- 标签与优先级

### 5.3 insight-evidence-extractor
输入：
- 标准化快照

输出：
- evidence item
- metric observation
- 初步 citation data

### 5.4 insight-snapshot-diff
输入：
- 同一来源不同时间快照

输出：
- 页面变化摘要
- 价格变动
- 功能变更
- 招聘 / 文案 / 定位变化

### 5.5 insight-competitor-matrix
输入：
- target company
- competitor set
- 指标维度

输出：
- feature matrix
- pricing matrix
- evidence-backed SWOT
- 战略差距点

### 5.6 insight-report-assembler
输入：
- analysis run
- evidence set
- citation set

输出：
- Word 报告
- Excel 底表
- 后续 PPT

### 5.7 insight-download-packager
输入：
- artifact list

输出：
- manifest
- zip
- 渠道可下载结果

---

## 6. 报告交付标准
### 6.1 Word
作为正式报告主交付：
- 适合终端用户下载
- 适合 Feishu / Qbot 分发
- 适合作为复盘档案

### 6.2 Excel
作为辅助底表：
- 证据清单
- 来源清单
- 评分表
- 可比矩阵
- 评测结果

### 6.3 PPT
作为管理层与对外汇报版交付：
- 当前不抢先做复杂模板
- 等 Word / Excel / 证据链稳定后接入

---

## 7. 当前结论
### 建议采纳
- skill 生态：用
- 但只用来增强 ORIS
- 不让第三方 skill 替代 ORIS 核心方法论
- 先做数据库与 schema
- 再做 ORIS 自建 skill scaffold
