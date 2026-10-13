from __future__ import annotations

import collections
import time
from typing import Any

from .aggregation import NLI_TO_CLAIM, aggregate_claim
from .data import derived_evidence_label
from .retrieval import BM25Retriever
from .sentence_selection import IDFOverlapSentenceSelector


def build_retrieval_records(
    claims: list[dict[str, Any]],
    folds: dict[int, str],
    retriever: BM25Retriever,
    selector: IDFOverlapSentenceSelector,
    *,
    top_k: int = 20,
    sentences_per_document: int = 3,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    records: list[dict[str, Any]] = []
    started = time.perf_counter()
    for claim in claims:
        retrieved = retriever.retrieve(claim["claim"], top_k=top_k)
        for document in retrieved:
            document["selected_sentences"] = selector.select(
                claim["claim"], document, top_n=sentences_per_document
            )
        gold_label = derived_evidence_label(claim)
        records.append(
            {
                "claim_id": claim["id"],
                "claim_text": claim["claim"],
                "fit_fold": folds[claim["id"]],
                "annotation_state": (
                    "EVIDENCE_ANNOTATED" if gold_label else "NO_ANNOTATED_EVIDENCE"
                ),
                "evaluation_eligible": gold_label is not None,
                "gold_evidence_label": gold_label,
                "gold_evidence_doc_ids": sorted(int(key) for key in claim["evidence"]),
                "gold_evidence": claim["evidence"],
                "retrieved_documents": retrieved,
            }
        )
    elapsed = time.perf_counter() - started
    return records, {
        "claim_count": len(records),
        "elapsed_seconds": elapsed,
        "claims_per_second": len(records) / elapsed if elapsed else 0.0,
    }


def build_e0_pairs(
    claims: list[dict[str, Any]], corpus_by_id: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for claim in claims:
        for doc_key, rationales in claim["evidence"].items():
            doc_id = int(doc_key)
            abstract = corpus_by_id[doc_id]["abstract"]
            for rationale_index, rationale in enumerate(rationales):
                sentence_indices = sorted(rationale["sentences"])
                premise = " ".join(abstract[index] for index in sentence_indices)
                pairs.append(
                    {
                        "pair_id": f"e0:{claim['id']}:{doc_id}:{rationale_index}",
                        "experiment": "E0_gold_evidence_oracle_diagnostic",
                        "claim_id": claim["id"],
                        "doc_id": doc_id,
                        "rationale_index": rationale_index,
                        "sentence_indices": sentence_indices,
                        "premise": premise,
                        "hypothesis": claim["claim"],
                        "gold_evidence_label": rationale["label"],
                        "evaluation_eligible": True,
                        "provenance": "authentic SciFact gold rationale; oracle diagnostic only",
                    }
                )
    return pairs


def finalize_e0(predictions: list[dict[str, Any]], folds: dict[int, str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for prediction in predictions:
        nli_label = prediction["predicted_nli_label"]
        predicted = NLI_TO_CLAIM.get(nli_label, "NO_RELATION")
        row = dict(prediction)
        row.update(
            {
                "fit_fold": folds[prediction["claim_id"]],
                "predicted_claim_label": predicted,
                "prediction_confidence": prediction["probabilities"][nli_label],
                "correct": predicted == prediction["gold_evidence_label"],
            }
        )
        records.append(row)
    return records


def build_e1_pairs(retrieval_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for record in retrieval_records:
        for document in record["retrieved_documents"][:5]:
            for selected in document["selected_sentences"]:
                pairs.append(
                    {
                        "pair_id": (
                            f"e1:{record['claim_id']}:{document['rank']}:"
                            f"{document['doc_id']}:{selected['sentence_index']}"
                        ),
                        "experiment": "E1_bm25_sentence_selection_nli",
                        "claim_id": record["claim_id"],
                        "doc_id": document["doc_id"],
                        "doc_rank": document["rank"],
                        "document_title": document["title"],
                        "sentence_index": selected["sentence_index"],
                        "selected_sentence_rank": selected["selected_rank"],
                        "sentence_selection_score": selected["selection_score"],
                        "premise": selected["sentence_text"],
                        "hypothesis": record["claim_text"],
                        "provenance": {
                            "dataset": "SciFact official corpus",
                            "source_file": "corpus.jsonl",
                            "retrieval": "BM25 top-5",
                            "sentence_selection": "label-free IDF overlap top-3",
                        },
                    }
                )
    return pairs


def _gold_selection_state(record: dict[str, Any], cutoff: int = 5) -> dict[str, Any]:
    gold_docs = {int(key): value for key, value in record["gold_evidence"].items()}
    retrieved = {
        document["doc_id"]: document for document in record["retrieved_documents"][:cutoff]
    }
    retrieved_gold_docs = sorted(set(gold_docs) & set(retrieved))
    any_gold_sentence_selected = False
    any_complete_rationale = False
    for doc_id in retrieved_gold_docs:
        selected = {
            sentence["sentence_index"] for sentence in retrieved[doc_id]["selected_sentences"]
        }
        gold_indices = {
            index for rationale in gold_docs[doc_id] for index in rationale["sentences"]
        }
        any_gold_sentence_selected |= bool(selected & gold_indices)
        any_complete_rationale |= any(
            set(rationale["sentences"]).issubset(selected)
            for rationale in gold_docs[doc_id]
        )
    return {
        "retrieval_hit_at_5": bool(retrieved_gold_docs),
        "retrieved_gold_doc_ids_at_5": retrieved_gold_docs,
        "any_gold_rationale_sentence_selected": any_gold_sentence_selected,
        "any_complete_gold_rationale_selected": any_complete_rationale,
    }


def finalize_e1(
    retrieval_records: list[dict[str, Any]],
    pair_predictions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_claim: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for prediction in pair_predictions:
        by_claim[prediction["claim_id"]].append(prediction)

    results: list[dict[str, Any]] = []
    for retrieval in retrieval_records:
        claim_predictions = by_claim[retrieval["claim_id"]]
        aggregation = aggregate_claim(claim_predictions)
        selection_state = _gold_selection_state(retrieval)
        gold_label = retrieval["gold_evidence_label"]
        eligible = retrieval["evaluation_eligible"]
        correct = eligible and aggregation["predicted_claim_label"] == gold_label
        categories: list[str] = []
        if eligible and not correct:
            if not selection_state["retrieval_hit_at_5"]:
                categories.append("retrieval_failure")
            elif not selection_state["any_complete_gold_rationale_selected"]:
                categories.append("sentence_selection_failure")
            else:
                categories.append("nli_or_reasoning_failure")
            if aggregation["predicted_claim_label"] == "NO_RELATION":
                categories.append("neutral_misclassification")
            if aggregation["support_contradict_conflict"]:
                categories.append("multiple_document_aggregation_failure")
            if any(row["truncated"] for row in claim_predictions):
                categories.append("truncation_related_failure")
            if any(
                NLI_TO_CLAIM.get(row["predicted_nli_label"]) == gold_label
                for row in claim_predictions
            ):
                categories.append("aggregation_failure")

        result = {
            "claim_id": retrieval["claim_id"],
            "claim_text": retrieval["claim_text"],
            "fit_fold": retrieval["fit_fold"],
            "annotation_state": retrieval["annotation_state"],
            "evaluation_eligible": eligible,
            "gold_evidence_label": gold_label,
            "gold_evidence_doc_ids": retrieval["gold_evidence_doc_ids"],
            **selection_state,
            **aggregation,
            "correct": correct if eligible else None,
            "failure_categories": categories,
            "sentence_predictions": sorted(
                claim_predictions,
                key=lambda row: (
                    row["doc_rank"],
                    row["selected_sentence_rank"],
                    row["sentence_index"],
                ),
            ),
        }
        results.append(result)
    return results
