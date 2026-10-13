#!/usr/bin/env python3
from __future__ import annotations

import argparse
import collections
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from trustworthy_ai_lab.data import load_json, load_jsonl, load_selected_claims, write_json, write_jsonl
from trustworthy_ai_lab.metrics import classification_metrics, error_breakdown, retrieval_metrics, sentence_selection_metrics
from trustworthy_ai_lab.phase2_protocol import tie_key
from trustworthy_ai_lab.phase2b import connected_group_lookup, evaluate_method, ranking_order
from trustworthy_ai_lab.phase3b import (
    FORMAL_METHODS,
    bootstrap_paired_dynamic,
    build_labeled_retrieval,
    risk_distribution,
    sha256_file,
    summarize_bootstrap,
)
from trustworthy_ai_lab.pipeline import finalize_e1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def verify_map(root: Path, values: dict[str, str]) -> None:
    failures = []
    for relative, expected in values.items():
        path = root / relative
        actual = sha256_file(path) if path.is_file() else None
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    if failures:
        raise RuntimeError(f"Frozen hash mismatch: {failures}")


def global_acceptance(rows: list[dict[str, Any]], method: str) -> set[int]:
    order = ranking_order(rows, f"risk_{method}")
    k80 = math.floor(0.8 * len(rows) + 0.5)
    return {int(rows[index]["claim_id"]) for index in order[:k80]}


def conditional_rows(rows: list[dict[str, Any]], metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for method in FORMAL_METHODS:
        accepted = global_acceptance(rows, method)
        for kind, field, strata in (
            ("gold_label", "gold_label", ("SUPPORT", "CONTRADICT")),
            ("predicted_label", "predicted_label", ("SUPPORT", "CONTRADICT", "NO_RELATION")),
        ):
            for stratum in strata:
                members = [row for row in rows if row[field] == stratum]
                accepted_members = [row for row in members if int(row["claim_id"]) in accepted]
                errors = sum(int(row["y_error"]) for row in members)
                accepted_errors = sum(int(row["y_error"]) for row in accepted_members)
                risks = [float(row[f"risk_{method}"]) for row in members]
                output.append({
                    "method": method, "stratum_type": kind, "stratum": stratum,
                    "total": len(members), "total_errors": errors,
                    "error_rate": errors / len(members) if members else None,
                    "accepted": len(accepted_members),
                    "coverage_within_stratum": len(accepted_members) / len(members) if members else None,
                    "accepted_errors": accepted_errors,
                    "selective_risk": accepted_errors / len(accepted_members) if accepted_members else None,
                    "mean_predicted_risk": float(np.mean(risks)) if risks else None,
                    "median_predicted_risk": float(np.median(risks)) if risks else None,
                    "global_k80": metrics[method]["k80"],
                })
    return output


def sensitivity_rows(rows: list[dict[str, Any]], metrics: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for method in FORMAL_METHODS:
        output.append({"analysis": "A_full_eligible", "stratum": "ALL", "method": method, **metrics[method]})
    non_nr = [row for row in rows if row["predicted_label"] != "NO_RELATION"]
    if non_nr:
        for method in FORMAL_METHODS:
            values, _ = evaluate_method(non_nr, method)
            output.append({"analysis": "B_non_no_relation_reranked", "stratum": "SUPPORT_OR_CONTRADICT", "method": method, **values})
    nr = [row for row in rows if row["predicted_label"] == "NO_RELATION"]
    for method in FORMAL_METHODS:
        risks = [float(row[f"risk_{method}"]) for row in nr]
        dist = risk_distribution(risks)
        auroc = None
        if nr:
            values, _ = evaluate_method(nr, method)
            auroc = values["error_detection_auroc"]
        output.append({
            "analysis": "C_no_relation_descriptive", "stratum": "NO_RELATION", "method": method,
            "n": len(nr), "errors": sum(int(row["y_error"]) for row in nr),
            "correct": len(nr) - sum(int(row["y_error"]) for row in nr),
            "error_rate": sum(int(row["y_error"]) for row in nr) / len(nr) if nr else None,
            "error_detection_auroc": auroc,
            **{f"risk_{key}": value for key, value in dist.items()},
        })
    for method in FORMAL_METHODS:
        accepted = global_acceptance(rows, method)
        for field, analysis, strata in (
            ("predicted_label", "D_predicted_category_global80", ("SUPPORT", "CONTRADICT", "NO_RELATION")),
            ("gold_label", "E_gold_category_global80_posthoc", ("SUPPORT", "CONTRADICT")),
        ):
            for stratum in strata:
                members = [row for row in rows if row[field] == stratum]
                accepted_members = [row for row in members if int(row["claim_id"]) in accepted]
                output.append({
                    "analysis": analysis, "stratum": stratum, "method": method, "n": len(members),
                    "errors": sum(int(row["y_error"]) for row in members),
                    "error_rate": sum(int(row["y_error"]) for row in members) / len(members) if members else None,
                    "accepted_global80": len(accepted_members),
                    "accepted_errors_global80": sum(int(row["y_error"]) for row in accepted_members),
                    "coverage_within_stratum": len(accepted_members) / len(members) if members else None,
                    "selective_risk_global80": sum(int(row["y_error"]) for row in accepted_members) / len(accepted_members) if accepted_members else None,
                })
    return output


def case_records(rows: list[dict[str, Any]], evaluated: dict[int, dict[str, Any]], claims: dict[int, dict[str, Any]], corpus: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    ears_order = ranking_order(rows, "risk_EARS")
    b1_order = ranking_order(rows, "risk_B1")
    rank_ears = {int(rows[index]["claim_id"]): rank for rank, index in enumerate(ears_order, 1)}
    n = len(rows)
    k = math.floor(0.8 * n + 0.5)
    ears_accepted = {int(rows[index]["claim_id"]) for index in ears_order[:k]}
    b1_accepted = {int(rows[index]["claim_id"]) for index in b1_order[:k]}
    selections = {
        "false_reassurance_low_EARS_risk_error": sorted((row for row in rows if row["y_error"]), key=lambda row: (row["risk_EARS"], tie_key(int(row["claim_id"]))))[:10],
        "unnecessary_rejection_high_EARS_risk_correct": sorted((row for row in rows if not row["y_error"]), key=lambda row: (-row["risk_EARS"], tie_key(int(row["claim_id"]))))[:10],
        "high_confidence_wrong_B0": sorted((row for row in rows if row["y_error"]), key=lambda row: (row["risk_B0"], tie_key(int(row["claim_id"]))))[:10],
        "EARS_rescue_vs_B1_at_global80": sorted((row for row in rows if row["y_error"] and int(row["claim_id"]) not in ears_accepted and int(row["claim_id"]) in b1_accepted), key=lambda row: (-row["risk_EARS"], tie_key(int(row["claim_id"]))))[:5],
        "EARS_harm_vs_B1_at_global80": sorted((row for row in rows if row["y_error"] and int(row["claim_id"]) in ears_accepted and int(row["claim_id"]) not in b1_accepted), key=lambda row: (row["risk_EARS"], tie_key(int(row["claim_id"]))))[:5],
    }
    output = []
    for category, selected in selections.items():
        for row in selected:
            claim_id = int(row["claim_id"])
            result = evaluated[claim_id]
            winner = result.get("winning_candidate")
            winning_pair = None
            if winner:
                winning_pair = next(item for item in result["sentence_predictions"] if item["pair_id"] == winner["source_pair_id"])
            gold_texts = []
            for doc_key, rationales in claims[claim_id]["evidence"].items():
                abstract = corpus[int(doc_key)]["abstract"]
                for rationale in rationales:
                    gold_texts.append({"doc_id": int(doc_key), "label": rationale["label"], "sentence_indices": rationale["sentences"], "text": " ".join(abstract[i] for i in rationale["sentences"])})
            output.append({
                "case_category": category, "claim_id": claim_id, "claim_text": result["claim_text"],
                "gold_label": row["gold_label"], "predicted_label": row["predicted_label"], "y_error": int(row["y_error"]),
                "failure_categories": result["failure_categories"], "ears_rank_low_to_high_risk": rank_ears[claim_id],
                "features": {key: row[key] for key in row if key.startswith("F")},
                "risks": {method: row[f"risk_{method}"] for method in FORMAL_METHODS},
                "retrieved_doc_ids_at_5": [item["doc_id"] for item in result["sentence_predictions"] if item["selected_sentence_rank"] == 1][:5],
                "gold_evidence": gold_texts,
                "winning_candidate": winner,
                "winning_pair": None if winning_pair is None else {"doc_id": winning_pair["doc_id"], "sentence_index": winning_pair["sentence_index"], "premise": winning_pair["premise"], "probabilities": winning_pair["probabilities"], "predicted_nli_label": winning_pair["predicted_nli_label"]},
            })
    return output


def make_figures(output: Path, metrics: dict[str, dict[str, Any]], curves: list[dict[str, Any]], bootstrap: list[dict[str, Any]], sensitivity: list[dict[str, Any]], phase2_path: Path) -> None:
    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    colors = {"B0": "#7f7f7f", "B1": "#1f77b4", "B2": "#ff7f0e", "EARS": "#2ca02c"}
    plt.figure(figsize=(7, 5))
    for method in FORMAL_METHODS:
        subset = [row for row in curves if row["method"] == method]
        plt.step([row["coverage"] for row in subset], [row["selective_risk"] for row in subset], where="post", label=method, color=colors[method])
    plt.xlabel("Coverage"); plt.ylabel("Selective risk"); plt.title("Independent Internal Test Risk–Coverage"); plt.legend(); plt.tight_layout(); plt.savefig(figure_dir / "independent_risk_coverage.png", dpi=180); plt.close()
    plt.figure(figsize=(6, 4)); plt.bar(FORMAL_METHODS, [metrics[m]["aurc"] for m in FORMAL_METHODS], color=[colors[m] for m in FORMAL_METHODS]); plt.ylabel("AURC (lower is better)"); plt.tight_layout(); plt.savefig(figure_dir / "independent_aurc.png", dpi=180); plt.close()
    plt.figure(figsize=(6, 4)); plt.bar(FORMAL_METHODS, [metrics[m]["errors_at_80"] for m in FORMAL_METHODS], color=[colors[m] for m in FORMAL_METHODS]); plt.ylabel("Accepted errors at global 80% coverage"); plt.tight_layout(); plt.savefig(figure_dir / "r80_error_count.png", dpi=180); plt.close()
    plt.figure(figsize=(7, 4)); plt.hist([row["delta_aurc_EARS_minus_B1"] for row in bootstrap], bins=60, alpha=.7, label="ΔAURC"); plt.axvline(0, color="black", linewidth=1); plt.xlabel("EARS − B1"); plt.ylabel("Bootstrap replicates"); plt.legend(); plt.tight_layout(); plt.savefig(figure_dir / "paired_bootstrap_delta_aurc.png", dpi=180); plt.close()
    full = {row["method"]: row for row in sensitivity if row["analysis"] == "A_full_eligible"}
    non = {row["method"]: row for row in sensitivity if row["analysis"] == "B_non_no_relation_reranked"}
    methods = list(FORMAL_METHODS); x = np.arange(len(methods)); width = .35
    plt.figure(figsize=(7, 4)); plt.bar(x-width/2, [full[m]["aurc"] for m in methods], width, label="Full"); plt.bar(x+width/2, [non[m]["aurc"] for m in methods], width, label="Non-NO_RELATION"); plt.xticks(x, methods); plt.ylabel("AURC"); plt.legend(); plt.tight_layout(); plt.savefig(figure_dir / "no_relation_sensitivity.png", dpi=180); plt.close()
    if phase2_path.is_file():
        phase2 = {row["method"]: float(row["aurc"]) for row in read_csv(phase2_path) if row["method"] in FORMAL_METHODS}
        plt.figure(figsize=(7, 4)); plt.bar(x-width/2, [phase2[m] for m in methods], width, label="Phase 2B OOF"); plt.bar(x+width/2, [metrics[m]["aurc"] for m in methods], width, label="Phase 3B independent"); plt.xticks(x, methods); plt.ylabel("AURC"); plt.legend(); plt.tight_layout(); plt.savefig(figure_dir / "phase2b_oof_vs_phase3b.png", dpi=180); plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output_dir.resolve()
    canonical = root / "reports/phase3b"
    output.mkdir(parents=True, exist_ok=True)
    model_manifest = load_json(root / "models/phase3b/final_model_manifest.json")
    freeze = load_json(canonical / "prediction_freeze_manifest.json")
    verify_map(root, model_manifest["code_sha256"])
    verify_map(root, model_manifest["artifact_sha256"])
    verify_map(root, freeze["artifact_sha256"])
    phase3a = load_json(root / "reports/phase3a/protocol_manifest.json")
    verify_map(root, phase3a["sha256"])
    if freeze["status"] != "PREDICTIONS_FROZEN_BEFORE_LABEL_ACCESS" or freeze["labels_or_gold_evidence_accessed"]:
        raise RuntimeError("Predictions were not validly frozen before label access")

    split = load_json(root / "splits/train_split_manifest.json")
    test_ids = {int(value) for value in split["outer_splits"]["internal_test"]["claim_ids"]}
    if len(test_ids) != 141:
        raise RuntimeError("Internal Test is not 141 claims")
    # First label access in Phase 3B occurs here, after all frozen hashes pass.
    claims = load_selected_claims(root / "data/raw/scifact/claims_train.jsonl", test_ids)
    claims_by_id = {int(row["id"]): row for row in claims}
    group_lookup = connected_group_lookup(claims)
    blind_retrieval = load_jsonl(canonical / "test_retrieval_results_label_blind.jsonl")
    blind_baseline = load_jsonl(canonical / "test_baseline_predictions.jsonl")
    labeled_retrieval = build_labeled_retrieval(blind_retrieval, claims)
    pair_predictions = [pair for row in blind_baseline for pair in row["sentence_predictions"]]
    evaluated = finalize_e1(labeled_retrieval, pair_predictions)
    blind_by_id = {int(row["claim_id"]): row for row in blind_baseline}
    for row in evaluated:
        blind = blind_by_id[int(row["claim_id"])]
        for field in ("predicted_claim_label", "winning_candidate", "support_contradict_conflict", "non_neutral_candidate_count"):
            if row[field] != blind[field]:
                raise RuntimeError(f"Label unsealing changed frozen aggregation for {row['claim_id']}")
    if len(evaluated) != 141:
        raise RuntimeError("Incomplete evaluated baseline")

    feature_rows = read_csv(canonical / "test_feature_matrix.csv")
    risk_pre = read_csv(canonical / "test_risk_scores_prelabel.csv")
    features = {int(row["claim_id"]): {key: float(value) for key, value in row.items() if key != "claim_id"} for row in feature_rows}
    risks = {int(row["claim_id"]): {key: float(value) for key, value in row.items() if key != "claim_id"} for row in risk_pre}
    eligible_results = [row for row in evaluated if row["evaluation_eligible"]]
    rows = []
    for result in eligible_results:
        claim_id = int(result["claim_id"])
        if claim_id not in features or claim_id not in risks:
            raise RuntimeError(f"Missing eligible test risk for {claim_id}; complete-case deletion prohibited")
        row = {
            "claim_id": claim_id, "group_id": int(group_lookup[claim_id]),
            "gold_label": result["gold_evidence_label"], "predicted_label": result["predicted_claim_label"],
            "y_error": int(not bool(result["correct"])), **features[claim_id], **risks[claim_id],
        }
        if row["gold_label"] not in ("SUPPORT", "CONTRADICT") or row["predicted_label"] not in ("SUPPORT", "CONTRADICT", "NO_RELATION"):
            raise RuntimeError("Illegal label mapping")
        if not all(math.isfinite(float(row[f"risk_{method}"])) for method in FORMAL_METHODS):
            raise RuntimeError("Nonfinite eligible risk")
        rows.append(row)
    rows.sort(key=lambda row: row["claim_id"])
    if len(rows) != len({row["claim_id"] for row in rows}) or not rows:
        raise RuntimeError("Eligible claim IDs are empty or duplicated")

    metric_map, curves = {}, []
    for method in FORMAL_METHODS:
        values, curve = evaluate_method(rows, method)
        values["overall_error_rate"] = sum(row["y_error"] for row in rows) / len(rows)
        values["accepted"] = values["k80"]
        values["rejected"] = len(rows) - values["k80"]
        values["rejected_errors"] = sum(row["y_error"] for row in rows) - values["errors_at_80"]
        metric_map[method] = values
        curves.extend(curve)
    bootstrap = bootstrap_paired_dynamic(rows, replicates=10_000, seed=20261016)
    cis = summarize_bootstrap(bootstrap, metric_map)
    ci_by_name = {row["estimand"]: row for row in cis}
    delta_aurc = metric_map["EARS"]["aurc"] - metric_map["B1"]["aurc"]
    delta_sr80 = metric_map["EARS"]["sr80"] - metric_map["B1"]["sr80"]
    aurc_ci = ci_by_name["delta_aurc_EARS_minus_B1"]
    sr_ci = ci_by_name["delta_sr80_EARS_minus_B1"]
    if delta_aurc < 0 and delta_sr80 < 0 and aurc_ci["ci_upper_95"] < 0 and sr_ci["ci_upper_95"] < 0:
        h1 = "SUPPORTED"
    elif delta_aurc > 0 and delta_sr80 > 0 and aurc_ci["ci_lower_95"] > 0 and sr_ci["ci_lower_95"] > 0:
        h1 = "UNFAVORABLE"
    else:
        h1 = "INCONCLUSIVE"
    comparisons = [
        {"contrast": "EARS_minus_B1", "metric": "AURC", "EARS": metric_map["EARS"]["aurc"], "B1": metric_map["B1"]["aurc"], "paired_difference": delta_aurc, "ci_lower_95": aurc_ci["ci_lower_95"], "ci_upper_95": aurc_ci["ci_upper_95"], "lower_is_better": True, "preregistered_h1_status": h1},
        {"contrast": "EARS_minus_B1", "metric": "Selective risk at 80% coverage", "EARS": metric_map["EARS"]["sr80"], "B1": metric_map["B1"]["sr80"], "paired_difference": delta_sr80, "ci_lower_95": sr_ci["ci_lower_95"], "ci_upper_95": sr_ci["ci_upper_95"], "lower_is_better": True, "preregistered_h1_status": h1},
    ]
    class_rows = conditional_rows(rows, metric_map)
    sensitivity = sensitivity_rows(rows, metric_map)
    corpus_rows = load_jsonl(root / "data/raw/scifact/corpus.jsonl")
    cases = case_records(rows, {int(row["claim_id"]): row for row in evaluated}, claims_by_id, {int(row["doc_id"]): row for row in corpus_rows})
    classification = classification_metrics(evaluated)

    write_csv(output / "test_risk_predictions.csv", rows)
    write_csv(output / "test_metrics.csv", [metric_map[m] for m in FORMAL_METHODS])
    write_csv(output / "paired_comparisons.csv", comparisons)
    write_csv(output / "bootstrap_confidence_intervals.csv", cis)
    write_csv(output / "bootstrap_replicates.csv", bootstrap)
    write_csv(output / "risk_coverage_curves.csv", curves)
    write_csv(output / "class_conditional_results.csv", class_rows)
    all_sensitivity_fields = sorted({key for row in sensitivity for key in row})
    write_csv(output / "no_relation_sensitivity.csv", sensitivity, all_sensitivity_fields)
    write_jsonl(output / "error_analysis_cases.jsonl", cases)
    write_jsonl(output / "test_evaluation_records.jsonl", evaluated)
    diagnostics = {
        "status": "COMPLETE", "internal_test_total": 141, "eligible": len(rows), "unannotated": 141-len(rows),
        "eligible_groups": len({row["group_id"] for row in rows}), "all_test_groups": len(set(group_lookup.values())),
        "classification": classification, "error_breakdown": error_breakdown(evaluated),
        "retrieval": retrieval_metrics(labeled_retrieval),
        "sentence_selection_at_5": sentence_selection_metrics(labeled_retrieval, 5),
        "h1_status": h1, "delta_aurc_EARS_minus_B1": delta_aurc, "delta_sr80_EARS_minus_B1": delta_sr80,
        "no_relation_eligible": sum(row["predicted_label"] == "NO_RELATION" for row in rows),
        "no_relation_errors": sum(row["predicted_label"] == "NO_RELATION" and row["y_error"] for row in rows),
        "h2": "NOT_EVALUATED_IN_PHASE3B", "h3": "NOT_EVALUATED_IN_PHASE3B",
    }
    write_json(output / "diagnostics.json", diagnostics)
    write_json(output / "data_access_log.json", {
        "created_at_utc": utc_now(), "internal_test_claim_text_access": "after final model freeze, before prediction freeze",
        "internal_test_label_access": "after prediction_freeze_manifest verification", "internal_test_labels_now_used": True,
        "calibration_accessed": False, "scifact_dev_accessed": False, "official_test_accessed": False,
        "h2_executed": False, "h3_executed": False,
    })
    make_figures(output, metric_map, curves, bootstrap, sensitivity, root / "reports/phase2b/main_metrics.csv")
    deterministic_names = ["test_risk_predictions.csv", "test_metrics.csv", "paired_comparisons.csv", "bootstrap_confidence_intervals.csv", "bootstrap_replicates.csv", "risk_coverage_curves.csv", "class_conditional_results.csv", "no_relation_sensitivity.csv", "error_analysis_cases.jsonl", "test_evaluation_records.jsonl", "diagnostics.json"]
    manifest = {
        "protocol_version": "phase3a-v1.0.0", "created_at_utc": utc_now(), "status": "PHASE3B_EVALUATION_COMPLETE",
        "h1_status": h1, "internal_test_labels_used": True,
        "final_model_manifest_sha256": sha256_file(root / "models/phase3b/final_model_manifest.json"),
        "prediction_freeze_manifest_sha256": sha256_file(canonical / "prediction_freeze_manifest.json"),
        "deterministic_artifact_sha256": {name: sha256_file(output / name) for name in deterministic_names},
        "bootstrap": {"replicates": 10000, "seed": 20261016, "retrain_models": False},
        "prohibited_data_used": [], "models_retrained_after_test_access": False,
    }
    write_json(output / "experiment_manifest.json", manifest)
    print(json.dumps({"status": "COMPLETE", "eligible": len(rows), "classification": classification, "EARS": metric_map["EARS"], "B1": metric_map["B1"], "comparisons": comparisons, "h1": h1}, indent=2))


if __name__ == "__main__":
    main()
