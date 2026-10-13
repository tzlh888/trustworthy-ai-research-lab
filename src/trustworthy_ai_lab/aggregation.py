from __future__ import annotations

from typing import Any


NLI_TO_CLAIM = {"entailment": "SUPPORT", "contradiction": "CONTRADICT"}


def aggregate_claim(sentence_predictions: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for row in sentence_predictions:
        nli_label = row["predicted_nli_label"]
        if nli_label == "neutral":
            continue
        claim_label = NLI_TO_CLAIM[nli_label]
        seen_labels.add(claim_label)
        class_probability = row["probabilities"][nli_label]
        candidates.append(
            {
                "claim_label": claim_label,
                "class_probability": class_probability,
                "doc_rank": row["doc_rank"],
                "selected_sentence_rank": row["selected_sentence_rank"],
                "sentence_index": row["sentence_index"],
                "doc_id": row["doc_id"],
                "source_pair_id": row["pair_id"],
            }
        )
    candidates.sort(
        key=lambda row: (
            -row["class_probability"],
            row["doc_rank"],
            row["selected_sentence_rank"],
            row["sentence_index"],
            row["doc_id"],
        )
    )
    if not candidates:
        return {
            "predicted_claim_label": "NO_RELATION",
            "prediction_confidence": None,
            "winning_candidate": None,
            "non_neutral_candidate_count": 0,
            "support_contradict_conflict": False,
        }
    winner = candidates[0]
    return {
        "predicted_claim_label": winner["claim_label"],
        "prediction_confidence": winner["class_probability"],
        "winning_candidate": winner,
        "non_neutral_candidate_count": len(candidates),
        "support_contradict_conflict": len(seen_labels) > 1,
    }
