# V3.1 Execution Decision

**Decision date:** 2026-10-19 (Europe/Budapest)
**Decision:** **NO-GO for formal V3.1 external-test execution.**
**Permitted next stage:** protocol hardening and development-only feasibility after explicit authorization.
**Not performed:** training, model inference, official external evaluation, F6 fitting, test scoring, API calls, commits, pushes, or publication.

## Why formal execution must stop

### 1. The proposed sample size was wrong

Check-COVID contains 1,504 claims overall, but the official test split contains 229. Only 153 meet the frozen V2 binary eligibility rule, and they form 50 evidence-document groups. Unequal group sizes can make the claim-weighted equivalent substantially smaller. The test cannot be powered or analyzed as 1,504 independent observations.

### 2. Retrieval scores are not comparable as proposed

Frozen V2 F4 requires deterministic top-two BM25 scores from a fixed 5,183-document corpus. Check-COVID's released Vespa artifacts contain filtered document IDs and abstracts but no BM25 scores; the IDs were emitted through an unordered set, and the underlying CORD-19 index was designed to change. F4 cannot be reconstructed faithfully.

A new V2 BM25 index over the released 347-document corpus is possible, but that is a small, gold-document-derived closed-corpus task. It is not the official open CORD-19 retrieval problem. Proceeding without renaming the estimand would be scientifically misleading.

### 3. Blindness is unavailable

The public Check-COVID test files contain labels, document mappings, and rationales. Aggregate labels were inspected for this mandatory feasibility audit. Future role separation can prevent adaptive use during inference, but cannot restore genuine blindness. Any report must disclose prior public availability and inspection.

### 4. Power is not established

No authorized frozen-model Check-COVID Dev predictions exist from which to calibrate the paired group-aware AURC simulation. The 0.80 power target and -0.020 planning alternative have not yet passed a development-based simulation or an operational-importance justification.

### 5. F6 is not defined or validated

F6 is not part of frozen V2. A defensible definition requires a valid probability distribution, label-free removal rules, rank- and score-matched controls, and development-only gold-evidence diagnostics. None has been frozen or run.

### 6. Exact public reproduction remains bounded

The frozen V2 repository is internally well documented and its corrected-result manifest verified, but the public package intentionally lacks some historical private claim-level artifacts and bundles. Corrected SciFact label sensitivity cannot be executed on reconstructed rows and presented as an exact frozen-score sensitivity unless the private rows are recovered and hash-verified.

## What the audit established

- Frozen V2 repository commit: `6bca11589fb35f4dc8ef5bf9ac642e3369741351`.
- Git object integrity check passed; the working tree was clean before inspection.
- The 30 artifacts in the corrected V2 analysis manifest matched their SHA-256 entries.
- Historical V2 conclusions and disclosures remain unchanged.
- Every proposed SciFact Dev correction was mapped to evidence document, V2 group, label effect, and eligibility effect.
- Proposed corrected SciFact Dev population: 182 eligible claims in 159 groups, versus 188/164 under original labels.
- Check-COVID authoritative split: 1,068/207/229 train/Dev/test.
- Check-COVID test under V2 eligibility: 153 claims in 50 groups.
- The released Check-COVID experiment variants omit several otherwise eligible test records; the authoritative claim files must control population accounting.
- Check-COVID and CORD-19 licensing terms require preserving underlying source obligations; the root MIT license is not a universal relicense of article abstracts.

## Frozen V2 project audit record

The public history contains nine commits from the initial research release through the final documentation merge. The substantive V2 portfolio was added at `3f679a202a3b4c2464516b3c4fdb987ba01ce58a`; later commit `101d01a0e61b2451e38b9a7ace8a9ef08ff47e36` and merge `6bca11589fb35f4dc8ef5bf9ac642e3369741351` changed only the personal-contribution publication-status wording. There is no need to rewrite history.

The audited tree includes protocols/configuration, source and tests, aggregate Phase 2–4 results, archived original V2 prose/source snapshots, dated corrective outputs, the numeric frozen-model specification, reports, paper/portfolio materials, cloud-demo artifacts, licensing, and AI-contribution disclosures. Raw SciFact data, model weights, and private claim-level caches are intentionally absent. That exclusion is compatible with a public release but blocks a complete public reconstruction of every historical phase.

The authoritative V2 conclusion is internally consistent across the final paper, closure report, and corrected analysis: Internal Test improved AURC but worsened R80, leaving H1 inconclusive; SciFact Dev reversed endpoint directions and did not establish a stable advantage; H2/H3 were not evaluated; no external, clinical, calibration, deployment, or causal-mechanism claim was established. The correction replay is explicitly post-study and cannot restore unseen-label status.

The root project license is Apache-2.0 for owner-controlled code, while SciFact, S2ORC abstracts, models, and dependencies retain separate terms. The repository discloses substantial AI assistance and human-owner responsibility. Those disclosures are part of the frozen scientific record.

## Conditional path to a future Go

The owner would need to authorize only the next preparatory stage, not test evaluation. That stage would:

1. choose and name the retrieval estimand—historical CORD-19 reconstruction or closed-347-document transfer;
2. implement an annotation-denying claim-only adapter and prove it on synthetic poison fields;
3. define F6 and run all controls on development data only;
4. run the paired group-aware power simulation on Check-COVID Dev;
5. create a hash-locked environment and reproduce the development pipeline twice from clean starts;
6. freeze models, code, corpus, statistics, access roles, and prediction-manifest schema;
7. issue a new signed Go/No-Go record before any test inference.

Formal test execution is allowed only if every gate passes. If retrieval compatibility cannot be restored, the scientifically honest options are:

- stop the cross-dataset full-pipeline claim;
- run a clearly labeled descriptive closed-corpus transfer analysis; or
- evaluate only components whose inputs and semantics are genuinely comparable.

## Recommended decision language

> V3.1 remains a protocol and feasibility study. The proposed Check-COVID external evaluation is not presently defensible as a confirmatory full-pipeline test because its effective test population is 153 claims in 50 document groups, official retrieval scores are unavailable and non-reproducible, public labels have been inspected, and power has not been established. No external evaluation was run.

## Preservation statement

No file in the frozen V2 repository was edited. No historical commit, result, conclusion, disclosure, or publication artifact was replaced. All new materials are standalone V3.1 audit documents.
