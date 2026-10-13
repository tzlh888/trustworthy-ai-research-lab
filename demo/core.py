from __future__ import annotations

import math
import collections
from typing import Iterable

from trustworthy_ai_lab.aggregation import aggregate_claim


DISCLAIMER = (
    "Research demonstration only. Outputs are not verified scientific facts, medical advice, "
    "or deployment recommendations. The base verifier achieved 0.488636 accuracy on 88 eligible "
    "held-out claims. B1 and EARS values are uncalibrated ranking scores, not probabilities of error."
)

NO_RELATION_EXPLANATION = (
    "NO_RELATION means that the frozen aggregation rule found no sentence whose top NLI class was "
    "entailment or contradiction. It is not a validated Evidence Insufficient label."
)


def validate_claim(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) < 8:
        raise ValueError("Enter a scientific claim of at least 8 characters.")
    if len(cleaned) > 1000:
        raise ValueError("The demo limits claims to 1,000 characters.")
    return cleaned


def descriptive_percentile(score: float, frozen_scores: Iterable[float]) -> float | None:
    values = sorted(float(value) for value in frozen_scores)
    if not values:
        return None
    if not math.isfinite(score) or not all(math.isfinite(value) for value in values):
        raise ValueError("Risk scores must be finite")
    return 100.0 * sum(value <= score for value in values) / len(values)


def score_language(method: str, score: float, percentile: float | None) -> str:
    context = "Frozen-test percentile unavailable."
    if percentile is not None:
        context = f"This score is at the {percentile:.1f}th percentile of the frozen eligible Internal Test for {method}."
    return (
        f"{method} uncalibrated ranking score: {score:.4f}. {context} "
        "Higher values ranked later in the experiment, but no deployment threshold was selected."
    )


def build_demo_retrieval_records(claims, retriever, selector, *, top_k: int, top_sentences: int):
    """Frozen label-free retrieval path for user-supplied demo claims."""
    records = []
    for claim in claims:
        documents = retriever.retrieve(claim["claim"], top_k=top_k)
        for document in documents:
            document["selected_sentences"] = selector.select(
                claim["claim"], document, top_n=top_sentences
            )
        records.append(
            {
                "claim_id": claim["id"],
                "claim_text": claim["claim"],
                "partition": "user_demo",
                "retrieved_documents": documents,
            }
        )
    return records


def finalize_demo_e1(retrieval_records, pair_predictions):
    """Apply the unchanged Phase 1 claim aggregation without gold labels."""
    by_claim = collections.defaultdict(list)
    for row in pair_predictions:
        by_claim[int(row["claim_id"])].append(row)
    output = []
    for retrieval in retrieval_records:
        claim_id = int(retrieval["claim_id"])
        sentence_predictions = sorted(
            by_claim[claim_id],
            key=lambda row: (
                row["doc_rank"], row["selected_sentence_rank"], row["sentence_index"]
            ),
        )
        if len(sentence_predictions) != 15:
            raise ValueError(f"Expected 15 E1 pairs for claim {claim_id}")
        output.append(
            {
                "claim_id": claim_id,
                "claim_text": retrieval["claim_text"],
                "partition": "user_demo",
                **aggregate_claim(sentence_predictions),
                "sentence_predictions": sentence_predictions,
            }
        )
    return output
