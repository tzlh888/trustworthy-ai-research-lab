# Phase 3B 错误分析

本分析只解释已冻结输出，不进行模型开发。

45 个 E1 错误中，非互斥失败类别计数为：retrieval failure 2、sentence-selection failure 10、NLI/reasoning failure 33、aggregation failure 14、multiple-document aggregation failure 14、neutral misclassification 6。类别由冻结规则派生；“NLI/reasoning”不能证明错误必然来自领域失配。

## False reassurance

按 EARS 风险从低到高选取的前 10 个实际错误包括 claim 1159、1234、441、682、1258、77、454、1109、394、453。最低风险的 claim 1159 风险为 0.267217，真实 SUPPORT、预测 CONTRADICT，冻结失败分类为 sentence-selection failure。claim 1109 则包含 retrieval failure。可见 EARS 仍会对多种上游失败给出较低风险，不能作为真实性保证。

## Unnecessary rejection

按 EARS 风险从高到低的正确预测包括 claim 98（0.793373）、245（0.776578）、667（0.741128）、105（0.724824）和 765（0.704652）。这些案例说明高风险并不等于错误，选择性预测会损失一部分正确覆盖。

## 与 B1 的 80% 边界交换

EARS 相对 B1 在全局 80% 边界拒绝了 3 个 B1 会接收的错误（claim 246、1138、670），但同时接收了 5 个 B1 会拒绝的错误（claim 223、1134、420、86、85），净结果是多 2 个接收错误。这直接解释了 AURC 改善而 R80 变差的现象。

所有选例均保留 claim 文本、gold evidence 原句与 sentence indices、检索 doc IDs、获胜 premise、NLI 概率、F1–F5、四种风险和失败类别，见 `reports/phase3b/error_analysis_cases.jsonl`。案例同时覆盖有利与不利于 EARS 的结果，没有只挑选支持方法的样本。

