# ORIS Entity Detection Policy

## 1. 目标
对 `company_profile` 类请求，系统只能识别一个 `target_company`。  
重点不是“尽量猜一个”，而是“尽量只在足够确定时输出一个正确目标公司”。

---

## 2. 必须避免的错误
- 把行业概念识别成公司  
  例如：`AI Agent`、`Workflow Automation`、`Developer Tooling`
- 把竞品/对比对象抢成主实体
- 把合作方/云厂商抢成主实体
- alias 一词多义时直接强绑到错误 canonical
- 识别失败后仍继续生成 company_profile 正文

---

## 3. 检测链路
1. compiler 做任务类型与问题抽取  
2. `company_entity_detector.py` 执行目标公司识别  
3. `entity_resolution.json` 做 canonical normalize  
4. 返回标准字段：
   - `target_company`
   - `confidence`
   - `method`
   - `reason`
   - `aliases`
5. 若结果为 `unknown / ambiguous / low_confidence`，则阻断 company_profile 正文生产

---

## 4. 推荐检测顺序
### 第一层：registry / exact / alias
- 先查 `config/insight_entity_registry.json`
- exact 命中优先于 fuzzy
- alias 命中必须满足“一对一、无歧义”

### 第二层：guarded local detection
- 允许本地规则做快速识别
- 但行业词、角色词、产品类词、地域词必须进入负面规则集
- local detect 只负责提名，不负责越权覆盖 canonical registry

### 第三层：LLM fallback
- 仅在前两层无法确定时启用
- LLM 输出必须结构化
- LLM 返回公司名后，仍需经过 resolution normalize
- 不允许 LLM 结果直接跳过 resolution 进入主链路

---

## 5. 阻断规则
出现以下任一情况，必须返回阻断而非垃圾正文：

- `target_company == unknown`
- alias 命中存在多义
- 命中的实体属于行业概念、能力标签、方法论、产品类别
- 用户请求本质上是“比较多个公司”，而不是单公司画像
- `confidence` 低于配置阈值
- 识别出的主实体只出现在 competitor / partner / vendor 槽位，没有明确主语地位

---

## 6. 主实体与竞品的边界
- `target_company` 只代表本次主分析对象
- `competitors` 是辅分析对象，不能反向污染主实体
- 若用户输入是“比较 A 与 B”，应优先进入 competitor benchmark / compare flow，而不是硬塞进 company_profile

---

## 7. 配置治理
以下文件必须视为正式配置，而不是临时脚本常量：
- `config/company_entity_detection.json`
- `config/entity_resolution.json`
- `config/company_focus_config.json`
- `config/insight_entity_registry.json`

规则：
- 行业负面词、模糊 alias、低置信度阈值，放配置文件
- 不在脚本里散落硬编码术语表
- 高频运营调优项，后续可迁移到数据库或管理端

---

## 8. 输出治理
识别成功：
- 进入 official ingest / company profile 主链路
- 渲染聊天版正文
- 注册正式报告产物

识别失败：
- 发送简短阻断说明
- 不发送 prompt、bootstrap、placeholder、空报告
- worker 日志写清楚失败原因，便于后续治理

---

## 9. 验证样例
### 应命中主实体
- “分析 Akkodis”
- “帮我做一份赛力斯公司画像”
- “看看引望的竞争力”

### 应阻断
- “AI Agent 行业现在怎么样”
- “Developer Tooling 最近趋势如何”
- “帮我看看 workflow automation”

### 应走比较流，而非 company_profile
- “比较华为云和阿里云”
- “Akkodis 和 Alten 谁更强”
