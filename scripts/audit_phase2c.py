#!/usr/bin/env python3
"""Read-only Phase 2C structural diagnostics from frozen Phase 2B OOF scores."""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from trustworthy_ai_lab.phase2b import ranking_order, safe_auroc


LABELS = ("SUPPORT", "CONTRADICT", "NO_RELATION")
METHODS = ("B1", "EARS")
CSV_FIELDS = (
    "scope",
    "fold",
    "predicted_label",
    "claims",
    "errors",
    "correct",
    "error_rate",
    "b1_mean_risk_correct",
    "b1_mean_risk_error",
    "b1_within_label_auroc",
    "ears_mean_risk_correct",
    "ears_mean_risk_error",
    "ears_within_label_auroc",
    "b1_accepted_at_global80",
    "b1_rejected_at_global80",
    "b1_accepted_errors_at_global80",
    "b1_rejected_errors_at_global80",
    "ears_accepted_at_global80",
    "ears_rejected_at_global80",
    "ears_accepted_errors_at_global80",
    "ears_rejected_errors_at_global80",
    "delta_accepted_errors_ears_minus_b1",
)


def load_oof(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    converted: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = dict(row)
        item["claim_id"] = int(row["claim_id"])
        item["group_id"] = int(row["group_id"])
        item["y_error"] = int(row["y_error"])
        for method in METHODS:
            item[f"risk_{method}"] = float(row[f"risk_{method}"])
        converted.append(item)
    if len(converted) != 329 or len({row["claim_id"] for row in converted}) != 329:
        raise ValueError("Frozen OOF population must contain 329 unique claims")
    if {row["gold_label"] for row in converted} != {"SUPPORT", "CONTRADICT"}:
        raise ValueError("Eligible gold-label space changed")
    if sum(row["y_error"] for row in converted) != 175:
        raise ValueError("Frozen error count changed")
    return converted


def accepted_claim_ids(rows: list[dict[str, Any]], method: str) -> set[int]:
    order = ranking_order(rows, f"risk_{method}")
    return {int(rows[index]["claim_id"]) for index in order[:263]}


def optional_stat(values: list[float], fn: Any) -> str:
    return "" if not values else repr(float(fn(values)))


def label_row(
    selected: list[dict[str, Any]],
    scope: str,
    fold: str,
    accepted: dict[str, set[int]],
) -> dict[str, Any]:
    if not selected:
        raise ValueError("Empty label stratum")
    result: dict[str, Any] = {
        "scope": scope,
        "fold": fold,
        "predicted_label": selected[0]["predicted_label"],
        "claims": len(selected),
        "errors": sum(row["y_error"] for row in selected),
    }
    result["correct"] = result["claims"] - result["errors"]
    result["error_rate"] = repr(result["errors"] / result["claims"])
    for method, prefix in (("B1", "b1"), ("EARS", "ears")):
        correct_risks = [row[f"risk_{method}"] for row in selected if not row["y_error"]]
        error_risks = [row[f"risk_{method}"] for row in selected if row["y_error"]]
        result[f"{prefix}_mean_risk_correct"] = optional_stat(correct_risks, mean)
        result[f"{prefix}_mean_risk_error"] = optional_stat(error_risks, mean)
        auroc = safe_auroc(
            [row["y_error"] for row in selected],
            [row[f"risk_{method}"] for row in selected],
        )
        result[f"{prefix}_within_label_auroc"] = "" if auroc is None else repr(auroc)
        accepted_rows = [row for row in selected if row["claim_id"] in accepted[method]]
        rejected_rows = [row for row in selected if row["claim_id"] not in accepted[method]]
        result[f"{prefix}_accepted_at_global80"] = len(accepted_rows)
        result[f"{prefix}_rejected_at_global80"] = len(rejected_rows)
        result[f"{prefix}_accepted_errors_at_global80"] = sum(
            row["y_error"] for row in accepted_rows
        )
        result[f"{prefix}_rejected_errors_at_global80"] = sum(
            row["y_error"] for row in rejected_rows
        )
    result["delta_accepted_errors_ears_minus_b1"] = (
        result["ears_accepted_errors_at_global80"]
        - result["b1_accepted_errors_at_global80"]
    )
    return result


def analyze(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    accepted = {method: accepted_claim_ids(rows, method) for method in METHODS}
    table: list[dict[str, Any]] = []
    for label in LABELS:
        table.append(
            label_row(
                [row for row in rows if row["predicted_label"] == label],
                "overall",
                "ALL",
                accepted,
            )
        )
    for fold in sorted({str(row["fold"]) for row in rows}):
        for label in LABELS:
            table.append(
                label_row(
                    [
                        row
                        for row in rows
                        if row["fold"] == fold and row["predicted_label"] == label
                    ],
                    "fold",
                    fold,
                    accepted,
                )
            )

    no_relation = [row for row in rows if row["predicted_label"] == "NO_RELATION"]
    counterfactual_accepted = [row for row in rows if row["predicted_label"] != "NO_RELATION"]
    summary = {
        "status": "POST-HOC DIAGNOSTIC",
        "eligible_claims": len(rows),
        "errors": sum(row["y_error"] for row in rows),
        "gold_label_counts": dict(Counter(row["gold_label"] for row in rows)),
        "predicted_label_counts": dict(Counter(row["predicted_label"] for row in rows)),
        "no_relation_errors": sum(row["y_error"] for row in no_relation),
        "counterfactual_reject_no_relation": {
            "accepted": len(counterfactual_accepted),
            "accepted_errors": sum(row["y_error"] for row in counterfactual_accepted),
            "empirical_sr80": sum(row["y_error"] for row in counterfactual_accepted)
            / len(counterfactual_accepted),
            "oracle_minimum_errors": 109,
            "oracle_minimum_sr80": 109 / 263,
        },
        "global_80_accepted_errors": {
            method: sum(
                row["y_error"] for row in rows if row["claim_id"] in accepted[method]
            )
            for method in METHODS
        },
    }
    if len(no_relation) != 66 or summary["no_relation_errors"] != 66:
        raise ValueError("Frozen NO_RELATION structure changed")
    if summary["counterfactual_reject_no_relation"]["accepted"] != 263:
        raise ValueError("Counterfactual acceptance count changed")
    if summary["global_80_accepted_errors"] != {"B1": 116, "EARS": 115}:
        raise ValueError("Frozen global SR80 result changed")
    return summary, table


def render_csv(rows: list[dict[str, Any]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--csv", action="store_true", help="print the frozen CSV analysis")
    args = parser.parse_args()
    rows = load_oof(args.root / "reports/phase2b/oof_risk_predictions.csv")
    summary, table = analyze(rows)
    if args.csv:
        print(render_csv(table), end="")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
