# Phase 3B NO_RELATION 敏感性分析

这是预注册的次要分析，不能替代完整 eligible 样本的 H1。

完整 88 条 eligible claim 中有 6 条被冻结 E1 预测为 NO_RELATION，6 条全部错误。这里的 NO_RELATION 是模型输出，不代表自然的 evidence insufficiency。由于该子集的 `y_error` 只有一个类别，各方法的 Error AUROC 均未定义并记录为 NA。

NO_RELATION 子集平均风险：B0 0.317362、B1 0.784569、B2 0.569908、EARS 0.801546。B1 与 EARS 均把这些错误整体赋予较高风险，说明 F3 的 NO_RELATION 指示信息确实影响排序，但不能据此声称完成了 evidence insufficiency detection。

移除 NO_RELATION 后，82 条 claim 内重新排序的结果为：

| 方法 | AURC | R80 |
|---|---:|---:|
| B0 | 0.409307 | 0.439394 |
| B1 | 0.286042 | 0.409091 |
| B2 | 0.411334 | 0.439394 |
| EARS | 0.247566 | 0.424242 |

EARS 的 AURC 优势仍存在，但 R80 仍劣于 B1；因此主要结果不是仅由 6 条 NO_RELATION claim 造成，结论仍是“全曲线排序较好、固定 80% 端点未改善”。按 predicted category 与 gold category 使用全局 k80 接收集的结果在 `reports/phase3b/no_relation_sensitivity.csv` 和 `class_conditional_results.csv` 中完整保存。

