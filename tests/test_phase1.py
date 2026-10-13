from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from trustworthy_ai_lab.aggregation import aggregate_claim
from trustworthy_ai_lab.data import load_phase1_data, load_selected_claims
from trustworthy_ai_lab.metrics import (
    classification_metrics,
    error_breakdown,
    retrieval_metrics,
    sentence_selection_metrics,
)
from trustworthy_ai_lab.nli import EXPECTED_ID2LABEL, NLIEngine
from trustworthy_ai_lab.retrieval import BM25Retriever, tokenize
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "cross-encoder/nli-distilroberta-base"
MODEL_REVISION = "b14d131f9d32668a5e6a982729b57ff6ed5dfcbd"


def tiny_corpus():
    return [
        {
            "doc_id": 20,
            "title": "No effect",
            "abstract": ["Treatment did not improve survival.", "Mortality was unchanged."],
            "structured": False,
        },
        {
            "doc_id": 10,
            "title": "Improved survival",
            "abstract": ["Treatment improved survival.", "A secondary sentence."],
            "structured": False,
        },
        {
            "doc_id": 30,
            "title": "Unrelated",
            "abstract": ["Cells were cultured overnight."],
            "structured": False,
        },
    ]


def test_tokenization_is_deterministic_and_nfkc_casefolded():
    assert tokenize("ＡBC-based Result") == tokenize("abc-based result")
    assert tokenize("ABC") == ["abc"]


def test_bm25_ranking_and_document_ids_are_deterministic():
    first = BM25Retriever(tiny_corpus()).retrieve("treatment improved survival", top_k=3)
    second = BM25Retriever(tiny_corpus()).retrieve("treatment improved survival", top_k=3)
    assert first == second
    assert first[0]["doc_id"] == 10
    assert {row["doc_id"] for row in first} == {10, 20, 30}
    assert [row["rank"] for row in first] == [1, 2, 3]


def test_bm25_ties_resolve_by_ascending_doc_id():
    results = BM25Retriever(tiny_corpus()).retrieve("nonexistenttoken", top_k=3)
    assert [row["doc_id"] for row in results] == [10, 20, 30]


def test_sentence_indices_and_text_are_preserved():
    selector = IDFOverlapSentenceSelector(tiny_corpus())
    document = tiny_corpus()[0]
    selected = selector.select("mortality unchanged", document, top_n=2)
    assert selected[0]["sentence_index"] == 1
    assert selected[0]["sentence_text"] == document["abstract"][1]
    assert sorted(row["sentence_index"] for row in selected) == [0, 1]


def test_aggregation_handles_neutral_and_multiple_documents():
    neutral = aggregate_claim(
        [
            {
                "pair_id": "n",
                "predicted_nli_label": "neutral",
                "probabilities": {"neutral": 0.8, "entailment": 0.1, "contradiction": 0.1},
                "doc_rank": 1,
                "selected_sentence_rank": 1,
                "sentence_index": 0,
                "doc_id": 10,
            }
        ]
    )
    assert neutral["predicted_claim_label"] == "NO_RELATION"
    conflict = aggregate_claim(
        [
            {
                "pair_id": "s",
                "predicted_nli_label": "entailment",
                "probabilities": {"neutral": 0.05, "entailment": 0.90, "contradiction": 0.05},
                "doc_rank": 2,
                "selected_sentence_rank": 1,
                "sentence_index": 0,
                "doc_id": 20,
            },
            {
                "pair_id": "c",
                "predicted_nli_label": "contradiction",
                "probabilities": {"neutral": 0.05, "entailment": 0.06, "contradiction": 0.89},
                "doc_rank": 1,
                "selected_sentence_rank": 1,
                "sentence_index": 0,
                "doc_id": 10,
            },
        ]
    )
    assert conflict["predicted_claim_label"] == "SUPPORT"
    assert conflict["support_contradict_conflict"] is True


def test_missing_evidence_is_excluded_not_counted_as_miss():
    records = [
        {"gold_evidence_doc_ids": [], "retrieved_documents": []},
        {
            "gold_evidence_doc_ids": [10],
            "retrieved_documents": [{"doc_id": 20}, {"doc_id": 10}],
        },
    ]
    metrics = retrieval_metrics(records)
    assert metrics["evidence_bearing_claim_denominator"] == 1
    assert metrics["empty_evidence_claim_count_excluded"] == 1
    assert metrics["claim_recall_at_5"] == 1.0


def test_eligible_label_evaluation_does_not_force_empty_evidence():
    records = [
        {
            "evaluation_eligible": True,
            "gold_evidence_label": "SUPPORT",
            "predicted_claim_label": "SUPPORT",
        },
        {
            "evaluation_eligible": False,
            "gold_evidence_label": None,
            "predicted_claim_label": "NO_RELATION",
        },
    ]
    metrics = classification_metrics(records)
    assert metrics["eligible_count"] == 1
    assert metrics["accuracy"] == 1.0


def test_selected_loader_never_deserializes_sealed_rows(tmp_path: Path):
    path = tmp_path / "claims.jsonl"
    path.write_text(
        '{"id": 1, "claim": "allowed", "evidence": {}}\n'
        '{"id": 2, this is intentionally invalid JSON after the id}\n',
        encoding="utf-8",
    )
    rows = load_selected_claims(path, {1})
    assert [row["id"] for row in rows] == [1]


def test_actual_loader_returns_only_frozen_fit_ids():
    claims, _, _, manifest = load_phase1_data(
        ROOT / "splits/train_split_manifest.json",
        ROOT / "data/raw/scifact/claims_train.jsonl",
        ROOT / "data/raw/scifact/corpus.jsonl",
    )
    fit = set(manifest["outer_splits"]["fit"]["claim_ids"])
    sealed = set(manifest["outer_splits"]["calibration"]["claim_ids"]) | set(
        manifest["outer_splits"]["internal_test"]["claim_ids"]
    )
    assert {row["id"] for row in claims} == fit
    assert not ({row["id"] for row in claims} & sealed)


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def test_persisted_phase1_outputs_are_fit_only_and_metrics_recompute_exactly():
    report = ROOT / "reports" / "phase1"
    manifest = json.loads((ROOT / "splits/train_split_manifest.json").read_text())
    fit = set(manifest["outer_splits"]["fit"]["claim_ids"])
    sealed = set(manifest["outer_splits"]["calibration"]["claim_ids"]) | set(
        manifest["outer_splits"]["internal_test"]["claim_ids"]
    )
    retrieval_rows = _read_jsonl(report / "fit_retrieval_results.jsonl")
    e1_rows = _read_jsonl(report / "e1_fit_predictions.jsonl")
    assert {row["claim_id"] for row in retrieval_rows} == fit
    assert {row["claim_id"] for row in e1_rows} == fit
    assert not ({row["claim_id"] for row in e1_rows} & sealed)

    persisted_retrieval = json.loads((report / "retrieval_metrics.json").read_text())
    assert retrieval_metrics(retrieval_rows) == persisted_retrieval["metrics"]
    assert sentence_selection_metrics(retrieval_rows, 5) == persisted_retrieval[
        "sentence_selection_at_5"
    ]
    assert sentence_selection_metrics(retrieval_rows, 20) == persisted_retrieval[
        "sentence_selection_at_20"
    ]
    persisted_e1 = json.loads((report / "e1_metrics.json").read_text())
    assert classification_metrics(e1_rows) == persisted_e1["metrics"]
    assert error_breakdown(e1_rows) == persisted_e1["error_breakdown"]


def test_error_analysis_sample_is_unique_fit_only_and_stratified():
    rows = _read_jsonl(ROOT / "reports/phase1/error_analysis_20_cases.jsonl")
    assert len(rows) == 20
    assert len({row["claim_id"] for row in rows}) == 20
    assert {row["analysis_stratum"] for row in rows} == {
        "retrieval_failure",
        "sentence_selection_failure",
        "aggregation_failure",
        "nli_or_reasoning_failure",
    }
    assert all(row["gold_evidence_trace"] for row in rows)


@pytest.fixture(scope="session")
def nli_engine():
    return NLIEngine(MODEL_ID, MODEL_REVISION, device="cpu", max_length=512)


@pytest.mark.integration
def test_nli_mapping_input_order_probability_and_truncation(nli_engine: NLIEngine):
    assert nli_engine.id2label == EXPECTED_ID2LABEL
    pairs = [
        {
            "pair_id": "short",
            "premise": "A man is eating pizza.",
            "hypothesis": "A man eats something.",
        },
        {
            "pair_id": "long",
            "premise": "scientific evidence " * 600,
            "hypothesis": "A short claim.",
        },
    ]
    predictions, _ = nli_engine.predict(pairs, batch_size=1)
    assert predictions[0]["premise"] == pairs[0]["premise"]
    assert predictions[0]["hypothesis"] == pairs[0]["hypothesis"]
    assert predictions[0]["input_order"] == "premise=evidence; hypothesis=claim"
    for row in predictions:
        assert math.isclose(sum(row["probabilities"].values()), 1.0, abs_tol=1e-6)
    assert predictions[0]["truncated"] is False
    assert predictions[1]["truncated"] is True


@pytest.mark.integration
def test_nli_cpu_repeated_run_is_consistent(nli_engine: NLIEngine):
    pairs = [
        {
            "pair_id": "repeat",
            "premise": "The intervention significantly reduced the measured outcome.",
            "hypothesis": "The intervention reduced the outcome.",
        }
    ]
    first, _ = nli_engine.predict(pairs, batch_size=1)
    second, _ = nli_engine.predict(pairs, batch_size=1)
    assert first[0]["predicted_nli_label"] == second[0]["predicted_nli_label"]
    for label in ("contradiction", "entailment", "neutral"):
        assert first[0]["probabilities"][label] == pytest.approx(
            second[0]["probabilities"][label], abs=1e-8
        )
