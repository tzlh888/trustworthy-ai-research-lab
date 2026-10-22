from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from typing import Any

import numpy as np


def _validate(errors: list[int], risks: list[float], case_ids: list[str]) -> None:
    if not errors or len(errors) != len(risks) or len(errors) != len(case_ids):
        raise ValueError("metric inputs must be non-empty and aligned")
    if set(errors) - {0, 1}:
        raise ValueError("errors must be binary")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("case_ids must be unique")
    if not all(math.isfinite(value) for value in risks):
        raise ValueError("risks must be finite")


def deterministic_order(risks: list[float], case_ids: list[str], *, seed: int = 20261015) -> list[int]:
    if len(risks) != len(case_ids):
        raise ValueError("risks and case_ids must align")
    return sorted(
        range(len(risks)),
        key=lambda index: (
            risks[index],
            hashlib.sha256(f"{seed}:{case_ids[index]}".encode()).hexdigest(),
            case_ids[index],
        ),
    )


def risk_coverage_curve(errors: list[int], risks: list[float], case_ids: list[str]) -> list[dict[str, float | int]]:
    _validate(errors, risks, case_ids)
    order = deterministic_order(risks, case_ids)
    cumulative = 0
    curve: list[dict[str, float | int]] = []
    for accepted, index in enumerate(order, 1):
        cumulative += errors[index]
        curve.append({
            "accepted": accepted, "coverage": accepted / len(errors),
            "accepted_errors": cumulative, "selective_risk": cumulative / accepted,
        })
    return curve


def aurc(errors: list[int], risks: list[float], case_ids: list[str]) -> float:
    curve = risk_coverage_curve(errors, risks, case_ids)
    return sum(float(point["selective_risk"]) for point in curve) / len(curve)


def risk_at_coverage(
    errors: list[int], risks: list[float], case_ids: list[str], *, coverage: float = 0.8
) -> dict[str, float | int]:
    if not 0 < coverage <= 1:
        raise ValueError("coverage must be in (0, 1]")
    curve = risk_coverage_curve(errors, risks, case_ids)
    accepted = math.floor(coverage * len(errors) + 0.5)
    accepted = max(1, accepted)
    point = curve[accepted - 1]
    return {"accepted": accepted, "errors": int(point["accepted_errors"]), "risk": float(point["selective_risk"])}


def auroc(errors: list[int], risks: list[float], case_ids: list[str]) -> float | None:
    _validate(errors, risks, case_ids)
    positives = [risk for error, risk in zip(errors, risks) if error == 1]
    negatives = [risk for error, risk in zip(errors, risks) if error == 0]
    if not positives or not negatives:
        return None
    favorable = sum((positive > negative) + 0.5 * (positive == negative) for positive in positives for negative in negatives)
    return favorable / (len(positives) * len(negatives))


def evaluate_rows(rows: list[dict[str, Any]], risk_key: str) -> dict[str, Any]:
    errors = [int(row["error"]) for row in rows]
    risks = [float(row[risk_key]) for row in rows]
    ids = [str(row["case_id"]) for row in rows]
    r80 = risk_at_coverage(errors, risks, ids)
    return {
        "n": len(rows), "aurc": aurc(errors, risks, ids), "r80": r80["risk"],
        "accepted_at_80": r80["accepted"], "errors_at_80": r80["errors"],
        "error_detection_auroc": auroc(errors, risks, ids),
    }


def grouped_paired_bootstrap(
    rows: list[dict[str, Any]], *, left: str, right: str,
    replicates: int = 2_000, seed: int = 20261022,
) -> dict[str, Any]:
    if not rows or replicates < 1:
        raise ValueError("rows and positive replicates are required")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row["group_id"])].append(row)
    group_ids = sorted(groups)
    rng = np.random.default_rng(seed)
    deltas: dict[str, list[float]] = {"aurc": [], "r80": []}
    for _ in range(replicates):
        sampled: list[dict[str, Any]] = []
        for draw, index in enumerate(rng.integers(0, len(group_ids), size=len(group_ids))):
            for row in groups[group_ids[int(index)]]:
                sampled.append({**row, "case_id": f"{row['case_id']}@bootstrap-{draw}"})
        left_metrics, right_metrics = evaluate_rows(sampled, left), evaluate_rows(sampled, right)
        for metric in deltas:
            deltas[metric].append(left_metrics[metric] - right_metrics[metric])
    return {
        "unit": "group", "paired": True, "replicates": replicates, "seed": seed,
        "intervals": {
            f"delta_{metric}_{left}_minus_{right}": {
                "p2_5": float(np.percentile(values, 2.5)),
                "p50": float(np.percentile(values, 50)),
                "p97_5": float(np.percentile(values, 97.5)),
            }
            for metric, values in deltas.items()
        },
    }
