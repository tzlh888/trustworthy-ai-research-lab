#!/usr/bin/env python3
"""Exact Study A+ mathematics and annotation-sensitivity calculations."""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


BOOTSTRAP_SEED = 20261016
BOOTSTRAP_REPLICATES = 10_000
TIE_SEED = 20261015
ELIGIBLE = {"SUPPORT", "CONTRADICT"}
EXPECTED = {
    "claims": "86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217",
    "corpus": "b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62",
    "frozen": "3c1ea9104569f18882881d5ff2861696c06ed723fff208f66fd0e7a60f35c941",
    "corrections": "c45ff40e3a8906192595462596dd56146e476aafa5b39fb3cf5a367b80a62b23",
    "protocol": "70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301",
}


@dataclass(frozen=True)
class Row:
    claim_id: int
    group_id: int
    label: str
    prediction: str
    b1: float
    ears: float

    @property
    def error(self) -> int:
        return int(self.label != self.prediction)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def normalize(text: str) -> str:
    return " ".join(
        "".join(char if char.isalnum() else " " for char in text.casefold()).split()
    )


def derived_label(claim: dict[str, Any]) -> str | None:
    labels = {
        rationale["label"]
        for rationales in claim["evidence"].values()
        for rationale in rationales
    }
    if not labels:
        return None
    if len(labels) != 1:
        raise ValueError(f"Mixed evidence labels for claim {claim['id']}: {labels}")
    return next(iter(labels))


def connected_groups(claims: list[dict[str, Any]]) -> dict[int, int]:
    parent = {int(claim["id"]): int(claim["id"]) for claim in claims}

    def find(value: int) -> int:
        while value != parent[value]:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: int, right: int) -> None:
        roots = sorted((find(left), find(right)))
        parent[roots[1]] = roots[0]

    buckets: dict[tuple[str, Any], list[int]] = collections.defaultdict(list)
    for claim in claims:
        claim_id = int(claim["id"])
        for doc_id in claim["cited_doc_ids"]:
            buckets[("doc", int(doc_id))].append(claim_id)
        buckets[("text", normalize(claim["claim"]))].append(claim_id)
    for members in buckets.values():
        for member in members[1:]:
            union(members[0], member)
    components: dict[int, list[int]] = collections.defaultdict(list)
    for claim_id in sorted(parent):
        components[find(claim_id)].append(claim_id)
    return {
        claim_id: min(members)
        for members in components.values()
        for claim_id in members
    }


def tie_key(claim_id: int) -> str:
    return hashlib.sha256(f"{TIE_SEED}:{claim_id}".encode()).hexdigest()


def aurc_direct(ordered_errors: Iterable[int]) -> float:
    errors = list(ordered_errors)
    if not errors or set(errors) - {0, 1}:
        raise ValueError("AURC requires a non-empty binary error sequence")
    cumulative = 0
    risks = []
    for k, error in enumerate(errors, 1):
        cumulative += error
        risks.append(cumulative / k)
    return math.fsum(risks) / len(errors)


def aurc_weights(n: int) -> list[float]:
    if n < 1:
        raise ValueError("n must be positive")
    return [math.fsum(1.0 / k for k in range(i, n + 1)) / n for i in range(1, n + 1)]


def aurc_weighted(ordered_errors: Iterable[int]) -> float:
    errors = list(ordered_errors)
    if not errors or set(errors) - {0, 1}:
        raise ValueError("AURC requires a non-empty binary error sequence")
    return math.fsum(weight * error for weight, error in zip(aurc_weights(len(errors)), errors))


def one_label_influence(n: int, one_based_rank: int, delta_error: int) -> float:
    if delta_error not in {-1, 0, 1} or not 1 <= one_based_rank <= n:
        raise ValueError("Invalid perturbation")
    return delta_error * aurc_weights(n)[one_based_rank - 1]


def paired_influence(
    n: int, b1_rank: int, ears_rank: int, delta_error: int
) -> float:
    return one_label_influence(n, ears_rank, delta_error) - one_label_influence(
        n, b1_rank, delta_error
    )


def ranking(rows: list[Row], method: str) -> list[Row]:
    risk = (lambda row: row.b1) if method == "B1" else (lambda row: row.ears)
    return sorted(rows, key=lambda row: (risk(row), tie_key(row.claim_id), row.claim_id))


def method_metrics(rows: list[Row], method: str) -> dict[str, Any]:
    ordered = ranking(rows, method)
    errors = [row.error for row in ordered]
    cumulative = np.cumsum(np.asarray(errors, dtype=int))
    risks = cumulative / np.arange(1, len(rows) + 1)
    k80 = math.floor(0.8 * len(rows) + 0.5)
    direct = float(np.mean(risks))
    weighted = aurc_weighted(errors)
    if not math.isclose(direct, weighted, rel_tol=0.0, abs_tol=2e-16):
        raise AssertionError((direct, weighted))
    return {
        "n": len(rows),
        "groups": len({row.group_id for row in rows}),
        "errors": sum(errors),
        "aurc": direct,
        "aurc_weighted": weighted,
        "k80": k80,
        "r80": int(cumulative[k80 - 1]) / k80,
    }


def evaluate(rows: list[Row]) -> dict[str, Any]:
    b1 = method_metrics(rows, "B1")
    ears = method_metrics(rows, "EARS")
    return {
        "B1": b1,
        "EARS": ears,
        "delta": {
            "aurc": ears["aurc"] - b1["aurc"],
            "r80": ears["r80"] - b1["r80"],
        },
    }


def percentile(values: list[float]) -> list[float]:
    low, high = np.percentile(np.asarray(values), [2.5, 97.5], method="linear")
    return [float(low), float(high)]


def bootstrap(rows: list[Row]) -> dict[str, list[float]]:
    groups: dict[int, list[Row]] = collections.defaultdict(list)
    for row in rows:
        groups[row.group_id].append(row)
    group_ids = sorted(groups)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    values: dict[str, list[float]] = collections.defaultdict(list)
    for _ in range(BOOTSTRAP_REPLICATES):
        sample = [
            row
            for draw in rng.integers(0, len(group_ids), size=len(group_ids))
            for row in groups[group_ids[int(draw)]]
        ]
        result = evaluate(sample)
        for method in ("B1", "EARS"):
            for metric in ("aurc", "r80"):
                values[f"{method}_{metric}"].append(result[method][metric])
        for metric in ("aurc", "r80"):
            values[f"delta_{metric}"].append(result["delta"][metric])
    return {name: percentile(series) for name, series in values.items()}


def build_rows(
    claims: list[dict[str, Any]],
    frozen: dict[int, dict[str, Any]],
    groups: dict[int, int],
    labels: dict[int, str | None],
) -> list[Row]:
    rows = []
    for claim in claims:
        claim_id = int(claim["id"])
        label = labels[claim_id]
        if label not in ELIGIBLE:
            continue
        score = frozen[claim_id]
        rows.append(
            Row(
                claim_id,
                groups[claim_id],
                str(label),
                str(score["predicted_label"]),
                float(score["risk_frozen_B1"]),
                float(score["risk_frozen_EARS"]),
            )
        )
    return rows


def scenario_labels(
    original: dict[int, str | None],
    corrections: dict[int, dict[str, Any]],
    adopted: set[int],
    literal_597: bool = False,
) -> dict[int, str | None]:
    labels = dict(original)
    for claim_id in adopted:
        labels[claim_id] = str(corrections[claim_id]["corrected_label"])
    if literal_597:
        labels[597] = "NEI"
    return labels


def enumerate_scenarios(
    claim_ids: list[int],
    claims: list[dict[str, Any]],
    frozen: dict[int, dict[str, Any]],
    groups: dict[int, int],
    original: dict[int, str | None],
    corrections: dict[int, dict[str, Any]],
    fixed_ids: set[int] | None = None,
    include_literal_597: bool = False,
) -> list[dict[str, Any]]:
    variables: list[int | str] = list(claim_ids)
    if include_literal_597:
        variables.append("597_literal")
    output = []
    for mask in range(1 << len(variables)):
        selected = {variables[i] for i in range(len(variables)) if mask & (1 << i)}
        adopted = {int(value) for value in selected if isinstance(value, int)}
        labels = scenario_labels(original, corrections, adopted, "597_literal" in selected)
        rows = build_rows(claims, frozen, groups, labels)
        if fixed_ids is not None:
            rows = [row for row in rows if row.claim_id in fixed_ids]
        result = evaluate(rows)
        output.append(
            {
                "mask": mask,
                "adopted": sorted(map(str, selected)),
                "modifications": len(selected),
                "n": len(rows),
                "groups": len({row.group_id for row in rows}),
                "B1_aurc": result["B1"]["aurc"],
                "EARS_aurc": result["EARS"]["aurc"],
                "delta_aurc": result["delta"]["aurc"],
            }
        )
    return output


def bounds(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    best = min(scenarios, key=lambda row: (row["delta_aurc"], row["modifications"]))
    worst = max(scenarios, key=lambda row: (row["delta_aurc"], -row["modifications"]))
    reversals = [row for row in scenarios if row["delta_aurc"] < 0]
    minimum = min((row["modifications"] for row in reversals), default=None)
    minimum_rows = [
        row for row in reversals if row["modifications"] == minimum
    ] if minimum is not None else []
    return {
        "scenario_count": len(scenarios),
        "minimum_delta": best,
        "maximum_delta": worst,
        "reversal_scenario_count": len(reversals),
        "minimum_modifications_for_point_reversal": minimum,
        "minimum_reversal_scenarios": minimum_rows,
    }


def endpoint_value(result: dict[str, Any], endpoint: str) -> float:
    if endpoint.startswith("delta_"):
        return result["delta"][endpoint.removeprefix("delta_")]
    method, metric = endpoint.split("_")
    return result[method][metric]


def decomposition(
    a_original: dict[str, Any],
    b_original: dict[str, Any],
    b_corrected: dict[str, Any],
    a_label_only: dict[str, Any],
) -> dict[str, Any]:
    endpoints = [
        "B1_aurc", "EARS_aurc", "delta_aurc",
        "B1_r80", "EARS_r80", "delta_r80",
    ]
    output = {}
    for endpoint in endpoints:
        a = endpoint_value(a_original, endpoint)
        b0 = endpoint_value(b_original, endpoint)
        b1 = endpoint_value(b_corrected, endpoint)
        al = endpoint_value(a_label_only, endpoint)
        composition_first = b0 - a
        label_after_composition = b1 - b0
        label_first = al - a
        composition_after_label = b1 - al
        output[endpoint] = {
            "A_original": a,
            "B_common_original": b0,
            "B_common_corrected": b1,
            "C_corrected": b1,
            "A_label_only": al,
            "path_composition_then_label": {
                "composition": composition_first,
                "label": label_after_composition,
            },
            "path_label_then_composition": {
                "label": label_first,
                "composition": composition_after_label,
            },
            "symmetric_shapley": {
                "composition": (composition_first + composition_after_label) / 2,
                "label": (label_after_composition + label_first) / 2,
                "combined": b1 - a,
            },
        }
    return output


def adversarial_flip_bound(rows: list[Row]) -> dict[str, Any]:
    baseline = evaluate(rows)["delta"]["aurc"]
    b1_ranks = {row.claim_id: i for i, row in enumerate(ranking(rows, "B1"), 1)}
    ears_ranks = {row.claim_id: i for i, row in enumerate(ranking(rows, "EARS"), 1)}
    candidates = []
    for row in rows:
        delta_error = 1 if row.error == 0 else -1
        influence = paired_influence(
            len(rows), b1_ranks[row.claim_id], ears_ranks[row.claim_id], delta_error
        )
        candidates.append({"claim_id": row.claim_id, "influence": influence})
    helpful = sorted((row for row in candidates if row["influence"] < 0), key=lambda row: row["influence"])
    running = baseline
    selected = []
    for candidate in helpful:
        selected.append(candidate)
        running += candidate["influence"]
        if running < 0:
            break
    return {
        "baseline_delta_aurc": baseline,
        "minimum_hypothetical_binary_error_flips": len(selected) if running < 0 else None,
        "selected": selected if running < 0 else [],
        "resulting_delta_aurc": running if running < 0 else None,
        "interpretation": "Mathematical adversarial binary-correctness flips; not documented annotation errors.",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-v2", type=Path, required=True)
    parser.add_argument("--private-v2", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, source_v2, private_v2, audit, out = (
        args.root.resolve(), args.source_v2.resolve(), args.private_v2.resolve(),
        args.audit.resolve(), args.output_dir.resolve()
    )
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "claims": private_v2 / "data/raw/scifact/claims_dev.jsonl",
        "corpus": private_v2 / "data/raw/scifact/corpus.jsonl",
        "frozen": private_v2 / ".cache/research_upgrade_v2_correction/2026-10-14/e1/corrected_blind_e1_features.jsonl",
        "corrections": audit / "corrections/dev_corrections.json",
        "protocol": source_v2 / "configs/research_upgrade_v2_protocol.json",
    }
    hashes = {name: sha256_file(path) for name, path in paths.items()}
    if hashes != EXPECTED:
        raise RuntimeError({name: (EXPECTED[name], hashes[name]) for name in EXPECTED if hashes[name] != EXPECTED[name]})

    claims = load_jsonl(paths["claims"])
    groups = connected_groups(claims)
    frozen_rows = load_jsonl(paths["frozen"])
    frozen = {int(row["claim_id"]): row for row in frozen_rows if row["partition"] == "dev"}
    correction_data = json.loads(paths["corrections"].read_text(encoding="utf-8"))
    corrections = {int(row["claim_id"]): row for row in correction_data["corrections"]}
    original = {int(claim["id"]): derived_label(claim) for claim in claims}
    primary_ids = sorted(claim_id for claim_id in corrections if claim_id != 597)
    flip_ids = sorted(
        claim_id for claim_id in primary_ids
        if str(corrections[claim_id]["corrected_label"]) in ELIGIBLE
    )
    exclusion_ids = sorted(set(primary_ids) - set(flip_ids))

    original_rows = build_rows(claims, frozen, groups, original)
    primary_labels = scenario_labels(original, corrections, set(primary_ids))
    corrected_rows = build_rows(claims, frozen, groups, primary_labels)
    common_ids = {row.claim_id for row in original_rows} & {row.claim_id for row in corrected_rows}
    common_original_rows = [row for row in original_rows if row.claim_id in common_ids]
    common_corrected_rows = [row for row in corrected_rows if row.claim_id in common_ids]
    label_only_rows = build_rows(
        claims, frozen, groups, scenario_labels(original, corrections, set(flip_ids))
    )

    original_result = evaluate(original_rows)
    common_original_result = evaluate(common_original_rows)
    corrected_result = evaluate(corrected_rows)
    label_only_result = evaluate(label_only_rows)
    assert (len(original_rows), len({row.group_id for row in original_rows})) == (188, 164)
    assert (len(corrected_rows), len({row.group_id for row in corrected_rows})) == (182, 159)
    expected_points = {
        "B1_aurc": 0.28157532540846636,
        "EARS_aurc": 0.2883553020068359,
        "delta_aurc": 0.0067799765983695415,
        "B1_r80": 0.41333333333333333,
        "EARS_r80": 0.4,
        "delta_r80": -0.013333333333333308,
    }
    for name, expected in expected_points.items():
        actual = endpoint_value(original_result, name)
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-15):
            raise AssertionError((name, actual, expected))

    # Exact per-annotation effects, relative to the original-label population.
    b1_ranks = {row.claim_id: i for i, row in enumerate(ranking(original_rows, "B1"), 1)}
    ears_ranks = {row.claim_id: i for i, row in enumerate(ranking(original_rows, "EARS"), 1)}
    by_claim = {int(claim["id"]): claim for claim in claims}
    influence_rows = []
    for claim_id in sorted(corrections):
        correction = corrections[claim_id]
        if claim_id == 597:
            result = original_result
            proposed_label = original[claim_id]
            corrected_eligible = True
            note = "Primary document-only interpretation: document 12779444 becomes NEI; claim stays SUPPORT through two other documents."
        else:
            labels = scenario_labels(original, corrections, {claim_id})
            scenario_rows = build_rows(claims, frozen, groups, labels)
            result = evaluate(scenario_rows)
            proposed_label = correction["corrected_label"]
            corrected_eligible = proposed_label in ELIGIBLE
            note = (
                "Fixed-membership one-label perturbation; exact weighted influence."
                if corrected_eligible
                else "Exact one-claim deletion effect; n and downstream AURC weights/ranks change, so the fixed-label formula does not apply."
            )
        b1_effect = result["B1"]["aurc"] - original_result["B1"]["aurc"]
        ears_effect = result["EARS"]["aurc"] - original_result["EARS"]["aurc"]
        paired_effect = result["delta"]["aurc"] - original_result["delta"]["aurc"]
        if claim_id != 597 and corrected_eligible:
            original_row = next(row for row in original_rows if row.claim_id == claim_id)
            new_error = int(str(proposed_label) != original_row.prediction)
            delta_error = new_error - original_row.error
            assert math.isclose(
                b1_effect,
                one_label_influence(len(original_rows), b1_ranks[claim_id], delta_error),
                rel_tol=0, abs_tol=3e-16,
            )
            assert math.isclose(
                paired_effect,
                paired_influence(len(original_rows), b1_ranks[claim_id], ears_ranks[claim_id], delta_error),
                rel_tol=0, abs_tol=3e-16,
            )
        evidence_docs = ";".join(sorted(by_claim[claim_id]["evidence"], key=int))
        influence_rows.append({
            "claim_id": claim_id,
            "document_id": "12779444" if claim_id == 597 else evidence_docs,
            "group_id": groups[claim_id],
            "original_label": original[claim_id],
            "proposed_label": proposed_label,
            "correction_status": "proposed_single_annotator_not_independently_adjudicated",
            "original_eligibility": True,
            "corrected_eligibility": corrected_eligible,
            "B1_rank": b1_ranks[claim_id],
            "EARS_rank": ears_ranks[claim_id],
            "B1_AURC_influence": b1_effect,
            "EARS_AURC_influence": ears_effect,
            "paired_delta_AURC_influence": paired_effect,
            "scenario_id": "individual_primary_from_original",
            "interpretation_notes": note,
        })
    literal_labels = scenario_labels(original, corrections, set(), literal_597=True)
    literal_result = evaluate(build_rows(claims, frozen, groups, literal_labels))
    influence_rows.append({
        "claim_id": 597,
        "document_id": "12779444;25742130;36355784",
        "group_id": groups[597],
        "original_label": original[597],
        "proposed_label": "NEI",
        "correction_status": "literal_JSON_scope_sensitivity_not_primary_resolution",
        "original_eligibility": True,
        "corrected_eligibility": False,
        "B1_rank": b1_ranks[597],
        "EARS_rank": ears_ranks[597],
        "B1_AURC_influence": literal_result["B1"]["aurc"] - original_result["B1"]["aurc"],
        "EARS_AURC_influence": literal_result["EARS"]["aurc"] - original_result["EARS"]["aurc"],
        "paired_delta_AURC_influence": literal_result["delta"]["aurc"] - original_result["delta"]["aurc"],
        "scenario_id": "claim597_literal_json_from_original",
        "interpretation_notes": "Exact claim deletion sensitivity for the internally inconsistent doc_id:null JSON interpretation.",
    })
    influence_rows.sort(key=lambda row: (row["scenario_id"], -abs(float(row["paired_delta_AURC_influence"])), int(row["claim_id"])))
    influence_fields = [
        "claim_id", "document_id", "group_id", "original_label", "proposed_label",
        "correction_status", "original_eligibility", "corrected_eligibility",
        "B1_rank", "EARS_rank", "B1_AURC_influence", "EARS_AURC_influence",
        "paired_delta_AURC_influence", "scenario_id", "interpretation_notes",
    ]
    write_csv(out / "ANNOTATION_INFLUENCE_ANALYSIS.csv", influence_rows, influence_fields)

    fixed_scenarios = enumerate_scenarios(
        flip_ids, claims, frozen, groups, original, corrections, fixed_ids=common_ids
    )
    primary_scenarios = enumerate_scenarios(
        primary_ids, claims, frozen, groups, original, corrections
    )
    all_scope_scenarios = enumerate_scenarios(
        primary_ids, claims, frozen, groups, original, corrections, include_literal_597=True
    )
    corrected_bootstrap = bootstrap(corrected_rows)
    expected_ci = {
        "delta_aurc": [-0.02181605832252585, 0.026993366644624574],
        "delta_r80": [-0.039735099337748325, 0.006993006993006978],
    }
    for name, expected in expected_ci.items():
        for actual, target in zip(corrected_bootstrap[name], expected):
            if not math.isclose(actual, target, rel_tol=0, abs_tol=1e-15):
                raise AssertionError((name, corrected_bootstrap[name], expected))

    result = {
        "schema_version": "study-a-plus-v1",
        "source_hashes": hashes,
        "definitions": {
            "tie_rule": f"ascending risk, then SHA-256({TIE_SEED}:claim_id), then claim_id",
            "aurc": "mean prefix error risk",
            "weights": "w_i=(1/n)*sum_{k=i}^n(1/k)",
            "bootstrap": {"seed": BOOTSTRAP_SEED, "replicates": BOOTSTRAP_REPLICATES},
        },
        "reproduction": {
            "original": original_result,
            "common_original": common_original_result,
            "corrected": corrected_result,
            "corrected_bootstrap_ci95": corrected_bootstrap,
        },
        "correction_sets": {"label_flips": flip_ids, "eligibility_exclusions": exclusion_ids},
        "label_uncertainty": {
            "fixed_common_5_label_disputes": bounds(fixed_scenarios),
            "all_11_primary_claim_level_proposals": bounds(primary_scenarios),
            "all_11_plus_literal_claim597": bounds(all_scope_scenarios),
            "hypothetical_adversarial_original": adversarial_flip_bound(original_rows),
            "hypothetical_adversarial_common": adversarial_flip_bound(common_original_rows),
        },
        "decomposition": decomposition(
            original_result, common_original_result, corrected_result, label_only_result
        ),
        "group_structure": {
            "original_groups": len({row.group_id for row in original_rows}),
            "common_corrected_groups": len({row.group_id for row in corrected_rows}),
            "lost_groups": sorted({row.group_id for row in original_rows} - {row.group_id for row in corrected_rows}),
            "group_graph_rebuilt_after_correction": False,
        },
        "enumeration_audit": {
            "fixed_common_scenarios": fixed_scenarios,
            "primary_scenarios": primary_scenarios,
            "all_scope_scenarios": all_scope_scenarios,
        },
    }
    (out / "STUDY_A_PLUS_RESULTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "fixed_bounds": result["label_uncertainty"]["fixed_common_5_label_disputes"],
        "primary_bounds": result["label_uncertainty"]["all_11_primary_claim_level_proposals"],
        "corrected_delta": corrected_result["delta"],
    }, indent=2))


if __name__ == "__main__":
    main()
