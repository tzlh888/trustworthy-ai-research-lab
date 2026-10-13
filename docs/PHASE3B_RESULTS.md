# Phase 3B 独立测试结果

协议版本：`phase3a-v1.0.0`。本阶段只检验冻结 H1；H2 与 H3 未执行。

## 测试总体

- Frozen Internal Test：141 条 claim。
- 可评价 SUPPORT/CONTRADICT：88 条；无 annotated evidence：53 条，未被改写为 Neutral、Evidence Insufficient 或正确预测。
- 全部 141 条 claim 均先完成 E1 推理和风险评分，之后才解封标签。
- E1 在 88 条 eligible claim 上：43 正确、45 错误，Accuracy 0.488636，Macro-F1 0.505266。
- Gold 分布：58 SUPPORT、30 CONTRADICT；预测为 NO_RELATION 的 eligible claim 为 6 条。
- Retrieval claim Recall@5 为 0.920455；该数值只用于描述 E1 管线，不是 H1 主指标。

## 独立风险排序结果

80% 覆盖的固定接收数为 `floor(0.8 × 88 + 0.5) = 70`。

| 方法 | AURC | Error AUROC | R80 | 80% 接收错误数 | 拒绝错误数 |
|---|---:|---:|---:|---:|---:|
| B0 Maximum Confidence | 0.420457 | 0.666667 | 0.471429 | 33 | 12 |
| B1 NLI-only | 0.300833 | 0.777261 | 0.428571 | 30 | 15 |
| B2 Evidence-only | 0.431151 | 0.575452 | 0.471429 | 33 | 12 |
| Full EARS | 0.264987 | 0.803101 | 0.457143 | 32 | 13 |

Full EARS 相对 B1 的 AURC 更低，但固定 80% 覆盖下风险更高：

- ΔAURC = EARS − B1 = **−0.035846**。
- ΔR80 = EARS − B1 = **+0.028571**，即相同 70 条接收量下多 2 个错误。

因此，EARS 的全曲线排序表现有所改善，但没有同时改善预注册的 R80 端点。H1 的正式结论为 **INCONCLUSIVE**，不能表述为获得独立支持。

机器可读结果见 `reports/phase3b/test_metrics.csv`、`paired_comparisons.csv`、`risk_coverage_curves.csv` 和 `diagnostics.json`。

