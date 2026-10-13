from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from trustworthy_ai_lab.phase2b import (
    _scale_fold,
    bootstrap_paired,
    evaluate_method,
    method_columns,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/phase2b"


def read_csv(name: str):
    with (REPORT / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_scaler_uses_training_only_and_leaves_indicators_unscaled():
    columns = ["F1_decision_confidence", "F3_is_no_relation"]
    train = np.asarray([[0.0, 0.0], [2.0, 1.0]])
    validation = np.asarray([[100.0, 1.0]])
    train_scaled, validation_scaled, parameters = _scale_fold(train, validation, columns)
    assert parameters["F1_decision_confidence"] == {"mean": 1.0, "scale": 1.0}
    assert train_scaled[:, 0].tolist() == [-1.0, 1.0]
    assert validation_scaled[0, 0] == 99.0
    assert train_scaled[:, 1].tolist() == [0.0, 1.0]
    assert validation_scaled[0, 1] == 1.0


def test_frozen_method_columns_are_exact():
    config = json.loads((ROOT / "reports/phase2b/PHASE2B_CONFIG.json").read_text())
    assert method_columns(config["methods"]["B1"]) == [
        "F1_decision_confidence",
        "F2_support_contradict_margin",
        "F3_is_contradict",
        "F3_is_no_relation",
    ]
    assert method_columns(config["methods"]["EARS"]) == [
        "F1_decision_confidence",
        "F2_support_contradict_margin",
        "F3_is_contradict",
        "F3_is_no_relation",
        "F4_bm25_top2_normalized_margin",
        "F5_evidence_conflict_rate",
    ]


def test_oof_population_is_complete_unique_and_finite():
    rows = read_csv("oof_risk_predictions.csv")
    assert len(rows) == len({int(row["claim_id"]) for row in rows}) == 329
    assert sum(int(row["y_error"]) for row in rows) == 175
    for method in ("B0", "B1", "B2", "EARS", "EARS_minus_F4", "EARS_minus_F5"):
        risks = np.asarray([float(row[f"risk_{method}"]) for row in rows])
        assert np.isfinite(risks).all()
        assert ((0 <= risks) & (risks <= 1)).all()


def test_main_metrics_recompute_exactly_from_oof():
    rows = []
    for row in read_csv("oof_risk_predictions.csv"):
        converted = dict(row)
        converted["claim_id"] = int(row["claim_id"])
        converted["y_error"] = int(row["y_error"])
        for key in row:
            if key.startswith("risk_"):
                converted[key] = float(row[key])
        rows.append(converted)
    persisted = {row["method"]: row for row in read_csv("main_metrics.csv")}
    for method in ("B0", "B1", "B2", "EARS"):
        metric, curve = evaluate_method(rows, method)
        assert len(curve) == 329
        assert metric["aurc"] == pytest.approx(float(persisted[method]["aurc"]), abs=1e-15)
        assert metric["sr80"] == pytest.approx(float(persisted[method]["sr80"]), abs=1e-15)
        assert metric["errors_at_80"] == int(persisted[method]["errors_at_80"])
        assert metric["error_detection_auroc"] == pytest.approx(
            float(persisted[method]["error_detection_auroc"]), abs=1e-15
        )


def test_fold_models_and_preprocessing_metadata_are_complete():
    records = json.loads((REPORT / "fold_model_metadata.json").read_text())
    assert len(records) == 25
    assert {(row["method"], row["held_out_fold"]) for row in records} == {
        (method, f"fold_{fold}")
        for method in ("B1", "B2", "EARS", "EARS_minus_F4", "EARS_minus_F5")
        for fold in range(1, 6)
    }
    assert all(row["converged"] and row["classes"] == [0, 1] for row in records)
    for row in records:
        assert row["training_claims"] + row["validation_claims"] == 329
        assert set(row["scaler"]).issubset(set(row["effective_columns"]))


def test_hash_audit_and_access_boundaries_pass():
    audit = json.loads((REPORT / "frozen_artifact_hash_audit.json").read_text())
    assert audit["status"] == "PASS"
    assert audit["phase0_phase1_registry"]["mismatches"] == {}
    assert audit["phase2a_registry"]["mismatches"] == {}
    access = json.loads((REPORT / "data_access_log.json").read_text())
    assert all("not accessed" in value or "not deserialized" in value for value in access["sealed_partition_status"].values())
    assert access["nli_rerun"] is False
    assert access["temperature_scaling"] is False


def test_bootstrap_is_deterministic_on_persisted_oof_first_20_replicates():
    rows = []
    for row in read_csv("oof_risk_predictions.csv"):
        converted = {
            "claim_id": int(row["claim_id"]),
            "group_id": int(row["group_id"]),
            "y_error": int(row["y_error"]),
        }
        for method in ("B0", "B1", "B2", "EARS"):
            converted[f"risk_{method}"] = float(row[f"risk_{method}"])
        rows.append(converted)
    first = bootstrap_paired(rows, replicates=20, seed=20261016)
    second = bootstrap_paired(rows, replicates=20, seed=20261016)
    assert first == second
    persisted = read_csv("bootstrap_replicates.csv")[:20]
    for expected, actual in zip(first, persisted):
        assert expected["replicate"] == int(actual["replicate"])
        assert expected["delta_aurc_EARS_minus_B1"] == pytest.approx(float(actual["delta_aurc_EARS_minus_B1"]), abs=1e-15)
        assert expected["delta_sr80_EARS_minus_B1"] == pytest.approx(float(actual["delta_sr80_EARS_minus_B1"]), abs=1e-15)


def test_experiment_manifest_declares_no_sealed_evaluation_or_calibration():
    manifest = json.loads((REPORT / "experiment_manifest.json").read_text())
    assert manifest["protocol_version"] == "phase2a-v1.0.0"
    assert manifest["input_summary"]["eligible_claims"] == 329
    assert manifest["models_fit"] == 25
    assert manifest["all_models_converged"] is True
    assert manifest["sealed_partition_performance_access"] == []
    assert manifest["probability_calibration_performed"] is False
    assert manifest["deployment_threshold_selected"] is False
    for section in ("input_sha256", "source_sha256"):
        for relative, expected in manifest[section].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_posthoc_diagnostics_are_consistent_with_main_results():
    diagnostics = json.loads((REPORT / "diagnostics.json").read_text())
    assert diagnostics["status"] == "post-hoc descriptive analysis only"
    assert diagnostics["ears_at_80"] == {
        "accepted": 263,
        "accepted_errors": 115,
        "rejected": 66,
        "rejected_errors": 60,
        "rejected_correct": 6,
        "oracle_minimum_accepted_errors_given_66_rejections": 109,
    }
    labels = {row["predicted_label"]: row for row in diagnostics["by_predicted_label"]}
    assert labels["NO_RELATION"]["claims"] == 66
    assert labels["NO_RELATION"]["errors"] == 66


def test_phase2a_frozen_files_still_match_both_registries():
    for registry_name in (
        "configs/phase2a_frozen_artifacts_v1.json",
        "reports/phase2a/protocol_artifact_manifest.json",
    ):
        registry = json.loads((ROOT / registry_name).read_text())
        for relative, expected in registry["sha256"].items():
            assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
