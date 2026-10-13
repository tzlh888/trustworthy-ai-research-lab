# Streamlit Cloud Deployment Test Record

## Final Result

All executable public-candidate checks passed. Tests were performed without retraining and without changing any frozen metric or prediction artifact.

## Automated Checks

| Check | Result | Evidence |
|---|---|---|
| Python syntax compilation | PASS | `demo/app.py`, `demo/core.py`, `demo/cloud_artifacts.py`, and the cloud audit script compiled under Python 3.12.15 |
| Public test suite | PASS | 16 passed, 61 skipped in 2.69 seconds |
| Frozen Phase 0-3B hash audit | PASS | All 13 hash-check sections passed; cross-checks confirmed H1 INCONCLUSIVE, no post-test retraining, and no prohibited data use |
| Public numeric model integrity | PASS | Manifest and numeric JSON matched fixed byte counts and SHA-256 values |
| Trusted-original numeric equivalence | PASS | 141 rows; B1 max difference 1.1102230246251565e-16; EARS max difference 5.551115123125783e-17; tolerance 1e-12 |
| Real official SciFact download | PASS | Archive and corpus checks passed; 8,307,875-byte corpus cached |
| Independent-process cache reuse | PASS | Second process reported `verified runtime cache` without downloading again |
| BM25/NLI/risk end-to-end path | PASS | Real corpus, pinned NLI, five displayed documents, finite B1/EARS scores, no Streamlit exception |
| Headless Streamlit server | PASS | Server started; `/_stcore/health` returned `ok`; root HTML returned successfully |
| Linux CPython 3.12 dependency resolution | PASS | All root requirements resolved for compatible x86_64 manylinux wheel tags |
| Public privacy/artifact scan | PASS | 122 files scanned; no prohibited raw data, serialized model, credential pattern, private path, or tool-workspace marker found |

The 61 skipped tests belong to the complete private research package and require intentionally excluded raw claims, claim-level predictions, internal reports, or joblib bundles. `tests/conftest.py` makes this boundary explicit. Setting `RUN_FULL_RESEARCH_TESTS=1` without the full private artifacts raises an error instead of misreporting a complete reproduction.

An initial run of the legacy full suite in the public checkout exposed those missing-private-artifact assumptions. The tests were not treated as experimental failures; the public/private test boundary was then made explicit, while all deployment, safety, publication, aggregate-result, and cloud-artifact checks remain active.

## Corpus Failure and Restart Tests

The artifact tests cover:

- verified download and extraction of only the expected tar member;
- clear failure when the official download is unavailable, with no fallback dataset;
- rejection of a corrupt present cache before any network fallback;
- reuse of a verified disk cache after a new process/runtime call;
- fixed corpus digest, size, row count, and unique document IDs at application startup.

The real network test downloaded the official archive. The first independent process reported `audited official download`; the second reported `verified runtime cache`. The corpus SHA-256 was `b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62` in both cases.

## End-to-End Scientific-Claim Smoke Tests

The same frozen UI path was exercised with real user-input claims. These outputs are demo smoke-test observations, not accuracy measurements and not new research findings.

| Input claim | E1 category | B1 score | EARS score | Example top document ID |
|---|---|---:|---:|---:|
| Vitamin D supplementation reduces mortality in adults. | NO_RELATION | 0.7640 | 0.8274 | 23267371 |
| Obesity increases the risk of hypertension. | CONTRADICT | 0.8150 | 0.7192 | 12206390 |
| Low-dose aspirin reduces cardiovascular mortality. | NO_RELATION | 0.8430 | 0.8541 | 7613033 |

For each claim, BM25 returned genuine SciFact papers, 15 selected sentence-claim pairs were processed, five document panels had traceable IDs and titles, both risk scores were finite, and the page retained all mandatory scientific limitations. A final forced-CPU AppTest repeated the first claim and completed without an exception.

These categories must not be interpreted as truth judgments. In particular, a displayed `NO_RELATION` is only the frozen aggregation outcome and is not a validated Evidence Insufficient label.

## Commands for Rechecking

Use a Python 3.12 environment with the repository installed or `PYTHONPATH` configured:

```bash
python3.12 -m py_compile \
  demo/app.py demo/core.py demo/cloud_artifacts.py \
  scripts/audit_cloud_deployment.py
python3.12 -m pytest -q
python3.12 scripts/audit_cloud_deployment.py --root .
EARS_DEMO_DEVICE=cpu streamlit run demo/app.py --server.headless true
```

The trusted-original equivalence audit is optional and only valid against the owner's private, hash-verified research package:

```bash
python3.12 scripts/audit_cloud_deployment.py \
  --root . \
  --original-root <private-research-root>
```

The script verifies the two joblib hashes before deserializing them. Never point this option at downloaded, uploaded, or otherwise untrusted serialized objects.

## Checks Not Performed

- No actual Streamlit Community Cloud build was triggered because the owner has not approved a push.
- No Linux container runtime smoke test was possible because the installed Docker client could not connect to a daemon.
- No multi-user concurrency, long-duration uptime, cold-start timing, or Cloud memory-pressure test was performed.
- No H2 or H3 experiment, new accuracy evaluation, threshold selection, or formal model training was performed.

