from __future__ import annotations

import collections
import math
import statistics
from typing import Any


GOLD_LABELS = ("SUPPORT", "CONTRADICT")
PREDICTED_LABELS = ("SUPPORT", "CONTRADICT", "NO_RELATION")


def classification_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in records if row.get("evaluation_eligible")]
    if not eligible:
        raise ValueError("No eligible records")
    matrix = {
        gold: {predicted: 0 for predicted in PREDICTED_LABELS} for gold in GOLD_LABELS
    }
    for row in eligible:
        gold = row["gold_evidence_label"]
        predicted = row["predicted_claim_label"]
        if gold not in GOLD_LABELS or predicted not in PREDICTED_LABELS:
            raise ValueError(f"Unsupported labels: {gold}, {predicted}")
        matrix[gold][predicted] += 1

    per_label: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    for label in GOLD_LABELS:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in GOLD_LABELS if other != label)
        fn = sum(matrix[label][predicted] for predicted in PREDICTED_LABELS if predicted != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        per_label[label] = {
            "support": sum(matrix[label].values()),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    correct = sum(matrix[label][label] for label in GOLD_LABELS)
    errors = len(eligible) - correct
    return {
        "eligible_count": len(eligible),
        "correct_count": correct,
        "error_count": errors,
        "accuracy": correct / len(eligible),
        "macro_f1_support_contradict": statistics.mean(f1_values),
        "per_label": per_label,
        "confusion_matrix": matrix,
        "no_relation_prediction_count": sum(
            matrix[label]["NO_RELATION"] for label in GOLD_LABELS
        ),
    }


def retrieval_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in records if row["gold_evidence_doc_ids"]]
    empty = [row for row in records if not row["gold_evidence_doc_ids"]]
    result: dict[str, Any] = {
        "evidence_bearing_claim_denominator": len(eligible),
        "empty_evidence_claim_count_excluded": len(empty),
    }
    for cutoff in (5, 20):
        claim_hits = 0
        gold_total = 0
        gold_hits = 0
        for row in eligible:
            retrieved = {item["doc_id"] for item in row["retrieved_documents"][:cutoff]}
            gold = set(row["gold_evidence_doc_ids"])
            claim_hits += bool(retrieved & gold)
            gold_total += len(gold)
            gold_hits += len(retrieved & gold)
        result[f"claim_recall_at_{cutoff}"] = claim_hits / len(eligible)
        result[f"claim_hits_at_{cutoff}"] = claim_hits
        result[f"gold_document_recall_at_{cutoff}"] = gold_hits / gold_total
        result[f"gold_document_hits_at_{cutoff}"] = gold_hits
        result["gold_document_denominator"] = gold_total
    return result


def sentence_selection_metrics(records: list[dict[str, Any]], cutoff: int) -> dict[str, Any]:
    gold_sentence_total = 0
    retrieved_gold_sentence_total = 0
    selected_gold_sentence_hits = 0
    claim_doc_total = 0
    retrieved_gold_claim_docs = 0
    complete_set_hits = 0
    for row in records:
        evidence = row.get("gold_evidence", {})
        retrieved_by_id = {
            document["doc_id"]: document
            for document in row["retrieved_documents"][:cutoff]
        }
        for doc_key, rationale_sets in evidence.items():
            claim_doc_total += 1
            gold_unique = {
                index for rationale in rationale_sets for index in rationale["sentences"]
            }
            gold_sentence_total += len(gold_unique)
            document = retrieved_by_id.get(int(doc_key))
            if document is None:
                continue
            retrieved_gold_claim_docs += 1
            retrieved_gold_sentence_total += len(gold_unique)
            selected = {item["sentence_index"] for item in document["selected_sentences"]}
            selected_gold_sentence_hits += len(selected & gold_unique)
            if any(set(rationale["sentences"]).issubset(selected) for rationale in rationale_sets):
                complete_set_hits += 1
    return {
        "retrieval_cutoff": cutoff,
        "gold_claim_document_denominator": claim_doc_total,
        "retrieved_gold_claim_documents": retrieved_gold_claim_docs,
        "gold_sentence_denominator": gold_sentence_total,
        "retrieved_gold_sentence_denominator": retrieved_gold_sentence_total,
        "selected_gold_sentence_hits": selected_gold_sentence_hits,
        "pipeline_micro_gold_sentence_recall": (
            selected_gold_sentence_hits / gold_sentence_total if gold_sentence_total else None
        ),
        "conditional_micro_gold_sentence_recall": (
            selected_gold_sentence_hits / retrieved_gold_sentence_total
            if retrieved_gold_sentence_total
            else None
        ),
        "complete_rationale_set_hit_count": complete_set_hits,
        "pipeline_complete_rationale_set_hit_rate": (
            complete_set_hits / claim_doc_total if claim_doc_total else None
        ),
        "conditional_complete_rationale_set_hit_rate": (
            complete_set_hits / retrieved_gold_claim_docs if retrieved_gold_claim_docs else None
        ),
    }


def probability_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    values = sorted(
        row["prediction_confidence"]
        for row in records
        if row.get("evaluation_eligible") and row.get("prediction_confidence") is not None
    )
    if not values:
        return {"count": 0}

    def quantile(fraction: float) -> float:
        index = min(len(values) - 1, max(0, math.ceil(fraction * len(values)) - 1))
        return values[index]

    return {
        "count": len(values),
        "min": values[0],
        "p25": quantile(0.25),
        "median": statistics.median(values),
        "p75": quantile(0.75),
        "p90": quantile(0.90),
        "max": values[-1],
        "mean": statistics.mean(values),
    }


def error_breakdown(records: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in records if row.get("evaluation_eligible")]
    errors = [row for row in eligible if not row["correct"]]
    categories: collections.Counter[str] = collections.Counter()
    by_label: collections.Counter[str] = collections.Counter()
    for row in errors:
        by_label[row["gold_evidence_label"]] += 1
        for category in row["failure_categories"]:
            categories[category] += 1
    return {
        "eligible_count": len(eligible),
        "error_count": len(errors),
        "error_rate": len(errors) / len(eligible) if eligible else None,
        "errors_by_gold_label": dict(sorted(by_label.items())),
        "category_counts_nonexclusive": dict(sorted(categories.items())),
        "class_distribution": dict(
            sorted(collections.Counter(row["gold_evidence_label"] for row in eligible).items())
        ),
    }
