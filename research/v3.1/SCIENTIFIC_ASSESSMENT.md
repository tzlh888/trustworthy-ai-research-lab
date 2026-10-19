# Updated Scientific Assessment

## Bottom line

Study A+ is technically sound and materially improves the transparency of Study A. It establishes that the small B1–EARS point comparison is annotation-sensitive and separates label effects from cohort-selection effects. It does **not** establish EARS superiority, a causal mechanism, definitive corrected ground truth, or an independent test result. In its present form it is not strong enough for a standalone empirical paper; its most defensible value is as a rigorous sensitivity appendix or reproducibility note attached to the original work and annotation audit.

## Technical correctness

The finite-sample AURC identity follows by exchanging finite sums. Exact label influence follows by linearity when cohort and ranking are fixed; deletion cases are correctly recomputed. Direct and weighted implementations agree to at most `5.55×10⁻17` on frozen data, exhaustive small-case tests and 10,000 randomized cases pass, and clean outputs are byte-identical. The group-aware paired bootstrap follows the previously declared seed, grouping and percentile convention.

Technical cautions remain. AURC is sensitive to the project's discrete coverage convention and tie rule. R80 is a discontinuous statistic with the target prefix selected by half-up integer rounding, `floor(0.8n + 0.5)` (`k=150` for `n=188`; `k=146` for `n=182`). Bootstrap intervals quantify resampling variability conditional on one annotation scenario; scenario bounds quantify annotation uncertainty and have no probability interpretation.

## Empirical validity

The analysis validly answers a narrow conditional question: with fixed V2 outputs, how do documented alternative annotations and their induced eligibility changes alter risk–coverage metrics? It does not answer how either method generalizes to an independent population. SciFact Dev has already been used and inspected; therefore it cannot be relabeled as a new blind test.

The corrected point estimate is ΔAURC `+0.001463` and its group-bootstrap interval spans zero widely. Two documented changes can reverse the point sign, while none of the reported scenarios creates reliable evidence of a method difference. The fact that all six removed claims were verifier errors explains much of the absolute metric improvement as selection, not as a model change. Observed subgroup or rank effects remain associational.

## Scientific novelty

The original SciFact paper defines claim–abstract SUPPORT/CONTRADICT relations and rationales, making document-level versus claim-level scope substantively important ([Wadden et al., 2020](https://aclanthology.org/2020.emnlp-main.609/)). The BioNLP 2026 audit already contributes the proposed label-error discovery and reports downstream F1 changes ([Sylvestre, 2026](https://aclanthology.org/people/julien-sylvestre/unverified/)). Study A+ does not independently rediscover or human-validate those errors.

Risk–coverage evaluation and selective rejection are established topics ([Geifman & El-Yaniv, 2017](https://proceedings.neurips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html); [Ding et al., 2020](https://openaccess.thecvf.com/content_CVPRW_2020/html/w1/Ding_Revisiting_the_Evaluation_of_Uncertainty_Estimation_and_Its_Application_to_CVPRW_2020_paper.html)). Recent work also shows that metric choice itself can alter selective-classification rankings and proposes AUGRC as an alternative ([Traub et al., 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/047c84ec50bd8ea29349b996fc64af4b-Abstract-Conference.html)). Benchmark-label errors and their ability to destabilize rankings are likewise established ([Northcutt, Athalye & Mueller, 2021](https://arxiv.org/abs/2103.14749)).

Against that background, the AURC weighted identity is a straightforward finite-sum rearrangement, not a verified new theorem. The useful increment is application-specific: exact annotation influence for two frozen rankings, exhaustive documented-scenario bounds, explicit Claim 597 scope handling, and a symmetric cohort/label decomposition. That is a credible methodological case study, but the novelty is modest and mostly in disciplined integration rather than a new general statistical method.

## Reproducibility

Artifact-based reproducibility is strong: inputs are hash-gated, code and tests are present, a fresh Python 3.12 environment reproduced points, intervals and enumerations, and outputs matched byte-for-byte. Full public reproducibility is incomplete because the exact compact E1 artifact is locally preserved but intentionally absent from the public V2 repository. A release decision would also need to resolve licensing and privacy/provenance requirements without rewriting V2 history.

Reproducibility of the annotation truth is weak: the corrections are proposed by a third-party single-annotator audit and Claim 597 is internally scope-ambiguous. Computational repetition cannot replace independent blinded expert adjudication.

## Publication readiness

Not ready as a standalone scientific submission. The sample is small and reused, the key corrections lack new independent adjudication, corrected paired intervals include zero, and there is no independent external test after the Check-COVID NO-GO. The sensitivity and decomposition are worth preserving, but they do not by themselves sustain a broad performance or mechanism claim.

A narrow follow-up could become defensible if it is limited to a pre-registered, blinded, multi-annotator adjudication of all disputed claim–document pairs—especially Claim 597—with reviewer expertise, conflict resolution, agreement statistics, immutable adjudication records, and no model scores shown to adjudicators. Metrics should then be recomputed once under the frozen analysis, with no threshold tuning. Even a completed adjudication may still yield a null or non-novel result.

## AI contribution disclosure

Study A+ source inspection, code drafting, mathematical derivation, execution, report drafting, and literature synthesis were substantively assisted by OpenAI Codex. The AI did not act as a human domain annotator, did not provide university or peer-review approval, and did not establish annotation ground truth. All numerical claims are tied to local scripts and hash-identified artifacts; scientific judgments should receive human author review before any dissemination.
