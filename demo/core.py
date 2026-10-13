from __future__ import annotations

import math
from typing import Iterable


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
