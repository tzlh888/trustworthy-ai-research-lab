from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader

from demo.cloud_artifacts import load_verified_numeric_models, score_frozen_models
from scripts.analyze_research_upgrade_v2 import overlap_sensitivity
from scripts.build_v2_release_candidate import build as build_release_candidate
from scripts.run_upgrade_v2_inference import _claim_rows, _partition_ids
from trustworthy_ai_lab.data import write_json
from trustworthy_ai_lab.phase2_protocol import extract_features
from trustworthy_ai_lab.phase3b import (
    build_blind_retrieval_records,
    finalize_e1_blind,
    load_claim_projections,
)
from trustworthy_ai_lab.pipeline import build_e1_pairs


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports/research_upgrade_v2/results"
CORRECTED = ROOT / "reports/research_upgrade_v2/corrections/2026-10-14/results"


def read_csv(name: str) -> list[dict[str, str]]:
    with (RESULTS / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_protocol_and_score_freeze_are_hash_linked() -> None:
    assert hashlib.sha256(
        (ROOT / "configs/research_upgrade_v2_protocol.json").read_bytes()
    ).hexdigest() == "70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301"
    analysis = json.loads((RESULTS / "analysis_manifest.json").read_text())
    assert analysis["protocol_sha256"] == "70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301"
    correction = json.loads(
        (ROOT / "configs/research_upgrade_v2_correction_2026-10-14.json").read_text()
    )
    assert correction["not_a_preregistration"] is True
    assert correction["historical_v2_disclosure"]["full_dev_json_records_deserialized_for_partition_id_discovery"] is True
    for verifier in ("e1", "e1_v2"):
        manifest = json.loads((RESULTS / f"blind_{verifier}_manifest.json").read_text())
        assert manifest["status"] == "PREDICTIONS_FROZEN_BEFORE_V2_EVALUATION_LABEL_ACCESS"
        assert "gold_labels_deserialized_for_scoring" in manifest


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


def _write_claim_fixture(path: Path, poison: str, *, reordered: bool = False) -> None:
    if reordered:
        rows = [
            {"evidence": {"999": [{"label": poison, "sentences": [999]}]}, "claim": "alpha claim", "id": 1},
            {"claim": "beta claim", "id": 2, "evidence": {"888": [{"label": poison, "sentences": [888]}]}},
        ]
    else:
        rows = [
            {"id": 1, "claim": "alpha claim", "evidence": {"999": [{"label": poison, "sentences": [999]}]}},
            {"id": 2, "claim": "beta claim", "evidence": {"888": [{"label": poison, "sentences": [888]}]}},
        ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class _FixedRetriever:
    def retrieve(self, claim: str, *, top_k: int) -> list[dict[str, object]]:
        assert top_k == 20
        return [
            {
                "doc_id": rank,
                "rank": rank,
                "title": f"document {rank}",
                "abstract": [f"sentence {rank} a", f"sentence {rank} b", f"sentence {rank} c"],
                "bm25_score": float(10 - rank),
            }
            for rank in range(1, 6)
        ]


class _FixedSelector:
    def select(self, claim: str, document: dict[str, object], *, top_n: int) -> list[dict[str, object]]:
        assert top_n == 3
        return [
            {
                "sentence_index": index,
                "selected_rank": index + 1,
                "selection_score": float(3 - index),
                "sentence_text": str(document["abstract"][index]),
            }
            for index in range(3)
        ]


def _scoring_projection(path: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    claims = load_claim_projections(path, expected_count=2)
    retrieval = build_blind_retrieval_records(
        claims, _FixedRetriever(), _FixedSelector(), top_k=20, top_sentences=3
    )
    pairs = build_e1_pairs(retrieval)
    predictions = []
    for pair in pairs:
        label = "entailment" if int(pair["doc_rank"]) == 1 else "neutral"
        probabilities = {
            "contradiction": 0.1,
            "entailment": 0.8 if label == "entailment" else 0.1,
            "neutral": 0.1 if label == "entailment" else 0.8,
        }
        predictions.append({**pair, "predicted_nli_label": label, "probabilities": probabilities})
    final = finalize_e1_blind(retrieval, predictions)
    features = [
        {"claim_id": row["claim_id"], **extract_features(row, retrieval[index])}
        for index, row in enumerate(final)
    ]
    risks = score_frozen_models(load_verified_numeric_models(ROOT), features)
    scoring = [
        {**row, "risk_B1": risks["B1"][index], "risk_EARS": risks["EARS"][index]}
        for index, row in enumerate(features)
    ]
    return pairs, features, scoring


def test_annotation_poisoning_cannot_change_scoring_inputs_or_outputs(tmp_path: Path) -> None:
    support = tmp_path / "support.jsonl"
    contradict = tmp_path / "contradict.jsonl"
    _write_claim_fixture(support, "SUPPORT")
    _write_claim_fixture(contradict, "CONTRADICT", reordered=True)
    assert load_claim_projections(support) == load_claim_projections(contradict)
    assert _scoring_projection(support) == _scoring_projection(contradict)


@pytest.mark.parametrize(
    "content,match",
    [
        ('{"id":1,"claim":"a"}\n{"id":1,"claim":"b"}\n', "Duplicate claim ID"),
        ('{"id":1,"id":2,"claim":"a"}\n', "Duplicate top-level key"),
        ('{"id":1,"evidence":{}}\n', "must contain id and claim"),
        ('{"id":1,"claim":"a","evidence": BROKEN}\n', "Invalid JSON value"),
        ('{"id":"1","claim":"a"}\n', "not an integer"),
    ],
)
def test_restricted_claim_projection_rejects_invalid_records(
    tmp_path: Path, content: str, match: str
) -> None:
    path = tmp_path / "claims.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_claim_projections(path)


def test_partition_discovery_does_not_call_full_record_loader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path
    (root / "splits").mkdir()
    (root / "data/raw/scifact").mkdir(parents=True)
    split = {
        "outer_splits": {
            "fit": {"claim_ids": [1]},
            "calibration": {"claim_ids": [2]},
            "internal_test": {"claim_ids": [3]},
        }
    }
    write_json(root / "splits/train_split_manifest.json", split)
    dev_rows = [
        {"evidence": {"9": [{"label": "POISON", "sentences": [9]}]}, "claim": f"dev {index}", "id": index}
        for index in range(1, 301)
    ]
    (root / "data/raw/scifact/claims_dev.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in dev_rows), encoding="utf-8"
    )
    monkeypatch.setattr(
        "scripts.run_upgrade_v2_inference.load_jsonl",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("full-record loader called")),
    )
    ids = _partition_ids(root, "e1")
    assert len(ids["dev"]) == 300


def test_train_dev_numeric_id_collision_preserves_partition_identity(tmp_path: Path) -> None:
    (tmp_path / "data/raw/scifact").mkdir(parents=True)
    (tmp_path / "data/raw/scifact/claims_train.jsonl").write_text(
        json.dumps({"id": 1, "claim": "train one", "evidence": {}}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "data/raw/scifact/claims_dev.jsonl").write_text(
        json.dumps({"claim": "dev one", "evidence": {"x": []}, "id": 1}) + "\n",
        encoding="utf-8",
    )
    rows = _claim_rows(tmp_path, {"fit": {1}, "dev": {1}})
    assert {(row["partition"], row["claim"]) for row in rows} == {
        ("fit", "train one"),
        ("dev", "dev one"),
    }


def test_overlap_sensitivity_is_deterministic_and_handles_empty_subset() -> None:
    parts = {
        "fit": [{"id": 1, "claim": "same claim", "cited_doc_ids": [10]}],
        "calibration": [],
        "internal_test": [],
        "dev": [
            {"id": 101, "claim": "Same, claim!", "cited_doc_ids": [20]},
            {"id": 102, "claim": "different", "cited_doc_ids": [10]},
        ],
    }
    frozen = [
        {"claim_id": 101, "group_id": 0, "gold_label": "SUPPORT", "predicted_label": "SUPPORT", "y_error": 0, "risk_frozen_B1": 0.1, "risk_frozen_EARS": 0.2},
        {"claim_id": 102, "group_id": 1, "gold_label": "CONTRADICT", "predicted_label": "SUPPORT", "y_error": 1, "risk_frozen_B1": 0.9, "risk_frozen_EARS": 0.8},
    ]
    first = overlap_sensitivity(parts, frozen)
    second = overlap_sensitivity(parts, frozen)
    assert first == second
    by_name = {row["analysis"]: row for row in first}
    assert by_name["normalized_claim_text_exclusion_claim_level"]["excluded_claim_ids"] == [101]
    assert by_name["shared_cited_document_exclusion_claim_level"]["excluded_claim_ids"] == [102]
    assert all(row["status"] == "INSUFFICIENT SAMPLE SIZE FOR RELIABLE COMPARISON" for row in first)


def test_historical_and_corrected_manifests_verify_every_listed_artifact() -> None:
    for directory in (RESULTS, CORRECTED):
        manifest = json.loads((directory / "analysis_manifest.json").read_text())
        for relative, expected in manifest["artifacts_sha256"].items():
            path = directory / relative
            assert path.is_file(), relative
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative


def test_corrective_replay_is_exact_and_evidence_level_is_honest() -> None:
    comparison = json.loads((CORRECTED / "corrective_inference_equivalence.json").read_text())
    assert comparison["historical_dev_labels_previously_observed"] is True
    for verifier, expected_count, expected_hash in (
        ("e1", 1109, "3c1ea9104569f18882881d5ff2861696c06ed723fff208f66fd0e7a60f35c941"),
        ("e1_v2", 827, "e508ae3574534f9a5541058c978685b89876abe3548e0d59d6d2e8d4ca35774f"),
    ):
        row = comparison["comparisons"][verifier]
        assert row["status"] == "VERIFIED"
        assert row["corrected_claim_count"] == row["historical_claim_count"] == expected_count
        assert row["predicted_label_differences"] == 0
        assert row["scoring_rows_with_any_difference"] == 0
        assert row["maximum_absolute_numeric_difference"] == 0.0
        assert row["corrected_private_artifact_sha256"] == row["historical_private_artifact_sha256"] == expected_hash
        manifest = json.loads((CORRECTED / f"corrected_blind_{verifier}_manifest.json").read_text())
        assert manifest["evidence_class"] == "post_study_corrective_replay_not_fresh_confirmation"
        assert manifest["non_projection_annotation_values_materialized_for_scoring"] is False


def test_corrected_output_names_overlap_counts_and_perturbation_metadata() -> None:
    assert (CORRECTED / "marginal_permutation_importance.csv").is_file()
    assert not (CORRECTED / "conditional_permutation_importance.csv").exists()
    perturbations = {row["perturbation"] for row in _read_csv_path(CORRECTED / "perturbation_robustness.csv")}
    assert "inject_deterministically_sampled_out_of_retrieval_document" in perturbations
    assert "inject_irrelevant_top5_document" not in perturbations
    overlap = {
        row["analysis"]: row
        for row in json.loads((CORRECTED / "overlap_sensitivity.json").read_text())
    }
    duplicate = overlap["normalized_claim_text_exclusion_claim_level"]
    assert duplicate["excluded_claim_ids"] == [870, 1292]
    assert duplicate["eligible_claims_retained"] == 188
    shared = overlap["shared_cited_document_exclusion_claim_level"]
    assert shared["excluded_dev_claims"] == 196
    assert shared["total_dev_claims_retained"] == 104
    assert shared["eligible_claims_retained"] == 64
    assert shared["eligible_connected_groups_retained"] == 53
    assert shared["delta_aurc_ci_lower_95"] < 0 < shared["delta_aurc_ci_upper_95"]
    assert shared["delta_r80_ci_lower_95"] < 0 < shared["delta_r80_ci_upper_95"]


def _read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_authoritative_manuscript_and_pdfs_match_current_research_state() -> None:
    report = ROOT / "reports/research_upgrade_v2/RESEARCH_PAPER_V2.md"
    paper = ROOT / "paper/Trustworthy_AI_Research_Lab_V2_Final.md"
    assert report.read_bytes() == paper.read_bytes()
    text = paper.read_text(encoding="utf-8")
    assert "INCONCLUSIVE" in text
    assert "0.281575" in text and "0.288355" in text
    assert "Study period: 12 October 2026" not in text
    assert "that future date was not supportable" in text
    assert "No third-party or publicly registered preregistration" in text
    full_pdf = PdfReader(ROOT / "paper/Trustworthy_AI_Research_Lab_V2_Final.pdf")
    summary_pdf = PdfReader(ROOT / "paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf")
    assert len(full_pdf.pages) == 6
    assert len(summary_pdf.pages) == 1
    full_text = "\n".join(page.extract_text() or "" for page in full_pdf.pages)
    summary_text = "\n".join(page.extract_text() or "" for page in summary_pdf.pages)
    assert "Evidence-Aware Risk Scoring" in full_text
    assert "INCONCLUSIVE" in full_text and "INCONCLUSIVE" in summary_text
    assert "Study period: 12 October 2026" not in full_text


def test_final_correction_audit_reports_dev_metric_directions() -> None:
    text = (ROOT / "reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md").read_text(encoding="utf-8")
    assert "EARS achieved worse AURC but better R80 than B1 on SciFact Dev" in text
    assert "paired confidence intervals for both Dev endpoint differences include zero" in text
    assert "EARS is worse on both primary Dev endpoints" not in text


def test_contribution_docs_preserve_attribution_and_verification_boundaries() -> None:
    ownership = (ROOT / "RESEARCH_OWNERSHIP.md").read_text(encoding="utf-8")
    contribution = (ROOT / "docs/PERSONAL_RESEARCH_CONTRIBUTION.md").read_text(encoding="utf-8")
    for text in (ownership, contribution):
        assert "solo-human-owner" in text
        assert "substantially AI-assisted" in text
        assert "unaided" in text
    assert "H1 INCONCLUSIVE" in contribution
    assert "NOT VERIFIED" in contribution
    worksheet_path = ROOT / "portfolio/OWNER_VERIFICATION_WORKSHEET.md"
    if worksheet_path.exists():
        worksheet = worksheet_path.read_text(encoding="utf-8")
        assert "PENDING OWNER-PERFORMED VERIFICATION" in worksheet
        assert worksheet.count("Final status: `NOT VERIFIED`") == 5


def test_release_builder_excludes_caches_private_data_and_unsafe_paths(tmp_path: Path) -> None:
    output = tmp_path / "candidate.zip"
    manifest = build_release_candidate(ROOT, output)
    assert manifest["status"] == "PASS"
    assert manifest["file_count"] == len(manifest["files"])
    assert manifest["zip_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == manifest["file_count"]
        assert all(not name.startswith("/") and ".." not in Path(name).parts for name in names)
        assert not any(
            token in name
            for name in names
            for token in ("__pycache__", ".pytest_cache", ".venv", "data/raw/", ".cache/")
        )
        assert "paper/Trustworthy_AI_Research_Lab_V2_Final.pdf" in names
        assert "reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md" in names
        assert "docs/PERSONAL_RESEARCH_CONTRIBUTION.md" in names
        assert "portfolio/RESEARCH_CONTRIBUTION_PARAGRAPH.md" in names
        assert "portfolio/OWNER_VERIFICATION_WORKSHEET.md" not in names
