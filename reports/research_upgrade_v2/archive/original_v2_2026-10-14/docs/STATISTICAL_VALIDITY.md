# Statistical Validity

## Estimands

Discrete AURC is the arithmetic mean of prefix risks for all accepted counts `k=1..n`. R80 uses `floor(0.8n+0.5)`, giving 150 accepted claims on SciFact Dev. Error-detection AUROC treats verifier error as the positive class. Scores are ordered from low to high risk with a deterministic SHA-256 claim-ID tie key.

## Dependence and uncertainty

SciFact Dev contains 188 eligible claims in 164 connected groups formed before eligibility filtering from shared cited documents and normalized claim text. The paired bootstrap samples 164 groups with replacement, includes all eligible claims in each sampled group, recomputes the coverage count, and uses 10,000 replicates with seed 20261016. Reported intervals are percentile intervals using linear quantiles.

This bootstrap quantifies fixed-score sampling uncertainty. It does not refit E1, the risk model, the calibration model, or model-selection decisions, so it understates full pipeline uncertainty. Shared documents across historical data and Dev create additional dependence not fully modeled by within-Dev groups.

## Paired results

All three Dev feature contrasts have 95% intervals spanning zero for both AURC and R80. This is absence of reliable improvement, not evidence of equivalence. No post-hoc alpha change, endpoint substitution, or favorable subset replaced the frozen comparison.

## Historical leave-one-group-out analysis

Removing each of 39 eligible Internal Test groups in turn produced ΔAURC from −0.04115 to −0.02966; all 39 favored EARS. ΔR80 ranged from +0.02857 to +0.04478; all 39 favored B1. This shows the endpoint conflict is not attributable to one group. It does not create new confirmatory evidence because the Internal Test has already been used.

At the exact 80% boundary, B1 and EARS share 65 of 70 accepted claims. Five leave and five enter under EARS. Three departing claims are errors, while all five entering claims are errors, explaining the two-error R80 deterioration without inference from aggregate numbers alone.

## Multiple analyses and interpretation

Feature correlations, permutation importance, calibration, E1-v2, perturbations, class strata, and interactions are secondary or exploratory. The interaction model is especially post-hoc and receives no success claim. Coefficients and permutation importance are associational, not causal. Small or unstable groups are described rather than treated as proof.

## Effective sample sizes

- Fit: 329 eligible claims; 243 connected groups.
- Calibration: 88 eligible claims; used only for Platt fitting.
- Internal Test: 88 eligible claims; 39 eligible groups; post-hoc only in v2.
- SciFact Dev: 188 eligible claims; 164 connected groups.

These counts are adequate for descriptive comparisons but modest for interaction discovery, calibration, or broad generalization.
