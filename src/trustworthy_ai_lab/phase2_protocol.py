from __future__ import annotations

import hashlib
import math
from typing import Any


FINAL_CATEGORIES = ("SUPPORT", "CONTRADICT", "NO_RELATION")


def _pair_by_id(record: dict[str, Any], pair_id: str) -> dict[str, Any]:
    matches = [row for row in record["sentence_predictions"] if row["pair_id"] == pair_id]
    if len(matches) != 1:
        raise ValueError("Winning pair must occur exactly once")
    return matches[0]


def decision_confidence(record: dict[str, Any]) -> float:
    """Confidence aligned to the frozen claim aggregation, including NO_RELATION."""
    category = record["predicted_claim_label"]
    if category not in FINAL_CATEGORIES:
        raise ValueError(f"Unknown final category: {category}")
    if category == "NO_RELATION":
        if record.get("winning_candidate") is not None:
            raise ValueError("NO_RELATION must not have a non-neutral winner")
        value = min(
            row["probabilities"]["neutral"] for row in record["sentence_predictions"]
        )
    else:
        winner = record.get("winning_candidate")
        if not winner:
            raise ValueError("Non-neutral decision is missing its winning candidate")
        pair = _pair_by_id(record, winner["source_pair_id"])
        nli_label = "entailment" if category == "SUPPORT" else "contradiction"
        value = pair["probabilities"][nli_label]
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("Invalid decision confidence")
    return value


def support_contradict_margin(record: dict[str, Any]) -> float:
    pairs = record["sentence_predictions"]
    support = max(row["probabilities"]["entailment"] for row in pairs)
    contradict = max(row["probabilities"]["contradiction"] for row in pairs)
    return abs(support - contradict)


def evidence_conflict_rate(record: dict[str, Any]) -> float:
    pairs = record["sentence_predictions"]
    support = sum(row["predicted_nli_label"] == "entailment" for row in pairs)
    contradict = sum(row["predicted_nli_label"] == "contradiction" for row in pairs)
    if support + contradict == 0:
        return 0.0
    return 2.0 * min(support, contradict) / (support + contradict)


def bm25_top2_normalized_margin(retrieval_record: dict[str, Any]) -> float:
    documents = retrieval_record["retrieved_documents"]
    if len(documents) < 2:
        raise ValueError("At least two retrieved documents are required")
    first = float(documents[0]["bm25_score"])
    second = float(documents[1]["bm25_score"])
    if first < second:
        raise ValueError("Retrieved documents are not score-sorted")
    return (first - second) / (abs(first) + abs(second) + 1e-12)


def extract_features(
    prediction_record: dict[str, Any], retrieval_record: dict[str, Any]
) -> dict[str, float]:
    """Extract only inference-time, label-free Phase 2 features."""
    if prediction_record["claim_id"] != retrieval_record["claim_id"]:
        raise ValueError("Prediction/retrieval claim mismatch")
    category = prediction_record["predicted_claim_label"]
    if category not in FINAL_CATEGORIES:
        raise ValueError("Unexpected predicted category")
    values = {
        "F1_decision_confidence": decision_confidence(prediction_record),
        "F2_support_contradict_margin": support_contradict_margin(prediction_record),
        "F3_is_contradict": float(category == "CONTRADICT"),
        "F3_is_no_relation": float(category == "NO_RELATION"),
        "F4_bm25_top2_normalized_margin": bm25_top2_normalized_margin(retrieval_record),
        "F5_evidence_conflict_rate": evidence_conflict_rate(prediction_record),
    }
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("Nonfinite feature value")
    return values


def risk_target(prediction_record: dict[str, Any]) -> int:
    if not prediction_record.get("evaluation_eligible"):
        raise ValueError("Risk target is defined only for eligible claims")
    return int(not bool(prediction_record["correct"]))


def tie_key(claim_id: int, seed: int = 20261015) -> str:
    return hashlib.sha256(f"{seed}:{claim_id}".encode("utf-8")).hexdigest()


def rank_claims(claim_ids: list[int], risks: list[float]) -> list[int]:
    if len(claim_ids) != len(risks) or len(set(claim_ids)) != len(claim_ids):
        raise ValueError("Claims and risks must be unique and aligned")
    if not all(math.isfinite(value) for value in risks):
        raise ValueError("Risk scores must be finite")
    return sorted(
        range(len(claim_ids)), key=lambda index: (risks[index], tie_key(claim_ids[index]))
    )


def risk_coverage(y_error: list[int], order: list[int]) -> list[dict[str, float | int]]:
    if sorted(order) != list(range(len(y_error))):
        raise ValueError("Order must be a permutation")
    cumulative = 0
    curve = []
    for accepted, index in enumerate(order, 1):
        if y_error[index] not in (0, 1):
            raise ValueError("y_error must be binary")
        cumulative += y_error[index]
        curve.append(
            {
                "accepted": accepted,
                "coverage": accepted / len(y_error),
                "selective_risk": cumulative / accepted,
            }
        )
    return curve


def discrete_aurc(curve: list[dict[str, float | int]]) -> float:
    if not curve:
        raise ValueError("AURC is undefined for an empty curve")
    return sum(float(row["selective_risk"]) for row in curve) / len(curve)


def fixed_coverage_count(n: int, coverage: float = 0.8) -> int:
    if n < 1 or not 0.0 < coverage <= 1.0:
        raise ValueError("Invalid coverage request")
    return math.floor(coverage * n + 0.5)
