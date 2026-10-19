# Study A Statistical Report

> Public-package copy. Only repository-relative path references were adapted; scientific results are unchanged from the hash-identified closure source.

## Status and estimand

Study A is complete as a **post-hoc, same-dataset annotation sensitivity analysis**. It is not a new independent test and does not establish corrected annotations as ground truth. All E1 predictions, B1/EARS risk scores, and risk-model parameters were held fixed. Only gold labels, eligibility, and the resulting correctness indicators were recomputed.

The exact frozen compact artifact has SHA-256 `3c1ea9104569f18882881d5ff2861696c06ed723fff208f66fd0e7a60f35c941`. Both the historical and corrective V2 copies match this hash.

## Cohorts

| Cohort | Eligible claims | Connected groups | Label counts | Definition |
|---|---:|---:|---|---|
| A | 188 | 164 | 124 SUPPORT, 64 CONTRADICT | Original eligible SciFact Dev population. |
| B, original labels | 182 | 159 | 119 SUPPORT, 63 CONTRADICT | Claims eligible under both original and primary proposed scenarios. |
| B, proposed labels | 182 | 159 | 116 SUPPORT, 66 CONTRADICT | Same claim membership as B; proposed labels applied. |
| C | 182 | 159 | 116 SUPPORT, 66 CONTRADICT | Primary proposed-corrected population under the original eligibility rule. |
| Literal Claim-597 sensitivity | 181 | 159 | 115 SUPPORT, 66 CONTRADICT | C plus literal application of Claim 597 as claim-level NEI. |

Cohorts B and C have the same membership because all six eligibility changes remove originally eligible claims; no originally ineligible claim becomes eligible. They differ conceptually because B is the common-population estimand and C is the corrected-population estimand.

The six exclusions are Claims `343`, `770`, `847`, `1216`, `1274`, and `1368`. Groups `343`, `770`, `847`, `1216`, and `1274` disappear. Group `1368` remains because Claim 1370 is still eligible. Exact row-level membership is in [`data/STUDY_A_COHORT_MANIFEST.csv`](data/STUDY_A_COHORT_MANIFEST.csv).

## Statistical definitions

- Rank claims by ascending frozen error-risk score.
- Break exact score ties by SHA-256 of `20261015:claim_id`.
- AURC is the arithmetic mean of prefix selective risks for acceptance counts 1 through n.
- R80 is selective risk at `floor(0.8*n + 0.5)` accepted claims.
- Δ is EARS minus B1; negative favors EARS.
- Bootstrap unit is the connected claim group defined on all 300 Dev claims by shared cited document or identical normalized claim text.
- Each interval uses 10,000 paired group-bootstrap replicates, seed `20261016`, and linear 2.5th/97.5th percentiles. Scores and models are not refit.

There were no exact B1 or EARS score ties in any reported point-estimate cohort. R80 accepted 150/188 claims in A (79.787%), 146/182 in B/C (80.220%), and 145/181 in the Claim-597 sensitivity (80.110%).

## Fixed-score results

| Scenario | B1 AURC | EARS AURC | ΔAURC | B1 R80 | EARS R80 | ΔR80 |
|---|---:|---:|---:|---:|---:|---:|
| A: original | 0.281575 | 0.288355 | +0.006780 | 0.413333 | 0.400000 | −0.013333 |
| B: common, original labels | 0.266784 | 0.274086 | +0.007302 | 0.397260 | 0.383562 | −0.013699 |
| B/C: common, proposed labels | 0.264484 | 0.265947 | +0.001463 | 0.390411 | 0.376712 | −0.013699 |
| Literal Claim-597 NEI | 0.266444 | 0.269382 | +0.002937 | 0.393103 | 0.379310 | −0.013793 |

Primary corrected-cohort 95% sampling intervals:

| Endpoint | Point estimate | 95% connected-group bootstrap interval |
|---|---:|---:|
| B1 AURC | 0.264484 | [0.194182, 0.344233] |
| EARS AURC | 0.265947 | [0.195970, 0.346283] |
| ΔAURC | +0.001463 | [−0.021816, +0.026993] |
| B1 R80 | 0.390411 | [0.312500, 0.478873] |
| EARS R80 | 0.376712 | [0.298611, 0.465278] |
| ΔR80 | −0.013699 | [−0.039735, +0.006993] |

Both paired intervals include zero. The analysis therefore does not establish an EARS advantage on either endpoint. AURC remains slightly worse for EARS, while R80 remains slightly better, preserving the original directional conflict.

## Label versus composition effects

Effects are defined as:

- composition = common cohort with original labels minus full original cohort;
- label = common cohort with proposed labels minus common cohort with original labels;
- combined = proposed-corrected cohort minus full original cohort.

| Endpoint | Composition | Label | Combined |
|---|---:|---:|---:|
| B1 AURC | −0.014791 | −0.002300 | −0.017091 |
| EARS AURC | −0.014269 | −0.008139 | −0.022408 |
| ΔAURC | +0.000522 | −0.005839 | −0.005317 |
| B1 R80 | −0.016073 | −0.006849 | −0.022922 |
| EARS R80 | −0.016438 | −0.006849 | −0.023288 |
| ΔR80 | −0.000365 | 0.000000 | −0.000365 |

All six claims removed by proposed NEI corrections were errors under the frozen prediction. Their removal therefore lowers both methods' absolute error-risk summaries by construction. Among the five retained label reversals, Claims 208 and 1385 change from error to correct, Claim 879 changes from correct to error, and Claims 593 and 808 remain errors because the frozen prediction is `NO_RELATION`. The net label-only change is one fewer error (90 to 89) on the common cohort.

The paired decomposition bootstrap interval for the corrected ΔAURC combined effect is [−0.021206, +0.004746], and the label component is [−0.022052, +0.003805]. For ΔR80, the combined interval is [−0.014427, +0.006993]; its label-only point effect is exactly zero at the rounded 80% boundary. These intervals do not support a stable change in the EARS-versus-B1 contrast.

## Annotation uncertainty

Sampling uncertainty and annotation uncertainty are different:

- bootstrap intervals condition on a chosen annotation scenario and quantify connected-group sampling variation;
- the annotation-scenario envelope varies which unratified proposals are adopted. It is not a confidence interval and carries no probability interpretation.

Across the original scenario, the primary proposal, the literal Claim-597 interpretation, and each leave-one-correction-out scenario:

- ΔAURC ranges from `−0.000168` to `+0.008045`;
- ΔR80 ranges from `−0.013793` to `−0.013333`;
- B1 AURC ranges from `0.254282` to `0.281575`;
- EARS AURC ranges from `0.256633` to `0.288355`.

The sign of ΔAURC is therefore annotation-sensitive, although all values are close to zero and the primary sampling interval is wide. The sign of ΔR80 is stable in these scenarios but its paired sampling interval includes zero.

## Scientific interpretation

The corrected annotations materially affect absolute reported risk mainly because the proposed NEI corrections remove six cases that the frozen model got wrong. They reduce the EARS-minus-B1 AURC gap, but do not turn the result into statistically supported evidence of superior risk ranking. No mechanism is established: a changed benchmark score is an arithmetic consequence of labels and cohort membership, not causal evidence about why EARS succeeds or fails.
