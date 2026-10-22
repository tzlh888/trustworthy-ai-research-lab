from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any


def analyze_features(rows: list[dict[str, Any]], *, minimum_groups: int = 5) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows must not be empty")
    strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing = {"F4": 0, "F5": 0}
    for row in rows:
        strata[str(row["failure_category"])].append(row)
        for short, key in (("F4", "F4_bm25_top2_normalized_margin"), ("F5", "F5_evidence_conflict_rate")):
            value = row.get(key)
            if value is None or not math.isfinite(float(value)):
                missing[short] += 1

    summaries = []
    for category, subset in sorted(strata.items()):
        groups = {str(row["group_id"]) for row in subset}
        record: dict[str, Any] = {
            "failure_category": category, "n": len(subset), "groups": len(groups),
            "evidence_status": "INSUFFICIENT_STRATUM" if len(groups) < minimum_groups else "EXPLORATORY",
        }
        for short, key in (("F4", "F4_bm25_top2_normalized_margin"), ("F5", "F5_evidence_conflict_rate")):
            values = [float(row[key]) for row in subset if row.get(key) is not None and math.isfinite(float(row[key]))]
            record[f"{short}_mean"] = statistics.mean(values) if values else None
            record[f"{short}_median"] = statistics.median(values) if values else None
        record["mean_EARS_minus_B1_risk"] = statistics.mean(
            float(row["risk_EARS"]) - float(row["risk_B1"]) for row in subset
        )
        summaries.append(record)
    non_neutral_counts = [row.get("non_neutral_evidence_count") for row in rows]
    f5_zero = [row for row in rows if row.get("F5_evidence_conflict_rate") == 0]
    return {
        "status": "POST_HOC_EXPLORATORY",
        "n": len(rows), "groups": len({str(row["group_id"]) for row in rows}),
        "missing": missing,
        "F5_zero_count": len(f5_zero),
        "F5_zero_without_non_neutral_evidence": sum(
            row.get("non_neutral_evidence_count") == 0 for row in f5_zero
        ),
        "F5_zero_ambiguity": "zero can mean no conflict or no non-neutral evidence",
        "strata": summaries,
        "sensitivity_without_disputed_or_outlier": _sensitivity(rows),
    }


def _sensitivity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    included = [row for row in rows if not row.get("annotation_disputed") and not row.get("outlier")]
    return {
        "excluded": len(rows) - len(included),
        "included": len(included),
        "mean_EARS_minus_B1_risk": (
            statistics.mean(float(row["risk_EARS"]) - float(row["risk_B1"]) for row in included)
            if included else None
        ),
    }
