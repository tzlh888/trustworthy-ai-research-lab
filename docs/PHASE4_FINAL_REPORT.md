# Phase 4 Final Deliverables and Acceptance Record

## Scientific status

Phase 4 changed no frozen model, prediction, feature, split, label, metric, bootstrap replicate, or Phase 3B conclusion. The independent evaluation contains 88 eligible claims. E1 accuracy is 0.488636. B1 and Full EARS have AURC values of 0.300833 and 0.264987, respectively, while their R80 values are 0.428571 and 0.457143. The paired EARS-minus-B1 differences are -0.035846 for AURC (95% CI [-0.076087, -0.003447]) and +0.028571 for R80 (95% CI [0, 0.063492]).

**H1 INCONCLUSIVE under the preregistered joint criterion.** H2 and H3 were **Not Evaluated**.

## Deliverables

- Eight-page English manuscript and one-page PDF summary.
- Five paper-quality visual artifacts in PNG and SVG, including unsmoothed curves, endpoint comparisons, grouped-bootstrap intervals, NO_RELATION sensitivity, and representative frozen cases.
- Local Streamlit research demo with explicit score and deployment boundaries.
- GitHub release candidate containing source, tests, aggregate results, publication figures, documentation, citation metadata, third-party notices, and a draft code license.
- Application materials: one-page summary, exactly 150-word project description, CV bullets, three-minute script, and ten evidence-based interview questions and answers.
- Read-only frozen-artifact audit, release privacy scan, and Phase 4 acceptance tests.

## Release boundary

The GitHub candidate is staged under `release/github/` only. No remote repository was created, no push was attempted, and nothing was published. Raw SciFact files, claim-level predictions, trained model bundles, caches, secrets, and machine-specific paths are excluded. The project owner must replace the author placeholder in `CITATION.cff`, approve the Apache-2.0 code-license choice, and choose the public repository URL before release.

## Interpretation boundary

EARS improved average ranking over all coverage prefixes but selected two more errors than B1 among the 70 claims accepted at the fixed 80% endpoint. Its outputs are uncalibrated ranking scores, not error probabilities. NO_RELATION is a frozen model aggregation outcome, not a validated Evidence Insufficient class. The weak base verifier, small independent sample, and in-domain held-out design prevent claims of general scientific-fact-checking reliability or high-stakes readiness.
