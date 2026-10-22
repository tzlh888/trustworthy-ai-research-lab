from __future__ import annotations

import math

import pytest

from trustworthy_ai_lab.failure_taxonomy import classify_case, summarize
from trustworthy_ai_lab.feature_analysis import analyze_features
from trustworthy_ai_lab.metrics_validation import auroc, aurc, grouped_paired_bootstrap, risk_at_coverage
from trustworthy_ai_lab.validation_readiness import audit_dataset, canonical_sha256, freeze_configuration


def case(**overrides):
    value = {
        "case_id": "c1", "group_id": "g1", "prediction": "SUPPORT",
        "reference_label": "CONTRADICT", "evidence_references": ["doc:1"],
        "data_provenance": "synthetic deterministic fixture",
        "gold_document_retrieved": False, "complete_reference_evidence_selected": False,
        "nli_on_reference_evidence_correct": False, "final_prediction_correct": False,
    }
    value.update(overrides)
    return value


def test_failure_taxonomy_rules_and_label_masking() -> None:
    blind = classify_case(case(), label_blind=True)
    assert blind.proposed_failure_category == "Retrieval Failure"
    assert blind.available_reference_label is None
    assert blind.reviewer_status == "PENDING"
    nli = classify_case(case(gold_document_retrieved=True, complete_reference_evidence_selected=True), label_blind=False)
    assert nli.proposed_failure_category == "NLI Inference Failure"
    assert nli.available_reference_label == "CONTRADICT"


def test_multiple_and_unresolved_are_not_human_truth() -> None:
    record = classify_case(case(gold_document_retrieved=None, complete_reference_evidence_selected=None), label_blind=True)
    assert record.proposed_failure_category == "Multiple / Unresolved"
    assert summarize([record])["human_confirmed_count"] == 0


def test_metrics_have_hand_checkable_direction_and_fixed_coverage() -> None:
    errors = [0, 1, 0, 1, 0]
    perfect_risks = [0.1, 0.9, 0.2, 0.8, 0.3]
    ids = [f"c{i}" for i in range(5)]
    assert aurc(errors, perfect_risks, ids) == pytest.approx((0 + 0 + 0 + 0.25 + 0.4) / 5)
    assert risk_at_coverage(errors, perfect_risks, ids) == {"accepted": 4, "errors": 1, "risk": 0.25}
    assert auroc(errors, perfect_risks, ids) == 1.0
    assert auroc([0, 0], [0.1, 0.2], ["a", "b"]) is None


def test_ties_are_deterministic_and_invalid_inputs_fail() -> None:
    result = aurc([0, 1], [0.5, 0.5], ["a", "b"])
    assert math.isfinite(result)
    assert result == aurc([0, 1], [0.5, 0.5], ["a", "b"])
    with pytest.raises(ValueError):
        aurc([], [], [])
    with pytest.raises(ValueError):
        aurc([2], [0.1], ["a"])
    with pytest.raises(ValueError):
        aurc([0], [float("nan")], ["a"])


def test_grouped_paired_bootstrap_is_deterministic() -> None:
    rows = [
        {"case_id": "a", "group_id": "g1", "error": 0, "risk_EARS": 0.1, "risk_B1": 0.2},
        {"case_id": "b", "group_id": "g1", "error": 1, "risk_EARS": 0.9, "risk_B1": 0.8},
        {"case_id": "c", "group_id": "g2", "error": 1, "risk_EARS": 0.7, "risk_B1": 0.3},
        {"case_id": "d", "group_id": "g2", "error": 0, "risk_EARS": 0.2, "risk_B1": 0.7},
    ]
    first = grouped_paired_bootstrap(rows, left="risk_EARS", right="risk_B1", replicates=50, seed=4)
    assert first == grouped_paired_bootstrap(rows, left="risk_EARS", right="risk_B1", replicates=50, seed=4)
    assert first["unit"] == "group" and first["paired"] is True


def test_feature_analysis_marks_small_strata_and_f5_zero_ambiguity() -> None:
    rows = [
        {"group_id": "g1", "failure_category": "Retrieval Failure", "F4_bm25_top2_normalized_margin": 0.9,
         "F5_evidence_conflict_rate": 0.0, "non_neutral_evidence_count": 0, "risk_B1": 0.2, "risk_EARS": 0.3},
        {"group_id": "g2", "failure_category": "NLI Inference Failure", "F4_bm25_top2_normalized_margin": 0.1,
         "F5_evidence_conflict_rate": 0.5, "non_neutral_evidence_count": 2, "risk_B1": 0.7, "risk_EARS": 0.6,
         "annotation_disputed": True},
    ]
    result = analyze_features(rows)
    assert result["status"] == "POST_HOC_EXPLORATORY"
    assert result["F5_zero_without_non_neutral_evidence"] == 1
    assert all(row["evidence_status"] == "INSUFFICIENT_STRATUM" for row in result["strata"])


def test_configuration_freeze_and_overlap_audit() -> None:
    config = {"model": "m", "features": ["F1"], "thresholds": {"coverage": 0.8},
              "metrics": ["AURC", "R80"], "protocol_recorded_at": "2026-10-22"}
    frozen = freeze_configuration(config)
    assert frozen["sha256"] == canonical_sha256(config)
    development = [{"claim_id": "d", "group_id": "g1", "document_ids": [1], "license": "CC"}]
    clean = [{"claim_id": "e", "group_id": "g2", "document_ids": [2], "license": "CC"}]
    assert audit_dataset(development, clean, expected_license="CC")["status"] == "READY BUT NOT EXTERNALLY VALIDATED"
    overlap = [{"claim_id": "d", "group_id": "g1", "document_ids": [1], "license": "CC"}]
    assert audit_dataset(development, overlap, expected_license="CC")["status"] == "BLOCKED"
