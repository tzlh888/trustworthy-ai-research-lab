from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from trustworthy_ai_lab.phase3b import (
    FORMAL_METHODS,
    METHOD_FEATURES,
    bootstrap_paired_dynamic,
    fit_final_models,
    load_claim_texts_only,
    score_bundle,
    score_numeric_spec,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]


def synthetic_fit_rows() -> list[dict[str, float | int]]:
    rows = []
    for index in range(329):
        rows.append({
            "claim_id": index + 1,
            "y_error": int(index < 175),
            "F1_decision_confidence": 0.1 + 0.8 * ((index * 17) % 329) / 328,
            "F2_support_contradict_margin": ((index * 31) % 101) / 100,
            "F3_is_contradict": float(index % 3 == 1),
            "F3_is_no_relation": float(index % 3 == 2),
            "F4_bm25_top2_normalized_margin": ((index * 13) % 97) / 96,
            "F5_evidence_conflict_rate": ((index * 7) % 19) / 18,
        })
    return rows


def test_frozen_method_features_are_exact() -> None:
    assert METHOD_FEATURES == {
        "B0": ["F1"], "B1": ["F1", "F2", "F3"],
        "B2": ["F4", "F5"], "EARS": ["F1", "F2", "F3", "F4", "F5"],
    }


def test_final_model_numeric_spec_agrees_to_tolerance() -> None:
    rows = synthetic_fit_rows()
    bundles, numeric = fit_final_models(rows)
    for method in ("B1", "B2", "EARS"):
        left = score_bundle(bundles[method], rows)
        right = score_numeric_spec(numeric["methods"][method], rows)
        assert max(abs(a - b) for a, b in zip(left, right)) <= 1e-12


def test_final_training_population_gate() -> None:
    with pytest.raises(ValueError, match="exactly 329"):
        fit_final_models(synthetic_fit_rows()[:-1])
    rows = synthetic_fit_rows()
    rows[0]["y_error"] = 0
    with pytest.raises(ValueError, match="target changed"):
        fit_final_models(rows)


def test_claim_text_loader_does_not_require_valid_evidence_json(tmp_path: Path) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text('{"id": 1, "claim": "alpha", "evidence": NOT_PARSED}\n{"id": 2, "claim": "beta", "evidence": {}}\n', encoding="utf-8")
    assert load_claim_texts_only(path, {1}) == [{"id": 1, "claim": "alpha"}]


def test_dynamic_grouped_bootstrap_is_deterministic() -> None:
    rows = []
    for claim_id in range(1, 9):
        row = {"claim_id": claim_id, "group_id": (claim_id + 1) // 2, "y_error": claim_id % 2}
        for offset, method in enumerate(FORMAL_METHODS):
            row[f"risk_{method}"] = ((claim_id * (offset + 2)) % 11) / 11
        rows.append(row)
    left = bootstrap_paired_dynamic(rows, replicates=25, seed=20261016)
    right = bootstrap_paired_dynamic(rows, replicates=25, seed=20261016)
    assert left == right
    assert all(row["k80"] == int(np.floor(0.8 * row["n_claims"] + 0.5)) for row in left)


def test_phase3a_manifest_is_still_intact() -> None:
    manifest = json.loads((ROOT / "reports/phase3a/protocol_manifest.json").read_text())
    assert manifest["protocol_version"] == "phase3a-v1.0.0"
    for relative, expected in manifest["sha256"].items():
        assert sha256_file(ROOT / relative) == expected


@pytest.mark.skipif(not (ROOT / "models/phase3b/final_model_manifest.json").exists(), reason="formal final models not yet trained")
def test_frozen_phase3b_model_manifest() -> None:
    manifest = json.loads((ROOT / "models/phase3b/final_model_manifest.json").read_text())
    assert manifest["status"] == "FINAL_MODELS_FROZEN_BEFORE_TEST_ACCESS"
    assert manifest["serialization_consistency"]["passed"] is True
    assert manifest["serialization_consistency"]["max_absolute_difference"] <= 1e-12
    for relative, expected in manifest["artifact_sha256"].items():
        assert sha256_file(ROOT / relative) == expected


@pytest.mark.skipif(not (ROOT / "reports/phase3b/experiment_manifest.json").exists(), reason="formal independent evaluation not yet run")
def test_phase3b_formal_outputs_are_complete() -> None:
    report = ROOT / "reports/phase3b"
    manifest = json.loads((report / "experiment_manifest.json").read_text())
    assert manifest["models_retrained_after_test_access"] is False
    assert manifest["prohibited_data_used"] == []
    for name, expected in manifest["deterministic_artifact_sha256"].items():
        assert sha256_file(report / name) == expected
    with (report / "test_risk_predictions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows and len({row["claim_id"] for row in rows}) == len(rows)
    for row in rows:
        for method in FORMAL_METHODS:
            assert np.isfinite(float(row[f"risk_{method}"]))


@pytest.mark.skipif(not (ROOT / "reports/phase3b/reproducibility_comparison.json").exists(), reason="second deterministic recalculation not yet run")
def test_phase3b_two_recalculations_match() -> None:
    comparison = json.loads((ROOT / "reports/phase3b/reproducibility_comparison.json").read_text())
    assert comparison["runs_compared"] == 2
    assert comparison["all_byte_identical"] is True
