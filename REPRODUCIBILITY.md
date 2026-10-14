# Reproducibility

## Recorded environment

- Python 3.12.15
- macOS on Apple Silicon, 24 GB RAM class
- PyTorch 2.14.1; Transformers 5.19.0
- scikit-learn 1.9.1; NumPy 2.5.4; SciPy 1.18.1
- rank-bm25 0.2.2; joblib 1.6.0
- formal Independent Test inference used MPS after a CPU/MPS smoke check

## Seeds

| Purpose | Seed |
|---|---:|
| Outer split | 20261012 |
| Cross-fit allocation | 20261013 |
| Logistic model | 20261014 |
| Ranking tie key | 20261015 |
| Grouped bootstrap | 20261016 |

## Frozen counts

- 527 fit claims; 329 eligible fit claims.
- 154 correct and 175 erroneous frozen E1 fit predictions.
- 141 Internal Test claims; 88 eligible after label unsealing.
- 55 connected groups across all test claims; 39 containing eligible claims.
- 10,000 paired bootstrap replicates.

## Integrity checks

Final B1, B2, and EARS models were saved as joblib bundles and lossless numeric JSON. On all 987 fit claim-method combinations, maximum absolute disagreement was `1.11e-16`, below the `1e-12` gate.

Two independent deterministic evaluations using frozen scores and labels produced byte-identical versions of 11 core artifacts, including all bootstrap replicates and case records. The final complete local suite passed 70 tests, including six Phase 4 acceptance tests.

## Known technical incidents

1. A pre-label safety scanner initially rejected the legal label-free feature name `F5_evidence_conflict_rate`. The process failed before writing predictions or opening labels. Complete inference was rerun from the beginning with only that documented field-name check corrected at runtime.
2. The final-training logger treated symbolic stdout `HEAD` as a Git commit even though `git rev-parse --verify HEAD` exited 128 in an uncommitted repository. Numeric artifacts are unaffected; SHA-256 manifests, not Git history, are authoritative.

Both incidents are preserved in the full local research record. Neither changed features, model parameters, scores, or conclusions.

## Release exclusions

The public candidate excludes raw SciFact files, claim-level predictions, model bundles, caches, machine paths, account identifiers, secrets, and temporary files. These must be generated locally. Aggregate metrics and publication figures are included.

## Reproduction boundary

The current Internal Test is no longer unseen. A clean rerun can reproduce the reported study, but any new model or feature development requires genuinely new data for a fresh untouched-evaluation claim.

## Public-checkout clarification and v2

The public checkout does not include the private Phase 0/1/3 manifests, claim-level artifacts, joblib bundles, or the README-referenced `scripts/build_phase1_reports.py`. Consequently, the original staged command list is a description of the complete private package, not a fully executable public clean-checkout workflow. Research Upgrade v2 supplies an executable public reconstruction using the audited raw download and lossless numeric model specification. See `reports/research_upgrade_v2/REPRODUCIBILITY_AUDIT.md`.

