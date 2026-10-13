from __future__ import annotations

import json
from pathlib import Path

from trustworthy_ai_lab.phase3_protocol import (
    EXPECTED_FEATURES,
    EXPECTED_LOGISTIC,
    validate_config_files,
    validate_manifest_hashes,
)


ROOT = Path(__file__).resolve().parents[1]


def test_phase3a_configs_are_cross_consistent():
    validate_config_files(ROOT)


def test_full_ears_is_only_primary_method_and_b1_is_comparator():
    protocol = json.loads((ROOT / "configs/phase3a_protocol_v1.json").read_text())
    assert protocol["primary_method"] == "EARS"
    assert protocol["primary_comparator"] == "B1"
    assert protocol["methods"]["EARS"]["features"] == EXPECTED_FEATURES["EARS"]
    assert "EARS_minus_F4" not in protocol["methods"]


def test_final_training_is_fit_only_and_untuned():
    protocol = json.loads((ROOT / "configs/phase3a_protocol_v1.json").read_text())
    assert protocol["data"]["final_training_partition"] == "fit"
    assert protocol["data"]["final_training_eligible_claims"] == 329
    assert protocol["final_training"]["logistic_regression"] == EXPECTED_LOGISTIC
    assert protocol["final_training"]["hyperparameter_search"] is False
    assert protocol["data"]["calibration_use"] == "PROHIBITED_IN_PHASE3A_AND_PHASE3B_H1"
    artifacts = protocol["final_training"]["required_artifacts_before_test_access"]
    assert any("models and preprocessing objects" in item for item in artifacts)
    assert "1e-12" in protocol["final_training"]["serialization_consistency_check"]


def test_internal_test_count_is_known_but_eligibility_is_sealed():
    evaluation = json.loads((ROOT / "configs/phase3a_evaluation_v1.json").read_text())
    assert evaluation["total_claims"] == 141
    assert evaluation["eligible_count"] == "UNKNOWN_UNTIL_PHASE3B"
    assert evaluation["eligibility"]["silent_exclusion"] is False
    assert evaluation["completeness"]["required_e1_rows"] == 141


def test_primary_statistics_and_success_rule_are_frozen():
    plan = json.loads((ROOT / "configs/phase3a_statistical_plan_v1.json").read_text())
    assert plan["bootstrap"]["replicates"] == 10000
    assert plan["bootstrap"]["seed"] == 20261016
    assert plan["bootstrap"]["paired"] is True
    assert plan["bootstrap"]["retrain_models"] is False
    assert plan["metrics"]["coverage_80_count"] == "floor(0.8*n + 0.5)"
    assert "both paired 95% CI upper bounds are strictly below zero" in plan["primary_contrast"]["supported"]


def test_no_relation_is_secondary_and_not_abstention_ground_truth():
    evaluation = json.loads((ROOT / "configs/phase3a_evaluation_v1.json").read_text())
    sensitivity = evaluation["no_relation_sensitivity"]
    assert sensitivity["status"] == "preregistered_secondary"
    assert sensitivity["cannot_replace_primary"] is True
    assert "AUROC is undefined" in sensitivity["no_relation"]
    assert "never relabel" in evaluation["eligibility"]["excluded_handling"]


def test_phase3a_manifest_hashes_match_and_no_models_or_metrics_exist():
    manifest = json.loads((ROOT / "reports/phase3a/protocol_manifest.json").read_text())
    validate_manifest_hashes(ROOT, manifest)
    assert manifest["models_trained"] == []
    assert manifest["test_predictions_generated"] == []
    assert manifest["test_performance_metrics_computed"] == []
    assert manifest["sealed_partition_content_accessed"] == []


def test_predecessor_audit_passes_without_phase3b_outputs():
    audit = json.loads((ROOT / "reports/phase3a/preflight_audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["phase0"]["mismatches"] == {}
    assert audit["phase0_phase1_cross_phase_registry"]["mismatches"] == {}
    for key in ("artifact_sha256", "data_hashes", "phase0_frozen_hashes_verified", "config_sha256"):
        assert audit["phase1_manifest_checks"][key]["mismatches"] == {}
    assert audit["phase1_manifest_checks"]["sealed_partitions_predicted"] == []
    assert audit["phase2a"]["mismatches"] == {}
    for section in audit["phase2b_manifest_checks"].values():
        assert section["mismatches"] == {}
    assert audit["phase3b_output_candidates"] == []


def test_data_access_log_confirms_seals_remained_closed():
    access = json.loads((ROOT / "reports/phase3a/data_access_log.json").read_text())
    assert access["final_models_trained"] is False
    assert access["phase3b_executed"] is False
    assert all(
        value in {"metadata only; no claim content", "not accessed"}
        for value in access["sealed_partition_status"].values()
    )
