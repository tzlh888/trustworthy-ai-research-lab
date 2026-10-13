# Phase 3B 准出决策

## 决策摘要

**H1：INCONCLUSIVE。下一研究阶段：CONDITIONAL GO。**

该结论允许在新协议和不复用当前 Internal Test 进行首次验证声明的前提下，开展独立 H2/H3 或外部复制；它不是对 Phase 4 发布、部署或“EARS 已被证实有效”的 GO。

## 必答问题

1. Internal Test 共 141 条，实际 eligible 为 **88** 条；其余 53 条无 annotated evidence。
2. E1：Accuracy **0.488636**、Macro-F1 **0.505266**、**45** 个错误。
3. EARS：AURC **0.264987**；R80 **0.457143**（70 条中 32 个错误）。
4. B1：AURC **0.300833**；R80 **0.428571**（70 条中 30 个错误）。
5. EARS 只改善 AURC；R80 恶化 0.028571，因此未同时改善两项。
6. ΔAURC 95% CI 为 **[−0.076087, −0.003447]**；ΔR80 95% CI 为 **[0.000000, 0.063492]**。联合预注册标准不满足。
7. Phase 2B 的轻微 OOF 双指标优势未完整保持：独立测试保留了 AURC 优势，没有保留 R80 优势。
8. NO_RELATION 没有单独主导结论：去除其 6 条全错样本后，EARS 仍改善 AURC、仍劣于 B1 的 R80；但 F3/NO_RELATION 对风险有明显贡献。
9. 存在明确 false reassurance，最低 EARS 风险错误为 claim 1159（风险 0.267217）；完整 10 例已保存。
10. Evidence-aware 特征对 AURC 排序的增量有独立证据，但对预注册 R80 没有可信增益；不能宣称总体增量贡献得到确认。
11. 三模型序列化通过 `1e-12` 一致性；两次统计复算的 11 个关键文件逐字节一致；全量测试 61 passed。训练日志的 Git 状态探测错误已单独更正，未影响数值。
12. H2 与 H3 均 **Not evaluated in Phase 3B**；外部数据泛化、开放世界 evidence insufficiency 和部署阈值也未解决。
13. 可以有条件进入预注册的 H2/H3 或外部复制设计；当前证据不足以进入以有效性宣称或部署为目标的 Phase 4。

## 条件

- 当前 Internal Test 已使用，任何模型、特征或阈值修改都不能再把它称为首次独立验证。
- 后续若修改 EARS，必须使用新的独立数据或建立清晰的探索/确认隔离。
- H2 必须建立真实、可审计的 evidence degradation 条件；H3 必须另行冻结 calibration 数据、ECE/Brier 与 Temperature Scaling 协议。
- 对外报告必须同时展示 AURC 改善和 R80 恶化，不能只选有利端点。

