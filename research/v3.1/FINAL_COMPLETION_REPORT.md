# Trustworthy-AI V3.1 Final Completion Report

> Sanitized public copy of the pre-publication closure report. Path references and release-boundary wording were adapted for this repository package; scientific conclusions are unchanged.

Date: 2026-10-19
Decision authority: project owner; this report is an AI-assisted technical audit, not external peer review.

## Closure declarations

`V3.1 RESEARCH DEVELOPMENT: CLOSED`

`FURTHER MODEL DEVELOPMENT: NO-GO`

`INDEPENDENT ANNOTATION RATIFICATION: NOT COMPLETED`

`SCIENTIFIC RESULTS: FROZEN`

`EXTERNAL VALIDATION: NOT ESTABLISHED`

No training, new inference, external evaluation, paid API use, commit, push, release, publication, or submission occurred during closure.

## Final verification status

| Category | Status | Evidence |
|---|---|---|
| V2 INTEGRITY | PASS | clean commit `6bca11589fb35f4dc8ef5bf9ac642e3369741351`; `git fsck --full` clean; public security audit PASS |
| STUDY A VERIFIED | PASS | source hashes, cohort construction, point estimates, and 10,000-replicate grouped bootstrap reproduced |
| STUDY A+ VERIFIED | PASS | mathematical tests pass; exact enumerations and clean-environment outputs are byte-identical |
| SCIENTIFIC INTEGRITY | PASS | null results, uncertainty, disputed labels, non-blind status, and causal limitations preserved |
| AI DISCLOSURE | PASS | substantive Codex assistance remains explicitly disclosed; third-party AI methodology is attributed |
| PATH AUDIT | PASS | candidate-release text, metadata, links, filenames and source references inspected; findings recorded |
| PERSONAL PATH EXPOSURE | PARTIAL | two historical, hash-identified records retain local paths and are excluded from the public release set |
| LINK INTEGRITY | PASS | no broken Markdown local link; all 13 unique external URLs returned HTTP 200 on 2026-10-19 |
| REPRODUCIBILITY | PARTIAL | isolated artifact replay succeeds, but exact private E1 artifact is not in the public repository and no independent human replication exists |
| FINAL DOCUMENTATION | PASS | five closure deliverables created; hashes recorded in the final manifest |
| V3.1 RESEARCH CLOSURE | PASS | required terminal declarations adopted; no further experimental stage authorized |

## Contribution boundaries

### Frozen V2

V2 developed and evaluated an evidence-aware risk score (EARS) against B1 for selective prediction in scientific claim verification. Its authoritative conclusion remains inconclusive: endpoint directions were inconsistent, H2/H3 were not evaluated, and no clinical, causal, calibration, deployment, or external-generalization claim was established. V2 is unchanged.

### Study A

Study A is a post-hoc SciFact Dev annotation-sensitivity analysis using frozen predictions and scores. It mapped third-party proposed corrections, preserved Claim 597's scope conflict, built original/common/corrected cohorts, and recomputed AURC/R80 without retraining. Corrected ΔAURC was `+0.0014628739705844218`, 95% grouped-bootstrap CI `[-0.02181605832252585, 0.026993366644624574]`; corrected ΔR80 was `-0.0136986301369863`, CI `[-0.039735099337748325, 0.006993006993006978]`. Neither interval excludes zero.

### Study A+

Study A+ derived and verified the finite-sample weighted AURC identity, calculated exact per-annotation influence, enumerated documented label/eligibility scenarios, and separated cohort-composition effects from label effects. Two documented proposals can reverse the near-zero ΔAURC point ordering; that reversal is not statistical significance. Most absolute AURC reduction arises from removing six observations that were frozen-model errors.

### Pre-existing and third-party work

Selective prediction, risk–coverage evaluation, AURC, and benchmark-label auditing are previously published methods. The proposed SciFact corrections originate from Julien Sylvestre's BioNLP 2026 audit. V3.1 treats them as proposed single-auditor corrections, not independently ratified truth, and does not claim discovery credit for them.

### AI-assisted work

OpenAI Codex materially assisted source inspection, code drafting and execution, mathematical checking, figure/report review, path and credential scanning, literature synthesis, and documentation. It did not serve as a biomedical annotator, independent human reviewer, university reviewer, or peer reviewer. Human ownership, source verification, licensing decisions, and any application/publication claims remain the project owner's responsibility.

## Final scientific conclusion

EARS superiority has **not** been statistically established. SciFact Dev is already inspected and is not a new blind or independent test. The corrected-label proposals remain independently unratified. Claim 597 retains both documented interpretations. Check-COVID formal external evaluation remains NO-GO, so external validation is not established.

Study A/A+ contributes a reproducible negative-result case study: benchmark annotations and eligibility rules can materially change selective-prediction metrics and even reverse a small point ordering. This is a useful integrity and sensitivity result, not evidence of a superior model or causal mechanism.

## Release boundary

This package contains portable Study A+ code, non-sensitive aggregate reports, tables, figures, and a manifest. The historical Study A metrics artifact and driver contain personal absolute paths and remain restricted; they were not copied into this repository package. The portable [`scripts/study_a_plus.py`](scripts/study_a_plus.py) supersedes the historical driver for artifact-based replay through command-line paths.

The closure did not itself authorize release. [`MANIFEST.sha256`](MANIFEST.sha256) is an integrity inventory, not scientific validation or publication approval.
