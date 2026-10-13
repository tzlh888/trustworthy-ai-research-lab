from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "phase3a-v1.0.0"
PRIMARY_METHODS = ("B0", "B1", "B2", "EARS")
EXPECTED_FEATURES = {
    "B0": ["F1"],
    "B1": ["F1", "F2", "F3"],
    "B2": ["F4", "F5"],
    "EARS": ["F1", "F2", "F3", "F4", "F5"],
}
EXPECTED_LOGISTIC = {
    "implementation": "sklearn.linear_model.LogisticRegression",
    "penalty": "l2",
    "C": 0.1,
    "solver": "lbfgs",
    "class_weight": None,
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-6,
    "random_state": 20261014,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_configs(
    protocol: dict[str, Any],
    evaluation: dict[str, Any],
    statistical: dict[str, Any],
) -> None:
    versions = {
        protocol.get("protocol_version"),
        evaluation.get("protocol_version"),
        statistical.get("protocol_version"),
    }
    if versions != {PROTOCOL_VERSION}:
        raise ValueError(f"Phase 3A version mismatch: {sorted(str(v) for v in versions)}")
    if protocol.get("status") != "FROZEN_BEFORE_PHASE3B_ACCESS":
        raise ValueError("Protocol is not frozen before Phase 3B access")
    if protocol.get("primary_method") != "EARS" or protocol.get("primary_comparator") != "B1":
        raise ValueError("Primary EARS-vs-B1 contrast changed")
    if tuple(evaluation.get("methods", [])) != PRIMARY_METHODS:
        raise ValueError("Independent-evaluation methods changed")
    actual_features = {
        method: specification["features"]
        for method, specification in protocol.get("methods", {}).items()
    }
    if actual_features != EXPECTED_FEATURES:
        raise ValueError("Frozen feature sets changed")
    if protocol["final_training"]["logistic_regression"] != EXPECTED_LOGISTIC:
        raise ValueError("Frozen logistic-regression settings changed")
    required_artifacts = protocol["final_training"]["required_artifacts_before_test_access"]
    if len(required_artifacts) != 3 or not any("joblib" in item for item in required_artifacts):
        raise ValueError("Final model/preprocessing serialization is not fully frozen")
    if "1e-12" not in protocol["final_training"]["serialization_consistency_check"]:
        raise ValueError("Serialization consistency tolerance changed")
    if protocol["data"]["final_training_eligible_claims"] != 329:
        raise ValueError("Final training population changed")
    if protocol["data"]["primary_evaluation_total_claims"] != 141:
        raise ValueError("Internal Test population changed")
    if statistical["bootstrap"] != {
        "replicates": 10000,
        "seed": 20261016,
        "paired": True,
        "retrain_models": False,
        "group_construction_population": "all 141 Internal Test claims before eligibility filtering",
        "group_edges": ["shared cited document ID", "identical normalized claim text"],
        "group_id": "minimum claim ID in connected component",
        "sampling_population": "connected groups containing at least one eligible claim",
        "draws_per_replicate": "number of eligible-containing groups, sampled with replacement",
        "include_draw": "all eligible claims in each sampled group; retain repeated group occurrences",
        "coverage_recalculation": "recompute n and floor(0.8*n + 0.5) in every replicate",
        "interval": "percentile 2.5th and 97.5th quantiles using numpy linear interpolation",
        "invalid_auroc_replicate": "record and omit only AUROC when sampled y_error has one class; keep AURC and R80",
        "empty_sampling_population": "stop; primary evaluation is not estimable",
    }:
        raise ValueError("Frozen bootstrap procedure changed")
    if not evaluation["no_relation_sensitivity"]["cannot_replace_primary"]:
        raise ValueError("NO_RELATION sensitivity could replace primary analysis")
    if evaluation["eligibility"]["silent_exclusion"]:
        raise ValueError("Silent exclusion is forbidden")


def validate_config_files(root: Path) -> None:
    validate_configs(
        load_json(root / "configs/phase3a_protocol_v1.json"),
        load_json(root / "configs/phase3a_evaluation_v1.json"),
        load_json(root / "configs/phase3a_statistical_plan_v1.json"),
    )


def validate_manifest_hashes(root: Path, manifest: dict[str, Any]) -> None:
    mismatches = {}
    for relative, expected in manifest["sha256"].items():
        actual = sha256_file(root / relative)
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        raise ValueError(f"Phase 3A frozen artifact mismatch: {mismatches}")
