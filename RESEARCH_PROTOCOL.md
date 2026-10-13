# Final Public Research Protocol

## Question and status

The confirmatory question was whether Full EARS improved both discrete AURC and selective risk at 80% coverage relative to the matched NLI-only B1 risk model on a previously unseen Internal Test.

Protocol version `phase3a-v1.0.0` was frozen before final risk-model training and Internal Test access. The joint H1 criterion required both EARS-minus-B1 point differences to be negative and both paired 95% CI upper bounds to be strictly below zero.

Final status: **H1 INCONCLUSIVE**. H2 evidence degradation and H3 calibration were **Not Evaluated**.

## Data isolation

- Official SciFact Train only was partitioned into 527 fit, 141 calibration, and 141 Internal Test claims.
- Connected groups used shared cited-document IDs and identical normalized claim text.
- Fit-only eligible claims trained risk models; the calibration split was not used.
- Internal Test claim text was processed only after final model artifacts were hashed.
- Test predictions, features, and risk scores were hashed before evidence labels were opened.
- Original SciFact Dev and official Test were not used for reported performance.

## Base verifier

- BM25Okapi: k1=1.5, b=0.75, epsilon=0.25.
- Top 20 retrieved documents; top five sent to NLI.
- Three label-free IDF-overlap sentences per NLI document.
- Pinned `cross-encoder/nli-distilroberta-base` revision `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`.
- Premise is the evidence sentence; hypothesis is the claim.
- Fixed label mapping: contradiction, entailment, neutral.
- Frozen claim aggregation and NO_RELATION rule.

## Risk models

The target is `1[frozen E1 prediction != authentic SUPPORT/CONTRADICT label]` on eligible fit claims. Full EARS contains six effective columns from F1-F5. B1 omits only F4-F5. Continuous columns are standardized from the 329 fit-only eligible claims using population standard deviation; F3 dummies are not scaled.

All learned methods use L2 logistic regression with C=0.1, lbfgs, no class weighting, fit intercept, maximum 2,000 iterations, tolerance 1e-6, and no additional hyperparameter search.

## Metrics and uncertainty

- claim-level coverage and selective risk;
- discrete AURC as the arithmetic mean of all prefix risks k=1,...,n;
- R80 at `floor(0.8n+0.5)` with an identical accepted count for every method;
- EARS-minus-B1 paired differences;
- 10,000 paired connected-group bootstrap replicates, seed 20261016;
- fixed score predictions and no bootstrap retraining;
- SHA-256 tie key based on seed 20261015 and claim ID.

## Semantic boundaries

Gold-evidence classification, end-to-end verification, evidence insufficiency, and model abstention are different tasks. Empty evidence is not a Neutral label. NO_RELATION is not a verified Evidence Insufficient label. Rejecting a prediction does not change its true label.

## Prohibitions retained after publication

Do not tune on the used Internal Test, claim official Test F1, relabel unannotated claims, report EARS scores as calibrated probabilities, infer H2/H3 results, hide the unfavorable R80 endpoint, or describe the system as deployment ready.

