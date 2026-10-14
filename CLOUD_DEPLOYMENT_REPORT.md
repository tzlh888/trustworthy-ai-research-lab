# Streamlit Cloud Deployment Repair Report

## Status

**READY FOR OWNER REVIEW AND PUSH; NOT YET DEPLOYED.** The public candidate now has a verified runtime path for the official SciFact corpus and the frozen B1/EARS models. No model was retrained, no experiment result was recomputed or changed, and no remote Git action was performed.

The repaired app preserves the scientific boundary statements: H1 is **INCONCLUSIVE** under the internally protocol-frozen joint criterion; no verified external preregistration is claimed; H2 and H3 are **NOT EVALUATED**; B1/EARS outputs are uncalibrated ranking scores; `NO_RELATION` is not Evidence Insufficient; and the interface is not suitable for medicine or other high-risk fact checking.

## Before and After

Before this repair, `demo/app.py` expected a locally present raw corpus and locally present joblib bundles. Those files were correctly excluded from the public repository, so Streamlit Community Cloud could render the page but could not execute the complete retrieval and risk-scoring path.

After this repair:

1. The app locates an already-present corpus only if it passes the frozen size and SHA-256 checks.
2. If absent, it downloads the Phase 0 audited official SciFact archive, verifies the complete archive, extracts only `data/corpus.jsonl`, verifies the extracted corpus, and atomically places it in an ignored runtime cache.
3. The public app verifies the original Phase 3B model manifest and lossless numeric specification before scoring.
4. The app applies the frozen preprocessing values, coefficients, intercept, and sigmoid directly. It never fits a scaler or Logistic Regression model.
5. BM25 retrieval, evidence-sentence selection, NLI input order, label mapping, claim aggregation, and inference features remain aligned with the frozen configuration.

## Runtime Artifact Design

### SciFact corpus

- Official audited URL: `https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz`
- Archive size: 3,115,079 bytes
- Archive SHA-256: `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be`
- Corpus size: 8,307,875 bytes
- Corpus SHA-256: `b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62`
- Verified corpus rows: 5,183 with unique integer document IDs

The order of resolution is an explicitly configured path, a local research-layout path, the runtime disk cache, and finally the audited official download. Every accepted path uses the same size and digest gate. A present but corrupt cache fails closed; it is not silently replaced with a third-party dataset.

Streamlit resource caches hold the verified artifact record, retrieval index, sentence selector, NLI engine, and risk specification during a process lifetime. The ignored disk cache avoids repeated corpus downloads after a Python process restart while the filesystem persists.

### Frozen B1 and EARS models

The public candidate uses the simpler and safer JSON option. It includes only:

- the original frozen model manifest; and
- the lossless numeric specification produced in Phase 3B.

Their public copies exactly match the original SHA-256 values. No pickle or joblib file is public or loaded by the app. The optional audit script loads the locally owned joblib bundles only after verifying their fixed trusted hashes, solely to compare outputs. Across all 141 frozen Internal Test feature rows, the maximum absolute differences were:

| Method | Maximum absolute difference | Required tolerance |
|---|---:|---:|
| B1 | 1.1102230246251565e-16 | 1e-12 |
| Full EARS | 5.551115123125783e-17 | 1e-12 |

This verifies numerical equivalence without publishing executable serialized objects or changing the scoring rule.

## NLI Runtime

- Model ID: `cross-encoder/nli-distilroberta-base`
- Frozen revision: `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`
- Input direction: premise = selected evidence sentence; hypothesis = user claim
- Label mapping: 0 contradiction, 1 entailment, 2 neutral
- Maximum length: 512 with `longest_first` truncation
- Cloud device: CPU; local Apple Silicon may use MPS unless `EARS_DEMO_DEVICE=cpu`

The tokenizer and model are loaded through the existing `NLIEngine` and cached as a Streamlit resource. The pinned model repository contains an approximately 328 MB safetensors weight file, so the first cold start is expected to be substantially slower than later warm starts. The app reports truncation per evidence pair and preserves the frozen 15-pair aggregation path.

## Dependency Selection

Streamlit Community Cloud is expected to discover the repository-root `requirements.txt` because there is no dependency file beside `demo/app.py`. The deployment should select Python 3.12. The cloud runtime file contains only imports needed by the demo and retains the frozen versions of NumPy, pandas, PyTorch, Transformers, rank-bm25, and Streamlit. Research-only scikit-learn, SciPy, sentence-transformers, and pytest remain in the phase-specific or project configuration rather than the cloud image.

Linux CPython 3.12 dependency resolution was checked against compatible x86_64 manylinux wheel tags. A real Linux container was not executed because the local Docker daemon was unavailable.

## Deployment Instructions

In Streamlit Community Cloud, configure:

- repository: the owner-approved GitHub repository;
- branch: `main` after the reviewed commit is pushed;
- app file: `demo/app.py`;
- Python: 3.12.

No secret is required. Do not add a raw corpus, joblib bundle, model weights, or Internal Test claim-level artifacts to the repository.

## Files Added or Changed

Deployment implementation:

- `demo/app.py`
- `demo/core.py`
- `demo/cloud_artifacts.py`
- `demo/frozen_parameters/final_model_manifest.json`
- `demo/frozen_parameters/final_model_numeric_spec.json`
- `requirements.txt`
- `.gitignore`
- `pyproject.toml`

Verification and documentation:

- `tests/conftest.py`
- `tests/test_cloud_deployment.py`
- `tests/test_phase4.py`
- `scripts/audit_cloud_deployment.py`
- `README.md`
- `demo/README.md`
- `CLOUD_DEPLOYMENT_REPORT.md`
- `CLOUD_DEPLOYMENT_TESTS.md`
- `CLOUD_ARTIFACT_MANIFEST.json`
- `CLOUD_SECURITY_AUDIT.md`

## Remaining Operational Limits

- No commit was pushed, so the repaired revision has not yet run inside an actual Streamlit Community Cloud instance.
- Cloud cold-start duration and peak memory were not measured on Streamlit infrastructure.
- Runtime access to the official SciFact host and Hugging Face remains an external availability dependency on a cold instance.
- A warm-instance disk cache is an optimization, not a durability guarantee; eviction correctly causes a new verified download.
- This repair establishes executable parity, not improved scientific validity. The independent research conclusion and limitations are unchanged.

