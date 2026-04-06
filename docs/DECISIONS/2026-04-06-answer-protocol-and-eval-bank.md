# 2026-04-06 Answer Protocol and Eval Bank

## 决策
将 ORIS 的正式回答标准、来源策略、路由原则、回答检查项，以及真实业务评测题库固化入仓库。

## 原因
当前系统已经完成基础通道和推理链路打通，下一阶段重点不再是“能不能回复”，而是“回答是否可商用、可审计、可复盘”。

## 本次落地内容
- docs/ANSWER_PROTOCOL.md
- docs/SOURCE_POLICY.md
- docs/ROUTING_POLICY.md
- config/answer_policy.json
- docs/EVAL_QUESTION_BANK_V1.md
- scripts/evals/oris_eval_bank_v1.json

## 后续要求
1. 所有正式回答逐步对齐 Answer Protocol
2. 所有关键结论必须给出数据、出处、链接
3. 后续每次模型路由或桥接逻辑变更后，至少跑一轮真实题库回归
