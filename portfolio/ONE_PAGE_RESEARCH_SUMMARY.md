# One-Page Research Summary

## Evidence-Aware Risk Scoring for Scientific Claim Verification

**Research question.** Can a risk estimator combining NLI behavior with label-free retrieval and evidence-consistency signals rank scientific claim-verification errors better than a matched NLI-only risk model?

**Motivation.** A verifier may be highly confident even when retrieval, sentence selection, NLI, or claim aggregation fails. Selective prediction asks whether high-risk outputs can be deferred for review while retaining useful predictions; it does not make the underlying classifier more accurate.

**Human research direction.** This is a solo-human-owner, substantially AI-assisted project. The human owner supplied the overarching objective and integrity requirements, required critical review and preservation of unfavorable results, and retains responsibility for public claims, authorship, licensing, and release. This role does not imply unaided design, coding, experimentation, or statistical analysis.

**System and comparison.** The project used official SciFact data with provenance, schema, license, overlap, and leakage audits. E1 combines BM25 retrieval, label-free lexical sentence selection, and a pinned DistilRoBERTa NLI cross-encoder. Full EARS is an L2 logistic error ranker using final-decision confidence, support-contradiction margin, predicted category, normalized BM25 top-two margin, and evidence-conflict rate. B1 uses the same samples, target, preprocessing, regularization, and solver but only the NLI-derived features.

**Historical result.** The frozen Internal Test contained 88 eligible claims in 39 connected groups. EARS improved AURC from 0.300833 to 0.264987 relative to B1, but worsened R80 from 0.428571 to 0.457143. Because the internally frozen joint criterion required both endpoints to improve, **H1 remained INCONCLUSIVE**. Historical H2 and H3 remained **NOT EVALUATED**.

**SciFact Dev result.** Dev contained 188 eligible claims in 164 groups. B1 achieved AURC 0.281575 and R80 0.413333; EARS achieved AURC 0.288355 and R80 0.400000. The endpoint directions reversed relative to the historical result, and both paired confidence intervals crossed zero. F4 did not improve ranking; F5 showed exploratory model-dependent association but no stable matched-model benefit. SciFact Dev is a separate official split from the same dataset family, not cross-dataset replication.

**Failure analysis and conclusion.** E1 Dev accuracy was 0.489, with SUPPORT recall 0.323 even though gold-document recall@5 was 0.842 and gold-sentence recovery was 0.516. Retrieving a relevant paper did not ensure that decisive evidence survived the pipeline. The project therefore supports a careful negative result and reproducible failure-analysis framework, not stable EARS superiority, calibrated error probabilities, external generalization, or deployment readiness.

**Later V3.1 sensitivity analysis.** V3.1 kept V2 predictions and scores frozen and evaluated proposed, independently unratified annotation corrections. On the proposed-corrected 182-claim/159-group cohort, EARS-minus-B1 ΔAURC was +0.001463 and ΔR80 was −0.013699; both paired intervals included zero. This post-hoc analysis did not create a new blind test and preserved the `INCONCLUSIVE` conclusion.

**AI assistance and evidence boundary.** AI-assisted systems contributed substantially to method and protocol discussions, implementation, debugging, experiment execution, statistical and reproducibility checks, writing, figures, PDFs, and demo development. The repository's [personal contribution statement](../docs/PERSONAL_RESEARCH_CONTRIBUTION.md) distinguishes owner direction and accountability, AI-assisted execution, project findings, unsupported stronger claims, and technical verification that remains pending until personally completed.
