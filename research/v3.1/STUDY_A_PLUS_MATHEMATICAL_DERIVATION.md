# Study A+ Mathematical Derivation

> Public-package copy. Only repository-relative path references were adapted; mathematics and numerical results are unchanged from the hash-identified closure source.

## Definitions

Let `n` eligible observations have a fixed risk ordering `π`, from lowest predicted risk (first retained) to highest. Let `e_(π_i) ∈ {0,1}` indicate whether the frozen verifier is wrong at rank `i`. Prefix risk at coverage `k/n` is

\[
R_k=\frac{1}{k}\sum_{i=1}^{k}e_{\pi_i}.
\]

The finite-sample convention used by V2 and Study A is the arithmetic mean of all `n` prefix risks:

\[
\operatorname{AURC}=\frac1n\sum_{k=1}^{n}R_k
=\frac1n\sum_{k=1}^{n}\frac1k\sum_{i=1}^{k}e_{\pi_i}.
\]

This is a discrete estimator under the project's stated convention; it should not be confused with every alternative interpolation convention called AURC in the literature.

## Weighted representation and proof

All sums are finite, so their order may be exchanged without a convergence condition:

\[
\begin{aligned}
\operatorname{AURC}
&=\frac1n\sum_{k=1}^{n}\sum_{i=1}^{k}\frac{e_{\pi_i}}{k}\\
&=\frac1n\sum_{i=1}^{n}e_{\pi_i}\sum_{k=i}^{n}\frac1k\\
&=\sum_{i=1}^{n}w_i e_{\pi_i},
\end{aligned}
\]

where

\[
w_i=\frac1n\sum_{k=i}^{n}\frac1k
=\frac{H_n-H_{i-1}}{n}.
\]

Each rank-`i` error contributes to every prefix `k ≥ i`, explaining why early errors have larger weights. The weights are positive and non-increasing; `w_i-w_{i+1}=1/(ni)`.

This algebraic identity is useful for exact influence calculation. It is not claimed as a new theorem.

## Exact fixed-cohort, fixed-ranking label influence

Suppose only the correctness indicator at claim `j` changes, from `e_j` to `e'_j`, while membership, frozen predictions, scores and ordering remain fixed. Let its rank be `r(j)` and `δ_j=e'_j-e_j ∈ {-1,0,1}`. By linearity,

\[
\operatorname{AURC}'-\operatorname{AURC}
=w_{r(j)}\delta_j.
\]

For paired rankings, let `r_E(j)` and `r_B(j)` be the EARS and B1 ranks. With `Δ=AURC_EARS-AURC_B1`,

\[
\Delta'-\Delta
=\delta_j\left(w_{r_E(j)}-w_{r_B(j)}\right).
\]

For several label changes with unchanged membership and rankings, these contributions add exactly. A correction can therefore decrease both methods' AURC yet improve or worsen the paired comparison depending on relative ranks.

The formula does **not** apply unchanged to a deletion or eligibility change: `n`, the deleted rank, subsequent ranks, and every weight can change. Such cases in Study A+ are recomputed exactly on the resulting cohort rather than approximated by one-label influence.

## Ties

The total order is ascending frozen risk, followed by ascending SHA-256 digest of the UTF-8 string `20261015:<claim_id>`, then numeric claim ID as a collision fallback. This is the pre-specified Study A deterministic tie rule. It makes the finite-sample value reproducible, but it does not erase the conceptual sensitivity of a discrete risk-coverage curve to ordering within a tied score block. A scientifically conservative extension could average over all within-block orders; that was not substituted post hoc here.

## Implementation and verification

[`scripts/study_a_plus.py`](scripts/study_a_plus.py) implements direct prefix AURC, weighted AURC, one-label influence, paired influence, cohort rebuilds, exact scenario enumeration, R80, and the group-aware paired bootstrap. [`scripts/test_study_a_plus.py`](scripts/test_study_a_plus.py) checks:

- every binary error sequence for `n=1,…,8` (510 sequences) under direct versus weighted calculation;
- one-label perturbations against direct recomputation;
- paired influence for exhaustive permutations through `n=6`;
- 10,000 randomized property cases with varying sizes, binary labels, and independent paired rankings.

All four test groups passed in the fresh environment (`4 passed in 7.12s`). On the original, common-original, and corrected frozen Study A cohorts, the maximum absolute direct-versus-weighted discrepancy was `5.551115123125783×10⁻17`, consistent with summation-order floating-point roundoff. No logical discrepancy was found.

The Study A corrected point estimates and group-bootstrap confidence intervals were reproduced with seed `20261016`, 10,000 replicates, and group sampling. The result JSON and influence CSV produced in the clean environment were byte-identical to the host run:

- [`data/STUDY_A_PLUS_RESULTS.json`](data/STUDY_A_PLUS_RESULTS.json): `829150e9052ef42384525c5b0c336bbbdbdf8119becb87ec717f59798953cdbd`
- [`data/ANNOTATION_INFLUENCE_ANALYSIS.csv`](data/ANNOTATION_INFLUENCE_ANALYSIS.csv): `89f238a1c20fec620e9bd4f628cdfd7a0858d96d9f4250eec570bec3c78c3eb0`

## Interpretation boundary

The exact influence is conditional on the frozen predictions, ranking, cohort, AURC convention, and a specified label alternative. It is neither the probability that an annotation is wrong nor causal evidence that a score component explains performance. Annotation uncertainty and sampling uncertainty remain distinct.
