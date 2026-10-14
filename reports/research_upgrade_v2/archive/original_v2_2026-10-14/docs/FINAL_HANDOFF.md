# Final Handoff

## Overall status

**PARTIAL.** The requested implementation, same-dataset validation, ablations, diagnostics, robustness study, calibration study, documentation, and clean-release checks were completed. The scientific evidence remains partial because no eligible genuine cross-dataset replication was available and the historical private research package cannot be fully reconstructed from the public checkout.

## What changed

- Added a frozen Research Upgrade v2 protocol and hash-gated, label-blind inference workflow.
- Added original E1 and candidate E1-v2 inference, four matched risk-model comparisons, 10,000-replicate connected-group bootstrap analysis, feature diagnostics, error analysis, robustness tests, calibration evaluation, and historical post-hoc sensitivity analysis.
- Added machine-readable aggregate outputs, five reconstructible figures, a technical report, updated paper, one-page summary, validation report, statistical and reproducibility audits, limitations, decision log, and this handoff.
- Corrected the public cloud scanner so local virtual environments are excluded as third-party dependency trees, while project-owned files remain scanned.
- Updated the README and release-facing governance documents without changing historical frozen outputs, the formal baseline, or the Streamlit pipeline.

## Experiments actually completed

| Study | Status | Main outcome |
|---|---|---|
| Historical frozen-result preservation | PASS | Internal Test remains 88 eligible claims / 39 groups; B1 AURC 0.300833, R80 0.428571; EARS AURC 0.264987, R80 0.457143; H1 remains INCONCLUSIVE. |
| Official SciFact Dev frozen-model evaluation | PASS | 188 eligible claims / 164 groups; B1 AURC 0.281575, R80 0.413333; EARS AURC 0.288355, R80 0.400000. |
| F4/F5 matched reconstructed-model ablation | PASS | All three paired 95% intervals against B1 crossed zero; no reliable incremental benefit was established. |
| E1 error analysis | PASS | Accuracy 92/188 = 0.489362; SUPPORT recall 0.322581, CONTRADICT recall 0.812500; gold-document recall@5 0.842105 and pipeline gold-sentence recall 0.516393. |
| E1-v2 exploratory transfer | PASS as exploratory | Accuracy fell to 0.473404. EARS-v2 improved AURC against B1-v2 (0.264414 vs 0.287246) but R80 was tied at 0.420000; no confirmatory interval was preregistered. |
| Historical leave-one-group-out and acceptance-set analysis | PASS as post-hoc | Every one of 39 exclusions retained better EARS AURC and worse EARS R80. At 80% coverage, switching to EARS removed three B1 errors but introduced five. |
| Evidence perturbation robustness | PASS as exploratory | Dropping the top document was most disruptive (rank correlations about 0.535); ±5% BM25-score perturbation was almost inert. |
| Held-out calibration study | PASS as exploratory | Platt scaling slightly improved B1 proper scores but worsened EARS Brier/log loss; neither score is a validated error probability. |
| Genuine cross-dataset replication | NOT EXECUTED | SciFact-Open duplicates all 279 original claims and has no strict non-overlap subset; HealthVer changes the task and has no compatible retrieval corpus or F4. |

## Independence and evidence boundary

SciFact Dev was not used by the historical project, and v2 scores were persisted before labels were opened. It nevertheless shares the SciFact data-generating process, two normalized claims, and 181 cited documents with historical data. It is therefore **independent same-dataset validation**, not external replication. SciFact-Open and HealthVer were audited and retained as exclusions rather than forced into an invalid favorable comparison.

The public lossless numeric B1/EARS parameters were evaluated on Dev. B1+F4 and B1+F5 are explicitly reconstructed models trained on regenerated E1 features. E1-v2 and the interaction model are exploratory. None changes the evidential status of the historical study.

## Supported and unsupported findings

Supported:

- the original AURC/R80 conflict is real and robust to removing any one historical connected group;
- the conflict is caused by different estimands and empirically observed boundary swaps, not a reporting error;
- the original verifier has a severe SUPPORT-recall problem, with important loss between document retrieval and sentence-level evidence recovery;
- F5 carries limited conditional signal in some analyses, but its endpoint-level benefit is unstable;
- evidence removal can materially alter risk rankings, while small score-only BM25 perturbations do not.

Not supported:

- a reliable general advantage for Full EARS over B1;
- a useful incremental contribution from F4 on SciFact Dev;
- a successful E1-v2 verifier upgrade;
- calibrated probability semantics for either risk score;
- genuine cross-dataset or deployment generalization;
- any retrospective change to H1, H2, or H3.

## Test and reproducibility results

The final clean release-candidate copy contained tracked files plus this upgrade, but excluded `.git`, `.venv`, ignored caches, raw data, and private research artifacts.

- Complete clean-copy test suite: **23 passed, 61 skipped, 0 failed**, with two third-party SWIG deprecation warnings, in 3.30 seconds.
- Upgrade-specific tests: **7 passed, 0 failed**.
- Regression suite in the research checkout, excluding the deliberately incompatible clean-release safety assertion: **22 passed, 61 skipped, 0 failed**.
- Clean-copy cloud/privacy audit: **PASS**; 169 files scanned, zero findings, public numeric-model integrity passed.
- `git diff --check`: **PASS**.

The 61 skips are private/full-research tests whose required raw data or intentionally excluded claim-level historical artifacts are absent from a public checkout. The same tests remain strict when those inputs exist. A full test run inside the working research checkout intentionally fails the release-safety assertion because downloaded raw SciFact files are present there; the clean release candidate passes that assertion.

V2 can be rerun from the commands and hashes in `REPRODUCIBILITY_AUDIT.md`. Full public replay of every historical phase remains **PARTIAL** because private manifests, claim-level Phase 1 artifacts, joblib bundles, and one historically referenced report-building script are not public. V2 nevertheless regenerated E1 outputs and reproduced the historical frozen point metrics from public numeric parameters to floating-point precision.

## Acceptance audit

| Acceptance area | Status | Reason |
|---|---|---|
| Original frozen results intact | PASS | Historical tracked outputs were not modified; H1 is unchanged. |
| New protocol and data boundary | PASS | Protocol, eligibility, group bootstrap, model hashes, and label gate were frozen. |
| Negative-result retention | PASS | Adverse Dev, E1-v2, F4, and calibration outcomes are reported. |
| New-data authenticity/applicability audit | PASS | All three requested data sources were acquired or inspected with hashes, semantics, overlap, and license boundaries recorded. |
| Same-dataset independent validation | PASS | Official SciFact Dev was fully evaluated. |
| Genuine cross-dataset validation | NOT EXECUTED | No audited source met the frozen full-pipeline and non-overlap requirements. |
| Feature contribution study | PASS | Four matched models, group-aware CV, paired intervals, stability, importance, VIF, shift, and post-hoc interactions were run. |
| E1 failure analysis | PASS | Class, retrieval, selection, aggregation, overlap, and copyright-conscious case diagnostics were produced. |
| Statistical validity | PASS | Prespecified metrics, fixed-score connected-group uncertainty, effective counts, and limitations are explicit. |
| Robustness and calibration | PASS as exploratory | Prespecified perturbations and held-out calibration were completed without revising H2/H3. |
| New code and old-function regression | PASS | Clean suite has no failures and demo/cloud checks pass. |
| Public reproducibility | PARTIAL | V2 is reproducible; the complete historical private workflow is not public. |
| Public content safety | PASS | Clean scanner checked 169 files and found no raw data, weights, private paths, or credentials. |
| Research presentation | PASS | Required Markdown reports, paper, summary, figures, result tables, and README links are present. |
| Publication readiness | PARTIAL | Cross-dataset replication is absent and owner confirmation of identity, license, claims, and any release is still required. |

## Artifact locations

- Protocol: `configs/research_upgrade_v2_protocol.json`
- Inference and analysis: `scripts/run_upgrade_v2_inference.py`, `scripts/analyze_research_upgrade_v2.py`
- Upgrade tests: `tests/test_research_upgrade_v2.py`
- Reports and paper: `reports/research_upgrade_v2/`
- Public aggregate results and figures: `reports/research_upgrade_v2/results/`
- Private regenerated claim/pair records: ignored `.cache/research_upgrade_v2/`
- Historical frozen work: original `reports/phase3b/`, `reports/phase4/`, and `demo/frozen_parameters/`

No v2 PDF was claimed or generated; the updated paper is delivered as Markdown. Historical PDFs were left unchanged.

## Blockers and remote actions

There was no ordinary unresolved software blocker. The remaining limitations are evidential or provenance constraints: no compatible non-overlapping external dataset, missing public historical private artifacts, and owner-controlled author/license/release confirmations. No push, pull request, GitHub release, remote mutation, or deployment occurred.

## Honest current claim

The project can now claim a prospectively frozen, label-gated same-dataset validation, matched F4/F5 ablations, a substantially stronger account of verifier and ranking failure modes, and reproducible public aggregate analyses. It does not claim an externally registered preregistration. It cannot claim that EARS is generally superior, externally replicated, calibrated, clinically valid, or deployment-ready. The mature contribution is the evidence boundary: retrieval/evidence-consistency features are plausible signals, but their incremental value is small, endpoint-dependent, verifier-dependent, and not externally validated.

**FINAL SCIENTIFIC STATUS: PARTIAL**  
**FINAL REPRODUCIBILITY STATUS: PARTIAL**  
**FINAL PUBLICATION READINESS: PARTIAL**  
**ORIGINAL H1 STATUS: INCONCLUSIVE**  
**GIT REMOTE ACTIONS: NONE**
