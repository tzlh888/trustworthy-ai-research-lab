# Phase 3B 统计分析

## 冻结估计量

风险按从低到高排序，平局使用 `SHA-256("20261015:claim_id")`。AURC 是 k=1…n 的前缀 selective risk 算术平均；R80 使用所有方法共同的 k=70。没有平滑曲线，也没有选择方法特异的覆盖率。

Bootstrap 在完整 141 条测试 claim 上先构造共享 cited document / 相同规范化 claim text 的 connected groups，再保留包含 eligible claim 的组。共有 55 个完整测试组、39 个 eligible-containing 组。执行 10,000 次 paired grouped-bootstrap，seed=20261016；每个 replicate 对所有方法使用完全相同的组抽样，固定风险分数，不重训模型，并按 replicate 的实际 n 重新计算 k80。

## 主要配对比较

| 对比 | 点估计 | 95% percentile CI | 判读 |
|---|---:|---:|---|
| ΔAURC (EARS − B1) | −0.035846 | [−0.076087, −0.003447] | AURC 端点支持 EARS 更低 |
| ΔR80 (EARS − B1) | +0.028571 | [0.000000, 0.063492] | R80 未改善，点估计更差 |

预注册 H1 要求两项差值均为负，且两项 CI 上界都严格小于 0。第二项不满足，因此正式判定为 **H1 INCONCLUSIVE**。这一区分很重要：AURC 的点估计和区间显示全排序改善，不等于预注册联合标准获得支持，也不等于部署阈值已经有效。

所有 10,000 个 replicate 对 AURC/R80 有效；本次各方法 Error AUROC 也均有 10,000 个有效 replicate。原始 replicate 保存在 `reports/phase3b/bootstrap_replicates.csv`。

