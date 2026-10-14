from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
import torch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from demo.cloud_artifacts import (
    ArtifactDownloadError,
    ArtifactIntegrityError,
    CloudArtifactError,
    ensure_scifact_corpus,
    load_verified_numeric_models,
    score_frozen_models,
)
from demo.core import (
    DISCLAIMER,
    NO_RELATION_EXPLANATION,
    build_demo_retrieval_records,
    descriptive_percentile,
    finalize_demo_e1,
    score_language,
    validate_claim,
)
from trustworthy_ai_lab.data import load_jsonl
from trustworthy_ai_lab.nli import NLIEngine
from trustworthy_ai_lab.phase2_protocol import extract_features
from trustworthy_ai_lab.pipeline import build_e1_pairs
from trustworthy_ai_lab.retrieval import BM25Retriever
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


st.set_page_config(page_title="EARS Research Demo", page_icon="🔬", layout="wide")


@st.cache_resource(show_spinner="Verifying public runtime artifacts...")
def prepare_cloud_artifacts():
    return ensure_scifact_corpus(ROOT), load_verified_numeric_models(ROOT)


@st.cache_resource(show_spinner="Loading the verified SciFact corpus and retrieval index...")
def load_retrieval(corpus_path_text: str):
    corpus_path = Path(corpus_path_text)
    corpus = load_jsonl(corpus_path)
    if len(corpus) != 5_183:
        raise ArtifactIntegrityError(
            f"Verified SciFact corpus has an unexpected row count ({len(corpus)} rather than 5,183)."
        )
    doc_ids = [int(row["doc_id"]) for row in corpus]
    if len(set(doc_ids)) != len(doc_ids):
        raise ArtifactIntegrityError("Verified SciFact corpus contains duplicate document IDs.")
    return corpus, BM25Retriever(corpus, k1=1.5, b=0.75, epsilon=0.25), IDFOverlapSentenceSelector(corpus)


@st.cache_resource(show_spinner="Loading the pinned NLI model...")
def load_nli():
    config = json.loads((ROOT / "configs/phase1_baseline.json").read_text(encoding="utf-8"))
    nli = config["nli"]
    device_request = os.environ.get("EARS_DEMO_DEVICE", "auto").casefold()
    if device_request not in {"auto", "cpu"}:
        raise ValueError("EARS_DEMO_DEVICE must be 'auto' or 'cpu'.")
    device = "mps" if device_request == "auto" and torch.backends.mps.is_available() else "cpu"
    engine = NLIEngine(nli["model_id"], nli["revision"], device=device, max_length=nli["max_length"])
    return engine, device, nli["formal_batch_size"] if device == "mps" else 4


@st.cache_resource(show_spinner=False)
def load_risk_models():
    return load_verified_numeric_models(ROOT)


@st.cache_data(show_spinner=False)
def frozen_score_context():
    path = ROOT / "reports/phase3b/test_risk_predictions.csv"
    if not path.is_file():
        return {"B1": [], "EARS": []}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {method: [float(row[f"risk_{method}"]) for row in rows] for method in ("B1", "EARS")}


def run_claim(claim_text: str, corpus_path: Path):
    corpus, retriever, selector = load_retrieval(str(corpus_path))
    retrieval = build_demo_retrieval_records(
        [{"id": 0, "claim": claim_text}], retriever, selector, top_k=20, top_sentences=3
    )
    pairs = build_e1_pairs(retrieval)
    engine, device, batch_size = load_nli()
    predictions, stats = engine.predict(pairs, batch_size=batch_size)
    baseline = finalize_demo_e1(retrieval, predictions)[0]
    features = {"claim_id": 0, **extract_features(baseline, retrieval[0])}
    model_spec = load_risk_models()
    risks = {method: values[0] for method, values in score_frozen_models(model_spec, [features]).items()}
    return retrieval[0], baseline, features, risks, device, stats


st.title("Evidence-Aware Risk Scoring - Research Demo")
st.error(DISCLAIMER)
st.caption("Frozen study: H1 INCONCLUSIVE. H2 evidence degradation and H3 calibration were NOT EVALUATED.")

try:
    verified_corpus, _ = prepare_cloud_artifacts()
except ArtifactDownloadError as exc:
    st.error(f"SciFact download failed: {exc}")
    st.info("The app did not load unverified fallback data. Retry after the official source is reachable.")
    st.stop()
except ArtifactIntegrityError as exc:
    st.error(f"Artifact integrity check failed: {exc}")
    st.info("The app stopped before retrieval or model scoring. Clear the app cache and restart; do not bypass the checksum gate.")
    st.stop()
except CloudArtifactError as exc:
    st.error(f"Runtime artifact setup failed: {exc}")
    st.stop()

st.success(
    "Runtime artifacts verified: official SciFact corpus "
    f"({verified_corpus.size_bytes / 1_000_000:.1f} MB) and frozen B1/EARS numeric parameters."
)
st.caption(
    "SciFact source: Allen Institute for AI official release. Corpus abstracts are S2ORC material under ODC-By 1.0. "
    f"Runtime source: {verified_corpus.source}."
)

claim = st.text_area("Scientific claim", placeholder="Example: A scientific intervention changes a measured outcome.", height=100, max_chars=1000)
run = st.button("Run frozen research pipeline", type="primary", disabled=not claim.strip())

if run:
    try:
        cleaned = validate_claim(claim)
        with st.spinner("Retrieving abstracts and running 15 NLI sentence pairs..."):
            retrieval, baseline, features, risks, device, stats = run_claim(cleaned, verified_corpus.path)
    except Exception as exc:
        st.error(
            "Inference could not complete. The verified artifacts remain unchanged. "
            f"Failure type: {type(exc).__name__}. Please retry after the pinned model is reachable."
        )
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
- The historical internally protocol-frozen study found lower EARS AURC but worse EARS R80 than B1. H1 was inconclusive; no verified external preregistration is claimed.
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
