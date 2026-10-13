from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import warnings
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from .phase2_protocol import fixed_coverage_count, tie_key


FEATURE_COLUMNS = {
    "F1": ["F1_decision_confidence"],
    "F2": ["F2_support_contradict_margin"],
    "F3": ["F3_is_contradict", "F3_is_no_relation"],
    "F4": ["F4_bm25_top2_normalized_margin"],
    "F5": ["F5_evidence_conflict_rate"],
}
CONTINUOUS_COLUMNS = {
    "F1_decision_confidence",
    "F2_support_contradict_margin",
    "F4_bm25_top2_normalized_margin",
    "F5_evidence_conflict_rate",
}
LEARNED_METHODS = ("B1", "B2", "EARS", "EARS_minus_F4", "EARS_minus_F5")
PRIMARY_METHODS = ("B0", "B1", "B2", "EARS")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_claim(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def connected_group_lookup(claims: list[dict[str, Any]]) -> dict[int, int]:
    """Build groups from every fit claim before eligible filtering."""
    parent = {int(row["id"]): int(row["id"]) for row in claims}
    if len(parent) != len(claims):
        raise ValueError("Duplicate fit claim IDs")

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            smaller, larger = sorted((left_root, right_root))
            parent[larger] = smaller

    buckets: dict[tuple[str, Any], list[int]] = collections.defaultdict(list)
    for row in claims:
        claim_id = int(row["id"])
        for doc_id in row["cited_doc_ids"]:
            buckets[("cited_doc", int(doc_id))].append(claim_id)
        buckets[("claim_text", normalize_claim(row["claim"]))].append(claim_id)
    for members in buckets.values():
        anchor = min(members)
        for member in members:
            union(anchor, member)

    components: dict[int, list[int]] = collections.defaultdict(list)
    for claim_id in sorted(parent):
        components[find(claim_id)].append(claim_id)
    return {
        claim_id: min(members)
        for members in components.values()
        for claim_id in members
    }


def method_columns(feature_ids: list[str]) -> list[str]:
    columns: list[str] = []
    for feature_id in feature_ids:
        if feature_id not in FEATURE_COLUMNS:
            raise ValueError(f"Unknown feature ID: {feature_id}")
        columns.extend(FEATURE_COLUMNS[feature_id])
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate effective feature column")
    return columns


def _matrix(rows: list[dict[str, Any]], columns: list[str]) -> np.ndarray:
    result = np.asarray([[float(row[column]) for column in columns] for row in rows])
    if result.ndim != 2 or result.shape != (len(rows), len(columns)):
        raise ValueError("Unexpected feature matrix shape")
    if not np.isfinite(result).all():
        raise ValueError("Nonfinite feature value")
    return result


def _scale_fold(
    train: np.ndarray, validation: np.ndarray, columns: list[str]
) -> tuple[np.ndarray, np.ndarray, dict[str, dict[str, float]]]:
    train_scaled = train.copy()
    validation_scaled = validation.copy()
    parameters: dict[str, dict[str, float]] = {}
    for column_index, column in enumerate(columns):
        if column not in CONTINUOUS_COLUMNS:
            continue
        mean = float(np.mean(train[:, column_index]))
        scale = float(np.std(train[:, column_index], ddof=0))
        if not math.isfinite(mean) or not math.isfinite(scale):
            raise ValueError("Nonfinite preprocessing statistic")
        if scale == 0.0:
            scale = 1.0
        train_scaled[:, column_index] = (train[:, column_index] - mean) / scale
        validation_scaled[:, column_index] = (
            validation[:, column_index] - mean
        ) / scale
        parameters[column] = {"mean": mean, "scale": scale}
    return train_scaled, validation_scaled, parameters


def cross_fit(
    rows: list[dict[str, Any]],
    method_features: dict[str, list[str]],
    logistic_parameters: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fit only on four folds and score the fifth; return one OOF row per claim."""
    if len(rows) != len({int(row["claim_id"]) for row in rows}):
        raise ValueError("Cross-fitting rows must have unique claim IDs")
    folds = sorted({str(row["fold"]) for row in rows})
    if len(folds) != 5:
        raise ValueError("Exactly five folds are required")

    scores: dict[int, dict[str, Any]] = {}
    for row in rows:
        claim_id = int(row["claim_id"])
        f1 = float(row["F1_decision_confidence"])
        scores[claim_id] = dict(row)
        scores[claim_id]["risk_B0"] = 1.0 - f1

    model_records: list[dict[str, Any]] = []
    for fold in folds:
        training = [row for row in rows if row["fold"] != fold]
        validation = [row for row in rows if row["fold"] == fold]
        train_groups = {int(row["group_id"]) for row in training}
        validation_groups = {int(row["group_id"]) for row in validation}
        if train_groups & validation_groups:
            raise ValueError(f"Group leakage in {fold}")
        y_train = np.asarray([int(row["y_error"]) for row in training], dtype=int)
        if set(y_train.tolist()) != {0, 1}:
            raise ValueError(f"Both risk classes are required in {fold} training")

        for method in LEARNED_METHODS:
            if method not in method_features:
                raise ValueError(f"Missing method specification: {method}")
            columns = method_columns(method_features[method])
            train_matrix = _matrix(training, columns)
            validation_matrix = _matrix(validation, columns)
            train_scaled, validation_scaled, scaler = _scale_fold(
                train_matrix, validation_matrix, columns
            )
            model = LogisticRegression(**logistic_parameters)
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                model.fit(train_scaled, y_train)
            convergence_messages = [
                str(item.message)
                for item in captured
                if issubclass(item.category, ConvergenceWarning)
            ]
            if convergence_messages or int(model.n_iter_[0]) >= int(
                logistic_parameters["max_iter"]
            ):
                raise RuntimeError(
                    f"{method} failed to converge in {fold}: {convergence_messages}"
                )
            classes = model.classes_.tolist()
            if classes != [0, 1]:
                raise RuntimeError(f"Unexpected target classes in {method}/{fold}: {classes}")
            risks = model.predict_proba(validation_scaled)[:, classes.index(1)]
            if not np.isfinite(risks).all() or np.any(risks < 0) or np.any(risks > 1):
                raise RuntimeError("Invalid predicted risk")
            for row, risk in zip(validation, risks):
                claim_id = int(row["claim_id"])
                output_name = f"risk_{method}"
                if output_name in scores[claim_id]:
                    raise RuntimeError("Duplicate out-of-fold risk score")
                scores[claim_id][output_name] = float(risk)

            record = {
                "method": method,
                "held_out_fold": fold,
                "training_claims": len(training),
                "training_errors": int(y_train.sum()),
                "validation_claims": len(validation),
                "feature_ids": method_features[method],
                "effective_columns": columns,
                "scaler": scaler,
                "coefficients": {
                    column: float(value)
                    for column, value in zip(columns, model.coef_[0])
                },
                "intercept": float(model.intercept_[0]),
                "classes": classes,
                "iterations": int(model.n_iter_[0]),
                "converged": True,
                "warnings": [str(item.message) for item in captured],
            }
            record["model_metadata_sha256"] = canonical_sha256(record)
            model_records.append(record)

    expected_risks = {f"risk_{method}" for method in ("B0",) + LEARNED_METHODS}
    for result in scores.values():
        present = {key for key in result if key.startswith("risk_")}
        if present != expected_risks:
            raise RuntimeError(f"Incomplete OOF scores for claim {result['claim_id']}")
    return [scores[key] for key in sorted(scores)], model_records


def ranking_order(rows: list[dict[str, Any]], risk_column: str) -> list[int]:
    if not rows:
        raise ValueError("Cannot rank empty rows")
    ids = [int(row["claim_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Main evaluation requires unique claims")
    risks = [float(row[risk_column]) for row in rows]
    if not all(math.isfinite(value) for value in risks):
        raise ValueError("Risk must be finite")
    return sorted(
        range(len(rows)), key=lambda i: (risks[i], tie_key(ids[i]), ids[i])
    )


def metric_from_order(
    y_error: list[int], order: list[int], coverage: float = 0.8
) -> dict[str, float | int]:
    if not y_error or sorted(order) != list(range(len(y_error))):
        raise ValueError("Order must be a non-empty permutation")
    cumulative = 0
    prefix_risks: list[float] = []
    k80 = fixed_coverage_count(len(y_error), coverage)
    errors80 = 0
    for accepted, index in enumerate(order, 1):
        value = int(y_error[index])
        if value not in (0, 1):
            raise ValueError("y_error must be binary")
        cumulative += value
        prefix_risks.append(cumulative / accepted)
        if accepted == k80:
            errors80 = cumulative
    return {
        "n": len(y_error),
        "aurc": float(np.mean(prefix_risks)),
        "k80": k80,
        "errors_at_80": errors80,
        "sr80": errors80 / k80,
    }


def safe_auroc(y_error: list[int], risks: list[float]) -> float | None:
    if len(y_error) != len(risks) or not y_error:
        raise ValueError("AUROC inputs must be non-empty and aligned")
    if set(y_error) - {0, 1}:
        raise ValueError("y_error must be binary")
    if len(set(y_error)) < 2:
        return None
    return float(roc_auc_score(y_error, risks))


def evaluate_method(
    rows: list[dict[str, Any]], method: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    risk_column = f"risk_{method}"
    order = ranking_order(rows, risk_column)
    y_error = [int(row["y_error"]) for row in rows]
    metrics = dict(metric_from_order(y_error, order))
    risks = [float(row[risk_column]) for row in rows]
    metrics.update(
        {
            "method": method,
            "error_detection_auroc": safe_auroc(y_error, risks),
        }
    )
    accepted_indices = set(order[: int(metrics["k80"])])
    for label in ("SUPPORT", "CONTRADICT"):
        label_indices = {
            index for index, row in enumerate(rows) if row["gold_label"] == label
        }
        accepted = label_indices & accepted_indices
        accepted_errors = sum(y_error[index] for index in accepted)
        prefix = label.lower()
        metrics[f"{prefix}_total"] = len(label_indices)
        metrics[f"{prefix}_accepted"] = len(accepted)
        metrics[f"{prefix}_coverage"] = len(accepted) / len(label_indices)
        metrics[f"{prefix}_accepted_errors"] = accepted_errors
        metrics[f"{prefix}_selective_risk"] = (
            accepted_errors / len(accepted) if accepted else None
        )

    counts = collections.Counter(risks)
    tied = [count for count in counts.values() if count > 1]
    metrics["tie_block_count"] = len(tied)
    metrics["largest_tie_block"] = max(tied, default=1)
    boundary_risk = risks[order[int(metrics["k80"]) - 1]]
    block = [i for i, risk in enumerate(risks) if risk == boundary_risk]
    before = [i for i in order if risks[i] < boundary_risk]
    slots = int(metrics["k80"]) - len(before)
    block_errors = sum(y_error[i] for i in block)
    block_correct = len(block) - block_errors
    before_errors = sum(y_error[i] for i in before)
    best_additional = max(0, slots - block_correct)
    worst_additional = min(slots, block_errors)
    metrics["sr80_tie_best"] = (before_errors + best_additional) / int(metrics["k80"])
    metrics["sr80_tie_worst"] = (before_errors + worst_additional) / int(metrics["k80"])

    curve: list[dict[str, Any]] = []
    cumulative = 0
    for accepted, index in enumerate(order, 1):
        cumulative += y_error[index]
        curve.append(
            {
                "method": method,
                "accepted": accepted,
                "coverage": accepted / len(rows),
                "accepted_errors": cumulative,
                "selective_risk": cumulative / accepted,
            }
        )
    return metrics, curve


def bootstrap_paired(
    rows: list[dict[str, Any]],
    methods: tuple[str, ...] = PRIMARY_METHODS,
    replicates: int = 10_000,
    seed: int = 20261016,
) -> list[dict[str, Any]]:
    groups: dict[int, list[int]] = collections.defaultdict(list)
    for index, row in enumerate(rows):
        groups[int(row["group_id"])].append(index)
    group_ids = sorted(groups)
    if len(group_ids) != 243:
        raise ValueError(f"Expected 243 eligible groups, found {len(group_ids)}")
    rng = np.random.default_rng(seed)
    tie_keys = [tie_key(int(row["claim_id"])) for row in rows]
    output: list[dict[str, Any]] = []
    for replicate in range(replicates):
        draws = rng.integers(0, len(group_ids), size=len(group_ids))
        sampled_indices: list[int] = []
        for draw in draws:
            sampled_indices.extend(groups[group_ids[int(draw)]])
        sampled_y = [int(rows[index]["y_error"]) for index in sampled_indices]
        record: dict[str, Any] = {
            "replicate": replicate,
            "n_claims": len(sampled_indices),
            "k80": fixed_coverage_count(len(sampled_indices)),
            "distinct_groups_drawn": len(set(int(value) for value in draws)),
        }
        for method in methods:
            risk_column = f"risk_{method}"
            order = sorted(
                range(len(sampled_indices)),
                key=lambda position: (
                    float(rows[sampled_indices[position]][risk_column]),
                    tie_keys[sampled_indices[position]],
                    position,
                ),
            )
            values = metric_from_order(sampled_y, order)
            record[f"aurc_{method}"] = values["aurc"]
            record[f"sr80_{method}"] = values["sr80"]
            risks = [float(rows[index][risk_column]) for index in sampled_indices]
            record[f"auroc_{method}"] = safe_auroc(sampled_y, risks)
        record["delta_aurc_EARS_minus_B1"] = (
            record["aurc_EARS"] - record["aurc_B1"]
        )
        record["delta_sr80_EARS_minus_B1"] = (
            record["sr80_EARS"] - record["sr80_B1"]
        )
        output.append(record)
    return output


def percentile_interval(values: Iterable[float]) -> tuple[float, float]:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        raise ValueError("No valid bootstrap values")
    lower, upper = np.percentile(array, [2.5, 97.5], method="linear")
    return float(lower), float(upper)
