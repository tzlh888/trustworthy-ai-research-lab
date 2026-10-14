# Evidence-Aware Risk Scoring for Scientific Claim Verification: A Protocol-Frozen Study with Corrective Replay and Failure Analysis

**Research chronology:** Public repository records and generated artifacts support work during 13-14 October 2026. Exact earlier execution chronology is documented only where supported by available records. A previous archival paper listed 15 November 2026 as the end of a completed study period; that future date was not supportable and is not used here.  
**Protocol status:** The historical and original V2 studies used internal protocol freezes and hash gates. No third-party or publicly registered preregistration is claimed.  
**Latest scientific correction:** 14 October 2026.

## Abstract

Scientific claim verifiers can be confidently wrong because retrieval, evidence selection, natural-language inference (NLI), or aggregation can fail. This study examines whether Evidence-Aware Risk Scoring (EARS), an L2 logistic error ranker that adds retrieval-margin and evidence-conflict features to NLI-derived uncertainty, ranks errors more effectively than a matched NLI-only model (B1). The historical frozen Internal Test contained 88 eligible claims in 39 connected groups. EARS improved discrete area under the risk-coverage curve (AURC: 0.264987 versus 0.300833) but worsened selective risk at 80% coverage (R80: 0.457143 versus 0.428571); the frozen conclusion remains H1 INCONCLUSIVE. Original V2 evaluated official SciFact Dev under an internally frozen protocol. Among 188 eligible claims in 164 groups, B1 achieved AURC 0.281575 and R80 0.413333, while EARS achieved AURC 0.288355 and R80 0.400000. Paired group-bootstrap intervals crossed zero for both differences. A 14 October corrective audit found that the historical V2 inference script had deserialized complete Dev JSON records while discovering IDs, although no annotation use in scoring was demonstrated. A restricted ID-and-claim parser was implemented and adversarially tested. Corrective E1 and E1-v2 replay produced exact scoring equality with the historical V2 artifacts. Post-hoc overlap sensitivity found that the two normalized-text duplicates were ineligible; after excluding Dev claims citing historical documents, 64 eligible claims in 53 groups remained, with EARS lower in AURC but tied at R80 and intervals crossing zero. Marginal permutation importance suggests model-dependent association for the evidence-conflict feature, but matched ablations do not establish stable incremental benefit. The evidence supports a bounded failure-oriented conclusion, not general EARS superiority, external replication, calibrated probabilities, or deployment readiness.

## 1. Introduction

Scientific claim verification combines document retrieval, sentence selection, relation classification, and claim-level aggregation. A mistake at any stage can produce a confident but wrong output. Selective prediction adds a second model that ranks predictions by estimated error risk, allowing a system to defer high-risk cases. This can be useful only if the risk ordering generalizes and if its scores are not confused with scientific truth or calibrated probability.

This project studies EARS, a compact risk ranker that augments NLI-derived signals with two label-free evidence-pipeline features. The goal is not to introduce a new uncertainty theory. It is to test whether retrieval separation and disagreement among evidence sentences carry useful predictive association beyond NLI confidence and predicted category.

The historical study produced a metric conflict: EARS improved average risk-coverage ordering but performed worse at one prespecified operating point. Original V2 added SciFact Dev evaluation, matched feature ablations, an alternative NLI encoder, and failure analysis. The present correction repairs provenance and terminology without changing the frozen scientific results.

## 2. Related Work

SciFact introduced expert-written claims paired with scientific abstracts, evidence labels, and rationales [1]. SciFact-Open evaluates scientific claim verification against a much larger open-domain corpus, but reuses the original claim set and uses pooled evidence annotation [2]. HealthVer contains health-related claim-evidence pairs labeled Supports, Refutes, or Neutral [3]; its pair-level supplied-evidence task is not equivalent to this project's claim-level retrieval and aggregation pipeline.

Selective classification studies how risk changes as a model accepts or rejects predictions [4, 5]. Maximum softmax confidence is a common baseline for error detection, but neural confidence can be miscalibrated [6] and uncertainty can degrade under shift [7]. Scientific-domain encoders and full-document verification systems such as SciBERT and MultiVerS show the importance of domain representation and evidence context [8, 9]. EARS uses established retrieval, NLI, logistic regression, and selective-prediction components rather than claiming a novel algorithm.

## 3. Research Questions

1. Do retrieval and evidence-consistency features offer incremental predictive information beyond NLI-derived uncertainty?
2. Does any incremental information generalize beyond the historical Internal Test?
3. Does evidence-aware risk scoring remain useful when the underlying verifier changes?
4. Why can average risk-coverage ranking improve while a fixed operating point deteriorates?
5. Under what conditions does EARS fail, and what do those failures reveal about selective prediction for scientific claim verification?

## 4. Methodology

### 4.1 E1 verifier

E1 indexes 5,183 SciFact title-plus-abstract documents with BM25 (`k1=1.5`, `b=0.75`, `epsilon=0.25`). The top 20 documents support retrieval diagnostics; the top five enter inference. Three sentences per document are selected by global-IDF weighted lexical overlap. The pinned `cross-encoder/nli-distilroberta-base` revision `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd` scores 15 sentence-claim pairs. Neutral pair predictions are removed. The highest-probability remaining entailment or contradiction determines SUPPORT or CONTRADICT; if none remains, the output is NO_RELATION.

### 4.2 Risk features and matched models

F1 is confidence aligned to the final aggregated decision. F2 is the absolute difference between maximum entailment and contradiction probabilities. F3 is the predicted claim category, represented by CONTRADICT and NO_RELATION dummies with SUPPORT as reference. F4 is the normalized BM25 top-two score margin. F5 is the evidence-conflict rate, computed from the counts of entailment and contradiction sentence candidates.

Four matched L2 logistic models use the same 329 eligible fit claims, error target, scaling, `C=0.1`, solver, and absence of class weighting or outcome-driven hyperparameter search:

| Model | Feature set |
|---|---|
| B1 | F1-F3 |
| B1 + F4 | F1-F4 |
| B1 + F5 | F1-F3 and F5 |
| Full EARS | F1-F5 |

### 4.3 E1-v2

The exploratory E1-v2 candidate replaces only the NLI encoder with pinned `cross-encoder/nli-deberta-v3-small` revision `e9890682d9e4279b7ae6d0fcfb435a43206280ec`. Retrieval, sentence selection, and aggregation are unchanged. This is a general-domain model substitution, not scientific-domain adaptation.

## 5. Experimental Protocol

The historical SciFact Train partition contains 527 fit, 141 calibration, and 141 Internal Test claims. The Internal Test has 88 eligible SUPPORT or CONTRADICT claims. The original Phase 3 protocol was internally frozen before Internal Test evaluation; its public artifacts report 39 eligible connected groups and H1 INCONCLUSIVE. H2 and H3 remain NOT EVALUATED in that historical study.

Original V2 used official SciFact Dev. Eligibility required authentic, non-empty, single-label SUPPORT or CONTRADICT evidence; empty evidence was never converted to Neutral or NO_RELATION. The V2 protocol file was internally frozen at SHA-256 `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`. It is unchanged by this correction.

The correction is not a fresh evaluation: Dev results were already known. The original V2 script projected claim text for scoring but first used a full-record loader to discover Dev IDs, causing complete annotation-bearing JSON objects to be deserialized. There is no observed evidence that annotation values affected retrieval, NLI inputs, feature extraction, or risk scoring, but the historical claim of perfect label-blind deserialization was too strong. The corrected parser validates each JSON record while materializing only `id` and `claim`, preserves partition-aware identities, and rejects malformed records, duplicate keys, duplicate IDs, missing fields, and invalid types. Corrective outputs are stored separately.

## 6. Datasets and Overlap Audit

SciFact Dev contains 300 claims, of which 188 are eligible for the primary B1/EARS error-ranking comparison. It is a separate official split but not a new scientific literature source. Relative to all 809 historical SciFact Train claims, Dev has zero exact claim-ID overlaps, two normalized claim-text overlaps, and 181 shared cited documents.

SciFact-Open was audited at commit `6fc2e2f2f97001f2fadb882600beb3e984d77aad`. All 279 claims duplicate original SciFact claim IDs and normalized texts, and no strict claim-and-evidence non-overlap subset exists. HealthVer contains 14,330 supplied evidence-claim pairs, but no equivalent abstract retrieval corpus or F4 definition. Neither dataset was forced into an invalid full-pipeline comparison. No genuine compatible cross-dataset replication was completed.

## 7. Statistical Methods

Predictions are ranked from lower to higher error risk. Discrete AURC is the arithmetic mean of selective risk at every accepted prefix. R80 accepts `floor(0.8n+0.5)` claims. Error AUROC treats an incorrect E1 prediction as the positive class. Connected groups are formed using shared cited documents and normalized claim identity.

Original V2 uncertainty uses 10,000 paired connected-group bootstrap draws with seed 20261016. The same sampled groups are applied to every compared fixed score vector. Scores and models are not retrained within bootstrap, so the intervals describe sampling variability conditional on the trained models and realized inference outputs, not training or model-selection uncertainty. The post-hoc overlap sensitivity uses 10,000 connected-group draws with seed 20261020 where at least 30 eligible claims, 20 groups, and both error classes remain.

Permutation importance is ordinary marginal feature permutation within a fitted multivariable model. It is not conditional permutation importance, does not isolate causal effects, and is not a substitute for matched model comparison.

## 8. Results

### 8.1 Historical Internal Test

| Model | Eligible claims / groups | AURC | R80 | Accepted errors at 80% |
|---|---:|---:|---:|---:|
| B1 | 88 / 39 | 0.300833 | 0.428571 | 30 / 70 |
| EARS | 88 / 39 | 0.264987 | 0.457143 | 32 / 70 |

EARS-minus-B1 AURC was -0.035846 with grouped-bootstrap 95% CI [-0.076087, -0.003447]. R80 difference was +0.028571 with CI [0.000000, 0.063492]. The joint internally frozen criterion required both endpoints to favor EARS. It was not satisfied, so H1 remains INCONCLUSIVE.

### 8.2 SciFact Dev matched comparison

| Model | AURC | R80 | Error AUROC | Errors / 150 accepted |
|---|---:|---:|---:|---:|
| B1 | 0.281575 | 0.413333 | 0.798007 | 62 |
| B1 + F4 | 0.290272 | 0.406667 | 0.787930 | 61 |
| B1 + F5 | 0.281007 | 0.406667 | 0.795063 | 61 |
| Full EARS | 0.288355 | 0.400000 | 0.787817 | 60 |

EARS-minus-B1 AURC was +0.006780, CI [-0.016939, +0.033066]. R80 difference was -0.013333, CI [-0.034247, +0.006849]. B1+F4 and B1+F5 intervals also crossed zero. The directions reverse relative to the historical Internal Test: on Dev, EARS has worse AURC but better R80. This reversal is evidence of endpoint and sample sensitivity, not proof of generalization.

### 8.3 Corrective inference replay

Corrective E1 processed 1,109 claims and 16,635 main NLI pairs plus 900 perturbation pairs. Corrective E1-v2 processed 827 claims and 12,405 pairs. Both used the original pinned revisions on MPS with zero truncations. Against the historical private compact artifacts, each replay had identical partition-aware claim keys, zero predicted-label differences, zero rows with any F1-F5 or frozen-risk difference, and maximum absolute numeric difference 0.0. The private compact SHA-256 values were identical within each verifier. This verifies numerical equivalence of scoring outputs; it does not restore the historical labels to an unseen state.

### 8.4 Verifier transfer

E1 accuracy on eligible Dev claims was 0.489362; E1-v2 accuracy was 0.473404. Under E1-v2, reconstructed B1 and EARS AURCs were 0.287246 and 0.264414, while both R80 values were 0.420000. Because the replacement verifier was weaker and the comparison was not a fresh test, this is exploratory and does not establish transfer.

## 9. Feature Contribution Analysis

F4 did not improve Dev ranking. F5 had positive marginal permutation importance within some fitted models and produced a small B1+F5 point improvement, but the paired AURC and R80 intervals crossed zero. Its fit-to-Dev standardized mean shift was modest, and extreme multicollinearity was not observed (maximum VIF 3.06; standardized condition number 3.59).

The correct interpretation is: **F5 exhibits exploratory model-dependent predictive association, but stable incremental benefit has not been established in the held-out comparison.** Marginal permutation importance neither proves an independent conditional effect nor a causal mechanism. The matched B1, B1+F4, B1+F5, and EARS comparisons remain the primary feature-contribution evidence.

## 10. Error and Sensitivity Analysis

### 10.1 E1 errors

E1 correctly predicted 92 of 188 eligible Dev claims. SUPPORT recall was 0.322581, compared with 0.812500 for CONTRADICT. Gold-document recall@5 was 0.842105, while pipeline gold-sentence recall was 0.516393 and complete-rationale recovery was 0.684211. Non-exclusive diagnostics counted 69 NLI/reasoning failures, 19 sentence-selection failures, eight retrieval failures, and 20 aggregation failures. These categories describe observable pipeline states and are not causal proof.

### 10.2 Historical AURC/R80 boundary

At historical 80% coverage, B1 and EARS shared 65 accepted claims and each had five unique accepted claims. Switching from B1 to EARS removed three errors but introduced five, changing accepted errors from 30 to 32. Across all 39 leave-one-eligible-group-out analyses, EARS retained lower AURC but higher R80. Average prefix quality and one discrete operating point are different estimands.

### 10.3 Post-hoc overlap sensitivity

Removing the two normalized-text duplicate Dev claims retained all 188 eligible claims because both duplicates were ineligible. Claim-level and connected-group versions therefore left the primary metrics unchanged.

Excluding every Dev claim that cited any document also cited in historical Train retained 104 of 300 total Dev claims and 64 eligible claims in 53 groups. B1/EARS AURCs were 0.364051/0.345359; R80 values were both 0.490196; error AUROCs were 0.769841/0.775794. EARS-minus-B1 AURC was -0.018692 with CI [-0.074248, +0.028015], and R80 difference was 0.0 with CI [-0.018868, +0.037037]. The group-level exclusion produced the same retained set because document-connected groups aligned with the exclusion. These are post-hoc fixed-score sensitivities, not independent confirmation.

### 10.4 Evidence perturbations and calibration

Dropping the top retrieved document reduced B1/EARS rank correlations to 0.535/0.534. Removing the lowest-ranked selected sentence from each document retained correlations near 0.937. Replacing rank five with a deterministically sampled corpus document outside the original retrieval set retained correlations 0.886/0.883. The sampled document was not previously retrieved and was not known cited evidence, but semantic irrelevance was not established. A fixed +/-5% top-two BM25 score perturbation barely changed rankings.

Platt scaling used 88 eligible historical Calibration claims and was evaluated on Dev. It slightly improved B1 Brier score and log loss but worsened both proper scores for EARS. The study does not validate either raw or transformed score as an error probability. Historical H3 remains NOT EVALUATED.

## 11. Scientific Limitations

SciFact Dev is same-dataset-family evidence with substantial shared-document overlap. The original V2 ID-discovery path deserialized annotation-bearing records, so perfect historical label-blindness is not claimed even though corrected replay shows that scores were unaffected. Dev was already observed before the correction and cannot become a fresh confirmatory set.

The base verifier has low accuracy and severe SUPPORT bias. Risk ranking cannot repair missing evidence or incorrect NLI decisions. Samples remain modest, calibration uses only 88 eligible claims, bootstrap conditions on fixed models, and post-hoc interactions and overlap filters are exposed to multiplicity. Synthetic perturbations do not estimate natural distribution shift. No external, clinical, policy, or deployment validity is established.

## 12. Research Integrity and Reproducibility

The historical Phase 3 outputs, original V2 results, and frozen V2 protocol are preserved. Original V2 documents and source snapshots are archived under `reports/research_upgrade_v2/archive/original_v2_2026-10-14/`. Corrective inference and analysis live under a separately dated correction directory and are labeled post-study replay.

The public repository intentionally excludes raw SciFact data, model weights, and private claim-level inference caches. Public aggregate outputs, numeric frozen model parameters, checksums, scripts, and tests are included. V2 correction replay is reproducible after downloading and checksum-verifying official SciFact and pinned model revisions. Complete replay of every historical private phase remains partial because several historical manifests, claim-level artifacts, and joblib bundles are not public.

The human project owner supplied the research objective and integrity constraints and retains responsibility for authorship, licensing, and publication. AI-assisted systems implemented and debugged code, executed experiments, performed statistical and reproducibility checks, and drafted documentation. The work is not represented as unaided human implementation. No peer review, institutional endorsement, external validation, or publication acceptance is claimed.

## 13. Conclusion

The corrected evidence answers the research questions more precisely without improving the headline claim. Retrieval and evidence-consistency features can alter error rankings, and F5 shows exploratory model-dependent association, but stable incremental benefit beyond NLI-derived signals was not established on SciFact Dev. No compatible cross-dataset replication was available. EARS behavior changes with the verifier and sample, while AURC and R80 can reverse because they measure global prefix quality and one local boundary.

The scientifically defensible contribution is therefore an audited negative-and-mechanistic result: evidence-aware risk ranking is plausible, but small, endpoint-sensitive, verifier-dependent, and not externally validated. Historical H1 remains INCONCLUSIVE.

## References

1. Wadden, D., Lin, S., Lo, K., Wang, L. L., van Zuylen, M., Cohan, A., and Hajishirzi, H. "Fact or Fiction: Verifying Scientific Claims." *EMNLP 2020*, 7534-7550. DOI: 10.18653/v1/2020.emnlp-main.609.
2. Wadden, D., Lo, K., Kuehl, B., Cohan, A., Beltagy, I., Wang, L. L., and Hajishirzi, H. "SciFact-Open: Towards Open-domain Scientific Claim Verification." *Findings of EMNLP 2022*, 4719-4734. DOI: 10.18653/v1/2022.findings-emnlp.347.
3. Sarrouti, M., Ben Abacha, A., Mrabet, Y., and Demner-Fushman, D. "Evidence-based Fact-Checking of Health-related Claims." *Findings of EMNLP 2021*, 3499-3512. DOI: 10.18653/v1/2021.findings-emnlp.297.
4. El-Yaniv, R. and Wiener, Y. "On the Foundations of Noise-free Selective Classification." *Journal of Machine Learning Research* 11(53), 1605-1641, 2010.
5. Geifman, Y. and El-Yaniv, R. "Selective Classification for Deep Neural Networks." *Advances in Neural Information Processing Systems 30*, 2017.
6. Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. "On Calibration of Modern Neural Networks." *ICML 2017*, PMLR 70, 1321-1330.
7. Ovadia, Y. et al. "Can You Trust Your Model's Uncertainty? Evaluating Predictive Uncertainty under Dataset Shift." *NeurIPS 2019*.
8. Beltagy, I., Lo, K., and Cohan, A. "SciBERT: A Pretrained Language Model for Scientific Text." *EMNLP-IJCNLP 2019*, 3615-3620. DOI: 10.18653/v1/D19-1371.
9. Wadden, D., Lo, K., Wang, L. L., Cohan, A., Beltagy, I., and Hajishirzi, H. "MultiVerS: Improving Scientific Claim Verification with Weak Supervision and Full-document Context." *Findings of NAACL 2022*, 61-76. DOI: 10.18653/v1/2022.findings-naacl.6.
10. Hendrycks, D. and Gimpel, K. "A Baseline for Detecting Misclassified and Out-of-Distribution Examples in Neural Networks." *ICLR 2017*.
