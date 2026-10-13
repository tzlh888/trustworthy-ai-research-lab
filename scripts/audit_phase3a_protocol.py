#!/usr/bin/env python3
"""Freeze Phase 3A without deserializing any sealed claim row."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trustworthy_ai_lab.phase3_protocol import sha256_file, validate_config_files


PHASE2B_REPORTS = (
    "PHASE2B_RESULTS.md",
    "PHASE2B_STATISTICAL_ANALYSIS.md",
    "PHASE2B_ABLATION.md",
    "PHASE2B_ERROR_ANALYSIS.md",
    "PHASE2B_LIMITATIONS.md",
    "PHASE2B_REPRODUCIBILITY.md",
    "PHASE2B_DECISION.md",
)
PHASE3A_ARTIFACTS = (
    "PHASE3_PROTOCOL.md",
    "PHASE3_FINAL_MODEL_TRAINING_PLAN.md",
    "PHASE3_INDEPENDENT_EVALUATION_PLAN.md",
    "PHASE3_STATISTICAL_ANALYSIS_PLAN.md",
    "PHASE3_NO_RELATION_SENSITIVITY_PLAN.md",
    "PHASE3_H2_H3_FUTURE_PLAN.md",
    "PHASE3_LEAKAGE_AND_SEAL_AUDIT.md",
    "PHASE3A_DECISION.md",
    "configs/phase3a_protocol_v1.json",
    "configs/phase3a_evaluation_v1.json",
    "configs/phase3a_statistical_plan_v1.json",
    "src/trustworthy_ai_lab/phase3_protocol.py",
    "scripts/audit_phase3a_protocol.py",
    "tests/test_phase3a.py",
    "reports/phase3a/preflight_audit.json",
    "reports/phase3a/data_access_log.json",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def check_registry(root: Path, relative: str) -> dict[str, Any]:
    registry = read_json(root / relative)
    mismatches = {}
    for artifact, expected in registry["sha256"].items():
        target = root / artifact
        actual = sha256_file(target) if target.is_file() else None
        if actual != expected:
            mismatches[artifact] = {"expected": expected, "actual": actual}
    return {
        "registry": relative,
        "checked": len(registry["sha256"]),
        "mismatches": mismatches,
    }


def check_phase2b_manifest(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    manifest_path = root / "reports/phase2b/experiment_manifest.json"
    manifest = read_json(manifest_path)
    output = {}
    for section in ("formal_outputs_sha256", "input_sha256", "source_sha256"):
        mismatches = {}
        for artifact, expected in manifest[section].items():
            target = (
                root / "reports/phase2b" / artifact
                if section == "formal_outputs_sha256"
                else root / artifact
            )
            actual = sha256_file(target) if target.is_file() else None
            if actual != expected:
                mismatches[artifact] = {"expected": expected, "actual": actual}
        output[section] = {"checked": len(manifest[section]), "mismatches": mismatches}
    output["manifest_sha256"] = sha256_file(manifest_path)
    output["protocol_version"] = manifest["protocol_version"]
    output["h1_status"] = manifest["preregistered_h1_status"]
    output["sealed_partition_performance_access"] = manifest[
        "sealed_partition_performance_access"
    ]
    report_hashes = {report: sha256_file(root / report) for report in PHASE2B_REPORTS}
    return output, report_hashes


def check_phase1_manifest(root: Path) -> dict[str, Any]:
    manifest_path = root / "reports/phase1/run_manifest.json"
    manifest = read_json(manifest_path)
    checks: dict[str, dict[str, Any]] = {}
    mappings = {
        "artifact_sha256": lambda name: root / "reports/phase1" / name,
        "data_hashes": lambda name: (
            root / "splits/train_split_manifest.json"
            if name == "train_split_manifest.json"
            else root / "data/raw/scifact" / name
        ),
        "phase0_frozen_hashes_verified": lambda name: root / name,
    }
    for section, resolver in mappings.items():
        mismatches = {}
        for artifact, expected in manifest[section].items():
            target = resolver(artifact)
            actual = sha256_file(target) if target.is_file() else None
            if actual != expected:
                mismatches[artifact] = {"expected": expected, "actual": actual}
        checks[section] = {"checked": len(manifest[section]), "mismatches": mismatches}
    actual_config = sha256_file(root / "configs/phase1_baseline.json")
    checks["config_sha256"] = {
        "checked": 1,
        "mismatches": {}
        if actual_config == manifest["config_sha256"]
        else {
            "configs/phase1_baseline.json": {
                "expected": manifest["config_sha256"],
                "actual": actual_config,
            }
        },
    }
    checks["manifest_sha256"] = sha256_file(manifest_path)
    checks["scope"] = manifest["scope"]
    checks["sealed_partitions_predicted"] = manifest["sealed_partitions_predicted"]
    return checks


def phase3b_output_candidates(root: Path) -> list[str]:
    pattern = re.compile(
        r"(?:phase3b)|(?:internal[_ -]?test.*(?:prediction|metric|score|result))|"
        r"(?:calibration.*(?:prediction|metric|score|result))",
        re.IGNORECASE,
    )
    candidates = []
    for path in root.rglob("*"):
        if path.is_file() and pattern.search(path.name):
            candidates.append(path.relative_to(root).as_posix())
    return sorted(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    validate_config_files(root)

    phase0 = check_registry(root, "reports/phase0_frozen_hashes.json")
    phase1 = check_phase1_manifest(root)
    phase0_phase1_cross_phase = check_registry(
        root, "configs/phase2a_frozen_artifacts_v1.json"
    )
    phase2a = check_registry(root, "reports/phase2a/protocol_artifact_manifest.json")
    phase2b, phase2b_reports = check_phase2b_manifest(root)
    candidates = phase3b_output_candidates(root)
    mismatches = (
        phase0["mismatches"]
        or any(
            value["mismatches"]
            for key, value in phase1.items()
            if key in {
                "artifact_sha256",
                "data_hashes",
                "phase0_frozen_hashes_verified",
                "config_sha256",
            }
        )
        or phase0_phase1_cross_phase["mismatches"]
        or phase2a["mismatches"]
        or any(
            value["mismatches"]
            for key, value in phase2b.items()
            if key in {"formal_outputs_sha256", "input_sha256", "source_sha256"}
        )
    )
    if mismatches or candidates:
        raise RuntimeError(
            f"Phase 3A preflight failed; mismatches={bool(mismatches)}, "
            f"Phase3B candidates={candidates}"
        )

    output_dir = root / "reports/phase3a"
    audit = {
        "protocol_version": "phase3a-v1.0.0",
        "status": "PASS",
        "scope": "hash and seal audit only; no final training or sealed claim deserialization",
        "phase0": phase0,
        "phase1_manifest_checks": phase1,
        "phase0_phase1_cross_phase_registry": phase0_phase1_cross_phase,
        "phase2a": phase2a,
        "phase2b_manifest_checks": {
            key: value
            for key, value in phase2b.items()
            if key in {"formal_outputs_sha256", "input_sha256", "source_sha256"}
        },
        "phase2b_manifest_sha256": phase2b["manifest_sha256"],
        "phase2b_protocol_version": phase2b["protocol_version"],
        "phase2b_h1_status": phase2b["h1_status"],
        "phase2b_sealed_performance_access": phase2b[
            "sealed_partition_performance_access"
        ],
        "phase2b_narrative_report_hashes_first_frozen_in_phase3a": phase2b_reports,
        "phase3b_output_candidates": candidates,
        "sealed_claim_rows_deserialized": [],
        "performance_metrics_computed": [],
    }
    write_json(output_dir / "preflight_audit.json", audit)

    access_log = {
        "protocol_version": "phase3a-v1.0.0",
        "phase": "3A",
        "events": [
            {
                "resource": "Phase 0/1 and Phase 2A hash registries",
                "partition": "frozen artifacts",
                "access": "read/hash",
                "purpose": "predecessor integrity"
            },
            {
                "resource": "Phase 2B experiment manifest, registered artifacts and narrative reports",
                "partition": "fit-only predecessor outputs",
                "access": "read/hash",
                "purpose": "verify no post-result mutation and establish report hashes"
            },
            {
                "resource": "splits/train_split_manifest.json",
                "partition": "split metadata",
                "access": "cryptographic hash only; no claim rows or label summaries inspected",
                "purpose": "verify the already registered split artifact"
            },
            {
                "resource": "project file names",
                "partition": "workspace metadata",
                "access": "name scan only",
                "purpose": "detect unauthorized Phase 3B outputs"
            }
        ],
        "sealed_partition_status": {
            "internal_test": "metadata only; no claim content",
            "calibration": "metadata only; no claim content",
            "raw_scifact_dev": "not accessed",
            "official_scifact_test": "not accessed"
        },
        "final_models_trained": False,
        "e1_inference_run": False,
        "test_predictions_generated": False,
        "test_metrics_computed": False,
        "probability_calibration": False,
        "threshold_selection": False,
        "h2_h3_experiments": False,
        "phase3b_executed": False
    }
    write_json(output_dir / "data_access_log.json", access_log)

    artifact_hashes = {artifact: sha256_file(root / artifact) for artifact in PHASE3A_ARTIFACTS}
    manifest = {
        "protocol_version": "phase3a-v1.0.0",
        "status": "FROZEN_BEFORE_PHASE3B_ACCESS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": artifact_hashes,
        "predecessor": {
            "phase2b_experiment_manifest_sha256": phase2b["manifest_sha256"],
            "phase2b_narrative_report_sha256": phase2b_reports
        },
        "models_trained": [],
        "test_predictions_generated": [],
        "test_performance_metrics_computed": [],
        "sealed_partition_content_accessed": [],
        "calibration_performed": False,
        "threshold_selected": False,
        "phase3b_executed": False
    }
    write_json(output_dir / "protocol_manifest.json", manifest)
    print(json.dumps({
        "status": "PASS",
        "protocol_version": manifest["protocol_version"],
        "frozen_artifacts": len(artifact_hashes),
        "phase3b_output_candidates": candidates,
        "sealed_partition_content_accessed": []
    }, indent=2))


if __name__ == "__main__":
    main()
