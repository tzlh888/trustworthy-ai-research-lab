from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from trustworthy_ai_lab.phase2_protocol import (
    decision_confidence,
    discrete_aurc,
    extract_features,
    fixed_coverage_count,
    rank_claims,
    risk_coverage,
)


ROOT = Path(__file__).resolve().parents[1]


def pair(pair_id, label, contradiction, entailment, neutral):
    return {
        "pair_id": pair_id,
        "predicted_nli_label": label,
        "probabilities": {
            "contradiction": contradiction,
            "entailment": entailment,
            "neutral": neutral,
        },
    }


def retrieval(claim_id=1):
    return {
        "claim_id": claim_id,
        "retrieved_documents": [
            {"bm25_score": 10.0},
            {"bm25_score": 6.0},
        ],
    }


def test_feature_extraction_uses_no_gold_fields_for_support():
    prediction = {
        "claim_id": 1,
        "predicted_claim_label": "SUPPORT",
        "winning_candidate": {"source_pair_id": "a"},
        "sentence_predictions": [
            pair("a", "entailment", 0.05, 0.90, 0.05),
            pair("b", "contradiction", 0.70, 0.10, 0.20),
        ],
    }
    features = extract_features(prediction, retrieval())
    assert features["F1_decision_confidence"] == pytest.approx(0.90)
    assert features["F2_support_contradict_margin"] == pytest.approx(0.20)
    assert features["F3_is_contradict"] == 0.0
    assert features["F3_is_no_relation"] == 0.0
    assert features["F4_bm25_top2_normalized_margin"] == pytest.approx(0.25)
    assert features["F5_evidence_conflict_rate"] == 1.0


def test_no_relation_confidence_is_weakest_neutral_pair():
    prediction = {
        "claim_id": 1,
        "predicted_claim_label": "NO_RELATION",
        "winning_candidate": None,
        "sentence_predictions": [
            pair("a", "neutral", 0.10, 0.10, 0.80),
            pair("b", "neutral", 0.32, 0.31, 0.37),
        ],
    }
    assert decision_confidence(prediction) == pytest.approx(0.37)
    features = extract_features(prediction, retrieval())
    assert features["F3_is_no_relation"] == 1.0
    assert features["F5_evidence_conflict_rate"] == 0.0


def test_metric_definitions_on_synthetic_data_only():
    ids = [10, 20, 30]
    risks = [0.2, 0.1, 0.3]
    errors = [1, 0, 1]
    order = rank_claims(ids, risks)
    curve = risk_coverage(errors, order)
    assert [row["accepted"] for row in curve] == [1, 2, 3]
    assert curve[-1]["selective_risk"] == pytest.approx(2 / 3)
    assert discrete_aurc(curve) == pytest.approx((0 + 0.5 + 2 / 3) / 3)
    assert fixed_coverage_count(329) == 263


def test_frozen_artifacts_have_not_changed():
    config = json.loads((ROOT / "configs/phase2a_frozen_artifacts_v1.json").read_text())
    for relative, expected in config["sha256"].items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected


def test_machine_protocol_forbids_training_and_sealed_access():
    protocol = json.loads((ROOT / "configs/phase2a_protocol_v1.json").read_text())
    assert protocol["phase"] == "2A"
    assert protocol["data"]["allowed_partition"] == "fit"
    assert set(protocol["data"]["sealed"]) == {
        "calibration",
        "internal_test",
        "raw_scifact_dev",
        "official_scifact_test",
    }
    assert any("train any risk model" in rule for rule in protocol["prohibitions"])


def test_baselines_are_fair_and_incremental_comparison_is_isolated():
    config = json.loads((ROOT / "configs/phase2a_baselines_v1.json").read_text())
    models = config["models"]
    assert set(models["EARS"]["features"]) - set(models["B1"]["features"]) == {
        "F4",
        "F5",
    }
    assert models["B1"]["type"] == models["B2"]["type"] == models["EARS"]["type"]
    assert config["logistic_regression"]["hyperparameter_selection"].startswith("none")


def test_feature_schema_contains_no_prohibited_input():
    schema = json.loads((ROOT / "configs/phase2a_feature_schema_v1.json").read_text())
    serialized_features = json.dumps(schema["features"])
    for name in schema["prohibited_inputs"]:
        assert name not in {feature["name"] for feature in schema["features"]}
    assert "gold_evidence_doc_ids" not in serialized_features
    assert "gold rationale" not in serialized_features.casefold()


def test_phase2a_audit_has_no_fold_leakage_or_performance_results():
    audit = json.loads((ROOT / "reports/phase2a/consistency_audit.json").read_text())
    assert audit["frozen_artifact_mismatches"] == {}
    assert audit["sealed_ids_in_predictions"] == []
    assert audit["risk_target"]["eligible_claims"] == 329
    assert audit["risk_target"]["errors"] == 175
    assert audit["bootstrap_groups"]["eligible_claim_group_count"] > 0
    assert audit["bootstrap_groups"]["largest_eligible_claims_in_one_group"] >= 1
    for pair_audit in audit["fold_leakage_pairs"].values():
        assert pair_audit == {
            "shared_cited_doc_count": 0,
            "shared_normalized_claim_count": 0,
        }
    assert len(audit["performance_metrics_intentionally_not_computed"]) == 6
