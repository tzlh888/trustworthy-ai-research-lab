# Phase 3B 泛化与解释限制

1. 这是同一 SciFact Train 的预冻结内部 hold-out，不是独立外部数据集。分组减少了 shared cited document 和重复文本泄漏，但不能阻断预训练知识、检索候选文档或科学领域之间的依赖。
2. 主评价只有 88 条 eligible claim、39 个 eligible-containing group，统计不确定性仍明显；53 条无 annotated evidence 的测试 claim 不能用于 SUPPORT/CONTRADICT 错误标签。
3. E1 本身较弱：Accuracy 0.488636、45/88 错误。EARS 只排序这些错误风险，不改变 E1 分类，也不能使科学结论变正确。
4. 证据检索 Recall@5 较高不意味着 rationale sentence、NLI 或聚合正确；错误仍主要归入 NLI/reasoning 与 sentence selection 阶段。
5. 通用 `cross-encoder/nli-distilroberta-base` 与科学文本存在可能的领域不匹配，但本阶段没有因果诊断，不能把具体错误归因于该因素。
6. NO_RELATION 是 E1 聚合输出，不是经验证的 evidence insufficiency 标签。本研究没有证明开放世界 evidence insufficiency detection。
7. AURC 改善与 R80 恶化并存，说明排序收益依赖评价位置；本阶段没有选择部署阈值，也没有证明实际决策效用。
8. H2 evidence degradation stress test 与 H3 probability calibration 均未获授权、未执行。没有 Temperature Scaling、ECE 或 Brier Score 结论。
9. 未使用 SciFact Dev 或 official Test，因此也没有 official Test F1。没有验证跨数据集、跨科学领域或真实部署泛化。

