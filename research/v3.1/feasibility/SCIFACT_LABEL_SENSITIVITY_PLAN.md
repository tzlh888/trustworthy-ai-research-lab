# SciFact Label Sensitivity Plan

**Purpose:** preserve frozen V2 results while specifying a post-study re-scoring sensitivity using the BioNLP 2026 proposed corrections. No sensitivity metrics were executed in this audit.

## Provenance and caveat

- SciFact Dev file SHA-256: `86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217`.
- Correction repository commit: `5711f3fdf2305552df2b6e700dca2ebd7c8806e1` (`v1.0-bionlp2026`).
- `dev_corrections.json` SHA-256: `c45ff40e3a8906192595462596dd56146e476aafa5b39fb3cf5a367b80a62b23`.
- The correction release describes 11 claim-level corrections and one per-document error. It also states that the judgments were made by one human annotator, with LLM assistance on flagged cases, and have not been ratified by an independent second human rater. Treat them as proposed corrections, not unquestionable ground truth.

## Complete Dev mapping to the V2 evaluation population

All 12 listed claims are in the 300-claim V2 SciFact Dev population and were originally eligible. V2 groups are built from all Dev claims using shared cited documents and normalized claim identity before eligibility filtering. “Group” below is the minimum claim ID in the connected component.

| Claim ID | Annotated evidence document(s) | Proposed scope | Original -> proposed | Change class | V2 group | Original / corrected eligible members in group | Effect |
|---:|---|---|---|---|---:|---:|---|
| 593 | 19675911 | document 19675911 | SUPPORT -> CONTRADICT | label reversal | 593 | 1 / 1 | label changes; eligibility retained |
| 879 | 8426046 | all annotated evidence | CONTRADICT -> SUPPORT | label reversal | 879 | 2 / 2 | label changes; eligibility retained |
| 1385 | 306006 | all annotated evidence | SUPPORT -> CONTRADICT | label reversal | 1385 | 1 / 1 | label changes; eligibility retained |
| 808 | 36606083 | all annotated evidence | SUPPORT -> CONTRADICT | label reversal | 808 | 1 / 1 | label changes; eligibility retained |
| 343 | 5884524 | all annotated evidence | SUPPORT -> NEI | outcome mismatch | 343 | 1 / 0 | claim excluded; group loses all eligible members |
| 1368 | 2425364 | all annotated evidence | SUPPORT -> NEI | outcome mismatch | 1368 | 2 / 1 | claim excluded; group retained through another claim |
| 770 | 15476777 | all annotated evidence | SUPPORT -> NEI | outcome mismatch | 770 | 1 / 0 | claim excluded; group loses all eligible members |
| 1216 | 24142891 | all annotated evidence | SUPPORT -> NEI | entity mismatch | 1216 | 1 / 0 | claim excluded; group loses all eligible members |
| 1274 | 4406819 | all annotated evidence | SUPPORT -> NEI | entity mismatch | 1274 | 1 / 0 | claim excluded; group loses all eligible members |
| 847 | 16787954 | all annotated evidence | CONTRADICT -> NEI | entity mismatch | 847 | 1 / 0 | claim excluded; group loses all eligible members |
| 208 | 13519661 | all annotated evidence | SUPPORT -> CONTRADICT | overgeneralization | 208 | 1 / 1 | label changes; eligibility retained |
| 597 | 12779444, 25742130, 36355784 | document 12779444 only | SUPPORT -> NEI for one document | per-document outcome mismatch | 597 | 2 / 2 | claim remains SUPPORT through two other documents; grouping unchanged |

### Correction-file contradiction for claim 597

The JSON entry for claim 597 has `doc_id: null`, although the correction README and paper call it a per-document error. The released manual-review trail and source abstracts identify document 12779444 as the mortality-only document; the other two documents discuss incidence. V3.1 must not apply the JSON entry as a claim-wide `SUPPORT -> NEI` change. Before execution, obtain an upstream clarification or create a local, reviewed erratum recording document 12779444 as the inferred scope. The unmodified upstream file and its hash must be retained.

## Population consequences

| Population | Eligible claims | Eligible connected groups | SUPPORT | CONTRADICT | Excluded/no eligible evidence |
|---|---:|---:|---:|---:|---:|
| Frozen original labels | 188 | 164 | 124 | 64 | 112 |
| Proposed corrected labels | 182 | 159 | 116 | 66 | 118 |

The six claim-wide NEI corrections remove six eligible claims. Five connected groups lose all eligible members; group 1368 retains one other eligible claim. Label edits do not change graph edges or group identities. The claim-597 document edit also leaves the graph unchanged because grouping uses cited documents from the original full population, not only corrected evidence.

## Two required analyses

### A. Original-label analysis — immutable reference

Do not recompute, rename, or overwrite the frozen V2 result. Cite the existing artifacts and report:

- n = 188, groups = 164;
- B1/EARS AURC = 0.281575/0.288355;
- B1/EARS R80 = 0.413333/0.400000;
- EARS-minus-B1 AURC = +0.006780, 95% grouped-bootstrap interval [-0.016939, +0.033066];
- EARS-minus-B1 R80 = -0.013333, 95% interval [-0.034247, +0.006849];
- interpretation: no stable EARS advantage.

Label this “frozen original-label V2 result.”

### B. Corrected-label fixed-score sensitivity — new, post-study

Use the exact frozen per-claim E1 predictions and B1/EARS risk scores. Apply the 11 claim-level edits and the document-scoped claim-597 edit only in a separate derived label layer. Then:

1. Recompute eligibility and error targets; do not refit a verifier, scaler, or risk model.
2. Preserve the all-300-claim group graph and filter to the 182 corrected eligible claims only after group construction.
3. Recompute B1 and EARS AURC, R80, error AUROC, accepted-error counts, and risk-coverage curves.
4. Generate 10,000 paired connected-group bootstrap replicates using the frozen V2 seed only if exact reproduction is desired; otherwise use a new declared seed and label the analysis V3.1.
5. Report corrected minus original change for each method and EARS minus B1 under each label regime.
6. Add a leave-one-correction-out sensitivity for the 11 claim-level corrections. Treat claim 597 separately because its correction is document-scoped.
7. Report rank positions and error-target flips for corrected claims, but do not expose copyrighted evidence text beyond short, attributed summaries.

This analysis isolates evaluation-label sensitivity. It does not estimate what would have happened had corrected Train labels been used to fit the risk models.

## Optional Train-correction analysis — separate and non-confirmatory

The companion release also proposes 13 Train corrections. Applying them would change fit labels, eligibility, cross-fit folds' class balance, final model coefficients, and all downstream predictions. That is a new model-fitting experiment, not a label-only sensitivity. It requires explicit authorization, a separate protocol version, corrected Train hash, group-aware refitting, and a new freeze before any held-out scoring. It was not performed.

## Required artifacts before execution

- lossless frozen claim-level predictions and B1/EARS risks for every SciFact Dev claim;
- a manifest proving those artifacts match the V2 prediction hashes;
- immutable original and derived correction files;
- machine-readable correction application log with old/new labels, scope, eligibility, and group;
- unit tests for claim 597 and for the 188 -> 182 and 164 -> 159 transitions;
- a report that never replaces the original V2 tables.

The public V2 repository intentionally omits some private claim-level caches. If the exact frozen rows cannot be recovered and hash-verified, the corrected-label sensitivity is blocked; reconstructed predictions must be labeled reconstructed and cannot stand in for the frozen result.

## Interpretation

A material metric change would establish sensitivity to proposed annotations, not that the correction mechanism caused V2 errors. A small change would not validate every original label. Both regimes must be shown side by side, and the single-annotator status of the proposed corrections must remain visible.

## Sources

- [BioNLP 2026 audit companion](https://github.com/Kefez/scifact-audit-bionlp2026)
- [ACL Anthology author/paper entry](https://aclanthology.org/people/julien-sylvestre/unverified/)
- [Official SciFact repository](https://github.com/allenai/scifact)
