#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from trustworthy_ai_lab.data import load_json, load_jsonl, write_json
from trustworthy_ai_lab.phase3b import (
    FEATURE_COLUMNS,
    LOGISTIC_PARAMETERS,
    METHOD_FEATURES,
    extract_fit_rows,
    fit_final_models,
    score_bundle,
    score_numeric_spec,
    sha256_file,
)


PACKAGES = ("numpy", "scipy", "scikit-learn", "joblib", "pandas", "torch", "transformers", "rank-bm25")
CODE_FILES = (
    "src/trustworthy_ai_lab/phase3b.py",
    "scripts/run_phase3b_train.py",
    "scripts/run_phase3b_inference.py",
    "scripts/run_phase3b_evaluate.py",
    "scripts/compare_phase3b_runs.py",
    "tests/test_phase3b.py",
    "requirements-phase3b.txt",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_hash_map(root: Path, expected: dict[str, str]) -> list[dict[str, Any]]:
    rows = []
    for relative, wanted in sorted(expected.items()):
        path = root / relative
        actual = sha256_file(path) if path.is_file() else None
        rows.append({"path": relative, "expected_sha256": wanted, "actual_sha256": actual, "match": actual == wanted})
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    reports = root / "reports" / "phase3b"
    models = root / "models" / "phase3b"
    if reports.exists() or models.exists():
        raise RuntimeError("Phase 3B output directory already exists; refusing to overwrite a possibly frozen run")

    p3_manifest_path = root / "reports/phase3a/protocol_manifest.json"
    p3_manifest = load_json(p3_manifest_path)
    protocol = load_json(root / "configs/phase3a_protocol_v1.json")
    predecessor_checks = verify_hash_map(root, p3_manifest["sha256"])
    phase2_manifest = load_json(root / "reports/phase2b/experiment_manifest.json")
    phase2_check = sha256_file(root / "reports/phase2b/experiment_manifest.json") == p3_manifest["predecessor"]["phase2b_experiment_manifest_sha256"]
    phase0 = load_json(root / "reports/phase0_frozen_hashes.json")
    phase0_checks = verify_hash_map(root, phase0["sha256"])
    phase1_manifest = load_json(root / "reports/phase1/run_manifest.json")
    phase1_checks = verify_hash_map(root, {f"reports/phase1/{k}": v for k, v in phase1_manifest["artifact_sha256"].items()})
    split = load_json(root / "splits/train_split_manifest.json")

    prior_audit = load_json(root / "reports/phase3a/preflight_audit.json")
    checks = {
        "phase3a_protocol_version": protocol.get("protocol_version") == "phase3a-v1.0.0",
        "phase3a_status_frozen": p3_manifest.get("status") == "FROZEN_BEFORE_PHASE3B_ACCESS",
        "phase3a_manifest_hashes_match": all(row["match"] for row in predecessor_checks),
        "phase2b_manifest_hash_matches": phase2_check,
        "phase0_hashes_match": all(row["match"] for row in phase0_checks),
        "phase1_artifact_hashes_match": all(row["match"] for row in phase1_checks),
        "fit_count_is_527": split["outer_splits"]["fit"]["claim_count"] == 527,
        "internal_test_count_is_141": split["outer_splits"]["internal_test"]["claim_count"] == 141,
        "primary_method_is_ears": protocol["primary_method"] == "EARS",
        "primary_comparator_is_b1": protocol["primary_comparator"] == "B1",
        "phase3a_recorded_no_sealed_access": p3_manifest["sealed_partition_content_accessed"] == [],
        "phase3a_preflight_passed": prior_audit.get("status") == "PASS",
        "no_preexisting_phase3b_outputs": True,
    }
    if not all(checks.values()):
        raise RuntimeError(f"Phase 3B preflight failed: {[key for key, ok in checks.items() if not ok]}")
    reports.mkdir(parents=True)
    models.mkdir(parents=True)
    write_json(reports / "preflight_audit.json", {
        "phase": "3B pre-test final-model gate", "checked_at_utc": utc_now(), "overall_status": "PASS",
        "internal_test_claim_content_accessed": False, "checks": checks,
        "phase3a_hash_checks": predecessor_checks, "phase0_hash_checks": phase0_checks,
        "phase1_artifact_checks": phase1_checks,
        "note": "Only split counts/IDs in the frozen manifest were inspected; Internal Test claim rows and labels were not deserialized.",
    })

    predictions = load_jsonl(root / "reports/phase1/e1_fit_predictions.jsonl")
    retrieval = load_jsonl(root / "reports/phase1/fit_retrieval_results.jsonl")
    rows = extract_fit_rows(predictions, {int(row["claim_id"]): row for row in retrieval})
    if len(rows) != 329 or sum(int(row["y_error"]) for row in rows) != 175:
        raise RuntimeError("Frozen final-training population is not 329 claims / 175 errors")
    bundles, numeric = fit_final_models(rows)

    model_paths: dict[str, Path] = {}
    for method, bundle in bundles.items():
        path = models / f"final_{method.lower()}_model_bundle.joblib"
        joblib.dump(bundle, path, compress=3)
        model_paths[method] = path
    numeric_path = models / "final_model_numeric_spec.json"
    write_json(numeric_path, numeric)
    write_json(models / "training_config.json", {
        "protocol_version": "phase3a-v1.0.0", "training_partition": "fit-only eligible",
        "training_claims": 329, "training_errors": 175, "training_correct": 154,
        "method_features": METHOD_FEATURES, "logistic_parameters": LOGISTIC_PARAMETERS,
        "hyperparameter_search": False,
    })
    write_json(models / "feature_schema.json", {
        "feature_ids": FEATURE_COLUMNS, "methods": METHOD_FEATURES,
        "continuous_standardization": ["F1_decision_confidence", "F2_support_contradict_margin", "F4_bm25_top2_normalized_margin", "F5_evidence_conflict_rate"],
        "categorical": ["F3_is_contradict", "F3_is_no_relation"],
        "gold_or_label_derived_inputs": [],
    })

    consistency = []
    max_error = 0.0
    for method in ("B1", "B2", "EARS"):
        loaded = joblib.load(model_paths[method])
        joblib_scores = score_bundle(loaded, rows)
        json_scores = score_numeric_spec(numeric["methods"][method], rows)
        for row, left, right in zip(rows, joblib_scores, json_scores):
            delta = abs(left - right)
            max_error = max(max_error, delta)
            consistency.append({"claim_id": row["claim_id"], "method": method, "joblib_risk": repr(left), "json_risk": repr(right), "absolute_difference": repr(delta)})
    write_csv(models / "fit_serialization_check.csv", consistency)
    if max_error > 1e-12:
        raise RuntimeError(f"Serialization consistency failed: {max_error}")

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False).stdout.strip() or None
        status = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, capture_output=True, check=False).stdout.splitlines()
    except OSError:
        commit, status = None, []
    versions = {name: importlib.metadata.version(name) for name in PACKAGES}
    training_log = {
        "completed_at_utc": utc_now(), "status": "PASS_AND_FROZEN", "internal_test_content_accessed": False,
        "training_claims": 329, "errors": 175, "correct": 154,
        "serialization_max_absolute_difference": max_error, "serialization_tolerance": 1e-12,
        "model_iterations": {method: numeric["methods"][method]["iterations"] for method in bundles},
        "software_versions": {"python": sys.version.split()[0], "platform": platform.platform(), **versions},
        "git_commit": commit, "git_status_entries": len(status), "repository_has_commits": commit is not None,
    }
    write_json(models / "training_log.json", training_log)

    artifact_files = sorted(path for path in models.iterdir() if path.is_file())
    code_hashes = {relative: sha256_file(root / relative) for relative in CODE_FILES}
    artifacts = {str(path.relative_to(root)): sha256_file(path) for path in artifact_files}
    manifest = {
        "protocol_version": "phase3a-v1.0.0", "created_at_utc": utc_now(), "status": "FINAL_MODELS_FROZEN_BEFORE_TEST_ACCESS",
        "internal_test_content_accessed_before_freeze": False,
        "training_population": {"partition": "fit", "eligible_claims": 329, "errors": 175, "correct": 154},
        "source_fit_artifacts": {
            "reports/phase1/e1_fit_predictions.jsonl": sha256_file(root / "reports/phase1/e1_fit_predictions.jsonl"),
            "reports/phase1/fit_retrieval_results.jsonl": sha256_file(root / "reports/phase1/fit_retrieval_results.jsonl"),
            "splits/train_split_manifest.json": sha256_file(root / "splits/train_split_manifest.json"),
        },
        "phase3a_protocol_manifest_sha256": sha256_file(p3_manifest_path),
        "code_sha256": code_hashes, "artifact_sha256": artifacts,
        "serialization_consistency": {"rows_checked": len(consistency), "max_absolute_difference": max_error, "tolerance": 1e-12, "passed": True},
        "software_versions": training_log["software_versions"], "git_commit": commit, "git_status_entries_at_freeze": len(status),
    }
    write_json(models / "final_model_manifest.json", manifest)
    # Byte-identical report copy, written only after the canonical manifest is complete.
    (reports / "final_model_manifest.json").write_bytes((models / "final_model_manifest.json").read_bytes())
    print(json.dumps({"status": "PASS_AND_FROZEN", "training_claims": 329, "max_abs_difference": max_error, "manifest_sha256": sha256_file(models / "final_model_manifest.json")}, indent=2))


if __name__ == "__main__":
    main()
