# Evidence-Aware Risk Scoring for Scientific Claim Verification

[![Research status](https://img.shields.io/badge/H1-INCONCLUSIVE-6B7280)](#independent-results)
[![Protocol](https://img.shields.io/badge/protocol-phase3a--v1.0.0-155E75)](RESEARCH_PROTOCOL.md)
[![License candidate](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

> Research prototype only. This is not a fact-checking service. The repository does not provide medical advice, a scientific-truth service, calibrated error probabilities, or a deployment-ready verifier.

## Research Question

Can a frozen error-risk model that combines NLI behavior with label-free retrieval/evidence signals rank scientific claim-verification errors better than a matched NLI-only risk model?

## Human Research Direction and Accountability

This is a solo-human-owner, substantially AI-assisted research project. The human project owner supplied the overarching research objective and integrity constraints, required critical review and preservation of unfavorable results, and retains responsibility for the accuracy of public claims, authorship, licensing, and release. These responsibilities do not imply that every method, technical decision, experiment, or line of code was independently produced without AI.

## Research Upgrade v2

The 2026-10-14 upgrade adds a label-gated evaluation on official SciFact Dev, matched F4/F5 ablations, verifier-transfer analysis, historical leave-one-group-out sensitivity, evidence perturbations, and held-out calibration. It strengthens the failure analysis but does **not** establish a general EARS advantage.

On 188 eligible Dev claims in 164 connected groups, frozen B1 achieved AURC 0.281575 and R80 0.413333; frozen EARS achieved AURC 0.288355 and R80 0.400000. The paired group-bootstrap intervals for EARS-minus-B1 included zero for both endpoints. F5 showed exploratory model-dependent association, while F4 did not improve Dev ranking. An exploratory DeBERTa NLI replacement reduced verifier accuracy from 0.489362 to 0.473404 and is not a promoted baseline.

Start here:

- [v2 technical report](reports/research_upgrade_v2/RESEARCH_UPGRADE_V2_REPORT.md)
- [final correction audit](reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md)
- [final reproducibility verification](reports/research_upgrade_v2/FINAL_REPRODUCIBILITY_VERIFICATION.md)
- [authoritative corrected V2 paper](paper/Trustworthy_AI_Research_Lab_V2_Final.md) and [verified PDF](paper/Trustworthy_AI_Research_Lab_V2_Final.pdf)
- [corrected one-page summary PDF](paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf)
- [dated paper erratum and archival notice](paper/ARCHIVAL_NOTICE_2026-10-14.md)
- [one-page research summary](reports/research_upgrade_v2/RESEARCH_ONE_PAGE_SUMMARY.md)
- [same-dataset held-out evaluation and independence audit](reports/research_upgrade_v2/INDEPENDENT_VALIDATION.md)
- [feature contribution](reports/research_upgrade_v2/FEATURE_CONTRIBUTION.md)
- [E1 error analysis](reports/research_upgrade_v2/E1_ERROR_ANALYSIS.md)
- [statistical validity](reports/research_upgrade_v2/STATISTICAL_VALIDITY.md)
- [limitations](reports/research_upgrade_v2/LIMITATIONS_V2.md)
- [historical V2 reproducibility audit](reports/research_upgrade_v2/REPRODUCIBILITY_AUDIT.md)
- [research ownership and AI disclosure](RESEARCH_OWNERSHIP.md)

## Method

The base E1 verifier retrieves SciFact abstracts with BM25, selects three sentences from each of the top five documents using label-free lexical overlap, and applies the pinned `cross-encoder/nli-distilroberta-base` model to 15 sentence-claim pairs. Claim aggregation produces SUPPORT, CONTRADICT, or the model output NO_RELATION.

Full EARS is an L2 logistic-regression error-ranking model using:

- final-decision confidence;
- support-contradiction margin;
- predicted decision category;
- normalized BM25 top-two margin;
- evidence-conflict rate.

The primary B1 comparator uses the same training claims, target, preprocessing, regularization, and solver, but only the NLI-derived features. EARS is a combination of established methods, not a claimed algorithmic breakthrough.

## Dataset

The study uses the official [SciFact](https://github.com/allenai/scifact) release. Only official Train was divided into connected cited-document groups:

| Partition | Claims | Use |
|---|---:|---|
| Fit | 527 | E1 fit-only analysis and final risk-model training |
| Calibration | 141 | Not used in the reported H1 study |
| Frozen Internal Test | 141 | One-time independent evaluation |

Only claims with authentic, single-label SUPPORT or CONTRADICT evidence enter error metrics. The Internal Test had 88 eligible claims; 53 claims without annotated evidence were not relabeled as Neutral or Evidence Insufficient.

Raw SciFact data are not redistributed here. Claims/annotations are CC BY 4.0; S2ORC abstracts are ODC-By 1.0; upstream SciFact code is Apache-2.0. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Independent Results

The frozen E1 verifier achieved **0.488636 accuracy** on 88 eligible Internal Test claims.

| Method | AURC ↓ | R80 ↓ | Errors among 70 accepted |
|---|---:|---:|---:|
| B0 maximum confidence | 0.420457 | 0.471429 | 33 |
| B1 NLI-only | 0.300833 | **0.428571** | **30** |
| B2 evidence-only | 0.431151 | 0.471429 | 33 |
| Full EARS | **0.264987** | 0.457143 | 32 |

- Delta AURC (EARS - B1): **-0.035846**, paired 95% CI **[-0.076087, -0.003447]**.
- Delta R80 (EARS - B1): **+0.028571**, paired 95% CI **[0.000000, 0.063492]**.

**H1 INCONCLUSIVE under the internally protocol-frozen joint criterion.** EARS improved average risk-coverage ranking but was worse at the fixed 80% coverage point. No verified third-party preregistration is claimed, and it is incorrect to claim that EARS was proven generally superior to NLI-only risk scoring.

![Risk-coverage curves](reports/figures/figure_1_risk_coverage_fit_vs_test.png)

## Limitations at a Glance

- only 88 eligible independent-test claims and 39 eligible connected groups;
- weak base verifier: 45 errors among 88 eligible claims;
- held-out subset of SciFact Train, not an external dataset;
- NO_RELATION is a model aggregation outcome, not validated evidence insufficiency;
- EARS values are uncalibrated ranking scores, not error probabilities;
- H2 evidence-degradation robustness and H3 probability calibration were **Not Evaluated**;
- no medical, clinical, policy, or other high-stakes deployment validation.

See [LIMITATIONS.md](LIMITATIONS.md) for the full boundary statement.

## Reproduce Locally

Python 3.12 is required. Apple Silicon with 24 GB RAM was sufficient for the recorded run.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-phase4.txt
pip install -e .
```

Download the audited official SciFact archive; the script checks its SHA-256:

```bash
bash scripts/download_scifact.sh data/raw/scifact
```

Generate and audit the split:

```bash
python scripts/audit_scifact.py \
  --data-dir data/raw/scifact \
  --output reports/data_audit.json
python scripts/make_train_splits.py \
  --train-file data/raw/scifact/claims_train.jsonl \
  --output splits/train_split_manifest.json \
  --seed 20261012
```

The historical Phase 1/2/3 scripts are retained for the complete private reproducibility package, where excluded manifests, joblib bundles, and claim-level artifacts are present. They are not advertised as a complete public-checkout workflow. The published Internal Test is no longer unseen and must not be reused for new model selection.

Regenerate publication figures from already-frozen aggregate outputs:

```bash
python scripts/build_phase4_figures.py --root . --output-dir reports/phase4/figures
```

Run all tests:

```bash
PYTHONPATH=. pytest -q
```

In the public checkout, tests requiring excluded raw data, claim-level predictions, complete internal reports, or joblib bundles are explicitly skipped. Deployment, safety, publication, aggregate-result, and cloud-artifact tests run normally. Set `RUN_FULL_RESEARCH_TESTS=1` only in the complete private reproducibility package.

The public repository does not contain the historical private manifests, bundles, or the formerly referenced `scripts/build_phase1_reports.py`. Aggregate historical results remain immutable, and the v2 reconstruction exactly recovers their point metrics.

Run the public v2 study instead:

```bash
pip install -r requirements-research-upgrade-v2.txt
bash scripts/download_scifact.sh data/raw/scifact
PYTHONPATH=. python scripts/run_upgrade_v2_inference.py --root . --verifier e1 --batch-size 32
PYTHONPATH=. python scripts/run_upgrade_v2_inference.py --root . --verifier e1_v2 --batch-size 24
PYTHONPATH=. python scripts/analyze_research_upgrade_v2.py --root .
```

Detailed environment, seeds, artifacts, and known technical incidents are documented in [REPRODUCIBILITY.md](REPRODUCIBILITY.md) and the [v2 reproducibility audit](reports/research_upgrade_v2/REPRODUCIBILITY_AUDIT.md).

## Local Research Demo

The Streamlit interface downloads the audited official SciFact archive when the corpus is absent, verifies both archive and corpus SHA-256 values, and loads the frozen B1/EARS models from verified lossless numeric JSON parameters. It does not deserialize joblib in the public deployment.

```bash
pip install -r requirements.txt
streamlit run demo/app.py
```

The demo displays retrieved documents and traceable document IDs, selected sentences, raw NLI scores, the E1 category, and uncalibrated B1/EARS ranking scores. It does not implement a deployment threshold. Streamlit Community Cloud should be configured for Python 3.12 with `demo/app.py` as the entrypoint. See [demo/README.md](demo/README.md).

## Repository Map

```text
configs/          frozen experiment configurations
demo/             local Streamlit research interface
paper/            reviewed manuscript source and PDF
reports/          aggregate results and publication figures only
scripts/          data, experiment, audit, and figure scripts
splits/           frozen group-aware split manifest
src/              reusable pipeline and evaluation code
tests/            unit and integration tests
```

Raw data, claim-level predictions, caches, secrets, and trained model bundles are excluded from the release candidate.

## AI Assistance and Contribution Evidence

AI-assisted systems contributed substantially to method and protocol discussions, implementation and debugging, experiment execution, statistical and reproducibility checks, research writing, figures, PDFs, and demo development. The project does not present those activities as unaided human work.

The public contribution record distinguishes documented owner actions, owner-declared responsibility, AI-assisted execution, research findings, unsupported stronger claims, and future owner-performed verification. See the [personal research contribution statement](docs/PERSONAL_RESEARCH_CONTRIBUTION.md) and the full [research ownership and AI-assistance policy](RESEARCH_OWNERSHIP.md).

## Citation and License

Use [CITATION.cff](CITATION.cff) after the owner confirms its existing public identity before any future release. Apache-2.0 remains an owner-controlled license decision. Dataset and model licenses remain separate.

