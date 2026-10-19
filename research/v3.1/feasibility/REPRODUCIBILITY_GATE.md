# V3.1 Reproducibility Gate

**Rule:** every item marked required must pass before external-test inference or scoring. A clean run is a gate, not a claim that the science is valid.

## 1. Preserve V2

- [x] Audit from a clean clone at commit `6bca11589fb35f4dc8ef5bf9ac642e3369741351`.
- [x] Confirm clean working tree at audit start.
- [x] `git fsck --full` produced no integrity errors.
- [x] Confirm the frozen V2 protocol SHA-256 `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`.
- [x] Verify all 30 files named in the corrected V2 analysis manifest against their SHA-256 values; zero mismatches.
- [x] Preserve historical results, archived documents, correction replay, negative conclusions, and AI/licensing disclosures.
- [ ] Do not write V3.1 outputs into the V2 repository or reuse V2 result paths.
- [ ] If future work occurs, create a new immutable V3.1 directory or branch without amending historical commits.

The audit found a documented boundary: the public V2 package omits some historical claim-level caches, joblib bundles, and manifests. The corrected V2 replay was previously verified in its recorded environment, but a complete historical private-workflow reproduction from the public checkout remains partial. Do not erase this limitation.

## 2. Source and data lock

Before execution, a machine-readable manifest must include:

- V3.1 protocol version and SHA-256;
- V2 commit and protocol hash;
- SciFact archive and extracted-file hashes;
- SciFact correction repository commit and correction-file hashes;
- Check-COVID commit and every used data-file hash;
- retrieval corpus identity, document count, and hash;
- model repository, exact revision, tokenizer files, and local file hashes;
- every source file participating in projection, retrieval, NLI, feature extraction, ranking, and scoring;
- random seeds, tie rule, canonical identifier encoding, and locale/timezone.

Any mismatch is a hard stop. Mutable URLs such as `latest`, model aliases, or a live Vespa endpoint cannot be the only identity.

## 3. Exact environment

Create from an empty directory or disposable container/VM. Record:

- OS image/digest and architecture;
- Python implementation and exact version;
- complete transitive dependency lock with hashes, not only top-level requirements;
- BLAS/runtime, PyTorch, Transformers, tokenizer, and device backend versions;
- CPU/GPU/MPS model and deterministic settings;
- environment variables by name, with secrets redacted;
- installed-package listing and container image digest;
- command lines, exit status, start/end time, stdout, and stderr.

The V2 project pins Python `>=3.12,<3.13` and top-level libraries, but exact future availability is not enough. Resolve and archive a hash-locked environment before test work. Do not silently substitute the host's Python 3.14 or newer package versions.

## 4. Clean-environment verification sequence

Required sequence:

1. Create disposable environment with networking disabled after required artifacts are fetched and hashed.
2. Install only from the lock or an archived wheelhouse.
3. Run unit and integration tests on synthetic fixtures.
4. Verify model loading and class mapping.
5. Reproduce a small, public development fixture twice; require byte-identical canonical outputs or document a justified numeric tolerance before test.
6. Run the complete development pipeline from raw, hashed inputs.
7. Delete the environment and repeat once independently.
8. Compare manifests, row identities, labels predicted, features, and numeric values.
9. Only if equivalence criteria pass may a new clean environment run claim-only external inference.

No test label file may be mounted during steps 1–9 of inference.

## 5. Label-access control

Define roles even if one person fills them at different times:

- **Custodian:** holds annotation-bearing files and creates the claim-only projection.
- **Model operator:** can access claim ID/text and the frozen candidate corpus, but not test `label`, assigned `cord_id`, `evidence_set`, or scoring code output.
- **Scorer:** receives only the frozen prediction artifact and labels after prediction-hash verification.
- **Auditor:** verifies hashes, logs, and order of operations.

The test files are public and were inspected at aggregate level in this audit. Access controls prevent adaptive use; they do not make the evaluation blind. Disclose that distinction.

## 6. Prediction canonicalization and hashing

Before labels are opened:

1. Require exactly one row per claim-only test ID.
2. Reject missing, duplicate, unexpected, or non-canonical IDs.
3. Use a versioned schema with explicit class order and units.
4. Require finite features/scores and valid probability vectors.
5. Sort by canonical UTF-8 claim ID.
6. Serialize as UTF-8 JSON Lines with sorted keys, fixed separators, no NaN/Infinity, and a terminal newline.
7. Hash exact bytes with SHA-256.
8. Hash each model/corpus/code dependency and the whole manifest.
9. Make the prediction artifact read-only and copy it to independently controlled storage.

The manifest must state that labels were not loaded by the inference process. It must not claim that nobody had ever seen public labels.

## 7. Audit log

Use an append-only log with:

- UTC and client-time timestamps;
- actor/role;
- command or action;
- input and output hashes;
- row counts and schema version;
- label-bearing file access;
- failures, retries, deviations, and approvals;
- test opening time and pre-opening prediction hash;
- final report and figure hashes.

Never overwrite failed attempts. A rerun after label access is post-hoc unless it is a byte-identical recovery from a documented infrastructure failure under the frozen code.

## 8. Statistical reproduction

Required tests include:

- group graph built before eligibility filtering;
- 229 Check-COVID test IDs in the claim-only view;
- 153 eligible claims and 50 groups after scoring metadata is opened;
- REFUTE mapped only to CONTRADICT and NOTENOUGHINFO excluded;
- paired samples identical across methods;
- deterministic tie handling, including repeated bootstrap groups;
- fixed coverage count and discrete AURC checked against hand-worked fixtures;
- bootstrap seed, number of replicates, percentile convention, and invalid-replicate handling recorded;
- power simulation type-I error checked under a known null.

## 9. License and redistribution gate

- Preserve Check-COVID citation and MIT notice.
- Preserve CORD-19 attribution and its text/data-mining-only license notice.
- Do not assume the Check-COVID MIT file relicenses every embedded article abstract.
- Publish hashes and derived aggregates rather than unnecessary source abstract text.
- Preserve SciFact claims/annotations and corpus license notices.
- Obtain legal review before commercial or broad redistribution use. This gate is not legal advice.

## 10. AI-contribution disclosure

Every protocol, report, repository README, and publication must disclose materially relevant AI assistance. Minimum disclosure:

> AI-assisted systems materially supported methodology review, source and dataset auditing, protocol drafting, statistical-design review, and any later implementation or analysis explicitly listed in the execution log. The human research owner authorized the work and retains responsibility for data access, licensing, research decisions, verification, authorship, and public claims.

Do not describe AI-generated or AI-reviewed material as independent human replication.

## 11. Gate report

Before test inference, produce a signed/hashed table with `PASS`, `FAIL`, or `NOT RUN` for:

| Gate | Current status |
|---|---|
| V2 preservation and manifest verification | PASS for this audit |
| Dataset identity and split audit | PASS |
| Retrieval-score comparability | FAIL |
| Claim-only projection | NOT RUN |
| Exact dependency lock | NOT RUN |
| Two clean development reproductions | NOT RUN |
| F6 validation | NOT RUN |
| Power/type-I-error thresholds | NOT RUN |
| Prediction hashing rehearsal | NOT RUN |
| Label-access workflow | NOT RUN |
| License/publication review | PARTIAL |

Any `FAIL` or required `NOT RUN` means no formal external test.
