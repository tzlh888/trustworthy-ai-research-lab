from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st
import torch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from demo.core import DISCLAIMER, NO_RELATION_EXPLANATION, descriptive_percentile, score_language, validate_claim
from trustworthy_ai_lab.data import load_jsonl
from trustworthy_ai_lab.nli import NLIEngine
from trustworthy_ai_lab.phase2_protocol import extract_features
from trustworthy_ai_lab.phase3b import build_blind_retrieval_records, finalize_e1_blind, score_bundle
from trustworthy_ai_lab.pipeline import build_e1_pairs
from trustworthy_ai_lab.retrieval import BM25Retriever
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


st.set_page_config(page_title="EARS Research Demo", page_icon="🔬", layout="wide")


@st.cache_resource(show_spinner="Loading the frozen corpus and retrieval index...")
def load_retrieval():
    corpus_path = ROOT / "data/raw/scifact/corpus.jsonl"
    corpus = load_jsonl(corpus_path)
    return corpus, BM25Retriever(corpus, k1=1.5, b=0.75, epsilon=0.25), IDFOverlapSentenceSelector(corpus)


@st.cache_resource(show_spinner="Loading the pinned NLI model...")
def load_nli():
    config = json.loads((ROOT / "configs/phase1_baseline.json").read_text(encoding="utf-8"))
    nli = config["nli"]
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    engine = NLIEngine(nli["model_id"], nli["revision"], device=device, max_length=nli["max_length"])
    return engine, device, nli["formal_batch_size"] if device == "mps" else 4


@st.cache_resource(show_spinner=False)
def load_risk_models():
    return {
        "B1": joblib.load(ROOT / "models/phase3b/final_b1_model_bundle.joblib"),
        "EARS": joblib.load(ROOT / "models/phase3b/final_ears_model_bundle.joblib"),
    }


@st.cache_data(show_spinner=False)
def frozen_score_context():
    path = ROOT / "reports/phase3b/test_risk_predictions.csv"
    if not path.is_file():
        return {"B1": [], "EARS": []}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {method: [float(row[f"risk_{method}"]) for row in rows] for method in ("B1", "EARS")}


def required_paths() -> list[Path]:
    return [
        ROOT / "data/raw/scifact/corpus.jsonl",
        ROOT / "configs/phase1_baseline.json",
        ROOT / "models/phase3b/final_b1_model_bundle.joblib",
        ROOT / "models/phase3b/final_ears_model_bundle.joblib",
    ]


def run_claim(claim_text: str):
    corpus, retriever, selector = load_retrieval()
    retrieval = build_blind_retrieval_records([{"id": 0, "claim": claim_text}], retriever, selector, top_k=20, top_sentences=3)
    pairs = build_e1_pairs(retrieval)
    engine, device, batch_size = load_nli()
    predictions, stats = engine.predict(pairs, batch_size=batch_size)
    baseline = finalize_e1_blind(retrieval, predictions)[0]
    features = {"claim_id": 0, **extract_features(baseline, retrieval[0])}
    models = load_risk_models()
    risks = {method: score_bundle(bundle, [features])[0] for method, bundle in models.items()}
    return retrieval[0], baseline, features, risks, device, stats


st.title("Evidence-Aware Risk Scoring - Research Demo")
st.error(DISCLAIMER)
st.caption("Frozen study: H1 INCONCLUSIVE. H2 evidence degradation and H3 calibration were not evaluated.")

missing = [path.relative_to(ROOT).as_posix() for path in required_paths() if not path.is_file()]
if missing:
    st.warning("This local demo requires non-public data/model artifacts. Missing: " + ", ".join(missing))
    st.info("Follow demo/README.md to obtain official SciFact data and reproduce the frozen model artifacts. These files are intentionally excluded from the public release candidate.")
    st.stop()

claim = st.text_area("Scientific claim", placeholder="Example: A scientific intervention changes a measured outcome.", height=100, max_chars=1000)
run = st.button("Run frozen research pipeline", type="primary", disabled=not claim.strip())

if run:
    try:
        cleaned = validate_claim(claim)
        with st.spinner("Retrieving abstracts and running 15 NLI sentence pairs..."):
            retrieval, baseline, features, risks, device, stats = run_claim(cleaned)
    except Exception as exc:
        st.exception(exc)
        st.stop()

    st.subheader("Frozen E1 output")
    left, middle, right = st.columns(3)
    left.metric("E1 predicted category", baseline["predicted_claim_label"])
    middle.metric("B1 ranking score", f"{risks['B1']:.4f}")
    right.metric("Full EARS ranking score", f"{risks['EARS']:.4f}")
    if baseline["predicted_claim_label"] == "NO_RELATION":
        st.warning(NO_RELATION_EXPLANATION)

    context = frozen_score_context()
    for method in ("B1", "EARS"):
        percentile = descriptive_percentile(risks[method], context[method])
        st.write(score_language(method, risks[method], percentile))
    st.info("The study's 80% coverage result was computed by ranking the whole frozen test set. It does not define a numerical score threshold for this new claim.")

    st.subheader("Inference-time features")
    st.dataframe(pd.DataFrame([features]).drop(columns=["claim_id"]), width="stretch", hide_index=True)

    st.subheader("Retrieved papers and selected evidence sentences")
    pair_by_key = {(row["doc_id"], row["sentence_index"]): row for row in baseline["sentence_predictions"]}
    for document in retrieval["retrieved_documents"][:5]:
        with st.expander(f"Rank {document['rank']} · document {document['doc_id']} · {document['title']}", expanded=document["rank"] == 1):
            st.caption(f"BM25 score: {document['bm25_score']:.4f}")
            sentence_rows = []
            for selected in document["selected_sentences"]:
                pair = pair_by_key[(document["doc_id"], selected["sentence_index"])]
                sentence_rows.append({
                    "sentence_index": selected["sentence_index"],
                    "selected_rank": selected["selected_rank"],
                    "sentence": selected["sentence_text"],
                    "top_nli": pair["predicted_nli_label"],
                    "contradiction": pair["probabilities"]["contradiction"],
                    "entailment": pair["probabilities"]["entailment"],
                    "neutral": pair["probabilities"]["neutral"],
                    "truncated": pair["truncated"],
                })
            st.dataframe(pd.DataFrame(sentence_rows), width="stretch", hide_index=True)

    st.subheader("How to interpret this demo")
    st.markdown(
        """
- Retrieval shows candidates from the fixed 5,183-document SciFact corpus, not an exhaustive literature search.
- NLI scores describe the pinned model's relation prediction for one sentence-claim pair; they do not establish scientific truth.
- B1 and EARS are uncalibrated ranking scores. Higher scores were ranked as riskier in the study, but individual values have no validated probability meaning.
- The independent study found lower EARS AURC but worse EARS R80 than B1. The preregistered joint conclusion was inconclusive.
- Do not use this interface for diagnosis, treatment, clinical decisions, policy, or other high-stakes fact checking.
"""
    )
    st.caption(f"Inference device: {device}; sentence pairs: {stats.pair_count}; elapsed: {stats.elapsed_seconds:.2f}s")

with st.sidebar:
    st.header("Frozen study results")
    st.write("Eligible Internal Test claims: 88")
    st.write("E1 accuracy: 0.488636")
    st.write("B1 AURC: 0.300833")
    st.write("EARS AURC: 0.264987")
    st.write("B1 R80: 0.428571")
    st.write("EARS R80: 0.457143")
    st.markdown("**Conclusion: H1 INCONCLUSIVE**")
    st.divider()
    st.caption("No claim text is sent to a project-operated external API. Hugging Face model files may be downloaded by Transformers when absent from the local cache.")
