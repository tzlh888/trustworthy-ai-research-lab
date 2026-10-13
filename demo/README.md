# Local Streamlit Research Demo

This interface runs the frozen E1 retrieval/NLI pipeline and the final B1/EARS risk models. It is a research visualization, not a fact-checking service.

## Requirements

- Python 3.12
- access to the pinned Hugging Face NLI revision on first download

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run demo/app.py
```

On first start, the app downloads only the Phase 0 audited official SciFact archive. It verifies the archive SHA-256, extracts only `data/corpus.jsonl`, verifies the corpus SHA-256, and atomically stores the result under the ignored `.cache/scifact/` directory. If `data/raw/scifact/corpus.jsonl` or `SCIFACT_CORPUS_PATH` is present, that file is accepted only after the same corpus size and checksum checks.

The public app does not deserialize joblib or pickle. It verifies the original Phase 3B model manifest and its lossless numeric JSON parameters, then applies the frozen scaler values, coefficients, intercept, and sigmoid directly. The JSON scorer was compared with the trusted original joblib bundles on the frozen Internal Test feature matrix at the `1e-12` gate.

The app displays retrieved papers and document IDs, selected sentences, raw NLI scores, the E1 category, and uncalibrated B1/EARS ranking scores. It never calls those scores error probabilities and does not implement a deployment threshold. `NO_RELATION` retains its frozen aggregation meaning and is not renamed Evidence Insufficient.

For Streamlit Community Cloud, deploy `demo/app.py` from the repository root and select Python 3.12 in Advanced settings. The root `requirements.txt` is the cloud dependency file. The first start downloads approximately 3.1 MB for SciFact and approximately 328 MB of pinned NLI weights from Hugging Face; subsequent reruns use disk and Streamlit resource caches while the instance remains warm.

SciFact claims and annotations are CC BY 4.0; corpus abstracts are S2ORC material under ODC-By 1.0. The demo downloads but does not commit the raw corpus. See `THIRD_PARTY_NOTICES.md`.
