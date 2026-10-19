# Power and Go/No-Go Plan

**Status:** simulation design only. No model inference, test scoring, or empirical power calculation was performed.

## Primary estimand and test

Let

`Delta = AURC(EARS) - AURC(B1)`.

Negative values favor EARS. The analysis is paired because both methods score the same claims. Dependence is handled at the connected evidence-document group level.

- Null: `Delta >= 0`.
- Directional alternative: `Delta < 0`.
- Primary inferential rule: reject the null only when the one-sided 95% group-resampling upper confidence bound is below zero.
- Report a two-sided 95% interval as well, so readers are not restricted to the directional decision.
- R80 and other endpoints are secondary and cannot rescue the primary result.

## Why the planning values are provisional

### Power = 0.80

Eighty percent is a convention, not a scientific property. It accepts a 20% chance of missing the planning alternative. Retain it only if the owner judges that miss rate acceptable relative to the cost of label access and the fact that the public test can only be used credibly once under a frozen protocol. The sensitivity report must also show power targets of 0.90.

### True `Delta = -0.020`

This is not yet a justified minimum important effect:

- historical Internal Test point difference: -0.035846;
- SciFact Dev original-label point difference: +0.006780;
- the sign changed across those samples;
- a two-point AURC change does not map directly to a fixed number of errors avoided at an operating threshold.

Use -0.020 as a planning alternative only. Before registration, add an operational translation on development data: show changes in expected accepted errors across the complete risk-coverage curve and at prespecified coverage points. If stakeholders cannot defend why that difference matters, report a power curve rather than calling -0.020 the minimum important effect.

## Simulation population

Use Check-COVID Dev only:

- 207 total claims;
- 139 V2-eligible SUPPORT/REFUTE claims;
- 50 evidence-document groups.

Generate and freeze B1/EARS development scores only after the retrieval adapter passes. Test labels, test scores, and test group outcomes must not enter the simulation.

## Simulation algorithm

### 1. Build an empirical group library

For each Dev group, retain together:

- claim IDs and group ID;
- binary error outcome for the frozen verifier;
- B1 and EARS risk scores;
- claim type and gold class for sensitivity stratification only;
- group size and retrieval diagnostics.

Use canonical ranks or probability-scale scores consistently. Preserve within-group outcome and score dependence.

### 2. Calibrate data-generating scenarios

Use at least these scenarios; a single favorable model is insufficient.

1. **Empirical transport:** resample observed Dev groups unchanged.
2. **Null:** perform group-level paired method-label swaps or another exchangeability-respecting construction so expected Delta is zero. This calibrates type-I error.
3. **Global discrimination improvement:** starting from B1 ranks, apply an outcome-dependent rank shift plus resampled EARS-minus-B1 residuals. Solve the shift parameter by bisection so mean generated Delta is -0.020. This is a simulation device, not a fitted test model.
4. **Heterogeneous improvement:** concentrate the same average effect in prespecified difficult strata, such as extracted claims or low-retrieval-margin groups.
5. **Cluster-concentrated improvement:** concentrate benefit in a minority of documents to test sensitivity to influential groups.
6. **Adverse transport:** increase group-level score correlation or reverse the Dev subgroup mix within the bounds observed in the official split.

For scenarios 3–5, verify after generation that the achieved mean Delta is within 0.001 of the target and that marginal error prevalence, group-size distribution, and score ties remain plausible. Do not merely add a constant to scores; AURC depends on ranks, so a constant produces no effect.

### 3. Generate a planned external sample

For each outer replicate:

1. Sample 50 groups with replacement from the scenario library.
2. Retain every eligible claim in each draw, including repeated group occurrences.
3. If matching the observed test group-size distribution, sample or reweight templates to the fixed pattern `37x2, 8x4, 2x6, 1x8, 1x10, 1x17` eligible claims.
4. Assign unique occurrence IDs so repeated groups do not collide under tie-breaking.
5. Compute paired B1 and EARS AURCs and Delta.

Use at least 5,000 outer replicates. Report Monte Carlo standard error and a binomial interval around estimated power.

### 4. Apply the proposed analysis inside each replicate

Within each outer replicate, use at least 2,000 paired group-bootstrap draws to estimate the one-sided upper bound. The replicate is a success if that bound is below zero. Record separately whether the point estimate is at most -0.020; do not silently make that a second significance criterion.

Use more inner draws near the decision boundary. Validate the nested procedure on synthetic fixtures with known null and strong-signal behavior.

### 5. Sensitivity grid

At minimum report power for true Delta values:

`0.000, -0.005, -0.010, -0.020, -0.030, -0.040`.

Report each under global, heterogeneous, cluster-concentrated, and adverse-transport scenarios, and at nominal alpha 0.05. Also report the smallest effect reaching 0.80 and 0.90 power.

## Go/No-Go gates before formal testing

All gates are conjunctive.

### G1 — source and population integrity

- Exact data commit and SHA-256 values match the audit.
- Authoritative test files contain 229 unique claims.
- The claim-only projection contains exactly 229 IDs and no annotation-bearing fields.
- Eligibility/scoring code is tested to yield 153 claims and 50 groups only after label opening.

**Failure:** stop.

### G2 — retrieval and feature comparability

- The corpus and BM25 implementation are immutable and score-bearing.
- Candidate-corpus choice is scientifically named: reconstructed CORD-19 or closed 347-document transfer.
- F1–F5 are finite and schema-compatible on all Dev claims.
- Any F4 distribution shift is quantified; no test-derived normalization is fitted.

**Current status:** fail. Official Vespa artifacts have no usable scores or deterministic rank.

### G3 — F6 validity

- F6 definition and probability vector pass all checks in `F6_NEGATIVE_CONTROL_PLAN.md`.
- Target removals differ from no-op and matched controls on Dev for a prespecified metric.
- F6 shows acceptable missingness and does not encode gold document identity or labels.

**Failure:** omit F6 and test only frozen B1/EARS if G2 and all other gates pass; do not redesign on test.

### G4 — power and error control

- Estimated null rejection rate is at most 0.05; its 95% Monte Carlo upper bound is at most 0.06.
- Estimated power at true Delta -0.020 is at least 0.80, and the 95% Monte Carlo lower bound is at least 0.78.
- Power is at least 0.80 in the prespecified conservative heterogeneous or cluster-concentrated scenario.
- The result is not driven by one document group in leave-one-group-out diagnostics on Dev.

**Current status:** not evaluated; therefore fail.

### G5 — model and analysis freeze

- Model weights/numeric specifications, preprocessing, corpus, retrieval, code, seeds, tie rule, inclusion logic, and environment are hashed.
- Dev-derived choices are closed.
- The scorer is containerized or otherwise cleanly reproducible.
- The prediction manifest format and canonical hashing test pass on fixtures.

**Failure:** stop.

### G6 — label isolation and disclosure

- Role-separated claim-only inference is operational.
- Predictions are hashed before scoring.
- Test-label access is append-only logged.
- Documents use “held-out with access controls,” not “blind” or “unseen.”

**Failure:** downgrade to exploratory/descriptive or stop.

## Post-test decision vocabulary

- **Statistical evidence of superiority:** one-sided upper bound below zero.
- **No statistical evidence:** upper bound includes zero; do not say equivalent.
- **Practically promising:** point estimate is at most -0.020, clearly labeled against the provisional planning threshold.
- **Practically established:** requires a separately justified utility criterion and an interval supporting it; the current protocol does not have one.
- **Incompatible analysis:** any gate violation, corpus drift, incomplete predictions, or post-label code change. Report no confirmatory conclusion.

## Current decision

Formal external testing is **No-Go**. The design has 50 independent groups, retrieval comparability currently fails, and empirical power has not been computed from an authorized frozen Dev run.
