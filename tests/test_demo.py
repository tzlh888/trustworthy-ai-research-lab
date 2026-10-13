from __future__ import annotations

import pytest

from demo.core import DISCLAIMER, NO_RELATION_EXPLANATION, descriptive_percentile, score_language, validate_claim


def test_claim_validation() -> None:
    assert validate_claim("  Scientific   claim text. ") == "Scientific claim text."
    with pytest.raises(ValueError):
        validate_claim("short")
    with pytest.raises(ValueError):
        validate_claim("x" * 1001)


def test_descriptive_percentile_is_descriptive_only() -> None:
    assert descriptive_percentile(0.3, [0.1, 0.2, 0.4, 0.8]) == 50.0
    assert descriptive_percentile(0.3, []) is None
    language = score_language("EARS", 0.3, 50.0)
    assert "uncalibrated ranking score" in language
    assert "no deployment threshold" in language


def test_safety_language_preserves_semantics() -> None:
    assert "not probabilities" in DISCLAIMER
    assert "not a validated Evidence Insufficient label" in NO_RELATION_EXPLANATION
