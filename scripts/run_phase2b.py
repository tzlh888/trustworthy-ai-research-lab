#!/usr/bin/env python3
"""Run the frozen, fit-only Phase 2B cross-fitted risk experiment.

This program deliberately has no code path for calibration, internal-test, Dev,
or official Test performance. It consumes only the frozen fit artifacts named in
the Phase 2A protocol.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from trustworthy_ai_lab.data import load_selected_claims
from trustworthy_ai_lab.phase2_protocol import extract_features, risk_target, tie_key
from trustworthy_ai_lab.phase2b import (
    LEARNED_METHODS,
    PRIMARY_METHODS,
    bootstrap_paired,
    connected_group_lookup,
    cross_fit,
    evaluate_method,
    method_columns,
    percentile_interval,
    ranking_order,
    sha256_file,
)


ALL_METHODS = ("B0",) + LEARNED_METHODS
ABLATION_METHODS = ("EARS", "EARS_minus_F4", "EARS_minus_F5", "B1", "B2")
CORE_REPRODUCIBILITY_FILES = (
    "oof_risk_predictions.csv",
    "risk_coverage_curves.csv",
    "main_metrics.csv",
    "paired_comparisons.csv",
    "bootstrap_confidence_intervals.csv",
    "bootstrap_replicates.csv",
    "ablation_results.csv",
    "class_conditional_results.csv",
    "coefficient_stability.csv",
    "fold_model_metadata.json",
    "error_analysis_cases.csv",
    "diagnostics.json",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames=None) -> None:
    materialized = list(rows)
    if fieldnames is None:
        if not materialized:
            raise ValueError(f"Cannot infer columns for empty CSV: {path.name}")
        fieldnames = list(materialized[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(materialized)


def audit_registry(root: Path, registry_path: Path) -> dict[str, Any]:
    registry = read_json(registry_path)
    mismatches = {}
    for relative, expected in registry["sha256"].items():
        target = root / relative
        actual = sha256_file(target) if target.is_file() else None
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    return {
        "registry": registry_path.relative_to(root).as_posix(),
        "protocol_version": registry.get("protocol_version"),
        "checked_file_count": len(registry["sha256"]),
        "mismatches": mismatches,
    }


def preflight(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    frozen_audit = audit_registry(root, root / "configs/phase2a_frozen_artifacts_v1.json")
    protocol_audit = audit_registry(
        root, root / "reports/phase2a/protocol_artifact_manifest.json"
    )
    if frozen_audit["mismatches"] or protocol_audit["mismatches"]:
        raise RuntimeError("Frozen artifact hash mismatch; Phase 2B training is blocked")

    protocol = read_json(root / "configs/phase2a_protocol_v1.json")
    baselines = read_json(root / "configs/phase2a_baselines_v1.json")
    config = read_json(root / "reports/phase2b/PHASE2B_CONFIG.json")
    versions = {
        protocol["protocol_version"],
        baselines["protocol_version"],
        config["protocol_version"],
        protocol_audit["protocol_version"],
        frozen_audit["protocol_version"],
    }
    if versions != {"phase2a-v1.0.0"}:
        raise RuntimeError(f"Protocol version mismatch: {sorted(versions)}")
    return (
        {
            "status": "PASS",
            "protocol_version": "phase2a-v1.0.0",
            "phase0_phase1_registry": frozen_audit,
            "phase2a_registry": protocol_audit,
        },
        baselines,
        config,
    )


def build_rows(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = read_json(root / "splits/train_split_manifest.json")
    fit_ids = set(manifest["outer_splits"]["fit"]["claim_ids"])
    calibration_ids = set(manifest["outer_splits"]["calibration"]["claim_ids"])
    test_ids = set(manifest["outer_splits"]["internal_test"]["claim_ids"])
    sealed_ids = calibration_ids | test_ids
    if len(fit_ids) != 527 or len(calibration_ids) != 141 or len(test_ids) != 141:
        raise RuntimeError("Frozen outer split counts changed")
    if fit_ids & sealed_ids:
        raise RuntimeError("Fit and sealed outer partitions overlap")

    fold_by_id: dict[int, str] = {}
    for fold, values in manifest["crossfit_validation_folds_within_fit"].items():
        for claim_id in values["claim_ids"]:
            if claim_id in fold_by_id:
                raise RuntimeError(f"Claim in multiple folds: {claim_id}")
            fold_by_id[int(claim_id)] = fold
    if set(fold_by_id) != fit_ids or len(set(fold_by_id.values())) != 5:
        raise RuntimeError("Frozen folds do not exactly partition fit")

    claims = load_selected_claims(
        root / "data/raw/scifact/claims_train.jsonl", fit_ids
    )
    group_by_id = connected_group_lookup(claims)
    if len(set(group_by_id.values())) != 380:
        raise RuntimeError("Full-fit connected group count changed")
    claim_by_id = {int(row["id"]): row for row in claims}

    predictions = read_jsonl(root / "reports/phase1/e1_fit_predictions.jsonl")
    retrieval_rows = read_jsonl(root / "reports/phase1/fit_retrieval_results.jsonl")
    retrieval = {int(row["claim_id"]): row for row in retrieval_rows}
    if {int(row["claim_id"]) for row in predictions} != fit_ids:
        raise RuntimeError("Frozen predictions are not exactly the fit partition")
    if set(retrieval) != fit_ids:
        raise RuntimeError("Frozen retrieval output is not exactly the fit partition")
    if fit_ids & sealed_ids != set():
        raise RuntimeError("Sealed ID in fit inputs")

    rows = []
    for prediction in predictions:
        if not prediction["evaluation_eligible"]:
            continue
        claim_id = int(prediction["claim_id"])
        if prediction["fit_fold"] != fold_by_id[claim_id]:
            raise RuntimeError(f"Fold mismatch for claim {claim_id}")
        y_error = risk_target(prediction)
        expected_error = int(
            prediction["predicted_claim_label"] != prediction["gold_evidence_label"]
        )
        if y_error != expected_error or bool(prediction["correct"]) == bool(y_error):
            raise RuntimeError(f"Target inconsistency for claim {claim_id}")
        features = extract_features(prediction, retrieval[claim_id])
        if any(not math.isfinite(float(value)) for value in features.values()):
            raise RuntimeError(f"Nonfinite features for claim {claim_id}")
        rows.append(
            {
                "claim_id": claim_id,
                "fold": fold_by_id[claim_id],
                "group_id": group_by_id[claim_id],
                "y_error": y_error,
                "gold_label": prediction["gold_evidence_label"],
                "predicted_label": prediction["predicted_claim_label"],
                "claim_text": claim_by_id[claim_id]["claim"],
                "failure_categories": "|".join(prediction["failure_categories"]),
                **features,
            }
        )
    rows.sort(key=lambda row: int(row["claim_id"]))
    if len(rows) != 329 or len({row["claim_id"] for row in rows}) != 329:
        raise RuntimeError("Eligible population is not 329 unique fit claims")
    if sum(row["y_error"] for row in rows) != 175:
        raise RuntimeError("Expected 175 risk targets equal to one")
    if sum(1 - row["y_error"] for row in rows) != 154:
        raise RuntimeError("Expected 154 correct predictions")
    eligible_groups = Counter(row["group_id"] for row in rows)
    if len(eligible_groups) != 243 or max(eligible_groups.values()) != 3:
        raise RuntimeError("Eligible bootstrap group structure changed")

    for left_index, left in enumerate(sorted(set(fold_by_id.values()))):
        left_groups = {
            group_by_id[claim_id]
            for claim_id, fold in fold_by_id.items()
            if fold == left
        }
        for right in sorted(set(fold_by_id.values()))[left_index + 1 :]:
            right_groups = {
                group_by_id[claim_id]
                for claim_id, fold in fold_by_id.items()
                if fold == right
            }
            if left_groups & right_groups:
                raise RuntimeError(f"Connected-group leakage: {left}/{right}")

    summary = {
        "fit_claims": len(fit_ids),
        "eligible_claims": len(rows),
        "correct": sum(1 - row["y_error"] for row in rows),
        "errors": sum(row["y_error"] for row in rows),
        "full_fit_groups": len(set(group_by_id.values())),
        "eligible_groups": len(eligible_groups),
        "maximum_eligible_group_size": max(eligible_groups.values()),
        "folds": {
            fold: {
                "eligible": sum(row["fold"] == fold for row in rows),
                "errors": sum(row["y_error"] for row in rows if row["fold"] == fold),
            }
            for fold in sorted(set(fold_by_id.values()))
        },
    }
    return rows, summary


def class_conditional(rows: list[dict[str, Any]], methods: Iterable[str]) -> list[dict[str, Any]]:
    output = []
    strata = (
        [("gold_label", value) for value in ("SUPPORT", "CONTRADICT")]
        + [
            ("predicted_label", value)
            for value in ("SUPPORT", "CONTRADICT", "NO_RELATION")
        ]
    )
    for method in methods:
        risk_column = f"risk_{method}"
        order = ranking_order(rows, risk_column)
        accepted = set(order[:263])
        for stratum_type, stratum in strata:
            indices = [
                index for index, row in enumerate(rows) if row[stratum_type] == stratum
            ]
            accepted_indices = [index for index in indices if index in accepted]
            accepted_errors = sum(rows[index]["y_error"] for index in accepted_indices)
            risks = [float(rows[index][risk_column]) for index in indices]
            output.append(
                {
                    "method": method,
                    "stratum_type": stratum_type,
                    "stratum": stratum,
                    "total": len(indices),
                    "total_errors": sum(rows[index]["y_error"] for index in indices),
                    "error_rate": sum(rows[index]["y_error"] for index in indices)
                    / len(indices),
                    "accepted": len(accepted_indices),
                    "coverage_within_stratum": len(accepted_indices) / len(indices),
                    "accepted_errors": accepted_errors,
                    "selective_risk": accepted_errors / len(accepted_indices)
                    if accepted_indices
                    else "",
                    "mean_predicted_risk": float(np.mean(risks)),
                    "median_predicted_risk": float(np.median(risks)),
                }
            )
    return output


def coefficient_table(model_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_method_feature: dict[tuple[str, str], dict[str, float]] = defaultdict(dict)
    for record in model_records:
        method = record["method"]
        fold = record["held_out_fold"]
        for feature, coefficient in record["coefficients"].items():
            by_method_feature[(method, feature)][fold] = float(coefficient)
        by_method_feature[(method, "(intercept)")][fold] = float(record["intercept"])
    output = []
    for (method, feature), fold_values in sorted(by_method_feature.items()):
        values = [fold_values[f"fold_{index}"] for index in range(1, 6)]
        signs = ["positive" if value > 0 else "negative" if value < 0 else "zero" for value in values]
        output.append(
            {
                "method": method,
                "feature": feature,
                **{f"coefficient_fold_{index}": values[index - 1] for index in range(1, 6)},
                "mean": float(np.mean(values)),
                "population_std": float(np.std(values, ddof=0)),
                "minimum": min(values),
                "maximum": max(values),
                "positive_folds": signs.count("positive"),
                "negative_folds": signs.count("negative"),
                "zero_folds": signs.count("zero"),
                "sign_stable": len(set(signs)) == 1,
                "causal_interpretation": False,
            }
        )
    return output


def bootstrap_intervals(
    replicates: list[dict[str, Any]], point_metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    mapping = {
        "aurc": "aurc",
        "sr80": "sr80",
        "auroc": "error_detection_auroc",
    }
    for method in PRIMARY_METHODS:
        for bootstrap_name, point_name in mapping.items():
            values = [
                row[f"{bootstrap_name}_{method}"]
                for row in replicates
                if row[f"{bootstrap_name}_{method}"] is not None
            ]
            lower, upper = percentile_interval(values)
            output.append(
                {
                    "estimand": f"{bootstrap_name}_{method}",
                    "kind": "method",
                    "method_or_contrast": method,
                    "metric": bootstrap_name,
                    "point_estimate": point_metrics[method][point_name],
                    "ci_lower_95": lower,
                    "ci_upper_95": upper,
                    "valid_replicates": len(values),
                    "invalid_replicates": len(replicates) - len(values),
                    "replicates": len(replicates),
                    "interval_method": "paired grouped percentile; numpy linear quantiles",
                }
            )
    primary_deltas = (
        (
            "delta_aurc_EARS_minus_B1",
            point_metrics["EARS"]["aurc"] - point_metrics["B1"]["aurc"],
            "aurc",
        ),
        (
            "delta_sr80_EARS_minus_B1",
            point_metrics["EARS"]["sr80"] - point_metrics["B1"]["sr80"],
            "sr80",
        ),
    )
    for estimand, point, metric in primary_deltas:
        values = [float(row[estimand]) for row in replicates]
        lower, upper = percentile_interval(values)
        output.append(
            {
                "estimand": estimand,
                "kind": "paired_contrast",
                "method_or_contrast": "EARS_minus_B1",
                "metric": metric,
                "point_estimate": point,
                "ci_lower_95": lower,
                "ci_upper_95": upper,
                "valid_replicates": len(values),
                "invalid_replicates": 0,
                "replicates": len(replicates),
                "interval_method": "paired grouped percentile; numpy linear quantiles",
            }
        )
    return output


def error_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank_maps = {}
    for method in PRIMARY_METHODS:
        order = ranking_order(rows, f"risk_{method}")
        rank_maps[method] = {index: rank for rank, index in enumerate(order, 1)}

    def materialize(category: str, indices: list[int]) -> list[dict[str, Any]]:
        result = []
        for index in indices:
            row = rows[index]
            result.append(
                {
                    "analysis_category": category,
                    "claim_id": row["claim_id"],
                    "claim_text": row["claim_text"],
                    "fold": row["fold"],
                    "gold_label": row["gold_label"],
                    "predicted_label": row["predicted_label"],
                    "y_error": row["y_error"],
                    "failure_categories": row["failure_categories"],
                    "F1_decision_confidence": row["F1_decision_confidence"],
                    "F2_support_contradict_margin": row["F2_support_contradict_margin"],
                    "F4_bm25_top2_normalized_margin": row["F4_bm25_top2_normalized_margin"],
                    "F5_evidence_conflict_rate": row["F5_evidence_conflict_rate"],
                    **{f"risk_{method}": row[f"risk_{method}"] for method in PRIMARY_METHODS},
                    **{f"risk_rank_{method}": rank_maps[method][index] for method in PRIMARY_METHODS},
                    "EARS_minus_B1_rank_shift": rank_maps["EARS"][index]
                    - rank_maps["B1"][index],
                }
            )
        return result

    errors = [i for i, row in enumerate(rows) if row["y_error"] == 1]
    correct = [i for i, row in enumerate(rows) if row["y_error"] == 0]
    high_confidence_wrong = sorted(
        errors, key=lambda i: (-rows[i]["F1_decision_confidence"], rows[i]["claim_id"])
    )[:10]
    false_reassurance = sorted(
        errors, key=lambda i: (rows[i]["risk_EARS"], tie_key(rows[i]["claim_id"]))
    )[:10]
    unnecessary = sorted(
        correct, key=lambda i: (-rows[i]["risk_EARS"], tie_key(rows[i]["claim_id"]))
    )[:10]
    rescue = sorted(
        errors,
        key=lambda i: (-(
            rank_maps["EARS"][i] - rank_maps["B1"][i]
        ), rows[i]["claim_id"]),
    )[:5]
    harm = sorted(
        errors,
        key=lambda i: (
            rank_maps["EARS"][i] - rank_maps["B1"][i], rows[i]["claim_id"]
        ),
    )[:5]
    return (
        materialize("high_confidence_wrong", high_confidence_wrong)
        + materialize("EARS_false_reassurance", false_reassurance)
        + materialize("EARS_high_risk_but_correct", unnecessary)
        + materialize("largest_EARS_rescue_vs_B1", rescue)
        + materialize("largest_EARS_harm_vs_B1", harm)
    )


def diagnostic_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Post-hoc slices for interpretation only; never fed back into a model."""
    order = ranking_order(rows, "risk_EARS")
    accepted = set(order[:263])
    by_predicted_label = []
    for label in ("SUPPORT", "CONTRADICT", "NO_RELATION"):
        indices = [index for index, row in enumerate(rows) if row["predicted_label"] == label]
        errors = [index for index in indices if rows[index]["y_error"] == 1]
        accepted_errors = [index for index in errors if index in accepted]
        risks = [float(rows[index]["risk_EARS"]) for index in indices]
        by_predicted_label.append(
            {
                "predicted_label": label,
                "claims": len(indices),
                "errors": len(errors),
                "error_rate": len(errors) / len(indices),
                "ears_median_risk": float(np.median(risks)),
                "ears_errors_accepted_at_80": len(accepted_errors),
                "ears_errors_rejected_at_80": len(errors) - len(accepted_errors),
            }
        )

    by_stage = []
    stages = ("retrieval_failure", "sentence_selection_failure", "nli_or_reasoning_failure")
    for stage in stages:
        indices = [
            index
            for index, row in enumerate(rows)
            if row["y_error"] == 1 and stage in row["failure_categories"].split("|")
        ]
        accepted_indices = [index for index in indices if index in accepted]
        risks = [float(rows[index]["risk_EARS"]) for index in indices]
        by_stage.append(
            {
                "primary_failure_stage": stage,
                "errors": len(indices),
                "accepted_at_80": len(accepted_indices),
                "rejected_at_80": len(indices) - len(accepted_indices),
                "ears_mean_risk": float(np.mean(risks)),
                "ears_median_risk": float(np.median(risks)),
            }
        )
    rejected = set(range(len(rows))) - accepted
    rejected_errors = sum(rows[index]["y_error"] for index in rejected)
    return {
        "status": "post-hoc descriptive analysis only",
        "ears_at_80": {
            "accepted": len(accepted),
            "accepted_errors": sum(rows[index]["y_error"] for index in accepted),
            "rejected": len(rejected),
            "rejected_errors": rejected_errors,
            "rejected_correct": len(rejected) - rejected_errors,
            "oracle_minimum_accepted_errors_given_66_rejections": max(0, 175 - 66),
        },
        "by_predicted_label": by_predicted_label,
        "by_primary_failure_stage": by_stage,
    }


def make_figures(
    output_dir: Path,
    curves: list[dict[str, Any]],
    metrics: dict[str, dict[str, Any]],
    replicates: list[dict[str, Any]],
    coefficients: list[dict[str, Any]],
    ablations: list[dict[str, Any]],
) -> None:
    figure_dir = output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    colors = {"B0": "#64748b", "B1": "#2563eb", "B2": "#f59e0b", "EARS": "#059669"}

    fig, ax = plt.subplots(figsize=(8, 5.2))
    for method in PRIMARY_METHODS:
        selected = [row for row in curves if row["method"] == method]
        ax.plot(
            [row["coverage"] for row in selected],
            [row["selective_risk"] for row in selected],
            label=f"{method} (AURC={metrics[method]['aurc']:.3f})",
            color=colors[method],
            linewidth=2,
        )
    ax.axvline(0.8, color="black", linestyle="--", linewidth=1, alpha=0.65)
    ax.set(xlabel="Coverage", ylabel="Selective risk", title="Fit-only OOF risk–coverage curves")
    ax.set_xlim(0, 1)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "risk_coverage_curve.png", dpi=180)
    plt.close(fig)

    methods = list(PRIMARY_METHODS)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    values = [metrics[method]["aurc"] for method in methods]
    bars = ax.bar(methods, values, color=[colors[m] for m in methods])
    ax.bar_label(bars, labels=[f"{value:.4f}" for value in values], padding=3)
    ax.set(ylabel="AURC (lower is better)", title="AURC comparison")
    ax.set_ylim(0, max(values) * 1.18)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(figure_dir / "aurc_comparison.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    values = [metrics[method]["sr80"] for method in methods]
    labels = [f"{metrics[m]['errors_at_80']}/263\n({metrics[m]['sr80']:.3f})" for m in methods]
    bars = ax.bar(methods, values, color=[colors[m] for m in methods])
    ax.bar_label(bars, labels=labels, padding=3)
    ax.set(ylabel="Selective risk at 80% coverage", title="R80 comparison")
    ax.set_ylim(0, max(values) * 1.22)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(figure_dir / "r80_comparison.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    for ax, name, title in (
        (axes[0], "delta_aurc_EARS_minus_B1", "ΔAURC: EARS − B1"),
        (axes[1], "delta_sr80_EARS_minus_B1", "ΔR80: EARS − B1"),
    ):
        values = [row[name] for row in replicates]
        ax.hist(values, bins=45, color="#0f766e", alpha=0.85)
        ax.axvline(0, color="black", linestyle="--", linewidth=1)
        ax.axvline(np.mean(values), color="#dc2626", linewidth=1.5)
        ax.set(title=title, xlabel="Paired difference", ylabel="Replicates")
        ax.grid(axis="y", alpha=0.15)
    fig.suptitle("10,000 paired grouped bootstrap replicates")
    fig.tight_layout()
    fig.savefig(figure_dir / "bootstrap_delta_distribution.png", dpi=180)
    plt.close(fig)

    ears_coefficients = [
        row for row in coefficients if row["method"] == "EARS" and row["feature"] != "(intercept)"
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(1, 6)
    for row in ears_coefficients:
        values = [row[f"coefficient_fold_{fold}"] for fold in range(1, 6)]
        ax.plot(x, values, marker="o", label=row["feature"])
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set(xticks=x, xlabel="Held-out fold", ylabel="Standardized-scale coefficient", title="EARS coefficient stability")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(figure_dir / "coefficient_stability.png", dpi=180)
    plt.close(fig)

    methods = [row["method"] for row in ablations]
    x = np.arange(len(methods))
    width = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(x - width / 2, [row["aurc"] for row in ablations], width, label="AURC", color="#2563eb")
    ax.bar(x + width / 2, [row["sr80"] for row in ablations], width, label="R80", color="#f59e0b")
    ax.set(xticks=x, xticklabels=methods, ylabel="Risk (lower is better)", title="Preregistered ablation comparison")
    ax.tick_params(axis="x", rotation=15)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figure_dir / "ablation_comparison.png", dpi=180)
    plt.close(fig)


def dependency_versions() -> dict[str, str]:
    packages = (
        "numpy",
        "scipy",
        "pandas",
        "scikit-learn",
        "matplotlib",
    )
    return {package: importlib.metadata.version(package) for package in packages}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="phase2b_fit_crossfit_v1")
    args = parser.parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()

    hash_audit, baselines, phase2b_config = preflight(root)
    write_json(output_dir / "frozen_artifact_hash_audit.json", hash_audit)
    rows, input_summary = build_rows(root)

    method_features = {
        method: list(specification["features"])
        for method, specification in baselines["models"].items()
    }
    if method_features != phase2b_config["methods"]:
        raise RuntimeError("Executable method feature sets differ from frozen config")
    logistic = dict(baselines["logistic_regression"])
    logistic.pop("implementation")
    logistic.pop("hyperparameter_selection")
    expected_logistic = dict(phase2b_config["logistic_regression"])
    expected_logistic.pop("hyperparameter_search")
    if logistic != expected_logistic:
        raise RuntimeError("Executable logistic parameters differ from frozen config")

    scored_rows, model_records = cross_fit(rows, method_features, logistic)
    if len(model_records) != 25 or not all(record["converged"] for record in model_records):
        raise RuntimeError("Expected 25 converged fold-specific models")

    oof_columns = [
        "claim_id", "fold", "group_id", "y_error", "gold_label", "predicted_label",
        "F1_decision_confidence", "F2_support_contradict_margin",
        "F3_is_contradict", "F3_is_no_relation",
        "F4_bm25_top2_normalized_margin", "F5_evidence_conflict_rate",
        *[f"risk_{method}" for method in ALL_METHODS],
    ]
    write_csv(
        output_dir / "oof_risk_predictions.csv",
        [{column: row[column] for column in oof_columns} for row in scored_rows],
        oof_columns,
    )
    write_json(output_dir / "fold_model_metadata.json", model_records)

    metrics: dict[str, dict[str, Any]] = {}
    curves = []
    for method in ALL_METHODS:
        metric, curve = evaluate_method(scored_rows, method)
        metric["overall_error_rate"] = 175 / 329
        metrics[method] = metric
        curves.extend(curve)
    main_rows = [metrics[method] for method in PRIMARY_METHODS]
    write_csv(output_dir / "main_metrics.csv", main_rows)
    write_csv(output_dir / "risk_coverage_curves.csv", curves)

    ablation_rows = [metrics[method] for method in ABLATION_METHODS]
    write_csv(output_dir / "ablation_results.csv", ablation_rows)
    conditional = class_conditional(scored_rows, PRIMARY_METHODS)
    write_csv(output_dir / "class_conditional_results.csv", conditional)
    coefficients = coefficient_table(model_records)
    write_csv(output_dir / "coefficient_stability.csv", coefficients)
    cases = error_cases(scored_rows)
    write_csv(output_dir / "error_analysis_cases.csv", cases)
    write_json(output_dir / "diagnostics.json", diagnostic_summary(scored_rows))

    bootstrap = bootstrap_paired(scored_rows, replicates=10_000, seed=20261016)
    write_csv(output_dir / "bootstrap_replicates.csv", bootstrap)
    intervals = bootstrap_intervals(bootstrap, metrics)
    write_csv(output_dir / "bootstrap_confidence_intervals.csv", intervals)
    delta_intervals = {
        row["estimand"]: row for row in intervals if row["kind"] == "paired_contrast"
    }
    delta_aurc = metrics["EARS"]["aurc"] - metrics["B1"]["aurc"]
    delta_sr80 = metrics["EARS"]["sr80"] - metrics["B1"]["sr80"]
    supported = (
        delta_intervals["delta_aurc_EARS_minus_B1"]["ci_upper_95"] < 0
        and delta_intervals["delta_sr80_EARS_minus_B1"]["ci_upper_95"] < 0
    )
    unfavorable = (
        delta_intervals["delta_aurc_EARS_minus_B1"]["ci_lower_95"] > 0
        and delta_intervals["delta_sr80_EARS_minus_B1"]["ci_lower_95"] > 0
    )
    decision = "SUPPORTED" if supported else "UNFAVORABLE" if unfavorable else "INCONCLUSIVE"
    comparisons = [
        {
            "contrast": "EARS_minus_B1",
            "metric": "AURC",
            "EARS": metrics["EARS"]["aurc"],
            "B1": metrics["B1"]["aurc"],
            "paired_difference": delta_aurc,
            "ci_lower_95": delta_intervals["delta_aurc_EARS_minus_B1"]["ci_lower_95"],
            "ci_upper_95": delta_intervals["delta_aurc_EARS_minus_B1"]["ci_upper_95"],
            "lower_is_better": True,
            "preregistered_h1_status": decision,
        },
        {
            "contrast": "EARS_minus_B1",
            "metric": "Selective risk at 80% coverage",
            "EARS": metrics["EARS"]["sr80"],
            "B1": metrics["B1"]["sr80"],
            "paired_difference": delta_sr80,
            "ci_lower_95": delta_intervals["delta_sr80_EARS_minus_B1"]["ci_lower_95"],
            "ci_upper_95": delta_intervals["delta_sr80_EARS_minus_B1"]["ci_upper_95"],
            "lower_is_better": True,
            "preregistered_h1_status": decision,
        },
    ]
    write_csv(output_dir / "paired_comparisons.csv", comparisons)

    make_figures(output_dir, curves, metrics, bootstrap, coefficients, ablation_rows)

    data_access_log = {
        "protocol_version": "phase2a-v1.0.0",
        "phase": "2B",
        "run_id": args.run_id,
        "events": [
            {"resource": "Phase 0/1 frozen hash registry", "partition": "metadata", "access": "read", "purpose": "pretraining integrity audit"},
            {"resource": "Phase 2A protocol artifact manifest", "partition": "metadata", "access": "read", "purpose": "pretraining integrity audit"},
            {"resource": "splits/train_split_manifest.json", "partition": "split metadata", "access": "read", "purpose": "select fit IDs and frozen folds; sealed IDs used only as exclusion set"},
            {"resource": "data/raw/scifact/claims_train.jsonl", "partition": "527 fit rows only", "access": "selective read before JSON parsing", "purpose": "claim text and frozen connected groups"},
            {"resource": "reports/phase1/e1_fit_predictions.jsonl", "partition": "fit only", "access": "read", "purpose": "frozen labels, target and F1/F2/F3/F5 extraction"},
            {"resource": "reports/phase1/fit_retrieval_results.jsonl", "partition": "fit only", "access": "read", "purpose": "frozen F4 extraction"},
        ],
        "sealed_partition_status": {
            "calibration": "not deserialized, predicted, scored, or inspected",
            "internal_test": "not deserialized, predicted, scored, or inspected",
            "raw_scifact_dev": "not accessed",
            "official_scifact_test": "not accessed",
        },
        "nli_rerun": False,
        "temperature_scaling": False,
        "threshold_selection": False,
        "phase3_or_phase4_activity": False,
    }
    write_json(output_dir / "data_access_log.json", data_access_log)

    artifact_hashes = {}
    for path in sorted(output_dir.rglob("*")):
        # Hash only run-produced scientific artifacts. Human-authored wrapper
        # reports and the comparison audit are maintained separately; including
        # PHASE2B_RUN_MANIFEST.json here would create a circular hash dependency.
        if (
            path.is_file()
            and path.name != "experiment_manifest.json"
            and not path.name.endswith(".md")
            and path.name not in {
                "PHASE2B_RUN_MANIFEST.json",
                "reproducibility_comparison.json",
            }
        ):
            artifact_hashes[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    manifest = {
        "phase": "2B",
        "scope": "strictly fit-only five-fold cross-fitted risk ranking",
        "run_id": args.run_id,
        "protocol_version": "phase2a-v1.0.0",
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_summary": input_summary,
        "features_by_method": {method: method_features[method] for method in ALL_METHODS},
        "effective_columns_by_method": {
            method: method_columns(method_features[method]) for method in LEARNED_METHODS
        },
        "logistic_regression": logistic,
        "models_fit": 25,
        "all_models_converged": True,
        "bootstrap": {
            "replicates": 10_000,
            "seed": 20261016,
            "rng": "numpy.random.default_rng (PCG64)",
            "groups_sampled_per_replicate": 243,
            "paired": True,
            "retraining": False,
            "duplicate_draw_tie_rule": "risk, frozen claim tie hash, bootstrap sample position",
            "quantile_method": "numpy percentile linear",
        },
        "preregistered_h1_status": decision,
        "dependencies": dependency_versions(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "input_sha256": {
            relative: sha256_file(root / relative)
            for relative in (
                "data/raw/scifact/claims_train.jsonl",
                "reports/phase1/e1_fit_predictions.jsonl",
                "reports/phase1/fit_retrieval_results.jsonl",
                "splits/train_split_manifest.json",
                "reports/phase2b/PHASE2B_CONFIG.json",
            )
        },
        "source_sha256": {
            relative: sha256_file(root / relative)
            for relative in (
                "scripts/run_phase2b.py",
                "src/trustworthy_ai_lab/phase2b.py",
                "src/trustworthy_ai_lab/phase2_protocol.py",
                "tests/test_phase2b.py",
                "requirements-phase2b.txt",
            )
        },
        "sealed_partition_performance_access": [],
        "probability_calibration_performed": False,
        "deployment_threshold_selected": False,
        "formal_outputs_sha256": artifact_hashes,
        "core_reproducibility_files": list(CORE_REPRODUCIBILITY_FILES),
    }
    write_json(output_dir / "experiment_manifest.json", manifest)
    print(json.dumps({
        "status": "completed",
        "run_id": args.run_id,
        "output_dir": output_dir.as_posix(),
        "h1": decision,
        "main_metrics": main_rows,
        "paired_comparisons": comparisons,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
