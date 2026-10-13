from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression

from .aggregation import aggregate_claim
from .data import derived_evidence_label
from .phase2_protocol import extract_features, fixed_coverage_count, tie_key
from .phase2b import (
    CONTINUOUS_COLUMNS,
    FEATURE_COLUMNS,
    connected_group_lookup,
    evaluate_method,
    method_columns,
    percentile_interval,
    safe_auroc,
)


FORMAL_METHODS = ("B0", "B1", "B2", "EARS")
LEARNED_METHODS = ("B1", "B2", "EARS")
METHOD_FEATURES = {
    "B0": ["F1"],
    "B1": ["F1", "F2", "F3"],
    "B2": ["F4", "F5"],
    "EARS": ["F1", "F2", "F3", "F4", "F5"],
}
LOGISTIC_PARAMETERS = {
    "penalty": "l2",
    "C": 0.1,
    "solver": "lbfgs",
    "class_weight": None,
    "fit_intercept": True,
    "max_iter": 2000,
    "tol": 1e-6,
    "random_state": 20261014,
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class FrozenPreprocessor:
    columns: list[str]
    means: list[float]
    scales: list[float]
    standardized: list[bool]

    @classmethod
    def fit(cls, rows: list[dict[str, Any]], columns: list[str]) -> "FrozenPreprocessor":
        matrix = np.asarray([[float(row[column]) for column in columns] for row in rows])
        if matrix.shape != (len(rows), len(columns)) or not np.isfinite(matrix).all():
            raise ValueError("Invalid final-training feature matrix")
        means, scales, standardized = [], [], []
        for index, column in enumerate(columns):
            is_continuous = column in CONTINUOUS_COLUMNS
            standardized.append(is_continuous)
            if is_continuous:
                mean = float(np.mean(matrix[:, index]))
                scale = float(np.std(matrix[:, index], ddof=0))
                if scale == 0.0:
                    scale = 1.0
            else:
                mean, scale = 0.0, 1.0
            means.append(mean)
            scales.append(scale)
        return cls(list(columns), means, scales, standardized)

    def transform(self, rows: list[dict[str, Any]]) -> np.ndarray:
        matrix = np.asarray(
            [[float(row[column]) for column in self.columns] for row in rows], dtype=float
        )
        if matrix.shape != (len(rows), len(self.columns)) or not np.isfinite(matrix).all():
            raise ValueError("Invalid scoring feature matrix")
        output = matrix.copy()
        for index, use_scaler in enumerate(self.standardized):
            if use_scaler:
                output[:, index] = (output[:, index] - self.means[index]) / self.scales[index]
        return output

    def as_dict(self) -> dict[str, Any]:
        return {
            "columns": self.columns,
            "means": self.means,
            "scales": self.scales,
            "standardized": self.standardized,
        }


def fit_final_models(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if len(rows) != 329 or len({int(row["claim_id"]) for row in rows}) != 329:
        raise ValueError("Final fit requires exactly 329 unique eligible fit claims")
    y = np.asarray([int(row["y_error"]) for row in rows], dtype=int)
    if int(y.sum()) != 175 or set(y.tolist()) != {0, 1}:
        raise ValueError("Frozen final-training target changed")
    bundles: dict[str, dict[str, Any]] = {}
    numeric: dict[str, Any] = {
        "schema_version": 1,
        "training_claims": len(rows),
        "training_errors": int(y.sum()),
        "methods": {},
    }
    for method in LEARNED_METHODS:
        columns = method_columns(METHOD_FEATURES[method])
        preprocessor = FrozenPreprocessor.fit(rows, columns)
        matrix = preprocessor.transform(rows)
        model = LogisticRegression(**LOGISTIC_PARAMETERS)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            model.fit(matrix, y)
        convergence = [
            str(item.message)
            for item in captured
            if issubclass(item.category, ConvergenceWarning)
        ]
        if convergence or int(model.n_iter_[0]) >= LOGISTIC_PARAMETERS["max_iter"]:
            raise RuntimeError(f"Final {method} did not converge: {convergence}")
        if model.classes_.tolist() != [0, 1]:
            raise RuntimeError(f"Unexpected classes for {method}: {model.classes_.tolist()}")
        bundles[method] = {
            "method": method,
            "feature_ids": METHOD_FEATURES[method],
            "preprocessor": preprocessor,
            "model": model,
        }
        numeric["methods"][method] = {
            "feature_ids": METHOD_FEATURES[method],
            "preprocessor": preprocessor.as_dict(),
            "coefficients": [float(value) for value in model.coef_[0]],
            "intercept": float(model.intercept_[0]),
            "classes": model.classes_.tolist(),
            "iterations": int(model.n_iter_[0]),
            "converged": True,
            "warnings": [str(item.message) for item in captured],
        }
    return bundles, numeric


def score_bundle(bundle: dict[str, Any], rows: list[dict[str, Any]]) -> list[float]:
    matrix = bundle["preprocessor"].transform(rows)
    model = bundle["model"]
    classes = model.classes_.tolist()
    if classes != [0, 1]:
        raise ValueError("Unexpected serialized model class order")
    risks = model.predict_proba(matrix)[:, 1]
    if not np.isfinite(risks).all():
        raise ValueError("Nonfinite serialized-model risk")
    return [float(value) for value in risks]


def _sigmoid(values: np.ndarray) -> np.ndarray:
    output = np.empty_like(values, dtype=float)
    positive = values >= 0
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[~positive])
    output[~positive] = exp_values / (1.0 + exp_values)
    return output


def score_numeric_spec(
    method_spec: dict[str, Any], rows: list[dict[str, Any]]
) -> list[float]:
    prep = method_spec["preprocessor"]
    columns = prep["columns"]
    matrix = np.asarray([[float(row[column]) for column in columns] for row in rows])
    for index, use_scaler in enumerate(prep["standardized"]):
        if use_scaler:
            matrix[:, index] = (
                matrix[:, index] - float(prep["means"][index])
            ) / float(prep["scales"][index])
    coefficients = np.asarray(method_spec["coefficients"], dtype=float)
    logits = matrix @ coefficients + float(method_spec["intercept"])
    risks = _sigmoid(logits)
    if not np.isfinite(risks).all():
        raise ValueError("Nonfinite numeric-spec risk")
    return [float(value) for value in risks]


def extract_fit_rows(
    predictions: list[dict[str, Any]], retrieval_by_id: dict[int, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for prediction in predictions:
        if not prediction["evaluation_eligible"]:
            continue
        claim_id = int(prediction["claim_id"])
        expected = int(
            prediction["predicted_claim_label"] != prediction["gold_evidence_label"]
        )
        if expected != int(not bool(prediction["correct"])):
            raise ValueError(f"Frozen target mismatch for {claim_id}")
        rows.append(
            {
                "claim_id": claim_id,
                "y_error": expected,
                **extract_features(prediction, retrieval_by_id[claim_id]),
            }
        )
    return sorted(rows, key=lambda row: row["claim_id"])


ID_PATTERN = re.compile(r'"id"\s*:\s*(\d+)')
CLAIM_KEY_PATTERN = re.compile(r'"claim"\s*:')


def load_claim_texts_only(path: Path, allowed_ids: set[int]) -> list[dict[str, Any]]:
    """Load IDs and claim strings without deserializing the evidence field."""
    decoder = json.JSONDecoder()
    selected, seen = [], set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            id_match = ID_PATTERN.search(line[:120])
            if id_match is None:
                raise ValueError(f"Missing claim ID at line {line_number}")
            claim_id = int(id_match.group(1))
            if claim_id not in allowed_ids:
                continue
            claim_match = CLAIM_KEY_PATTERN.search(line)
            if claim_match is None:
                raise ValueError(f"Missing claim text at line {line_number}")
            text, _ = decoder.raw_decode(line[claim_match.end() :].lstrip())
            if not isinstance(text, str):
                raise ValueError("Claim is not a JSON string")
            selected.append({"id": claim_id, "claim": text})
            seen.add(claim_id)
    if seen != allowed_ids or len(selected) != len(allowed_ids):
        raise ValueError("Label-blind loader did not return exactly the allowed IDs")
    return sorted(selected, key=lambda row: row["id"])


def build_blind_retrieval_records(
    claims: list[dict[str, Any]], retriever: Any, selector: Any, *, top_k: int, top_sentences: int
) -> list[dict[str, Any]]:
    records = []
    for claim in claims:
        documents = retriever.retrieve(claim["claim"], top_k=top_k)
        for document in documents:
            document["selected_sentences"] = selector.select(
                claim["claim"], document, top_n=top_sentences
            )
        records.append(
            {
                "claim_id": claim["id"],
                "claim_text": claim["claim"],
                "partition": "internal_test",
                "retrieved_documents": documents,
            }
        )
    return records


def finalize_e1_blind(
    retrieval_records: list[dict[str, Any]], pair_predictions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_claim: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in pair_predictions:
        by_claim[int(row["claim_id"])].append(row)
    output = []
    for retrieval in retrieval_records:
        claim_id = int(retrieval["claim_id"])
        sentence_predictions = sorted(
            by_claim[claim_id],
            key=lambda row: (
                row["doc_rank"],
                row["selected_sentence_rank"],
                row["sentence_index"],
            ),
        )
        if len(sentence_predictions) != 15:
            raise ValueError(f"Expected 15 E1 pairs for claim {claim_id}")
        output.append(
            {
                "claim_id": claim_id,
                "claim_text": retrieval["claim_text"],
                "partition": "internal_test",
                **aggregate_claim(sentence_predictions),
                "sentence_predictions": sentence_predictions,
            }
        )
    return output


def build_labeled_retrieval(
    blind_retrieval: list[dict[str, Any]], claims: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    claim_by_id = {int(row["id"]): row for row in claims}
    output = []
    for blind in blind_retrieval:
        claim = claim_by_id[int(blind["claim_id"])]
        gold_label = derived_evidence_label(claim)
        output.append(
            {
                **blind,
                "fit_fold": "internal_test",
                "annotation_state": "EVIDENCE_ANNOTATED" if gold_label else "NO_ANNOTATED_EVIDENCE",
                "evaluation_eligible": gold_label is not None,
                "gold_evidence_label": gold_label,
                "gold_evidence_doc_ids": sorted(int(key) for key in claim["evidence"]),
                "gold_evidence": claim["evidence"],
            }
        )
    return output


def bootstrap_paired_dynamic(
    rows: list[dict[str, Any]], replicates: int = 10_000, seed: int = 20261016
) -> list[dict[str, Any]]:
    groups: dict[int, list[int]] = collections.defaultdict(list)
    for index, row in enumerate(rows):
        groups[int(row["group_id"])].append(index)
    group_ids = sorted(groups)
    if not group_ids:
        raise ValueError("No eligible bootstrap groups")
    rng = np.random.default_rng(seed)
    tie_keys = [tie_key(int(row["claim_id"])) for row in rows]
    output = []
    for replicate in range(replicates):
        draws = rng.integers(0, len(group_ids), size=len(group_ids))
        sampled = []
        for draw in draws:
            sampled.extend(groups[group_ids[int(draw)]])
        y = [int(rows[index]["y_error"]) for index in sampled]
        record: dict[str, Any] = {
            "replicate": replicate,
            "n_claims": len(sampled),
            "k80": fixed_coverage_count(len(sampled)),
            "group_draws": len(group_ids),
            "distinct_groups_drawn": len(set(int(value) for value in draws)),
        }
        for method in FORMAL_METHODS:
            risks = [float(rows[index][f"risk_{method}"]) for index in sampled]
            order = sorted(
                range(len(sampled)),
                key=lambda position: (
                    risks[position], tie_keys[sampled[position]], position
                ),
            )
            cumulative = 0
            prefixes = []
            k80 = record["k80"]
            errors80 = None
            for accepted, position in enumerate(order, 1):
                cumulative += y[position]
                prefixes.append(cumulative / accepted)
                if accepted == k80:
                    errors80 = cumulative
            record[f"aurc_{method}"] = float(np.mean(prefixes))
            record[f"sr80_{method}"] = int(errors80) / int(k80)
            record[f"auroc_{method}"] = safe_auroc(y, risks)
        record["delta_aurc_EARS_minus_B1"] = record["aurc_EARS"] - record["aurc_B1"]
        record["delta_sr80_EARS_minus_B1"] = record["sr80_EARS"] - record["sr80_B1"]
        output.append(record)
    return output


def summarize_bootstrap(
    replicates: list[dict[str, Any]], metrics: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    mapping = {"aurc": "aurc", "sr80": "sr80", "auroc": "error_detection_auroc"}
    for method in FORMAL_METHODS:
        for boot_name, point_name in mapping.items():
            values = [row[f"{boot_name}_{method}"] for row in replicates]
            valid = [float(value) for value in values if value is not None]
            lower, upper = percentile_interval(valid)
            output.append(
                {
                    "estimand": f"{boot_name}_{method}", "kind": "method",
                    "method_or_contrast": method, "metric": boot_name,
                    "point_estimate": metrics[method][point_name],
                    "ci_lower_95": lower, "ci_upper_95": upper,
                    "valid_replicates": len(valid),
                    "invalid_replicates": len(values) - len(valid),
                }
            )
    for name, point, metric_name in (
        ("delta_aurc_EARS_minus_B1", metrics["EARS"]["aurc"] - metrics["B1"]["aurc"], "aurc"),
        ("delta_sr80_EARS_minus_B1", metrics["EARS"]["sr80"] - metrics["B1"]["sr80"], "sr80"),
    ):
        values = [float(row[name]) for row in replicates]
        lower, upper = percentile_interval(values)
        output.append(
            {
                "estimand": name, "kind": "paired_contrast",
                "method_or_contrast": "EARS_minus_B1", "metric": metric_name,
                "point_estimate": point, "ci_lower_95": lower, "ci_upper_95": upper,
                "valid_replicates": len(values), "invalid_replicates": 0,
            }
        )
    return output


def risk_distribution(values: Iterable[float]) -> dict[str, float | int]:
    array = np.asarray(list(values), dtype=float)
    if array.size == 0:
        return {"count": 0}
    return {
        "count": int(array.size), "minimum": float(np.min(array)),
        "q25": float(np.percentile(array, 25, method="linear")),
        "median": float(np.median(array)), "mean": float(np.mean(array)),
        "q75": float(np.percentile(array, 75, method="linear")),
        "maximum": float(np.max(array)),
    }
