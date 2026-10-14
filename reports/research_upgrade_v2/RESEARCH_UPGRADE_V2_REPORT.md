# Research Upgrade v2: Technical Report

## Executive finding

This upgrade preserves the published Phase 3 result and its **H1 INCONCLUSIVE** decision. It adds a frozen, label-gated evaluation on official SciFact Dev, feature ablations, a verifier-transfer experiment, post-hoc Internal Test sensitivity, perturbation tests, and a small-sample calibration study. The central result is negative but informative: on 188 eligible SciFact Dev claims in 164 connected groups, evidence-aware features did **not** provide reliable incremental ranking information beyond B1's NLI-derived features.

## Evidence levels

- **Historical internally protocol-frozen result:** the unchanged 88-claim Internal Test result: B1 AURC 0.300833 / R80 0.428571; EARS AURC 0.264987 / R80 0.457143; H1 INCONCLUSIVE. No verified external preregistration is claimed.
- **Post-hoc historical:** exact reconstruction of the frozen scores, leave-one-group-out sensitivity, and the 80%-acceptance swap analysis. These do not revise H1.
- **Independent same-dataset validation:** official SciFact Dev, excluded from the historical study. It is not cross-dataset replication: two normalized claims and 181 cited documents overlap with historical SciFact data.
- **Reconstructed model experiments:** B1+F4, B1+F5, EARS refits, and E1-v2 risk models trained on the original fit partition. The public numeric B1/EARS parameters were also evaluated separately and produced the same Dev scores as the reconstructed B1/EARS models.
- **Genuine cross-dataset evaluation:** not achieved. SciFact-Open duplicates all 279 original claims; HealthVer is an evidence-pair task without an equivalent retrieval corpus or F4 definition.

## Methods

The v2 protocol was internally frozen at SHA-256 `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301` before SciFact Dev evaluation. E1 retained its pinned DistilRoBERTa NLI revision and all retrieval, selection, and aggregation rules. The original scoring path used only claim IDs/text downstream but deserialized full Dev records during ID discovery. No annotation dependence in scoring was detected, but perfect historical label-blindness is not claimed. Corrective restricted-parser replay of 16,635 E1 and 12,405 E1-v2 pairs was exactly equal to the historical scoring artifacts.

The four matched risk models were B1 (F1–F3), B1+F4, B1+F5, and Full EARS (F1–F5). All used the same 329 eligible fit claims, target, preprocessing, L2 logistic regression, `C=0.1`, and no hyperparameter selection. Dev uncertainty used 10,000 paired connected-group bootstrap samples with fixed model scores.

## Main results

| Model | Dev AURC ↓ | Dev R80 ↓ | Error AUROC ↑ | Errors / 150 accepted |
|---|---:|---:|---:|---:|
| B1 | 0.281575 | 0.413333 | 0.798007 | 62 |
| B1+F4 | 0.290272 | 0.406667 | 0.787930 | 61 |
| B1+F5 | 0.281007 | 0.406667 | 0.795063 | 61 |
| Full EARS | 0.288355 | 0.400000 | 0.787817 | 60 |

Paired Dev contrasts against B1 were:

| Contrast | ΔAURC (95% CI) | ΔR80 (95% CI) |
|---|---:|---:|
| B1+F4 − B1 | +0.008697 [−0.000368, +0.019294] | −0.006667 [−0.020551, +0.012987] |
| B1+F5 − B1 | −0.000568 [−0.023399, +0.024382] | −0.006667 [−0.032900, +0.006623] |
| EARS − B1 | +0.006780 [−0.016939, +0.033066] | −0.013333 [−0.034247, +0.006849] |

None supplies stable incremental evidence. Ordinary marginal permutation importance was negative for F4 and positive for F5 in some fitted models, but the matched performance intervals still crossed zero. This procedure does not establish conditional or causal importance. Maximum VIF was 3.06 and the standardized design condition number was 3.59, so extreme collinearity was not the main explanation.

## Verifier behavior and transfer

E1 achieved 92/188 accuracy (0.489362). SUPPORT recall was 0.322581 versus 0.812500 for CONTRADICT; 84 of 124 SUPPORT claims were wrong, compared with 12 of 64 CONTRADICT claims. Gold-document recall@5 was 0.842105, but pipeline gold-sentence recall was 0.516393 and complete-rationale recovery was 0.684211. Thus retrieval often found the right document while lexical sentence selection and NLI/aggregation lost decisive evidence.

E1-v2 replaced only the NLI encoder with pinned `nli-deberta-v3-small`. It was worse: 0.473404 accuracy, with SUPPORT recall 0.282258. On this candidate verifier, reconstructed EARS improved AURC (0.264414 versus B1 0.287246) but not R80 (both 0.420000). This is exploratory evidence that feature usefulness may interact with verifier behavior, not proof of transfer: the base verifier itself did not improve and no paired transfer interval was frozen in advance.

## Why historical AURC and R80 disagree

The exact frozen historical metrics were reproduced from public numeric parameters and newly generated E1 features. At 80% coverage, B1 and EARS shared 65 accepted claims and each had five unique accepted claims. Moving from B1 to EARS removed three errors but introduced five, producing the observed 30-to-32 error increase. Yet EARS improved risk over many other prefixes, lowering average AURC. All 39 leave-one-eligible-group-out runs retained negative ΔAURC (−0.04115 to −0.02966) and positive ΔR80 (+0.02857 to +0.04478).

## Robustness and calibration

Dropping the top retrieved document sharply changed rankings (Spearman 0.535 for B1 and 0.534 for EARS). Removing one selected sentence per document was milder (about 0.937); replacing rank five with a deterministically sampled document outside the original retrieval set yielded about 0.884. Semantic irrelevance was not established. A +/-5% top-two BM25 score perturbation barely changed EARS ranking (0.9992), implying that observed fragility came mainly through changed NLI evidence, not F4 alone.

Platt calibration used only 88 eligible historical Calibration claims and evaluated on Dev. For B1 it modestly improved Brier score (0.18738→0.18626), log loss (0.55659→0.55114), and ECE (0.05659→0.04341). For EARS it worsened Brier score (0.19128→0.19458) and log loss (0.56128→0.56740), although ECE decreased. This small, mixed study does not justify calling either score a validated error probability. Historical H3 remains NOT EVALUATED.

## Answers to the five research questions

1. **Incremental information:** not reliably demonstrated. F5 shows exploratory model-dependent predictive association; F4 does not improve Dev ranking.
2. **Generalization beyond Internal Test:** not supported on same-dataset Dev, and no valid cross-dataset replication was available.
3. **Verifier transfer:** exploratory EARS AURC improvement appears under E1-v2, but the verifier is weaker and R80 is unchanged; transfer is not validated.
4. **AURC versus R80:** average prefix quality and one discrete cutoff are different estimands; two net additional errors crossed the historical 80% boundary under EARS.
5. **Failure conditions:** EARS fails when F4 is weak, evidence perturbations alter NLI behavior, category bias dominates, or an operating point is sensitive to a few boundary swaps.

## Verdict

The upgrade materially strengthens the evidence boundary and failure analysis, not the superiority claim. It supports a mature negative conclusion: evidence-aware risk scoring is plausible but its incremental value is small, endpoint-dependent, and not externally replicated in this project.
