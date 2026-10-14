# Same-Dataset Held-Out Evaluation and Independence Audit

## Protocol and corrected access disclosure

Official SciFact Dev was evaluated under internally frozen protocol SHA-256 `70ae…2301`. The original V2 inference path used a claim-only projection for scoring but first deserialized full Dev JSON records to discover IDs. No annotation use in scoring was demonstrated, but perfect historical label-blindness is not claimed. The corrected restricted parser materializes only IDs and claim strings; corrective E1/E1-v2 replay was exactly equal to the historical scoring artifacts. Dev results were already known before correction, so the replay is not a fresh evaluation. Manifests record 300 Dev claims and 188 eligible SUPPORT/CONTRADICT claims.

## Independence audit

SciFact Dev was not used in the published project, but it belongs to the same dataset family. Relative to all 809 historical SciFact Train claims, it has zero ID overlap, two normalized claim-text overlaps, and 181 shared cited documents. Its evidence grade is therefore **independent same-dataset validation**, not external replication.

SciFact-Open was downloaded and hash-audited. All 279 claims share both IDs and normalized claim text with original SciFact, 194 use at least one evidence document from the original corpus, and the strict non-overlap subset is empty. Its 12,236-document candidate corpus is pool-conditioned and much smaller than the documented 500K corpus. It was not evaluated.

HealthVer contains 14,330 evidence–claim pairs with Supports, Refutes, and Neutral labels. Neutral is an annotated relation, not missing evidence or E1 NO_RELATION. The repository provides no equivalent abstract-retrieval corpus, so F4 and the full E1 pipeline are undefined. It was not forced into the comparison.

## Frozen-model result on SciFact Dev

The public, lossless frozen B1/EARS numeric parameters were applied without refitting:

| Model | n / groups | AURC | R80 | AUROC |
|---|---:|---:|---:|---:|
| B1 | 188 / 164 | 0.281575 | 0.413333 | 0.798007 |
| EARS | 188 / 164 | 0.288355 | 0.400000 | 0.787817 |

EARS improved the chosen 80% point by two errors but worsened average ranking and AUROC. The paired intervals from the matched reconstructed four-model study cross zero. The independent same-dataset result therefore does not validate a general EARS advantage.

## Evidence status

- Frozen-model scoring on SciFact Dev: **completed; same-dataset held-out evidence**.
- Same-dataset generalization: **evaluated; no reliable incremental EARS benefit**.
- Genuine cross-dataset replication: **NOT VALIDATED**.
- HealthVer full-pipeline evaluation: **not applicable without changing the task**.

The machine-readable source audit is `results/external_dataset_audit.json`; overlap details are in `results/dataset_overlap_audit.json`.
