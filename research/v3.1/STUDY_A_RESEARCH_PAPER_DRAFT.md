# Annotation Uncertainty Changes Selective-Prediction Estimates on SciFact: A Frozen-Score Sensitivity Study

> Public-package copy of an unreviewed draft. It is not a peer-reviewed or accepted publication; path and publication-status wording were updated without changing results.

## Abstract

Benchmark annotations are often treated as fixed while uncertainty estimates are analyzed as if the labels were error-free. We study how 11 proposed claim-level corrections and one ambiguously encoded document-level correction to SciFact Dev affect a previously frozen selective-prediction comparison. Predictions, B1 and EARS risk scores, model parameters, and ranking rules were held fixed. We evaluated the original eligible cohort (188 claims, 164 connected groups), the common eligible cohort (182 claims, 159 groups), and the proposed-corrected cohort (182 claims, 159 groups). Under the proposed labels, B1 and EARS AURC were 0.2645 and 0.2659 (ΔAURC EARS−B1 = 0.0015; 95% connected-group bootstrap interval −0.0218 to 0.0270). R80 was 0.3904 and 0.3767 (ΔR80 = −0.0137; interval −0.0397 to 0.0070). Six proposed NEI corrections removed cases that were all errors under the frozen prediction, making cohort composition a major contributor to lower absolute risk. Annotation scenarios changed the sign of ΔAURC in one leave-one-out case, but no primary paired interval excluded zero. The corrections were produced by a third-party single annotator and are not treated as established truth. The study shows that annotation and eligibility decisions can materially change selective-prediction summaries without providing evidence that one uncertainty model generalizes better.

## 1. Introduction

Selective prediction ranks model outputs by estimated error risk so that higher-risk cases can be deferred. Its evaluation depends twice on benchmark annotation: labels define whether a model prediction is correct, and eligibility rules determine which cases enter the risk–coverage curve. Annotation corrections can therefore alter both the outcome and the population.

The frozen Trustworthy-AI V2 study evaluated B1 and EARS on SciFact Dev and found conflicting endpoint directions with paired confidence intervals spanning zero. A later BioNLP 2026 audit proposed corrections to 11 Dev claim labels plus one per-document mismatch. Study A asks a narrow question: if those proposals are applied without changing any model output or risk score, how sensitive are V2's selective-prediction estimates?

This is not a blind replication. SciFact Dev results and the proposed corrections were known before analysis, and SciFact Dev remains the same dataset family used by V2.

## 2. Sources and correction status

We used the official SciFact Dev claims and corpus with frozen V2 hashes, the exact frozen E1 compact artifact, and the tagged BioNLP audit repository. Historical and corrective copies of the compact artifact were byte-identical.

The correction audit explicitly reports a single human annotator assisted by language models and recommends independent multi-annotator review. We therefore call every correction “proposed.” Claim 597 is internally inconsistent across audit artifacts: the JSON represents claim-level NEI with no document ID, whereas the paper and README describe one mortality document among three evidence documents. The primary analysis treats document 12779444 as the proposed mismatch and retains the claim-level SUPPORT label; a literal-JSON sensitivity excludes the claim.

## 3. Methods

### 3.1 Frozen quantities

We held constant the E1 predicted claim labels, B1 and EARS risk scores, risk-model parameters, and ranking rules. We did not rerun inference, retrain, recalibrate, optimize a threshold, or select a favorable scenario.

### 3.2 Eligibility and cohorts

The original V2 rule includes a claim if exactly one non-empty evidence label can be derived and that label is SUPPORT or CONTRADICT. NEI and unannotated claims are excluded from error-risk metrics.

- Cohort A: the 188 originally eligible claims.
- Cohort B: the 182 claims eligible in both the original and primary proposed scenarios.
- Cohort C: the 182 claims eligible after applying the proposals and the original rule.

Connected groups were built on all 300 Dev claims using shared cited-document IDs or identical normalized claim text. The minimum claim ID names each component.

### 3.3 Metrics and uncertainty

Claims were ranked by ascending fixed risk, with exact ties broken by SHA-256 of `20261015:claim_id`. AURC is the mean of prefix selective risks. R80 is evaluated at `floor(0.8n+0.5)`. Differences are EARS minus B1.

We resampled connected groups with replacement 10,000 times using seed 20261016. Methods were evaluated on the same sampled claims in each replicate. Percentile intervals use linear interpolation. These intervals quantify fixed-score sampling uncertainty conditional on labels; they do not quantify whether a correction is true.

We decomposed change into a composition component (A to B under original labels), a label component (original to proposed labels within B), and their combined effect (A to C). Annotation uncertainty was summarized by the original scenario, the primary proposal, the literal Claim-597 interpretation, and one-at-a-time omission of every proposed claim-level correction. This scenario envelope is not a confidence interval.

## 4. Results

The original analysis reproduced exactly: B1/EARS AURC was 0.2816/0.2884 and R80 was 0.4133/0.4000. The proposed-corrected analysis yielded AURC 0.2645/0.2659 and R80 0.3904/0.3767. The paired ΔAURC interval was [−0.0218, 0.0270], and the paired ΔR80 interval was [−0.0397, 0.0070].

Six proposals changed SUPPORT or CONTRADICT to NEI and reduced the eligible population from 188 to 182. All six excluded claims were frozen-prediction errors. Their removal reduced B1/EARS AURC by 0.0148/0.0143 before any retained claim was relabeled. On the common cohort, the five label reversals changed two errors to correct, one correct to error, and left two errors as errors, yielding one fewer net error.

The composition, label, and combined effects on ΔAURC were +0.0005, −0.0058, and −0.0053. The corrected ΔAURC remained slightly positive. Across annotation scenarios, ΔAURC ranged from −0.0002 to +0.0080; ΔR80 ranged from −0.0138 to −0.0133. The literal Claim-597 interpretation produced 181 eligible claims but did not alter the scientific conclusion.

## 5. Discussion

The main finding is instability of the evaluation target, not superiority of a method. Proposed corrections make both models' absolute selective-risk estimates look better mainly by excluding six cases that both contribute errors to the original benchmark population. Such improvement cannot be interpreted as improved model behavior.

The EARS-versus-B1 contrast is less sensitive than the absolute metrics but remains uncertain. Label changes narrow the positive ΔAURC gap, and one leave-one-out scenario crosses slightly below zero, yet paired sampling intervals are much wider than these point changes. R80 continues to favor EARS at the point estimate, but its interval includes zero.

These are observational benchmark consequences. They do not identify why either risk model ranks cases as it does, and no dataset-specific difference establishes a causal mechanism.

## 6. Limitations

The proposed corrections are not an official SciFact release and lack independent human ratification. Claim 597 has unresolved machine-readable scope. SciFact Dev labels and earlier results were already inspected. The analysis concerns one verifier and two frozen risk models on one same-family development split. Bootstrap intervals condition on the chosen corrections and do not include annotator uncertainty. The local exact artifact permits deterministic recomputation, but a clean isolated-environment replay was not completed.

## 7. Conclusion

Study A provides a reproducible demonstration that annotation corrections can change selective-prediction metrics through both relabeling and eligibility-driven composition. It does not provide statistically supported evidence that EARS outperforms B1, and it does not establish the proposed corrections as truth. Independent multi-annotator adjudication is required before a corrected benchmark claim is defensible.

## Data, code, and disclosure

The Study A materials are published here as research artifacts, not as a peer-reviewed paper. The analysis record preserves hashes, seeds, metric definitions, and cohort membership. OpenAI Codex assisted with source review, code, execution, figures, and drafting. It did not perform human biomedical adjudication. Human review remains required before reuse or submission.
