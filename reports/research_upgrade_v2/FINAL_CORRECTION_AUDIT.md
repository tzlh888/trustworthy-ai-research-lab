# Research Upgrade V2 Final Correction Audit

**Audit date:** 14 October 2026  
**Starting repository HEAD:** `e5d6c56b0b5b4723bf5cd3aa08625e2bce381aab`  
**Frozen V2 protocol SHA-256:** `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`  
**Correction specification SHA-256:** `fa36b25b01ea28f0b6c4be7153c4a14868e05c9fff06dd0d25940983503db60d`

## Scope and evidence classes

This audit repairs implementation and reporting defects without revising the frozen protocol or presenting previously observed SciFact Dev results as fresh confirmation. Original V2 outputs remain in `results/`; corrected outputs are in `corrections/2026-10-14/results/`; the prior V2 prose and relevant source snapshots are retained in `archive/original_v2_2026-10-14/`.

The historical run, corrected implementation, corrective replay, and current scientific interpretation are distinct evidence classes. The historical run deserialized complete Dev JSON records to discover IDs. Available code and artifacts show that only IDs and claim text entered retrieval and scoring, but this does not establish a perfectly label-blind historical execution. The corrected replay is post-study verification because Dev results were already known.

## Defect-by-defect findings

| Priority | Defect and original behavior | Correction | Direct evidence | Status / remaining uncertainty |
|---|---|---|---|---|
| P0-1 | The historical paper described a completed period ending 15 November 2026 and called the work preregistered. | Preserved the historical paper, added a dated archival notice, and produced a new authoritative manuscript using only supported October chronology and “internally protocol-frozen.” | `paper/ARCHIVAL_NOTICE_2026-10-14.md`; final Markdown and rendered PDF. | **PASS.** No third-party preregistration is claimed. Exact historical execution times remain limited to available manifests and file history. |
| P0-2 | `_partition_ids()` deserialized complete Dev annotation records. Historical provenance language was too strong. | Added a structural JSON projection parser that materializes only top-level `id` and `claim`; validates complete JSON, duplicate keys/IDs, types, counts, and missing fields; preserves partition identity. Added poisoning and regression tests. | `src/trustworthy_ai_lab/phase3b.py`; `scripts/run_upgrade_v2_inference.py`; `tests/test_research_upgrade_v2.py`. | **PASS for corrected code; historical blindness NOT VERIFIED.** Changing the parser cannot make Dev unseen again. |
| P0-2 replay | Equality of corrected and historical inference had been assumed rather than tested. | Re-ran E1 and E1-v2 using the corrected projection pathway and compared every scoring row while excluding timestamps and non-scoring metadata. | `corrective_inference_equivalence.json`; corrected inference manifests. | **PASS.** E1: 1,109 claims, zero differing rows/labels, max numeric difference 0, identical SHA-256 `3c1e…c941`. E1-v2: 827 claims, same conditions, SHA-256 `e508…774f`. This is corrective equivalence, not fresh validation. |
| P0-3 | Current documents contained overstrong independence, preregistration, blindness, reproducibility, and feature-contribution language. | Synchronized current README, paper, summary, reports, limitations, reproducibility, ownership, publication checklist, cloud report, and demo warnings with the actual evidence boundary. | Current release-facing documents and documentation consistency tests. | **PASS within audited files.** Archived/historical files intentionally retain prior wording and are marked superseded. |
| P1-1 | Ordinary `permutation_importance` output was named conditional permutation importance. | Renamed the current output to `marginal_permutation_importance.csv` and limited interpretation to exploratory model-dependent association. | Corrected analysis script, manifest, reports, paper, and CSV. | **PASS.** No causal or conditionally independent contribution is inferred. |
| P1-2 | Dev overlap was measured but lacked score-preserving sensitivity analysis. | Added deterministic claim- and connected-group-level exclusions for normalized duplicate claims and shared cited documents, using original frozen B1/EARS scores and 10,000 connected-group bootstrap replicates where supported. | `overlap_sensitivity.json` and `.csv`; deterministic tests. | **PASS as post-hoc sensitivity.** Duplicate-text exclusions removed no eligible claims. Shared-document exclusion retained 64 eligible claims in 53 groups; both paired intervals crossed zero. |
| P1-3 | The evidence injection was called semantically irrelevant although selection only guaranteed that the document was outside the retrieved set. | Retained the exact deterministic selection algorithm and renamed the current experiment `inject_deterministically_sampled_out_of_retrieval_document`. | Corrected inference/analysis scripts, CSV, figure input, reports, and manifest. | **PASS.** Semantic irrelevance is explicitly not established. |
| P2-1 | Prior packaging contained caches and was not a reproducible final candidate. | Added a deterministic ZIP builder with a fixed timestamp, explicit exclusions, required-file gate, source sensitive-data scan, archive path/CRC checks, sorted entries, per-file hashes, and a sidecar manifest. | `scripts/build_v2_release_candidate.py`; final ZIP manifest; full tests and cloud/privacy audit in a new extraction. | **PASS.** The final publication-corrected candidate passed 38 tests with 61 documented skips and zero failures; 226 files passed the privacy scan. A clean package does not make the missing historical private workflow public. |
| P2-2 | The old PDF did not represent corrected V2 evidence. | Produced a definitive 16-section manuscript and PDF, retained the old paper as historical, and visually inspected every rendered page. | `paper/Trustworthy_AI_Research_Lab_V2_Final.md` and `.pdf`; PDF verification recorded in the reproducibility report. | **PASS.** Scientific claims remain limited; publication is not implied. |
| P2-3 | No matching corrected one-page academic PDF existed. | Updated the single audience-neutral summary and generated a one-page PDF with ownership and AI-assistance disclosure. | `RESEARCH_ONE_PAGE_SUMMARY.md`; `paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf`. | **PASS.** No admissions endorsement or significant-outperformance claim is made. |

## Preserved numerical record

The historical Internal Test remains 88 eligible claims in 39 groups. B1 AURC/R80 remain 0.300833/0.428571; EARS remain 0.264987/0.457143. H1 remains **INCONCLUSIVE**; H2 and H3 remain **NOT EVALUATED**.

The unchanged primary SciFact Dev result remains 188 eligible claims in 164 groups. B1 AURC/R80 are 0.281575/0.413333; EARS are 0.288355/0.400000. EARS achieved worse AURC but better R80 than B1 on SciFact Dev, reversing the respective metric directions observed in the historical Internal Test. The paired confidence intervals for both Dev endpoint differences include zero; therefore, the Dev results do not establish a statistically supported overall EARS advantage or stable generalization.

For the shared-cited-document exclusion, 196 of 300 Dev claims were excluded, leaving 104 total, 64 eligible, and 53 eligible connected groups. B1 versus EARS AURC was 0.364051 versus 0.345359 (paired delta -0.018692, 95% group-bootstrap interval [-0.074248, 0.028015]); R80 was tied at 0.490196 (delta 0, interval [-0.018868, 0.037037]). This post-hoc subset does not establish an EARS advantage.

## Integrity conclusions

- Historical results and the frozen V2 protocol were not rewritten.
- Corrected inference prevents annotation-field materialization and is adversarially tested.
- Corrected scoring is empirically identical to the historical scoring artifacts, but the historical provenance defect remains disclosed.
- No compatible, non-overlapping cross-dataset replication was completed.
- Risk scores are ranking scores, not validated error probabilities.
- The public V2 correction is reproducible within its documented download/runtime boundary; the full historical private workflow remains only partially publicly reproducible.
- No push, pull request, release, deployment, commit, license change, or author-identity change was performed.

**Scientific readiness:** PASS as an accurately bounded research artifact with inconclusive/negative findings.  
**Public release authorization:** PENDING HUMAN OWNER review of authorship, identity, license, and publication claims.
