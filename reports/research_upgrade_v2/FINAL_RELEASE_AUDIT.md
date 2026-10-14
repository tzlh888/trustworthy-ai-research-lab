# Final Release Audit

> **Correction notice (14 October 2026):** This earlier audit is retained for provenance. The authoritative final audit is `FINAL_CORRECTION_AUDIT.md`, with corrected inference evidence in `corrections/2026-10-14/results/`. Historical V2 claim files were fully deserialized for ID discovery; the corrected replay uses restricted ID/claim projections and is exactly equivalent at the scoring-artifact level. Test and package counts below describe the earlier candidate, not the final corrected candidate.

## Status matrix

| Area | Status | Evidence |
|---|---|---|
| Original frozen results intact | PASS | Phase 3B tracked files unchanged; H1 remains INCONCLUSIVE |
| New protocol frozen before Dev label evaluation | PASS | protocol and blind-manifest hashes |
| New same-dataset validation | PASS | 188 claims, 164 groups, frozen model scores |
| Genuine cross-dataset validation | NOT EXECUTED | SciFact-Open fully overlaps; HealthVer task mismatch |
| F4/F5 matched ablation | PASS | four models, same samples/settings, paired intervals |
| E1 error analysis | PASS | confusion, per-class, retrieval, selection, taxonomy |
| E1-v2 candidate | PASS as exploratory study | completed and retained despite worse accuracy |
| Robustness and calibration | PASS as new exploratory studies | four perturbations; held-out Platt evaluation |
| Historical clean public replay | PARTIAL | excluded private artifacts and a missing helper script |
| Public content safety | PASS | clean candidate: 169 files scanned, zero findings; no raw claim/evidence text or model weights in v2 results |
| Publication readiness | PARTIAL | no external replication; author/license confirmation still required |

## Consistency checks

The README, v2 paper, one-page summary, reports, and final handoff all state:

- historical H1 is INCONCLUSIVE;
- historical H2/H3 are NOT EVALUATED;
- Dev does not validate a general EARS advantage;
- E1-v2 is not a successful verifier upgrade;
- scores are not calibrated probabilities;
- no remote action occurred during this task.

## Licensing and attribution

SciFact claims/annotations are CC BY 4.0; its S2ORC abstracts are ODC-By 1.0. The original NLI and E1-v2 model cards identify Apache-2.0. SciFact-Open and HealthVer audited commits lacked repository LICENSE files, so their data were not copied into release outputs. The project LICENSE and `CITATION.cff` retain owner-controlled identity/license decisions.

## Strict-review findings

The audit found no test-set tuning in v2, no arbitrary Neutral mapping, no fabricated significance, and no hidden adverse result. Corrected issues were: a missing tokenizer dependency, an eligible-population alignment error, and an overstated historical clean-reproduction command. The interaction result is segregated as post-hoc. Cross-dataset generalization remains unsupported.

The final clean-copy suite passed 23 tests, skipped 61 tests requiring intentionally excluded private/raw inputs, and failed none. The clean cloud audit scanned 169 files and passed its privacy and numeric-model integrity checks. The research checkout retains raw SciFact downloads only as ignored local inputs; they are absent from the clean candidate.

## Remote state

The repository already had a public GitHub remote when cloned. This task performed fetch/clone and public data/model downloads only. It did not push, open a pull request, create a release, or deploy.
