# Evidence-Aware Risk Scoring for Scientific Claim Verification: Replication, Ablation, and Failure Analysis

## Abstract

Selective prediction may reduce harm from scientific claim verifiers by ranking unreliable predictions for review. We study Evidence-Aware Risk Scoring (EARS), an L2 logistic error-ranker that augments natural-language-inference (NLI) uncertainty with a BM25 retrieval-margin feature and an evidence-conflict feature. The historical frozen evaluation found lower EARS discrete area under the risk–coverage curve (AURC) than an NLI-only baseline (B1), but worse selective risk at 80% coverage (R80), yielding an inconclusive preregistered result. We preserve that result and conduct a protocol-frozen same-dataset validation on official SciFact Dev. Among 188 eligible claims in 164 connected groups, B1 achieved AURC 0.2816 and R80 0.4133; EARS achieved AURC 0.2884 and R80 0.4000. Paired group-bootstrap intervals for both differences included zero. F4 alone worsened AURC, while F5 supplied weak conditional signal without reliable endpoint gains. A DeBERTa-based verifier candidate reduced accuracy from 0.4894 to 0.4734. Error analysis attributes the dominant failure to low SUPPORT recall, incomplete evidence-sentence recovery, and NLI/aggregation errors. SciFact-Open fully overlaps original SciFact claims, and HealthVer changes task granularity, so genuine cross-dataset replication was not claimed. The results support a failure-oriented conclusion: evidence-aware features can change rankings, but their incremental value is small, verifier-dependent, and operating-point sensitive.

## 1. Introduction

Scientific claim verification combines information retrieval, evidence selection, and textual inference. A verifier can fail at any stage, and a high-confidence answer is not necessarily correct. Selective prediction addresses this problem by accepting low-risk outputs and deferring high-risk outputs. This work asks whether retrieval ambiguity and disagreement among retrieved evidence provide useful error information beyond NLI behavior.

The original project compared B1, an NLI-only error ranker, with Full EARS. Its frozen Internal Test result improved average AURC but worsened the prespecified 80% operating point. That discrepancy motivated five questions: whether F4/F5 add information, whether it generalizes, whether it transfers to another verifier, why AURC and R80 disagree, and when EARS fails.

## 2. Related Work

SciFact introduced expert-annotated scientific claims and evidence abstracts for retrieval, rationale selection, and label prediction [1]. SciFact-Open expanded evidence discovery toward open-domain retrieval but reuses the original claim set [2]. HealthVer studies health-related evidence–claim relation classification, including Neutral pairs [3]. Selective prediction and risk–coverage evaluation separate prediction quality from the decision to defer [4]. NLI cross-encoders supply sentence-level relation probabilities, but their scores need not be calibrated for pipeline-level errors.

EARS does not claim a new uncertainty theory. It combines established retrieval, NLI, logistic regression, and selective-prediction components to test a narrow incremental-information hypothesis.

## 3. Methodology

### 3.1 E1 verifier

BM25 indexes 5,183 SciFact title-plus-abstract documents with `k1=1.5`, `b=0.75`, and `epsilon=0.25`. The top 20 support retrieval diagnostics; the top five enter NLI. For each, three sentences are selected by global-IDF weighted lexical overlap. The pinned `cross-encoder/nli-distilroberta-base` revision scores 15 premise–claim pairs. Neutral pair predictions are removed; the highest-probability remaining entailment or contradiction determines SUPPORT or CONTRADICT. If none remains, the output is NO_RELATION.

### 3.2 Risk features

F1 is confidence in the exact aggregated decision. F2 is the absolute gap between maximum entailment and contradiction probabilities. F3 is the predicted category, encoded with SUPPORT as reference and two dummy columns. F4 is the normalized BM25 top-two margin. F5 is twice the smaller of entailment/contradiction candidate counts divided by their sum, or zero if both counts are zero.

B1 uses F1–F3; B1+F4 and B1+F5 isolate each evidence feature; EARS uses F1–F5. All use fixed L2 logistic regression with `C=0.1`, identical scaling, no class weighting, and no hyperparameter search.

### 3.3 E1-v2

An exploratory candidate replaces only the NLI model with pinned `cross-encoder/nli-deberta-v3-small`. Retrieval, sentence selection, and aggregation remain unchanged. It is a stronger general NLI encoder, not a scientific-domain model.

## 4. Experimental Setup

The historical SciFact Train partition remains 527 fit, 141 calibration, and 141 Internal Test claims. New development uses fit only. Official SciFact Dev is the final v2 evaluation split. Eligibility requires authentic, non-empty, single-label SUPPORT or CONTRADICT evidence; empty evidence is never mapped to Neutral or NO_RELATION.

The v2 protocol and input hashes were frozen before Dev label evaluation. Claim-only inference produced and hashed scores first. Connected groups use shared cited documents and exact normalized claim text. Discrete AURC averages every prefix risk. R80 accepts `floor(0.8n+0.5)` claims. Ten thousand paired group-bootstrap samples quantify fixed-score uncertainty.

## 5. Results

### 5.1 Historical result

On 88 eligible Internal Test claims, B1/EARS AURCs were 0.300833/0.264987 and R80 values were 0.428571/0.457143. The joint historical criterion was not met: H1 remains INCONCLUSIVE.

### 5.2 SciFact Dev

| Model | AURC ↓ | R80 ↓ | AUROC ↑ |
|---|---:|---:|---:|
| B1 | 0.281575 | 0.413333 | 0.798007 |
| B1+F4 | 0.290272 | 0.406667 | 0.787930 |
| B1+F5 | 0.281007 | 0.406667 | 0.795063 |
| EARS | 0.288355 | 0.400000 | 0.787817 |

EARS-minus-B1 was +0.006780 AURC (95% CI −0.016939 to +0.033066) and −0.013333 R80 (−0.034247 to +0.006849). F4 and F5 contrasts were likewise inconclusive. The frozen numeric B1/EARS models and reconstructed versions agreed on these point results.

### 5.3 Verifier transfer

E1 accuracy was 0.489362; E1-v2 accuracy was 0.473404. Under E1-v2, B1/EARS AURCs were 0.287246/0.264414 and both R80 values were 0.420000. This exploratory pattern suggests feature usefulness can depend on verifier behavior, but it does not establish transfer because E1-v2 is weaker and the comparison lacks a preregistered paired interval.

### 5.4 Error analysis

E1 SUPPORT recall was 0.322581 versus 0.812500 for CONTRADICT. Gold-document recall@5 was 0.842105, but pipeline gold-sentence recall was 0.516393 and complete-rationale recovery 0.684211. NLI/reasoning failures affected 69 errors, sentence selection 19, retrieval 8, and aggregation 20; categories overlap.

### 5.5 Robustness and calibration

Dropping the top document reduced rank correlation to about 0.535 for both methods. Removing one sentence retained about 0.937; irrelevant-evidence injection retained about 0.884. Platt calibration slightly improved B1 proper scores but worsened EARS Brier and log loss. Scores remain unvalidated as probabilities.

## 6. Discussion

F5 exhibits conditional information: its permutation importance is positive and it helps the E1-v2 AURC pattern. Yet the matched Dev ablation supplies no reliable endpoint improvement. F4 is largely independent of other features but does not improve ranking, showing that low collinearity is not sufficient for usefulness.

The historical endpoint conflict is concrete. At 80% coverage, EARS swaps five claims into and five out of the B1 accepted set. Five entering claims are errors, while only three leaving claims are errors. EARS can therefore improve many earlier prefixes—and average AURC—while degrading one discrete boundary. All 39 leave-one-group-out analyses preserve this directional conflict.

The failure mechanism is verifier-centric. SUPPORT evidence is often retrieved but not selected completely, and the aggregation rule favors a high-confidence contradictory candidate. Evidence-aware risk ranking may flag some such cases, but it cannot create missing evidence or repair relation reasoning.

## 7. Limitations

SciFact Dev is not an external dataset and shares 181 cited documents with historical data. SciFact-Open has no non-overlapping claim subset; HealthVer lacks a compatible retrieval task. Samples are modest, calibration is small, bootstrap fixes trained scores, and interaction results are post-hoc. E1-v2 is not scientific-domain adapted. No medical or deployment validity is established.

## 8. Conclusion

The upgraded evidence does not support a general claim that EARS outperforms NLI-only risk scoring. It does show exactly where the method helps, fails, and becomes endpoint-sensitive. That bounded conclusion is scientifically stronger than the earlier aggregate-only account: EARS remains a useful research hypothesis, not a validated deployment method.

## References

1. Wadden, D. et al. “Fact or Fiction: Verifying Scientific Claims.” EMNLP, 2020. https://arxiv.org/abs/2004.14974
2. Wadden, D. et al. “SciFact-Open: Towards Open-Domain Scientific Claim Verification.” 2022. https://arxiv.org/abs/2210.13777
3. Sarrouti, M. et al. “Evidence-based Fact-Checking of Health-related Claims.” EMNLP, 2021.
4. Geifman, Y. and El-Yaniv, R. “Selective Classification for Deep Neural Networks.” NeurIPS, 2017.
5. Liu, Y. et al. “RoBERTa: A Robustly Optimized BERT Pretraining Approach.” 2019.
6. He, P. et al. “DeBERTa: Decoding-enhanced BERT with Disentangled Attention.” ICLR, 2021.
