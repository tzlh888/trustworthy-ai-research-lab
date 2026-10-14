from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/research_upgrade_v2/results"


def read_csv(name: str) -> list[dict[str, str]]:
    with (RESULTS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_protocol_and_score_freeze_are_hash_linked() -> None:
    analysis = json.loads((RESULTS / "analysis_manifest.json").read_text())
    assert analysis["protocol_sha256"] == "70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301"
    assert analysis["labels_opened_only_after_blind_manifests_verified"] is True
    for verifier in ("e1", "e1_v2"):
        manifest = json.loads((RESULTS / f"blind_{verifier}_manifest.json").read_text())
        assert manifest["status"] == "PREDICTIONS_FROZEN_BEFORE_V2_EVALUATION_LABEL_ACCESS"
        assert manifest["gold_labels_deserialized_for_scoring"] is False


def test_historical_results_and_h1_remain_unchanged() -> None:
    historical = {row["method"]: row for row in read_csv("../../phase3b/test_metrics.csv")}
    assert round(float(historical["B1"]["aurc"]), 6) == 0.300833
    assert round(float(historical["EARS"]["aurc"]), 6) == 0.264987
    assert round(float(historical["B1"]["sr80"]), 6) == 0.428571
    assert round(float(historical["EARS"]["sr80"]), 6) == 0.457143
    text = (ROOT / "RESEARCH_PROTOCOL.md").read_text(encoding="utf-8")
    assert "H1 INCONCLUSIVE" in text


def test_same_dataset_dev_ablation_is_complete_and_aligned() -> None:
    rows = [
        row for row in read_csv("all_metrics.csv")
        if row["evidence_level"] == "same_dataset_dev_reconstructed" and row["verifier"] == "e1"
    ]
    assert {row["method"] for row in rows} == {"B1", "B1_plus_F4", "B1_plus_F5", "EARS"}
    assert {int(row["n"]) for row in rows} == {188}
    assert {int(row["k80"]) for row in rows} == {150}


def test_group_bootstrap_and_paired_intervals_are_complete() -> None:
    rows = read_csv("dev_bootstrap_replicates.csv")
    assert len(rows) == 10_000
    assert all(int(row["group_draws"]) == 164 for row in rows)
    intervals = {row["estimand"]: row for row in read_csv("dev_bootstrap_intervals.csv")}
    for name in (
        "delta_aurc_B1_plus_F4_minus_B1",
        "delta_aurc_B1_plus_F5_minus_B1",
        "delta_aurc_EARS_minus_B1",
        "delta_sr80_EARS_minus_B1",
    ):
        assert int(intervals[name]["valid_replicates"]) == 10_000


def test_overlap_audit_prevents_external_replication_overclaim() -> None:
    audit = json.loads((RESULTS / "external_dataset_audit.json").read_text())
    assert audit["scifact_open"]["overlap_with_original_scifact"]["same_normalized_claim_text"] == 279
    assert audit["scifact_open"]["overlap_with_original_scifact"]["strict_no_claim_or_evidence_overlap_subset"] == 0
    assert audit["scifact_open"]["used_for_performance_evaluation"] is False
    assert audit["healthver"]["used_for_performance_evaluation"] is False


def test_ranking_and_calibration_outputs_are_numerically_finite() -> None:
    for name in ("all_metrics.csv", "calibration_metrics.csv", "perturbation_robustness.csv"):
        rows = read_csv(name)
        assert rows
        for row in rows:
            for key, value in row.items():
                if value == "" or key in {"method", "verifier", "evidence_level", "score_kind", "perturbation"}:
                    continue
                try:
                    number = float(value)
                except ValueError:
                    continue
                assert number == number and abs(number) != float("inf")


def test_public_results_do_not_include_raw_claim_or_evidence_text() -> None:
    forbidden = ('"claim_text"', '"sentence_predictions"', '"gold_evidence":')
    for path in RESULTS.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".jsonl", ".csv", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            assert not any(token in text for token in forbidden)
