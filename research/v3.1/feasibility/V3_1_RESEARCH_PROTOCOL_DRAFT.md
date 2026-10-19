# Trustworthy-AI V3.1 Research Protocol — Draft

**Status:** protocol and feasibility audit only; no V3.1 experiment is authorized or reported.
**Audit date:** 2026-10-19 (Europe/Budapest).
**Frozen V2 source:** `tzlh888/trustworthy-ai-research-lab`, commit `6bca11589fb35f4dc8ef5bf9ac642e3369741351`.
**Frozen V2 protocol SHA-256:** `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`.

## 1. Purpose and evidence boundary

V3.1 asks whether the frozen V2 error-risk ranking behavior is reliable within SciFact and transportable to a materially different claim-verification dataset. It focuses on benchmark reliability, generalization boundaries, and controls for unstable evidence pipelines. It does not reopen, overwrite, or reinterpret the historical V2 result as if it were newly observed.

The V2 record remains:

| Evaluation | Eligible claims / connected groups | B1 AURC | EARS AURC | B1 R80 | EARS R80 | Preserved conclusion |
|---|---:|---:|---:|---:|---:|---|
| Historical Internal Test | 88 / 39 | 0.300833 | 0.264987 | 0.428571 | 0.457143 | H1 inconclusive |
| SciFact Dev, original labels | 188 / 164 | 0.281575 | 0.288355 | 0.413333 | 0.400000 | no stable EARS advantage; paired intervals cross zero |

Historical H2 and H3 remain not evaluated. Risk scores remain ranking scores, not validated error probabilities. V2 already disclosed that its original Dev ID-discovery path deserialized annotation-bearing records and that the public package lacks some historical claim-level artifacts. V3.1 must preserve those disclosures.

## 2. Research questions and estimands

### RQ1 — benchmark-label sensitivity

How much do the released BioNLP 2026 proposed SciFact Dev corrections change eligibility, grouping, and the fixed-score B1-versus-EARS comparison?

- Original-label estimand: the frozen V2 Dev result, unchanged.
- Corrected-label estimand: EARS-minus-B1 discrete AURC on the corrected eligible Dev population, using the exact same frozen predictions and risk scores.
- The corrected-label analysis is a post-study sensitivity analysis, not a new validation set.

### RQ2 — external transportability

On the official Check-COVID test split, does frozen EARS rank errors better than frozen B1 under a task adapter specified before test scoring?

- Primary estimand: `Delta AURC = AURC(EARS) - AURC(B1)`; negative favors EARS.
- Unit analyzed: eligible claims; dependence handled by paired resampling of connected evidence-document groups.
- External-test population under the V2 eligibility rule: 153 SUPPORT/REFUTE claims in 50 connected document groups, not all 1,504 dataset claims.
- Confirmatory status is conditional on the compatibility, power, isolation, and reproducibility gates below. These gates currently do not pass.

### RQ3 — evidence-instability behavior

Does a prespecified, label-free F6 document-omission sensitivity measure add stable predictive information beyond B1, and does it behave differently from rank- and score-matched removal controls?

This question is developmental on SciFact Dev and Check-COVID Dev only. Gold-evidence diagnostics are forbidden as model inputs and are restricted to post-hoc development diagnostics.

## 3. Datasets and populations

### SciFact

- Use the official archive with SHA-256 `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`.
- Dev SHA-256: `86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217`.
- Corpus SHA-256: `b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62`.
- Original eligibility: authentic, non-empty evidence with exactly one label in `{SUPPORT, CONTRADICT}`.
- Group edges: shared cited document or identical normalized claim text, constructed on all 300 Dev claims before eligibility filtering.
- Proposed corrections come from the BioNLP 2026 companion release at commit `5711f3fdf2305552df2b6e700dca2ebd7c8806e1`; they remain proposed because the release states that they are single-human-annotator judgments not yet ratified by an independent second human rater.

### Check-COVID

- Pin repository commit `3ae70f8cac4df13a3ce56878e20d8e76790e422d`.
- Official files contain 1,068 train, 207 Dev, and 229 test claims; test is split across 180 composed and 49 extracted claims.
- Map `REFUTE` to V2 `CONTRADICT`; retain `SUPPORT`; exclude `NOTENOUGHINFO` from the V2 binary error-risk estimand. Do not map NOTENOUGHINFO to V2's predicted `NO_RELATION` category.
- Group by the single assigned `cord_id` and normalized claim identity, constructed before label filtering. No cross-document normalized-text edges were found in test; the result is 50 groups.
- The public test files are annotation-bearing and their aggregate labels were inspected during this feasibility audit. The study must never be described as genuinely blind.

## 4. Frozen systems and task adapter

No model training, tuning, threshold selection, or feature selection may occur after test access.

The frozen V2 components are:

- verifier: `cross-encoder/nli-distilroberta-base`, revision `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`;
- BM25: `rank-bm25` `BM25Okapi`, `k1=1.5`, `b=0.75`, `epsilon=0.25`;
- retrieval: top 20, with top 5 passed to label-free sentence selection;
- sentence selection: three global-IDF lexical-overlap sentences per document;
- aggregation: frozen V2 logic;
- B1 features: F1, F2, F3;
- EARS features: F1–F5;
- numeric model specification SHA-256: `c472f5b0f6035ca1fb70154efc4f76798681db8d5b8d2084f831cb6b62d9d90b`.

The Check-COVID adapter may change only identifiers and schema names. It must not use `label`, `evidence_set`, assigned `cord_id`, claim type, or gold rationales during inference. Claim type may be used later for descriptive subgroup analysis if it is frozen before label scoring.

### Retrieval compatibility gate

The official Check-COVID baseline queried a changing CORD-19 Vespa service, took up to ten hits, filtered them, converted the retained IDs through a Python `set`, and released neither BM25 scores nor deterministic rank order. Those artifacts cannot produce V2 F4. Two alternatives exist:

1. **Strict comparability:** reconstruct and freeze the exact historical CORD-19 index and Vespa scoring/ranking. No such snapshot or score-bearing artifact was located. This route is currently blocked.
2. **Closed-corpus transport study:** apply the V2 BM25 implementation to the released 347-document Check-COVID corpus. This yields mechanically comparable scores but changes the task from open, changing CORD-19 retrieval to a small gold-document-derived candidate pool. Results must be labeled closed-corpus transfer, not an official end-to-end Check-COVID replication.

No formal test may proceed until one route is chosen, justified, hashed, and shown on development data to provide at least two retrievable documents per claim and complete finite F1–F6 features.

## 5. Outcomes and analysis

### Primary

- Paired `Delta AURC` between frozen EARS and B1 on eligible external-test claims.
- Discrete AURC is the mean selective risk over every accepted prefix, with lower predicted risk accepted first.
- Ties use a predeclared dataset-specific SHA-256 key; the seed and claim-ID canonicalization must be frozen before inference.

### Secondary, descriptive

- R80, error-detection AUROC, accepted-error counts, and full risk-coverage curves.
- SUPPORT/REFUTE and composed/extracted subgroup estimates with intervals.
- Retrieval diagnostics, feature distribution shift, and F6 negative controls on development data.

Secondary analyses do not rescue a failed primary result and do not establish mechanisms.

### Uncertainty

- Resample connected groups with replacement; include all eligible claims in each sampled group and preserve repeated group occurrences.
- Use identical sampled groups for B1 and EARS.
- Report point estimate, interval, group count, claim count, invalid-replicate handling, and Monte Carlo error.
- Fixed-score intervals exclude model-training and model-selection uncertainty.

## 6. Label access and test isolation

The following ordering is mandatory:

1. Freeze protocol, source commit, dependency lock, corpus, claim-only input, model artifacts, feature code, tie rule, and analysis code.
2. A data custodian creates a claim-only test view containing only canonical claim ID and text. The model operator cannot read the annotation-bearing source during inference.
3. Run inference once in a clean environment. Canonically sort predictions, hash the exact bytes, and sign a manifest containing row count, schema, timestamps, command, environment, and all upstream hashes.
4. Verify completeness and hashes without labels.
5. Only then may the scorer load labels and eligibility metadata. Scoring produces an append-only access log.
6. Any post-label code or parameter change invalidates confirmatory status. Corrections require a new, explicitly post-hoc analysis label.

Because public labels have been inspected, permitted wording is “pre-specified held-out evaluation with role-separated label access.” Prohibited wording includes “blind test,” “unseen labels,” and “preregistered” unless a real third-party preregistration exists.

## 7. F6 and negative controls

F6 is not part of frozen V2 and has no audited current definition. Before any model fitting, define it as a label-free document-omission sensitivity statistic computed from valid probability vectors. The selected statistic, perturbation strength, rank handling, and aggregation must be frozen on development data.

Required controls are detailed in `F6_NEGATIVE_CONTROL_PLAN.md` and include:

- a no-op determinism control;
- label-free document removal;
- rank-matched and BM25-score-matched removal controls;
- replacement and deletion controls that separate missing-content effects from rank/score effects;
- probability-vector validation before divergence or distance is computed;
- gold-document diagnostics only after development predictions are frozen.

An association between F6 and errors is observational. Even a dataset-specific performance difference does not show that evidence instability caused the errors or that the removed document was mechanistically decisive.

## 8. Power and Go/No-Go

The 0.80 power target and true `Delta AURC = -0.020` alternative are provisional planning values. The effect is smaller than the historical Internal-Test point difference (-0.035846) and opposite the SciFact Dev point difference (+0.006780); it has no established operational utility threshold. It may be retained only as a clearly labeled minimum planning alternative, alongside sensitivity scenarios.

Before external scoring, the development-only simulation in `POWER_AND_GO_NO_GO_PLAN.md` must show:

- one-sided type-I error at most 0.05, with Monte Carlo uncertainty reported;
- at least 0.80 probability of rejecting `Delta AURC >= 0` when the data-generating `Delta AURC` is -0.020;
- at least 0.80 power under the prespecified conservative dependence/effect scenario, not just the most favorable model;
- stable conclusions across reasonable group-size and effect-heterogeneity scenarios.

If these conditions fail, the external analysis is stopped or downgraded to descriptive feasibility. The test set is not used to redesign the model, feature, corpus, or power model.

## 9. Interpretation rules

- A negative external `Delta AURC` is evidence of dataset-specific transport under the chosen adapter, not universal generalization.
- A subgroup difference is an observational association unless an intervention was randomized and the required causal assumptions are defended.
- Document-removal effects are controlled perturbation effects on the pipeline, not proof that natural errors were caused by retrieval or evidence instability.
- A significant result with a small effect may lack operational importance; a non-significant result may be imprecise rather than evidence of equivalence.
- Unsupported or incompatible external evaluation must be stopped rather than reframed as success.

## 10. Reproducibility and disclosure

Execution is allowed only after the full gate in `REPRODUCIBILITY_GATE.md` passes. Required outputs include exact dependency versions, immutable source and dataset hashes, hardware/backend details, deterministic seeds, complete stdout/stderr and access logs, claim-level predictions under controlled storage, and a transparent AI-contribution statement.

V3.1 must disclose that AI systems materially assisted methodology review, code or analysis design, auditing, and drafting. The human owner remains responsible for research decisions, data/license compliance, execution authorization, and public claims.

## 11. Current protocol decision

**No-Go for formal Check-COVID test evaluation.** The released retrieval artifacts do not provide comparable BM25 scores or deterministic rank order, the public labels have already been inspected, and development-based power has not been established. **Go only for protocol preservation, correction mapping, offline adapter tests on synthetic fixtures, and development-only feasibility work after explicit authorization.**

## Sources

- [Frozen V2 repository](https://github.com/tzlh888/trustworthy-ai-research-lab)
- [SciFact official repository](https://github.com/allenai/scifact)
- [BioNLP 2026 SciFact audit companion](https://github.com/Kefez/scifact-audit-bionlp2026)
- [Check-COVID official repository](https://github.com/posuer/Check-COVID)
- [Check-COVID paper](https://aclanthology.org/2023.findings-acl.888/)
- [CORD-19 license](https://github.com/allenai/cord19/blob/master/LICENSE)
