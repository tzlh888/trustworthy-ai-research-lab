# V3.1 Research Summary

## Research question

Trustworthy-AI V2 tested whether EARS, a frozen risk ranker combining NLI signals with label-free evidence-pipeline features, ranked scientific claim-verification errors better than the matched NLI-only B1 model. V2's joint conclusion was `H1 INCONCLUSIVE`: improvements were not stable across endpoints or evaluation populations.

V3.1 therefore examined a narrower question: how reliable is the SciFact Dev comparison when documented benchmark-annotation proposals change correctness labels, eligibility, and bootstrap grouping?

## Study A

Study A kept every prediction, score, model parameter, threshold rule, and tie rule frozen. It evaluated the original 188-claim/164-group cohort, a common 182-claim/159-group cohort, and the proposed-corrected 182-claim/159-group cohort. Corrected ΔAURC was `+0.001463` and corrected ΔR80 was `−0.013699`; both paired 95% confidence intervals included zero.

All six claims excluded by proposed NEI corrections were frozen-verifier errors. The lower absolute AURC/R80 values therefore partly reflect a changed evaluation population rather than improved model behavior.

## Study A+

Study A+ expressed finite-sample AURC as an exact weighted sum of ranked binary errors, verified that identity through exhaustive and randomized tests, and computed annotation-level influence. Exact enumeration showed that two documented proposals can reverse the small ΔAURC point ordering under a fixed common cohort. The reversal does not imply statistical significance or annotation truth.

A symmetric decomposition attributed most of the paired ΔAURC change to retained-label corrections, while most absolute-metric reduction came from cohort composition. Claim 597 remains ambiguous between document-level and literal claim-level interpretations.

## Scientific conclusion

The contribution is a reproducible benchmark-reliability and sensitivity case study, not a superior-model claim. Proposed corrections remain independently unratified, SciFact Dev is not a new blind test, and external generalization is not established. V3.1 development is closed and further model development is NO-GO.
