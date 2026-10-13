# One-Page Research Summary

## Evidence-Aware Risk Scoring for Scientific Claim Verification

**Research question.** Can a risk estimator that observes both NLI behavior and label-free evidence-retrieval signals rank scientific claim-verification errors better than an NLI-only risk model?

**Motivation.** A verifier may be highly confident even when retrieval, sentence selection, NLI, or claim aggregation fails. Selective prediction studies whether high-risk outputs can be rejected while retaining a useful fraction of predictions. It does not make the underlying classifier more accurate.

**Data and system.** I used the official SciFact data and audited provenance, schema, licenses, duplicates, and leakage risks. The frozen E1 pipeline used BM25 retrieval, label-free lexical sentence selection, and a pinned DistilRoBERTa NLI cross-encoder. Train was divided by connected cited-document groups into 527 fit, 141 calibration, and 141 Internal Test claims. Calibration was not used in this study.

**Method.** Full EARS is an L2 logistic-regression error-ranking model. Its frozen inference-time features represent final-decision confidence, support-contradiction margin, predicted category, BM25 top-two margin, and evidence conflict. B1 is a fair NLI-only comparator trained on the same 329 eligible fit claims with the same target, preprocessing, regularization, and solver. The only method difference is the evidence features.

**Independent result.** The Internal Test contained 88 eligible SUPPORT/CONTRADICT claims. The base verifier achieved 0.488636 accuracy. EARS improved AURC from 0.300833 to 0.264987 relative to B1. The paired difference was -0.035846, with 95% grouped-bootstrap CI [-0.076087, -0.003447]. At the preregistered 80% coverage point, however, EARS was worse: selective risk 0.457143 versus 0.428571, a difference of +0.028571 with CI [0.000000, 0.063492]. EARS accepted 32 errors among 70 claims; B1 accepted 30.

**Conclusion.** H1 was **inconclusive under the preregistered joint criterion** because both endpoints had to improve. EARS changed error ranking and improved average prefix behavior, but did not reliably improve the fixed operating point. H2 evidence-degradation robustness and H3 probability calibration were not evaluated.

**Integrity and limitations.** Models and predictions were hashed before test-label access. Confidence intervals used 10,000 paired connected-group bootstrap replicates. Two deterministic recalculations produced byte-identical core results. The test sample was small, the base verifier made 45/88 errors, NO_RELATION was not a ground-truth insufficiency label, and the Internal Test was not an external dataset. This system is not suitable for medical or other high-stakes fact checking.

**Verifiable contribution.** I developed and documented the research question, staged protocol, leakage controls, frozen comparison, reproducibility checks, error analyses, and restrained interpretation. AI-assisted tools supported implementation and drafting; all public claims remain subject to my review and explanation.

