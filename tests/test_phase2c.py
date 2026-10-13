from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.audit_phase2c import analyze, load_oof


ROOT = Path(__file__).resolve().parents[1]


def test_phase2c_counterfactual_and_frozen_counts():
    summary, rows = analyze(load_oof(ROOT / "reports/phase2b/oof_risk_predictions.csv"))
    assert summary["status"] == "POST-HOC DIAGNOSTIC"
    assert summary["eligible_claims"] == 329
    assert summary["errors"] == 175
    assert summary["no_relation_errors"] == 66
    assert summary["counterfactual_reject_no_relation"] == {
        "accepted": 263,
        "accepted_errors": 109,
        "empirical_sr80": pytest.approx(109 / 263),
        "oracle_minimum_errors": 109,
        "oracle_minimum_sr80": pytest.approx(109 / 263),
    }
    assert len(rows) == 18


def test_phase2c_saved_label_table_matches_recalculation():
    _, expected = analyze(load_oof(ROOT / "reports/phase2b/oof_risk_predictions.csv"))
    with (ROOT / "PREDICTED_LABEL_RISK_ANALYSIS.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        actual = list(csv.DictReader(handle))
    assert len(actual) == len(expected)
    for actual_row, expected_row in zip(actual, expected):
        assert actual_row == {key: str(value) for key, value in expected_row.items()}
