#!/usr/bin/env python3
"""Evaluate frozen and reconstructed v2 research artifacts after score freeze."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ks_2samp, spearmanr
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, confusion_matrix, log_loss, roc_auc_score

from demo.cloud_artifacts import load_verified_numeric_models, score_frozen_models
from trustworthy_ai_lab.aggregation import aggregate_claim
from trustworthy_ai_lab.data import derived_evidence_label, load_json, load_jsonl, write_json, write_jsonl
from trustworthy_ai_lab.metrics import (
    classification_metrics,
    error_breakdown,
    retrieval_metrics,
    sentence_selection_metrics,
)
from trustworthy_ai_lab.phase2_protocol import extract_features, tie_key
from trustworthy_ai_lab.phase2b import (
    connected_group_lookup,
    evaluate_method,
    method_columns,
    percentile_interval,
    safe_auroc,
)
from trustworthy_ai_lab.phase3b import FrozenPreprocessor, build_labeled_retrieval, sha256_file
from trustworthy_ai_lab.pipeline import finalize_e1


METHOD_FEATURES = {
    "B1": ["F1", "F2", "F3"],
    "B1_plus_F4": ["F1", "F2", "F3", "F4"],
    "B1_plus_F5": ["F1", "F2", "F3", "F5"],
    "EARS": ["F1", "F2", "F3", "F4", "F5"],
}
LOGISTIC = {
    "penalty": "l2", "C": 0.1, "solver": "lbfgs", "class_weight": None,
    "fit_intercept": True, "max_iter": 2000, "tol": 1e-6,
    "random_state": 20261014,
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def split_claims(root: Path) -> dict[str, list[dict[str, Any]]]:
    train = load_jsonl(root / "data/raw/scifact/claims_train.jsonl")
    dev = load_jsonl(root / "data/raw/scifact/claims_dev.jsonl")
    split = load_json(root / "splits/train_split_manifest.json")
    by_id = {int(row["id"]): row for row in train}
    output = {
        name: [by_id[int(value)] for value in spec["claim_ids"]]
        for name, spec in split["outer_splits"].items()
    }
    output["dev"] = dev
    return output


def analyze_overlap(parts: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    def norm(text: str) -> str:
        return " ".join("".join(c if c.isalnum() else " " for c in text.casefold()).split())
    historical = parts["fit"] + parts["calibration"] + parts["internal_test"]
    dev = parts["dev"]
    h_ids = {int(row["id"]) for row in historical}
    d_ids = {int(row["id"]) for row in dev}
    h_text = {norm(row["claim"]) for row in historical}
    d_text = {norm(row["claim"]) for row in dev}
    h_docs = {int(doc) for row in historical for doc in row["cited_doc_ids"]}
    d_docs = {int(doc) for row in dev for doc in row["cited_doc_ids"]}
    return {
        "historical_claims": len(historical), "dev_claims": len(dev),
        "exact_id_overlap": len(h_ids & d_ids),
        "normalized_claim_text_overlap": len(h_text & d_text),
        "shared_cited_document_count": len(h_docs & d_docs),
        "historical_unique_cited_documents": len(h_docs),
        "dev_unique_cited_documents": len(d_docs),
        "interpretation": "SciFact Dev is a separate official split but remains same-dataset-family validation; shared documents lower independence even if claim texts are distinct.",
    }


def fold_map(root: Path) -> dict[int, str]:
    split = load_json(root / "splits/train_split_manifest.json")
    return {
        int(claim_id): name
        for name, spec in split["crossfit_validation_folds_within_fit"].items()
        for claim_id in spec["claim_ids"]
    }


def labeled_outputs(root: Path, verifier: str, claims: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cache = root / ".cache/research_upgrade_v2" / verifier
    retrieval = load_jsonl(cache / "retrieval.jsonl")
    pairs = load_jsonl(cache / "pair_predictions.jsonl")
    claim_ids = {int(row["id"]) for row in claims}
    subset_retrieval = [row for row in retrieval if int(row["claim_id"]) in claim_ids]
    subset_pairs = [row for row in pairs if int(row["claim_id"]) in claim_ids]
    labeled = build_labeled_retrieval(subset_retrieval, claims)
    evaluated = finalize_e1(labeled, subset_pairs)
    return labeled, evaluated


def rows_for_partition(
    root: Path,
    verifier: str,
    partition: str,
    claims: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    labeled, evaluated = labeled_outputs(root, verifier, claims)
    compact_all = load_jsonl(
        root / f".cache/research_upgrade_v2/{verifier}/blind_{verifier}_features.jsonl"
    )
    compact = {
        int(row["claim_id"]): row for row in compact_all if row["partition"] == partition
    }
    groups = connected_group_lookup(claims)
    folds = fold_map(root) if partition == "fit" else {}
    rows = []
    for result in evaluated:
        if not result["evaluation_eligible"]:
            continue
        claim_id = int(result["claim_id"])
        features = {key: value for key, value in compact[claim_id].items() if key.startswith("F")}
        row = {
            "claim_id": claim_id,
            "group_id": int(groups[claim_id]),
            "gold_label": result["gold_evidence_label"],
            "predicted_label": result["predicted_claim_label"],
            "y_error": int(not bool(result["correct"])),
            **features,
        }
        if partition == "fit":
            row["fold"] = folds[claim_id]
        if "risk_frozen_B1" in compact[claim_id]:
            row["risk_frozen_B1"] = float(compact[claim_id]["risk_frozen_B1"])
            row["risk_frozen_EARS"] = float(compact[claim_id]["risk_frozen_EARS"])
        rows.append(row)
    return sorted(rows, key=lambda row: row["claim_id"]), labeled, evaluated


def fit_models(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    y = np.asarray([int(row["y_error"]) for row in rows])
    bundles, coefficients = {}, []
    for method, feature_ids in METHOD_FEATURES.items():
        columns = method_columns(feature_ids)
        prep = FrozenPreprocessor.fit(rows, columns)
        matrix = prep.transform(rows)
        model = LogisticRegression(**LOGISTIC).fit(matrix, y)
        bundles[method] = {"preprocessor": prep, "model": model, "columns": columns}
        for column, value in zip(columns, model.coef_[0]):
            coefficients.append({
                "method": method, "feature": column, "coefficient": float(value),
                "intercept": float(model.intercept_[0]), "iterations": int(model.n_iter_[0]),
            })
    return bundles, coefficients


def score_models(rows: list[dict[str, Any]], bundles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output = [dict(row) for row in rows]
    for method, bundle in bundles.items():
        matrix = bundle["preprocessor"].transform(rows)
        risks = bundle["model"].predict_proba(matrix)[:, 1]
        for row, risk in zip(output, risks):
            row[f"risk_{method}"] = float(risk)
    return output


def metrics_for(rows: list[dict[str, Any]], methods: Iterable[str], evidence: str, verifier: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metrics, curves = [], []
    for method in methods:
        values, curve = evaluate_method(rows, method)
        values.update({"evidence_level": evidence, "verifier": verifier})
        metrics.append(values)
        for point in curve:
            point.update({"evidence_level": evidence, "verifier": verifier})
        curves.extend(curve)
    return metrics, curves


def bootstrap_all(rows: list[dict[str, Any]], methods: list[str], replicates: int = 10_000) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[int, list[int]] = collections.defaultdict(list)
    for index, row in enumerate(rows):
        groups[int(row["group_id"])].append(index)
    group_ids = sorted(groups)
    rng = np.random.default_rng(20261016)
    records = []
    for replicate in range(replicates):
        sampled = []
        for draw in rng.integers(0, len(group_ids), size=len(group_ids)):
            sampled.extend(groups[group_ids[int(draw)]])
        record: dict[str, Any] = {"replicate": replicate, "n": len(sampled), "group_draws": len(group_ids)}
        sample_rows = [rows[index] for index in sampled]
        for method in methods:
            # Occurrence IDs preserve duplicated group draws while retaining stable tie order.
            local = [dict(row, claim_id=int(row["claim_id"]) * 100000 + pos) for pos, row in enumerate(sample_rows)]
            values, _ = evaluate_method(local, method)
            record[f"aurc_{method}"] = values["aurc"]
            record[f"sr80_{method}"] = values["sr80"]
            record[f"auroc_{method}"] = values["error_detection_auroc"]
        records.append(record)
    intervals = []
    points, _ = metrics_for(rows, methods, "point", "point")
    point_by = {row["method"]: row for row in points}
    for method in methods:
        for metric, point_name in (("aurc", "aurc"), ("sr80", "sr80"), ("auroc", "error_detection_auroc")):
            values = [row[f"{metric}_{method}"] for row in records if row[f"{metric}_{method}"] is not None]
            lower, upper = percentile_interval(values)
            intervals.append({
                "estimand": f"{metric}_{method}", "point_estimate": point_by[method][point_name],
                "ci_lower_95": lower, "ci_upper_95": upper, "valid_replicates": len(values),
            })
    for candidate in ("B1_plus_F4", "B1_plus_F5", "EARS"):
        for metric, point_name in (("aurc", "aurc"), ("sr80", "sr80")):
            values = [row[f"{metric}_{candidate}"] - row[f"{metric}_B1"] for row in records]
            lower, upper = percentile_interval(values)
            intervals.append({
                "estimand": f"delta_{metric}_{candidate}_minus_B1",
                "point_estimate": point_by[candidate][point_name] - point_by["B1"][point_name],
                "ci_lower_95": lower, "ci_upper_95": upper, "valid_replicates": len(values),
            })
    return records, intervals


def crossfit(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored = {int(row["claim_id"]): dict(row) for row in rows}
    records = []
    for held in sorted({row["fold"] for row in rows}):
        train = [row for row in rows if row["fold"] != held]
        valid = [row for row in rows if row["fold"] == held]
        bundles, coefficients = fit_models(train)
        fold_scored = score_models(valid, bundles)
        for row in fold_scored:
            scored[int(row["claim_id"])].update({key: value for key, value in row.items() if key.startswith("risk_")})
        for row in coefficients:
            records.append({**row, "held_out_fold": held, "training_n": len(train), "validation_n": len(valid)})
    return [scored[key] for key in sorted(scored)], records


def diagnostics(rows: list[dict[str, Any]], labeled: list[dict[str, Any]], evaluated: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in evaluated if row["evaluation_eligible"]]
    labels = ["SUPPORT", "CONTRADICT", "NO_RELATION"]
    gold = [row["gold_evidence_label"] for row in eligible]
    pred = [row["predicted_claim_label"] for row in eligible]
    cm = confusion_matrix(gold, pred, labels=labels).tolist()
    taxonomy = collections.Counter(
        category for row in eligible for category in row["failure_categories"]
    )
    overlaps = collections.Counter(
        tuple(sorted(row["failure_categories"])) for row in eligible if row["failure_categories"]
    )
    return {
        "classification": classification_metrics(evaluated),
        "confusion_labels": labels,
        "confusion_matrix": cm,
        "retrieval": retrieval_metrics(labeled),
        "sentence_selection_at_5": sentence_selection_metrics(labeled, 5),
        "error_breakdown": error_breakdown(evaluated),
        "failure_taxonomy_counts": dict(taxonomy),
        "failure_category_combinations": {" + ".join(key): value for key, value in overlaps.items()},
        "eligible_claims": len(rows),
        "eligible_groups": len({row["group_id"] for row in rows}),
    }


def feature_diagnostics(fit: list[dict[str, Any]], dev: list[dict[str, Any]], bundles: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    features = method_columns(["F1", "F2", "F3", "F4", "F5"])
    corr = np.corrcoef(np.asarray([[row[f] for f in features] for row in fit], dtype=float), rowvar=False)
    correlations = [
        {"feature_left": left, "feature_right": right, "pearson_r": float(corr[i, j])}
        for i, left in enumerate(features) for j, right in enumerate(features) if i < j
    ]
    shifts = []
    for feature in features:
        a = np.asarray([row[feature] for row in fit], dtype=float)
        b = np.asarray([row[feature] for row in dev], dtype=float)
        pooled = math.sqrt((float(np.var(a)) + float(np.var(b))) / 2) or 1.0
        ks = ks_2samp(a, b, method="auto")
        shifts.append({
            "feature": feature, "fit_mean": float(np.mean(a)), "dev_mean": float(np.mean(b)),
            "standardized_mean_difference": float((np.mean(b) - np.mean(a)) / pooled),
            "ks_statistic": float(ks.statistic), "ks_pvalue_descriptive": float(ks.pvalue),
        })
    importance = []
    y = np.asarray([row["y_error"] for row in dev])
    for method, bundle in bundles.items():
        matrix = bundle["preprocessor"].transform(dev)
        result = permutation_importance(
            bundle["model"], matrix, y, scoring="roc_auc", n_repeats=100,
            random_state=20261018,
        )
        for feature, mean, std in zip(bundle["columns"], result.importances_mean, result.importances_std):
            importance.append({"method": method, "feature": feature, "auroc_decrease_mean": float(mean), "auroc_decrease_std": float(std)})
    return correlations, shifts, importance


def multicollinearity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    features = method_columns(["F1", "F2", "F3", "F4", "F5"])
    matrix = np.asarray([[row[name] for name in features] for row in rows], dtype=float)
    standardized = (matrix - matrix.mean(axis=0)) / np.where(matrix.std(axis=0) == 0, 1, matrix.std(axis=0))
    singular = np.linalg.svd(standardized, compute_uv=False)
    vif_rows = []
    for index, feature in enumerate(features):
        target = matrix[:, index]
        predictors = np.delete(matrix, index, axis=1)
        fitted = np.column_stack([np.ones(len(rows)), predictors]) @ np.linalg.lstsq(
            np.column_stack([np.ones(len(rows)), predictors]), target, rcond=None
        )[0]
        denominator = float(np.sum((target - target.mean()) ** 2))
        r2 = 0.0 if denominator == 0 else 1.0 - float(np.sum((target - fitted) ** 2)) / denominator
        vif_rows.append({"feature": feature, "r_squared_from_other_features": r2, "vif": float(1.0 / max(1e-12, 1.0-r2))})
    return {
        "condition_number_standardized_design": float(singular[0] / singular[-1]),
        "vif": vif_rows,
        "interpretation": "Descriptive collinearity diagnostics; coefficients are not causal effects.",
    }


def interaction_analysis(fit: list[dict[str, Any]], dev: list[dict[str, Any]]) -> dict[str, Any]:
    base = method_columns(["F1", "F2", "F3", "F4", "F5"])
    def matrix(rows: list[dict[str, Any]]) -> np.ndarray:
        values = []
        for row in rows:
            source = [float(row[name]) for name in base]
            source += [
                float(row["F4_bm25_top2_normalized_margin"]) * float(row["F5_evidence_conflict_rate"]),
                float(row["F1_decision_confidence"]) * float(row["F4_bm25_top2_normalized_margin"]),
                float(row["F1_decision_confidence"]) * float(row["F5_evidence_conflict_rate"]),
            ]
            values.append(source)
        return np.asarray(values, dtype=float)
    x_fit, x_dev = matrix(fit), matrix(dev)
    mean, scale = x_fit.mean(axis=0), x_fit.std(axis=0)
    scale[scale == 0] = 1.0
    model = LogisticRegression(**LOGISTIC).fit((x_fit-mean)/scale, [row["y_error"] for row in fit])
    risks = model.predict_proba((x_dev-mean)/scale)[:, 1]
    scored = [{**row, "risk_INTERACTION": float(risk)} for row, risk in zip(dev, risks)]
    metrics, _ = evaluate_method(scored, "INTERACTION")
    return {
        "status": "POST_HOC_EXPLORATORY",
        "terms": ["F4*F5", "F1*F4", "F1*F5"],
        "fit_n": len(fit), "evaluation_n": len(dev),
        "metrics": metrics,
        "coefficients": {
            name: float(value) for name, value in zip(base + ["F4_x_F5", "F1_x_F4", "F1_x_F5"], model.coef_[0])
        },
        "warning": "Interaction terms were not a confirmatory endpoint and coefficients are not causal effects.",
    }


def class_conditional(rows: list[dict[str, Any]], methods: Iterable[str]) -> list[dict[str, Any]]:
    output = []
    for method in methods:
        ordered = sorted(rows, key=lambda row: (row[f"risk_{method}"], tie_key(int(row["claim_id"]))))
        accepted = {int(row["claim_id"]) for row in ordered[:math.floor(.8*len(rows)+.5)]}
        for field, kind in (("gold_label", "true_label"), ("predicted_label", "predicted_label")):
            for value in sorted({row[field] for row in rows}):
                subset = [row for row in rows if row[field] == value]
                accepted_subset = [row for row in subset if int(row["claim_id"]) in accepted]
                output.append({
                    "method": method, "stratum_type": kind, "stratum": value,
                    "n": len(subset), "errors": sum(row["y_error"] for row in subset),
                    "error_rate": sum(row["y_error"] for row in subset)/len(subset),
                    "mean_risk": float(np.mean([row[f"risk_{method}"] for row in subset])),
                    "accepted_at_global80": len(accepted_subset),
                    "accepted_errors": sum(row["y_error"] for row in accepted_subset),
                })
    return output


def calibration(fit_rows: list[dict[str, Any]], dev_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary, bins = [], []
    for method in ("B1", "EARS"):
        field = f"risk_frozen_{method}"
        x_fit = np.asarray([[row[field]] for row in fit_rows])
        y_fit = np.asarray([row["y_error"] for row in fit_rows])
        x_dev = np.asarray([[row[field]] for row in dev_rows])
        y_dev = np.asarray([row["y_error"] for row in dev_rows])
        calibrator = LogisticRegression(C=1e6, solver="lbfgs", max_iter=2000, random_state=20261019).fit(x_fit, y_fit)
        raw = x_dev[:, 0]
        calibrated = calibrator.predict_proba(x_dev)[:, 1]
        for kind, values in (("raw_uncalibrated_score", raw), ("platt_calibrated", calibrated)):
            ece = 0.0
            for index in range(10):
                lo, hi = index / 10, (index + 1) / 10
                mask = (values >= lo) & ((values < hi) if index < 9 else (values <= hi))
                if not mask.any():
                    continue
                confidence = float(np.mean(values[mask])); observed = float(np.mean(y_dev[mask]))
                ece += int(mask.sum()) / len(values) * abs(confidence - observed)
                bins.append({"method": method, "score_kind": kind, "bin": index, "n": int(mask.sum()), "mean_score": confidence, "observed_error_rate": observed})
            summary.append({
                "method": method, "score_kind": kind,
                "brier_score": float(brier_score_loss(y_dev, values)),
                "log_loss": float(log_loss(y_dev, np.column_stack([1-values, values]), labels=[0, 1])),
                "ece_10_equal_width": float(ece),
                "calibration_fit_n": len(fit_rows), "evaluation_n": len(dev_rows),
                "calibrator_coefficient": None if kind.startswith("raw") else float(calibrator.coef_[0, 0]),
                "calibrator_intercept": None if kind.startswith("raw") else float(calibrator.intercept_[0]),
            })
    return summary, bins


def historical_posthoc(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    translated = []
    for row in rows:
        translated.append({
            **row,
            "risk_B1": row["risk_frozen_B1"],
            "risk_EARS": row["risk_frozen_EARS"],
        })
    logo = []
    for group in sorted({row["group_id"] for row in translated}):
        subset = [row for row in translated if row["group_id"] != group]
        b1, _ = evaluate_method(subset, "B1"); ears, _ = evaluate_method(subset, "EARS")
        logo.append({
            "left_out_group": group, "n": len(subset),
            "b1_aurc": b1["aurc"], "ears_aurc": ears["aurc"], "delta_aurc": ears["aurc"]-b1["aurc"],
            "b1_r80": b1["sr80"], "ears_r80": ears["sr80"], "delta_r80": ears["sr80"]-b1["sr80"],
        })
    acceptance = {}
    accepted_sets = {}
    for method in ("B1", "EARS"):
        ordered = sorted(translated, key=lambda row: (row[f"risk_{method}"], tie_key(int(row["claim_id"]))))
        k = math.floor(.8 * len(ordered) + .5)
        accepted_sets[method] = {int(row["claim_id"]) for row in ordered[:k]}
    b_only = accepted_sets["B1"] - accepted_sets["EARS"]
    e_only = accepted_sets["EARS"] - accepted_sets["B1"]
    by_id = {int(row["claim_id"]): row for row in translated}
    acceptance = {
        "accepted_each": len(accepted_sets["B1"]),
        "shared_accepted": len(accepted_sets["B1"] & accepted_sets["EARS"]),
        "b1_only_count": len(b_only), "ears_only_count": len(e_only),
        "errors_leaving_when_B1_to_EARS": sum(by_id[i]["y_error"] for i in b_only),
        "errors_entering_when_B1_to_EARS": sum(by_id[i]["y_error"] for i in e_only),
        "b1_only_claim_ids": sorted(b_only), "ears_only_claim_ids": sorted(e_only),
    }
    return logo, acceptance


def perturbations(root: Path, dev_claims: list[dict[str, Any]], base_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cache = root / ".cache/research_upgrade_v2/e1"
    retrieval = [row for row in load_jsonl(cache / "retrieval.jsonl") if row["partition"] == "dev"]
    pair_rows = load_jsonl(cache / "pair_predictions.jsonl")
    ids = {int(row["id"]) for row in dev_claims}
    pairs_by: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in pair_rows:
        if int(row["claim_id"]) in ids:
            pairs_by[int(row["claim_id"])].append(row)
    injected_by: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in load_jsonl(cache / "injection_predictions.jsonl"):
        injected_by[int(row["claim_id"])].append(row)
    numeric = load_verified_numeric_models(root)
    base_by = {int(row["claim_id"]): row for row in base_rows}
    feature_sets: dict[str, list[dict[str, Any]]] = {name: [] for name in (
        "drop_top_retrieved_document", "remove_lowest_selected_sentence_per_document",
        "inject_irrelevant_top5_document", "bm25_score_jitter",
    )}
    for record in retrieval:
        claim_id = int(record["claim_id"]); pairs = pairs_by[claim_id]
        variants = {
            "drop_top_retrieved_document": [row for row in pairs if int(row["doc_rank"]) != 1],
            "remove_lowest_selected_sentence_per_document": [row for row in pairs if int(row["selected_sentence_rank"]) < 3],
            "inject_irrelevant_top5_document": [row for row in pairs if int(row["doc_rank"]) != 5] + injected_by[claim_id],
            "bm25_score_jitter": pairs,
        }
        for name, chosen in variants.items():
            agg = aggregate_claim(chosen)
            shell = {**record, "retrieved_documents": [dict(doc) for doc in record["retrieved_documents"]]}
            if name == "drop_top_retrieved_document":
                shell["retrieved_documents"] = shell["retrieved_documents"][1:]
            elif name == "bm25_score_jitter":
                first, second = shell["retrieved_documents"][:2]
                values = sorted((float(first["bm25_score"]) * .95, float(second["bm25_score"]) * 1.05), reverse=True)
                first["bm25_score"], second["bm25_score"] = values
            prediction = {"claim_id": claim_id, **agg, "sentence_predictions": chosen}
            feature_sets[name].append({"claim_id": claim_id, **extract_features(prediction, shell)})
    output = []
    for name, features in feature_sets.items():
        # Risk-ranking performance is defined only for claims with authentic
        # SUPPORT/CONTRADICT labels. Unannotated Dev claims remain available to
        # retrieval diagnostics but cannot enter label-based robustness metrics.
        features = [row for row in features if int(row["claim_id"]) in base_by]
        scores = score_frozen_models(numeric, features)
        for method in ("B1", "EARS"):
            base = np.asarray([base_by[int(row["claim_id"])][f"risk_frozen_{method}"] for row in features])
            changed = np.asarray(scores[method])
            rho = float(spearmanr(base, changed).statistic)
            top = math.floor(.8 * len(base) + .5)
            base_order = set(np.argsort(base, kind="stable")[:top].tolist())
            changed_order = set(np.argsort(changed, kind="stable")[:top].tolist())
            output.append({
                "perturbation": name, "method": method, "n": len(base),
                "spearman_rank_correlation": rho,
                "mean_absolute_score_change": float(np.mean(np.abs(changed-base))),
                "accepted80_jaccard": len(base_order & changed_order) / len(base_order | changed_order),
            })
    return output


def make_figures(output: Path, metrics: list[dict[str, Any]], diagnostics_map: dict[str, Any], calibration_bins: list[dict[str, Any]], perturb: list[dict[str, Any]], coefficients: list[dict[str, Any]]) -> None:
    figures = output / "figures"; figures.mkdir(parents=True, exist_ok=True)
    selected = [row for row in metrics if row["evidence_level"] == "same_dataset_dev_reconstructed"]
    plt.figure(figsize=(7, 4)); plt.bar([row["method"] for row in selected], [row["aurc"] for row in selected]); plt.ylabel("Discrete AURC (lower is better)"); plt.xticks(rotation=20); plt.tight_layout(); plt.savefig(figures / "dev_ablation_aurc.png", dpi=180); plt.close()
    cm = np.asarray(diagnostics_map["e1"]["confusion_matrix"])
    plt.figure(figsize=(5, 4)); plt.imshow(cm, cmap="Blues"); plt.colorbar(); labels=diagnostics_map["e1"]["confusion_labels"]; plt.xticks(range(3),labels,rotation=25); plt.yticks(range(3),labels); plt.xlabel("Predicted"); plt.ylabel("Gold");
    for i in range(3):
        for j in range(3): plt.text(j,i,str(cm[i,j]),ha="center",va="center")
    plt.tight_layout(); plt.savefig(figures / "dev_e1_confusion_matrix.png", dpi=180); plt.close()
    plt.figure(figsize=(7,4))
    for method in ("B1","EARS"):
        rows=[r for r in calibration_bins if r["method"]==method and r["score_kind"]=="platt_calibrated"]
        plt.plot([r["mean_score"] for r in rows],[r["observed_error_rate"] for r in rows],marker="o",label=method)
    plt.plot([0,1],[0,1],"--",color="black"); plt.xlabel("Mean calibrated score"); plt.ylabel("Observed error rate"); plt.legend(); plt.tight_layout(); plt.savefig(figures / "dev_calibration_reliability.png",dpi=180); plt.close()
    plt.figure(figsize=(8,4)); names=sorted({r["perturbation"] for r in perturb}); x=np.arange(len(names));
    for offset,method in ((-.18,"B1"),(.18,"EARS")):
        vals=[next(r["spearman_rank_correlation"] for r in perturb if r["perturbation"]==n and r["method"]==method) for n in names]
        plt.bar(x+offset,vals,.36,label=method)
    plt.xticks(x,names,rotation=25,ha="right"); plt.ylabel("Spearman rank correlation"); plt.ylim(-1,1); plt.legend(); plt.tight_layout(); plt.savefig(figures / "perturbation_rank_stability.png",dpi=180); plt.close()
    ears=[r for r in coefficients if r["method"]=="EARS"]
    plt.figure(figsize=(7,4)); plt.bar([r["feature"] for r in ears],[r["coefficient"] for r in ears]); plt.axhline(0,color="black",linewidth=.8); plt.xticks(rotation=30,ha="right"); plt.ylabel("Standardized logistic coefficient"); plt.tight_layout(); plt.savefig(figures / "ears_coefficients.png",dpi=180); plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, required=True); args=parser.parse_args()
    root=args.root.resolve(); output=root/"reports/research_upgrade_v2/results"; output.mkdir(parents=True,exist_ok=True)
    protocol_hash=sha256_file(root/"configs/research_upgrade_v2_protocol.json")
    if protocol_hash!="70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301": raise RuntimeError("Protocol hash changed")
    for verifier in ("e1","e1_v2"):
        manifest=load_json(output/f"blind_{verifier}_manifest.json")
        if manifest["status"]!="PREDICTIONS_FROZEN_BEFORE_V2_EVALUATION_LABEL_ACCESS": raise RuntimeError("Scores not frozen")
    parts=split_claims(root); write_json(output/"dataset_overlap_audit.json",analyze_overlap(parts))
    all_metrics=[]; all_curves=[]; diagnostics_map={}; coefficient_rows=[]
    dev_scored_by={}; bundles_by={}; raw_rows={}
    for verifier in ("e1","e1_v2"):
        fit_rows,_,_=rows_for_partition(root,verifier,"fit",parts["fit"])
        dev_rows,labeled,evaluated=rows_for_partition(root,verifier,"dev",parts["dev"])
        raw_rows[(verifier,"fit")]=fit_rows; raw_rows[(verifier,"dev")]=dev_rows
        oof,fold_coeff=crossfit(fit_rows); m,c=metrics_for(oof,list(METHOD_FEATURES),"fit_group_crossfit",verifier); all_metrics+=m; all_curves+=c
        bundles,coeff=fit_models(fit_rows); bundles_by[verifier]=bundles; coefficient_rows += [{**row,"verifier":verifier,"scope":"full_fit"} for row in coeff] + [{**row,"verifier":verifier,"scope":"crossfit"} for row in fold_coeff]
        dev_scored=score_models(dev_rows,bundles); dev_scored_by[verifier]=dev_scored
        m,c=metrics_for(dev_scored,list(METHOD_FEATURES),"same_dataset_dev_reconstructed",verifier); all_metrics+=m; all_curves+=c
        diagnostics_map[verifier]=diagnostics(dev_rows,labeled,evaluated)
        write_json(output/f"{verifier}_dev_diagnostics.json",diagnostics_map[verifier])
    # Public numeric frozen B1/EARS are evaluated separately from reconstructed ablations.
    frozen_dev=[]
    for row in raw_rows[("e1","dev")]: frozen_dev.append({**row,"risk_B1":row["risk_frozen_B1"],"risk_EARS":row["risk_frozen_EARS"]})
    m,c=metrics_for(frozen_dev,["B1","EARS"],"same_dataset_dev_frozen_model","e1"); all_metrics+=m; all_curves+=c
    bootstrap,intervals=bootstrap_all(dev_scored_by["e1"],list(METHOD_FEATURES)); write_csv(output/"dev_bootstrap_replicates.csv",bootstrap); write_csv(output/"dev_bootstrap_intervals.csv",intervals)
    correlations,shifts,importance=feature_diagnostics(raw_rows[("e1","fit")],raw_rows[("e1","dev")],bundles_by["e1"])
    write_csv(output/"feature_correlations.csv",correlations); write_csv(output/"feature_distribution_shift.csv",shifts); write_csv(output/"conditional_permutation_importance.csv",importance)
    write_json(output/"multicollinearity_diagnostics.json",multicollinearity(raw_rows[("e1","fit")]))
    write_json(output/"interaction_analysis.json",interaction_analysis(raw_rows[("e1","fit")],raw_rows[("e1","dev")]))
    write_csv(output/"class_conditional_risk.csv",class_conditional(dev_scored_by["e1"],METHOD_FEATURES))
    calibration_rows,calibration_bins=rows_for_partition(root,"e1","calibration",parts["calibration"])[0],None
    calibration_summary,calibration_bins=calibration(calibration_rows,raw_rows[("e1","dev")]); write_csv(output/"calibration_metrics.csv",calibration_summary); write_csv(output/"calibration_bins.csv",calibration_bins)
    internal_rows=rows_for_partition(root,"e1","internal_test",parts["internal_test"])[0]
    logo,acceptance=historical_posthoc(internal_rows); write_csv(output/"historical_internal_logo_sensitivity.csv",logo); write_json(output/"historical_internal_acceptance_analysis.json",acceptance)
    perturb=perturbations(root,parts["dev"],raw_rows[("e1","dev")]); write_csv(output/"perturbation_robustness.csv",perturb)
    write_csv(output/"all_metrics.csv",all_metrics); write_csv(output/"risk_coverage_curves.csv",all_curves); write_csv(output/"coefficient_stability.csv",coefficient_rows)
    # Copyright-conscious case records: IDs and derived diagnostics only, no claim/evidence text.
    _,_,evaluated=rows_for_partition(root,"e1","dev",parts["dev"])
    cases=[{"claim_id":int(r["claim_id"]),"gold_label":r["gold_evidence_label"],"predicted_label":r["predicted_claim_label"],"failure_categories":r["failure_categories"],"retrieval_hit_at_5":r["retrieval_hit_at_5"],"complete_gold_rationale_selected":r["any_complete_gold_rationale_selected"]} for r in evaluated if r["evaluation_eligible"] and not r["correct"]]
    write_jsonl(output/"representative_failure_records.jsonl",cases[:20])
    make_figures(output,all_metrics,diagnostics_map,calibration_bins,perturb,coefficient_rows)
    artifacts={p.relative_to(output).as_posix():sha256_file(p) for p in sorted(output.rglob("*")) if p.is_file() and p.name!="analysis_manifest.json"}
    manifest={"status":"COMPLETE","protocol_sha256":protocol_hash,"labels_opened_only_after_blind_manifests_verified":True,"artifacts_sha256":artifacts,"counts":{"dev_eligible":len(raw_rows[("e1","dev")]),"dev_groups":len({r['group_id'] for r in raw_rows[("e1","dev")]}),"fit_eligible":len(raw_rows[("e1","fit")]),"internal_eligible":len(internal_rows)}}
    write_json(output/"analysis_manifest.json",manifest); print(json.dumps(manifest,indent=2))


if __name__=="__main__": main()
