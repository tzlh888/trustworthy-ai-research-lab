#!/usr/bin/env python3
"""Fit-only Phase 2A consistency/leakage audit. This script never trains a model."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from trustworthy_ai_lab.data import load_selected_claims
from trustworthy_ai_lab.phase2_protocol import extract_features, risk_target


PREDICTIONS = ("SUPPORT", "CONTRADICT", "NO_RELATION")
GOLD = ("SUPPORT", "CONTRADICT")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def normalize_claim(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def connected_group_lookup(claims: list[dict[str, Any]]) -> dict[int, int]:
    parent = {row["id"]: row["id"] for row in claims}

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
        for doc_id in row["cited_doc_ids"]:
            buckets[("cited_doc", doc_id)].append(row["id"])
        buckets[("claim_text", normalize_claim(row["claim"]))].append(row["id"])
    for members in buckets.values():
        anchor = min(members)
        for member in members:
            union(anchor, member)
    components: dict[int, list[int]] = collections.defaultdict(list)
    for claim_id in parent:
        components[find(claim_id)].append(claim_id)
    return {
        claim_id: min(members)
        for members in components.values()
        for claim_id in members
    }


def classification_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    matrix = {gold: {prediction: 0 for prediction in PREDICTIONS} for gold in GOLD}
    for row in rows:
        matrix[row["gold_evidence_label"]][row["predicted_claim_label"]] += 1
    per_label = {}
    f1s = []
    for label in GOLD:
        tp = matrix[label][label]
        fp = sum(matrix[other][label] for other in GOLD if other != label)
        fn = sum(matrix[label][prediction] for prediction in PREDICTIONS if prediction != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1s.append(f1)
        per_label[label] = {"precision": precision, "recall": recall, "f1": f1}
    correct = sum(matrix[label][label] for label in GOLD)
    counts = collections.Counter(row["gold_evidence_label"] for row in rows)
    majority = max(GOLD, key=lambda label: counts[label])
    majority_accuracy = counts[majority] / len(rows)
    majority_f1 = 2 * majority_accuracy / (1 + majority_accuracy)
    return {
        "confusion_matrix": matrix,
        "eligible_count": len(rows),
        "correct_count": correct,
        "error_count": len(rows) - correct,
        "accuracy": correct / len(rows),
        "macro_f1": sum(f1s) / len(f1s),
        "per_label": per_label,
        "majority_class_baseline": {
            "predicted_label": majority,
            "accuracy": majority_accuracy,
            "macro_f1": majority_f1 / 2,
        },
    }


def pearson(left: list[float], right: list[float]) -> float | None:
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_ss = sum((x - left_mean) ** 2 for x in left)
    right_ss = sum((y - right_mean) ** 2 for y in right)
    if left_ss == 0 or right_ss == 0:
        return None
    return numerator / math.sqrt(left_ss * right_ss)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root

    frozen = json.loads((root / "configs/phase2a_frozen_artifacts_v1.json").read_text())
    mismatches = {}
    for relative, expected in frozen["sha256"].items():
        actual = sha256(root / relative)
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        raise RuntimeError(f"Frozen artifact mismatch: {mismatches}")

    manifest = json.loads((root / "splits/train_split_manifest.json").read_text())
    fit_ids = set(manifest["outer_splits"]["fit"]["claim_ids"])
    sealed_ids = set(manifest["outer_splits"]["calibration"]["claim_ids"]) | set(
        manifest["outer_splits"]["internal_test"]["claim_ids"]
    )
    claims = load_selected_claims(root / "data/raw/scifact/claims_train.jsonl", fit_ids)
    fold_by_id = {
        claim_id: fold_name
        for fold_name, fold in manifest["crossfit_validation_folds_within_fit"].items()
        for claim_id in fold["claim_ids"]
    }
    if set(fold_by_id) != fit_ids or fit_ids & sealed_ids:
        raise RuntimeError("Frozen fold partition is invalid")

    fold_leakage = {}
    for left_index, left in enumerate(sorted(set(fold_by_id.values()))):
        left_rows = [row for row in claims if fold_by_id[row["id"]] == left]
        left_docs = {doc for row in left_rows for doc in row["cited_doc_ids"]}
        left_texts = {normalize_claim(row["claim"]) for row in left_rows}
        for right in sorted(set(fold_by_id.values()))[left_index + 1 :]:
            right_rows = [row for row in claims if fold_by_id[row["id"]] == right]
            right_docs = {doc for row in right_rows for doc in row["cited_doc_ids"]}
            right_texts = {normalize_claim(row["claim"]) for row in right_rows}
            fold_leakage[f"{left}__{right}"] = {
                "shared_cited_doc_count": len(left_docs & right_docs),
                "shared_normalized_claim_count": len(left_texts & right_texts),
            }

    all_predictions = read_jsonl(root / "reports/phase1/e1_fit_predictions.jsonl")
    if {row["claim_id"] for row in all_predictions} != fit_ids:
        raise RuntimeError("Frozen E1 predictions are not exactly fit")
    if {row["claim_id"] for row in all_predictions} & sealed_ids:
        raise RuntimeError("Sealed ID found in E1 predictions")
    eligible = [row for row in all_predictions if row["evaluation_eligible"]]
    if len(eligible) != 329 or len({row["claim_id"] for row in eligible}) != 329:
        raise RuntimeError("Risk target is not one row per eligible claim")
    group_by_id = connected_group_lookup(claims)
    eligible_group_sizes = collections.Counter(
        group_by_id[row["claim_id"]] for row in eligible
    )

    retrieval = {
        row["claim_id"]: row
        for row in read_jsonl(root / "reports/phase1/fit_retrieval_results.jsonl")
    }
    feature_rows = {
        row["claim_id"]: extract_features(row, retrieval[row["claim_id"]])
        for row in eligible
    }
    feature_names = list(next(iter(feature_rows.values())))
    feature_summary = {}
    for name in feature_names:
        values = [feature_rows[claim_id][name] for claim_id in sorted(feature_rows)]
        feature_summary[name] = {
            "count": len(values),
            "missing_or_nonfinite": sum(not math.isfinite(value) for value in values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
        }
    correlations = {}
    continuous = [name for name in feature_names if not name.startswith("F3_")]
    for index, left in enumerate(continuous):
        for right in continuous[index + 1 :]:
            correlations[f"{left}__{right}"] = pearson(
                [feature_rows[cid][left] for cid in sorted(feature_rows)],
                [feature_rows[cid][right] for cid in sorted(feature_rows)],
            )

    fold_target_counts = {}
    for fold in sorted(set(fold_by_id.values())):
        validation = [row for row in eligible if fold_by_id[row["claim_id"]] == fold]
        validation_errors = sum(risk_target(row) for row in validation)
        fold_target_counts[fold] = {
            "validation_claims": len(validation),
            "validation_errors": validation_errors,
            "validation_correct": len(validation) - validation_errors,
            "training_claims": len(eligible) - len(validation),
            "training_errors": sum(risk_target(row) for row in eligible) - validation_errors,
        }

    primary = collections.Counter()
    nonexclusive = collections.Counter()
    for row in eligible:
        if risk_target(row):
            stage = [
                category
                for category in row["failure_categories"]
                if category
                in ("retrieval_failure", "sentence_selection_failure", "nli_or_reasoning_failure")
            ]
            if len(stage) != 1:
                raise RuntimeError(f"Invalid primary failure attribution: {row['claim_id']}")
            primary.update(stage)
            nonexclusive.update(row["failure_categories"])

    result = {
        "protocol_version": frozen["protocol_version"],
        "scope": "fit-only Phase 2A audit; no risk model trained and no risk-ranking metric computed",
        "frozen_artifact_mismatches": mismatches,
        "sealed_ids_in_predictions": [],
        "classification_recalculation": classification_audit(eligible),
        "risk_target": {
            "eligible_claims": len(eligible),
            "unique_claims": len({row["claim_id"] for row in eligible}),
            "errors": sum(risk_target(row) for row in eligible),
            "correct": sum(1 - risk_target(row) for row in eligible),
            "fold_counts": fold_target_counts,
        },
        "failure_categories": {
            "primary_mutually_exclusive": dict(sorted(primary.items())),
            "nonexclusive": dict(sorted(nonexclusive.items())),
        },
        "fold_leakage_pairs": fold_leakage,
        "bootstrap_groups": {
            "construction_population": "all 527 fit claims before eligible filtering",
            "fit_group_count": len(set(group_by_id.values())),
            "eligible_claim_group_count": len(eligible_group_sizes),
            "largest_eligible_claims_in_one_group": max(eligible_group_sizes.values()),
            "group_id_rule": "minimum claim ID in cited-document/normalized-text connected component"
        },
        "feature_extractability": feature_summary,
        "label_free_feature_correlations": correlations,
        "performance_metrics_intentionally_not_computed": [
            "B0 AURC",
            "B1 AURC",
            "B2 AURC",
            "EARS AURC",
            "selective risk at 80% coverage",
            "error-detection AUROC"
        ]
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
