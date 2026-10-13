# Phase 3B 可复现性与完整性记录

## 顺序与封存

1. Phase 0–3A 与 Phase 1/2B 依赖哈希在测试内容读取前通过。
2. 只用 329 条 fit eligible claim 训练最终 B1/B2/EARS；154 正确、175 错误。B1/B2/EARS 分别 11/4/12 次迭代收敛。
3. joblib 与 lossless JSON 在 987 个训练 claim-method 分数上的最大绝对差为 `1.1102230246251565e-16`，通过 `1e-12` 门槛。
4. 模型封存后才读取 141 条测试 claim 文本；2,115 个 E1 sentence pair 在 MPS 上推理。标签解封前已写入 baseline、F1–F5、四方法风险与 prediction freeze manifest。
5. 标签解封后执行 10,000 次 paired grouped-bootstrap；没有重训模型。

## 两次确定性复算

正式评价执行两次。`reproducibility_comparison.json` 比较 11 个关键产物，全部逐字节一致，包括测试风险、主指标、配对比较、10,000 个 bootstrap replicate、曲线、分层分析、案例和 diagnostics。带时间戳的 access log / manifest 与 PNG metadata 被明确排除，未虚构逐字节一致。

## 测试

- Phase 3B 预运行：6 passed，3 个依赖正式产物的集成测试 skipped。
- 全量测试首次在 collection 阶段失败：旧 `tests/test_phase2c.py` 未在默认启动方式下解析仓库 `scripts` 包；没有执行到实验断言。
- 以仓库根显式加入 `PYTHONPATH=.` 后：**61 passed**，用时 3.22 秒。

## 已披露技术事件

第一次无标签推理在写文件前 fail-closed：字段名扫描器把冻结且合法的 `F5_evidence_conflict_rate` 因包含单词 `evidence` 而误报为标签泄漏。没有读取 gold evidence/标签，也没有写预测。完整推理随后从头重跑，仅在运行时把合法 F5 字段加入审计白名单；冻结源码、模型、特征、NLI 与风险分数逻辑未改。事件保存在 `reports/phase3b/technical_incidents.json`。

训练日志的 git 探测还有一个元数据缺陷：无提交仓库中 `git rev-parse HEAD` 退出码为 128，但脚本错误地把 stdout `HEAD` 当作 commit。真实状态是仓库没有可解析 HEAD commit，全部文件仍为 untracked。冻结模型文件未回写；更正保存在 `reports/phase3b/metadata_corrections.json`。这不影响数值结果，但意味着复现依赖 SHA-256 manifests，而不是 Git commit。

本阶段未访问 Calibration、SciFact Dev 或 official Test 来做性能评价；H2/H3 未执行；没有 GitHub push。

