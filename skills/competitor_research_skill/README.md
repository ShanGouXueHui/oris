# competitor_research_skill

当前版本：`db_backed_beta`

定位：
- 作为 ORIS 的竞争对手研究 skill
- 不再只输出 scaffold 文本
- 直接编排 `official_source_ingest_skill`
- 将目标公司及竞争对手的官方来源采集入库
- 再从 insight DB 读取 snapshot / evidence / metric / citation 汇总，输出对标矩阵

当前阶段能力：
- 接收目标公司、竞争对手、维度、实体级 sources
- 逐个实体调用 `official_source_ingest_skill`
- 输出 DB-backed benchmark 结果
- 生成可被 `account_strategy_skill` 与 `report_build_skill` 消费的 comparison JSON

后续升级：
- 真正写入 `competitor_set / competitor_set_member`
- 加入更丰富的 metric normalization 与评分逻辑
- 接入 Word / Excel / PPT 正式物料生成
