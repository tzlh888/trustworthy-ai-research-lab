# Local Streamlit Research Demo

This interface runs the frozen E1 retrieval/NLI pipeline and the final B1/EARS risk models. It is a research visualization, not a fact-checking service.

## Requirements

- Python 3.12
- official SciFact corpus at `data/raw/scifact/corpus.jsonl`
- frozen local model bundles in `models/phase3b/`
- access to the pinned Hugging Face NLI revision on first download

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-phase4.txt
pip install -e .
streamlit run demo/app.py
```

The app displays retrieved papers, selected sentences, raw NLI scores, the E1 category, and uncalibrated B1/EARS ranking scores. It never calls those scores error probabilities and does not implement a deployment threshold. `NO_RELATION` retains its frozen aggregation meaning and is not renamed Evidence Insufficient.

Raw SciFact data and joblib bundles are intentionally excluded from the GitHub release candidate. Reproduce them locally using the documented pipeline and verify their manifests before running the demo.
