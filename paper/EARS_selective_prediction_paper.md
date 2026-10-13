# Evidence-Aware Risk Scoring for Scientific Claim Verification: A Preregistered Study of Selective Prediction

**Independent student research project**  
**Study period:** 12 October 2026 - 15 November 2026  
**Protocol:** `phase3a-v1.0.0`

## Abstract

Scientific claim verification systems can produce confident decisions even when retrieval or reasoning fails. This study asks whether a small error-risk model that combines inference-time evidence signals with natural-language-inference (NLI) signals can rank verification errors better than an NLI-only risk model. We evaluate Evidence-Aware Risk Scoring (EARS), a preregistered L2 logistic regression over six effective features derived from decision confidence, support-contradiction margin, predicted category, BM25 score separation, and evidence conflict. The base verifier uses BM25 retrieval, lexical sentence selection, and a fixed DistilRoBERTa NLI cross-encoder. Model and feature choices were frozen before accessing a 141-claim Internal Test split drawn from SciFact Train. Of these claims, 88 had authentic SUPPORT or CONTRADICT evidence labels and were eligible for the primary claim-level evaluation. The base verifier achieved 0.488636 accuracy. Relative to the NLI-only B1 risk model, EARS improved area under the discrete risk-coverage curve (AURC: 0.264987 versus 0.300833; paired difference -0.035846, 95% grouped-bootstrap CI [-0.076087, -0.003447]). At the preregistered 80% coverage point, however, EARS was worse (selective risk 0.457143 versus 0.428571; difference +0.028571, 95% CI [0.000000, 0.063492]). Because the joint criterion required both interval upper bounds to be strictly below zero, H1 was inconclusive. A secondary analysis showed that this metric conflict persisted after excluding six eligible claims predicted as NO_RELATION. The results support a narrow conclusion: evidence-aware features changed error ranking and improved average prefix behavior, but did not reliably improve the fixed operating point. They do not establish a generally superior verifier, calibrated error probabilities, evidence-insufficiency detection, or deployment readiness.

## 1. Introduction

Scientific claim verification combines information retrieval and language inference. A system must find potentially relevant scientific documents, identify useful passages, and determine whether they support or contradict a claim. Errors can therefore originate before the final classifier receives its input. A verifier may assign high softmax confidence to a decision based on an irrelevant, incomplete, or misleading sentence. Conversely, a difficult-looking evidence set may still lead to a correct decision. This pipeline structure motivates an error-risk score that observes both the verifier and its retrieved evidence.

Selective prediction provides a framework for studying such scores. A selective system orders predictions from low to high estimated risk and accepts only a chosen fraction. The resulting risk-coverage curve measures how the error rate changes with coverage [2,3]. A common baseline uses maximum softmax probability: high-confidence predictions are accepted first [4]. This baseline is simple and often informative, but softmax scores do not directly represent the truth of a scientific claim, the adequacy of retrieved evidence, or a calibrated probability of correctness.

We study a deliberately modest alternative called Evidence-Aware Risk Scoring (EARS). EARS is not proposed as a novel learning algorithm. It is a frozen combination of established components: BM25 retrieval, a pretrained NLI cross-encoder, inference-time features, standardized inputs, and L2 logistic regression. The independent research question is empirical: after a verifier has produced a prediction, do two evidence-related signals add error-ranking value beyond an otherwise identical NLI-only error model?

The study emphasizes methodology over favorable results. SciFact data were audited before modeling; Train was divided into document-grouped fit, calibration, and Internal Test partitions; risk features and statistics were frozen before test access; predictions were saved before labels were opened; and all primary uncertainty intervals used paired connected-group bootstrap resampling. The final result is mixed. EARS had a lower AURC than the NLI-only comparator, yet it accepted two additional errors at the fixed 80% coverage point. Under the preregistered joint criterion, H1 is therefore inconclusive.

This conflict is scientifically informative. It shows why a single aggregate ranking metric should not be translated automatically into a deployment threshold. It also highlights the limiting role of the base verifier: 45 of 88 eligible test claims were wrong. Risk ranking can help organize mistakes, but it cannot repair the underlying scientific reasoning.

## 2. Related Work

### 2.1 Scientific claim verification

SciFact introduced a benchmark in which systems retrieve abstracts, identify rationales, and predict whether scientific evidence supports or refutes a claim [1]. The dataset contains expert-written claims paired with evidence-bearing abstracts and sentence-level rationales. Later systems strengthened scientific claim verification through sequence-to-sequence retrieval and verification (VerT5erini) [6], full-document context and weak supervision (MultiVerS) [7], and open-domain evaluation over approximately 500,000 abstracts (SciFact-Open) [8]. These works show that retrieval, rationale selection, and label prediction are distinct sources of performance.

Domain-specific pretraining is also relevant. SciBERT demonstrated that pretraining on scientific text can improve a range of scientific NLP tasks [9]. Our base verifier instead uses `cross-encoder/nli-distilroberta-base`, a lightweight general-domain NLI model. This choice makes the experiment feasible on a 24 GB Apple Silicon machine, but creates a plausible domain-mismatch risk. The present study does not causally test that risk.

### 2.2 Selective classification and confidence

Selective classification formalizes a trade-off between coverage and risk [2]. Later work applied selective methods to deep neural networks and studied risk guarantees under rejection [3]. Maximum softmax probability is a widely used baseline for detecting errors and out-of-distribution inputs [4]. It is important, however, to distinguish ranking utility from probability calibration. Calibration asks whether confidence values correspond to empirical frequencies, while selective ranking asks whether errors occur later in the ordered list.

Guo et al. studied temperature scaling as a post-hoc calibration method [5]. Ovadia et al. showed that uncertainty quality and post-hoc calibration can degrade under dataset shift [10]. We did not execute the preregistered calibration hypothesis (H3); EARS outputs are therefore called risk scores, not calibrated error probabilities.

### 2.3 Originality boundary

Logistic regression, standardized features, confidence margins, BM25 scores, and risk-coverage evaluation are established techniques. The contribution of this project is the controlled study design: an inference-only evidence-aware feature set, a matched NLI-only comparator, explicit separation of abstention from labels, leakage controls, a prediction-before-label freeze, and independent reporting of conflicting endpoints. We make no claim that EARS is an algorithmic breakthrough.

## 3. Research Questions

The broader protocol defined three hypotheses, but Phase 3B authorized only H1.

**H1 - Evidence-aware selective risk.** At matched coverage, does Full EARS rank base-verifier errors better than the NLI-only B1 model? The preregistered success rule required both (i) the 95% CI upper bound for EARS-minus-B1 AURC to be strictly below zero and (ii) the corresponding upper bound for selective risk at 80% coverage (R80) to be strictly below zero.

**H2 - Evidence degradation robustness.** Not evaluated. No evidence deletion, replacement, or irrelevant-document stress experiment was executed.

**H3 - Probability calibration.** Not evaluated. No temperature scaling, Brier score, expected calibration error, or calibration-split fitting was executed.

The narrow scope prevents two semantic errors. First, model abstention is an action, not a truth label. Second, an NLI NO_RELATION output is not a validated annotation of evidence insufficiency.

## 4. Dataset

We used the official SciFact release [1,11]. Claims and evidence annotations are distributed under CC BY 4.0, corpus abstracts originate from S2ORC under ODC-By 1.0, and official SciFact code uses Apache-2.0 [11]. The local audit recorded source files and SHA-256 hashes.

Only the 809 claims in the official Train file were partitioned for model development and independent testing. Connected groups were formed using shared cited-document identifiers and identical normalized claim text before assignment. The frozen outer split contained 527 fit claims, 141 calibration claims, and 141 Internal Test claims. Calibration was not used in this study. Original SciFact Dev was restricted to integrity checks, and official Test has no public labels; neither was used for performance evaluation.

Among 527 fit claims, 329 had authentic annotated evidence yielding a single SUPPORT or CONTRADICT label. These 329 claims contained 154 correct and 175 incorrect frozen E1 predictions and formed the final risk-model training population. The other 198 fit claims had no annotated evidence and were not assigned artificial Neutral or Evidence Insufficient targets.

The frozen Internal Test contained 141 claims. All 141 received retrieval, NLI, aggregation, feature extraction, and risk scoring before labels were read. After label unsealing, 88 claims were eligible for primary evaluation and 53 had no annotated evidence. The eligible gold distribution was 58 SUPPORT and 30 CONTRADICT. All primary methods used exactly the same 88 claims.

## 5. Methodology

### 5.1 Base verifier (E1)

The end-to-end verifier uses BM25Okapi over title-plus-abstract text with `k1=1.5`, `b=0.75`, and `epsilon=0.25`. Tokenization applies Unicode normalization, case folding, and a word-token regular expression without stemming or stop-word removal. The top 20 documents are retained for retrieval diagnostics. For NLI, the top five documents are used, and the three sentences per document with greatest global-IDF weighted lexical overlap are selected. This creates 15 premise-hypothesis pairs per claim.

The premise is a retrieved sentence and the hypothesis is the scientific claim. The pinned NLI model is `cross-encoder/nli-distilroberta-base` at revision `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`, with label IDs contradiction=0, entailment=1, and neutral=2. Inputs use longest-first truncation at 512 tokens. Entailment maps to SUPPORT and contradiction maps to CONTRADICT. Neutral sentence predictions are removed before claim aggregation. The highest-probability remaining SUPPORT or CONTRADICT candidate wins; if no non-neutral candidate remains, the claim prediction is NO_RELATION.

### 5.2 Frozen features

All risk features are available at inference time and use no gold label, gold document ID, rationale index, correctness flag, or split membership.

- **F1 decision confidence:** probability aligned to the final aggregation decision. For NO_RELATION, the rule uses the minimum sentence-level neutral probability.
- **F2 support-contradiction margin:** absolute difference between the maximum entailment and contradiction probabilities across candidate sentences.
- **F3 predicted category:** two fixed dummy variables for CONTRADICT and NO_RELATION, with SUPPORT as the reference.
- **F4 BM25 top-two normalized margin:** `(score1 - score2) / (|score1| + |score2| + 1e-12)`.
- **F5 evidence conflict rate:** twice the smaller of the entailment-candidate and contradiction-candidate counts divided by their sum; zero if both counts are zero.

The six effective columns are F1, F2, two F3 dummies, F4, and F5. Continuous columns are standardized using population means and standard deviations estimated only from the 329 eligible fit claims. Categorical dummies are not scaled.

### 5.3 Compared risk methods

**B0 - Maximum Confidence:** `risk = 1 - F1`. No model is trained.

**B1 - NLI-only:** L2 logistic regression using F1, F2, and F3 (four effective columns).

**B2 - Evidence-only:** the same logistic regression using F4 and F5.

**Full EARS:** the same logistic regression using F1-F5 (six effective columns).

B1 is the primary comparator because it controls for model family, training examples, target, regularization, solver, and preprocessing while excluding only F4-F5. B1 and EARS were both trained on all 329 eligible fit claims using `C=0.1`, `solver=lbfgs`, L2 regularization, no class weighting, tolerance `1e-6`, and a maximum of 2,000 iterations. No hyperparameter search followed test access. B1 converged in 11 iterations, B2 in 4, and EARS in 12.

### 5.4 Serialization and access controls

Each final model was saved as a joblib bundle with its fitted preprocessor and as a lossless JSON numeric specification. Rescoring all 987 fit claim-method combinations yielded a maximum absolute difference of `1.11e-16`, below the `1e-12` gate.

The Phase 3A protocol and all predecessor hashes were verified before model fitting. Final model hashes were then frozen. Only after this freeze were the 141 Internal Test claim texts deserialized. E1 predictions, features, and B0/B1/B2/EARS scores were hashed before authentic evidence labels were opened. Models were not retrained after label access.

## 6. Experimental Setup

The evaluation unit is the claim. For each risk method, eligible claims are sorted from low to high risk. Ties use the SHA-256 digest of `20261015:claim_id`. At every prefix `k=1,...,n`, coverage is `k/n` and selective risk is accepted errors divided by `k`. AURC is the arithmetic mean of these n prefix risks; it is not a trapezoidal integral or oracle-normalized score.

R80 uses `k=floor(0.8n+0.5)`. With n=88, all methods accept exactly 70 claims. The primary differences are EARS minus B1, so negative values favor EARS.

Uncertainty intervals use 10,000 paired connected-group bootstrap replicates with seed 20261016. Groups were formed on all 141 Internal Test claims before eligibility filtering, using shared cited-document IDs or identical normalized claim text. There were 55 complete test groups and 39 groups containing at least one eligible claim. Each replicate samples groups with replacement and applies the same draws to all methods. Risk models are never retrained inside bootstrap. AURC and the replicate-specific rounded 80% prefix are recomputed for every sample. Percentile intervals use linear 2.5th and 97.5th percentiles.

## 7. Results

### 7.1 Base verification

E1 correctly classified 43 of 88 eligible claims and made 45 errors, for accuracy 0.488636. Macro-F1 over SUPPORT and CONTRADICT was 0.505266. The confusion matrix showed 20 correct SUPPORT predictions, 23 correct CONTRADICT predictions, 35 SUPPORT claims predicted CONTRADICT, four CONTRADICT claims predicted SUPPORT, and six eligible claims predicted NO_RELATION. Retrieval claim Recall@5 was 0.920455 (81/88); this does not imply that the selected sentence or final NLI decision was correct.

### 7.2 Selective risk

| Method | AURC | Error AUROC | R80 | Errors among 70 accepted | Errors among 18 rejected |
|---|---:|---:|---:|---:|---:|
| B0 | 0.420457 | 0.666667 | 0.471429 | 33 | 12 |
| B1 | 0.300833 | 0.777261 | 0.428571 | 30 | 15 |
| B2 | 0.431151 | 0.575452 | 0.471429 | 33 | 12 |
| Full EARS | **0.264987** | **0.803101** | 0.457143 | 32 | 13 |

EARS had the lowest AURC and highest descriptive error-detection AUROC. Evidence-only B2 performed worse than B1 and EARS, indicating that F4-F5 were not sufficient risk signals by themselves. Maximum-confidence B0 also underperformed B1, consistent with observed high-confidence errors.

At R80, however, B1 was best among the four frozen methods. EARS accepted 32 errors versus B1's 30. This endpoint conflict is visible in the risk-coverage curves: EARS is often below B1 at lower and intermediate coverage, but the order does not guarantee a better prefix at exactly 70 accepted claims.

## 8. Statistical Analysis

The paired AURC difference was `-0.035846`, with 95% CI `[-0.076087, -0.003447]`. For this estimand, the entire interval favored EARS. The paired R80 difference was `+0.028571`, with CI `[0.000000, 0.063492]`. Its point estimate favored B1, and the interval did not have a strictly negative upper bound.

The preregistered decision rule required both point differences to be negative and both CI upper bounds to be strictly below zero. That rule was not satisfied. The formal result is:

**H1 INCONCLUSIVE under the preregistered joint criterion.**

This statement is stronger than saying that results were mixed and weaker than claiming that EARS failed in every respect. The AURC analysis supplies independent evidence of an average ranking improvement, but the fixed operating point does not. Reporting only AURC would be favorable-result selection; reporting only R80 would discard the broader curve.

The 88-claim, 39-group effective sample also limits precision. Grouped resampling appropriately preserves known cited-document dependence, but cannot account for all similarities among scientific topics, retrieved candidates, or pretrained knowledge.

## 9. Error Analysis

Frozen non-exclusive diagnostics assigned 33 of 45 errors to NLI-or-reasoning failure, ten to sentence-selection failure, two to retrieval failure, 14 to aggregation failure, 14 to multiple-document aggregation failure, and six to neutral misclassification. These are rule-based pipeline diagnoses, not causal proof.

### 9.1 High NLI softmax and false reassurance

Maximum softmax confidence was not a reliable truth indicator. Claim 1159 was a SUPPORT claim predicted CONTRADICT with B0 risk approximately 0.00194, meaning the winning NLI class probability was approximately 0.998. EARS raised the risk to 0.267, yet this remained among its lowest-risk errors. Other low-EARS-risk errors included claims 1234, 441, 682, and 1258. These cases show two distinct limitations: EARS can correct part of an overconfident ranking, but evidence-aware metadata cannot guarantee recognition of a wrong scientific decision.

### 9.2 Unnecessary rejection

Some correct decisions received high EARS scores. Correct claims 98 and 245 had EARS scores 0.793 and 0.777. A selective system that rejects high-score cases therefore sacrifices correct coverage as well as errors. A risk score must be judged by the ordering as a whole, not by interpreting any single value as a probability.

### 9.3 The R80 boundary

At the common 70-claim acceptance boundary, EARS rejected three errors that B1 accepted (claims 246, 1138, and 670) but accepted five errors that B1 rejected (claims 223, 1134, 420, 86, and 85). The net difference was two additional accepted errors. This local exchange explains how an improved AURC can coexist with worse R80.

### 9.4 NO_RELATION

Six eligible claims were predicted NO_RELATION and all six were errors. Their mean EARS score was 0.801546, so EARS generally ranked them as risky. Error AUROC within this subset is undefined because only one error class is present. After excluding these six claims and reranking the remaining 82 without retraining, EARS still improved AURC over B1 (0.247566 versus 0.286042) but remained worse at R80 (0.424242 versus 0.409091). The overall conflict is therefore not solely a NO_RELATION artifact. Nevertheless, NO_RELATION is a powerful feature value in this dataset and must not be reinterpreted as validated evidence insufficiency.

## 10. Discussion

The fairest positive interpretation is narrow: adding BM25 score separation and evidence-conflict rate to the matched NLI-only model improved average error ranking on a previously unseen internal split. This effect persisted when NO_RELATION predictions were removed. It suggests that evidence-pipeline signals can contain information not fully represented by NLI confidence and category.

The negative interpretation is equally important. The evidence features did not improve the preregistered R80 operating point. Evidence-only B2 was weak. The base verifier was wrong on more than half of eligible claims. An EARS score is produced by a logistic regression trained on this verifier's historical errors; it cannot identify whether the underlying scientific literature is complete, whether a retrieved abstract is methodologically sound, or whether a claim is true in the world.

AURC and R80 answer related but different questions. AURC averages every discrete coverage prefix, emphasizing global ordering. R80 evaluates one local prefix fixed in advance. An improved global ordering can still place a few errors on the wrong side of a specific boundary. This is not a mathematical contradiction and should not be resolved by selecting whichever metric is more favorable after seeing the data.

The experiment also illustrates the danger of treating softmax as epistemic certainty. B0's AURC was 0.420457, substantially worse than B1 and EARS, and several errors had very high winning-class probabilities. The result does not imply that confidence is useless: F1 remains an input to both B1 and EARS, and B1 was the strongest method at R80. Rather, confidence becomes more useful when interpreted within a carefully defined error-ranking task instead of as direct scientific truth.

## 11. Limitations

First, the independent sample contains only 88 eligible claims and 39 eligible connected groups. Bootstrap intervals cannot create information absent from this small sample. Second, the Internal Test is a held-out portion of SciFact Train, not an external dataset. Grouping addresses two observed leakage channels but not shared scientific domains, retrieval candidates, or pretraining exposure.

Third, 53 test claims lacked annotated evidence and could not support a primary SUPPORT/CONTRADICT error target. The study does not evaluate naturally occurring evidence insufficiency. Fourth, the verifier uses a general-domain sentence-level NLI model and simple lexical sentence selection; full-document scientific models such as MultiVerS represent stronger alternatives, but were not substituted after protocol freeze.

Fifth, EARS scores are uncalibrated ranking outputs. H3 was not evaluated, so values such as 0.80 must not be described as an 80% chance of error. No deployment threshold was selected. The 80% coverage point is an experimental estimand, not an instruction to accept predictions below a numerical score.

Sixth, failure-stage labels are diagnostic rules based on retrieval hits, rationale coverage, NLI predictions, and aggregation. They cannot prove why a model failed. Finally, no medical, clinical, or other high-stakes utility evaluation was conducted. The system must not be used to validate treatment claims or replace expert assessment.

## 12. Conclusion

This preregistered study tested whether a frozen evidence-aware error model generalizes beyond fit-only analysis. Full EARS improved AURC relative to a matched NLI-only comparator, with a paired interval below zero. At the preregistered 80% coverage point, it performed worse, accepting two more errors, and the paired interval did not favor EARS. H1 is therefore inconclusive under the joint criterion.

The main contribution is not a claim of universal superiority. It is a reproducible negative-and-positive result: evidence-aware signals can alter and sometimes improve error ranking, while their benefit may not survive at a particular operating point. H2 and H3 remain unevaluated. A stronger verifier, external test data, and separately preregistered robustness and calibration studies would be required before making broader reliability claims.

## References

[1] D. Wadden, S. Lin, K. Lo, L. L. Wang, M. van Zuylen, A. Cohan, and H. Hajishirzi. “Fact or Fiction: Verifying Scientific Claims.” *EMNLP*, 2020, pp. 7534-7550. https://doi.org/10.18653/v1/2020.emnlp-main.609

[2] R. El-Yaniv and Y. Wiener. “On the Foundations of Noise-free Selective Classification.” *Journal of Machine Learning Research*, 11(53):1605-1641, 2010. https://www.jmlr.org/papers/v11/el-yaniv10a.html

[3] Y. Geifman and R. El-Yaniv. “Selective Classification for Deep Neural Networks.” *Advances in Neural Information Processing Systems 30*, 2017. https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html

[4] D. Hendrycks and K. Gimpel. “A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks.” *ICLR*, 2017. https://arxiv.org/abs/1610.02136

[5] C. Guo, G. Pleiss, Y. Sun, and K. Q. Weinberger. “On Calibration of Modern Neural Networks.” *ICML*, PMLR 70:1321-1330, 2017. https://proceedings.mlr.press/v70/guo17a.html

[6] R. Pradeep, X. Ma, R. Nogueira, and J. Lin. “Scientific Claim Verification with VerT5erini.” *Louhi Workshop*, 2021, pp. 94-103. https://aclanthology.org/2021.louhi-1.11/

[7] D. Wadden, K. Lo, L. L. Wang, A. Cohan, I. Beltagy, and H. Hajishirzi. “MultiVerS: Improving Scientific Claim Verification with Weak Supervision and Full-document Context.” *Findings of NAACL*, 2022, pp. 61-76. https://doi.org/10.18653/v1/2022.findings-naacl.6

[8] D. Wadden, K. Lo, B. Kuehl, A. Cohan, I. Beltagy, L. L. Wang, and H. Hajishirzi. “SciFact-Open: Towards Open-domain Scientific Claim Verification.” *Findings of EMNLP*, 2022, pp. 4719-4734. https://doi.org/10.18653/v1/2022.findings-emnlp.347

[9] I. Beltagy, K. Lo, and A. Cohan. “SciBERT: A Pretrained Language Model for Scientific Text.” *EMNLP-IJCNLP*, 2019, pp. 3615-3620. https://doi.org/10.18653/v1/D19-1371

[10] Y. Ovadia, E. Fertig, J. Ren, Z. Nado, D. Sculley, S. Nowozin, J. V. Dillon, B. Lakshminarayanan, and J. Snoek. “Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty under Dataset Shift.” *NeurIPS*, 2019. https://proceedings.neurips.cc/paper/2019/hash/8558cb408c1d76621371888657d2eb1d-Abstract.html

[11] Allen Institute for AI. “SciFact repository and license.” https://github.com/allenai/scifact (accessed 13 October 2026).

## Research Integrity and Contribution Statement

The project owner defined the research objective, approved the staged protocols, controlled release decisions, and is responsible for understanding and defending the conclusions. AI-assisted tools supported literature discovery, code generation, statistical implementation, document drafting, and reproducibility checks. Numerical claims were checked against frozen machine-readable artifacts, and final scientific interpretations were constrained by preregistered rules. No publication, peer review, institutional affiliation, research supervisor, or external validation is claimed.

## Appendix A. Reproducibility Checklist

**Data provenance.** The study used files from the official Allen Institute for AI SciFact repository. The local audit recorded the download source, file SHA-256 values, row counts, field schemas, and licensing distinctions between claims/annotations, abstracts, and code. Raw data are not included in the public release candidate; users are directed to the official source and checksum-verifying workflow.

**Frozen software inputs.** The base verifier used `cross-encoder/nli-distilroberta-base` at revision `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`. The final risk models used scikit-learn 1.9.1, NumPy 2.5.4, SciPy 1.18.1, and joblib 1.6.0. The recorded Apple Silicon run used Python 3.12.15 and PyTorch 2.14.1. Exact requirements and model metadata are stored with the research package.

**Seeds and deterministic rules.** The split seed was 20261012, cross-fit allocation seed 20261013, logistic-model seed 20261014, risk-ranking tie seed 20261015, and grouped-bootstrap seed 20261016. Tie resolution, connected-group construction, standardization with population standard deviation, and the discrete AURC formula were specified before Internal Test access.

**Access order.** Predecessor hashes were checked first. B1, B2, and EARS were fit on exactly 329 eligible fit claims and serialized. The 141 Internal Test claim texts were then processed without deserializing labels. Baseline predictions, F1-F5, and four risk scores were saved and hashed. Authentic evidence labels were opened only after this prediction freeze. The Internal Test is now permanently considered used.

**Independent recomputation.** The final evaluation was executed twice using frozen scores and labels. Eleven key outputs - including risk predictions, main metrics, paired contrasts, all 10,000 bootstrap replicates, risk-coverage curves, sensitivity tables, and case records - were byte-identical. Joblib and lossless JSON risk implementations agreed within `1.11e-16` on all fit claim-method combinations.

**Explicit exclusions.** No calibration fitting, temperature scaling, deployment-threshold selection, evidence-degradation intervention, SciFact Dev evaluation, official Test evaluation, external-dataset validation, or post-test model selection was performed. H2 and H3 remain Not Evaluated. These exclusions are methodological boundaries, not missing values to be inferred from H1.

