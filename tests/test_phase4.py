from __future__ import annotations

import csv
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]


def rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_phase4_metrics_match_frozen_phase3b_outputs() -> None:
    metrics = {row["method"]: row for row in rows("reports/phase3b/test_metrics.csv")}
    assert int(metrics["EARS"]["n"]) == 88
    assert round(float(metrics["B1"]["aurc"]), 6) == 0.300833
    assert round(float(metrics["EARS"]["aurc"]), 6) == 0.264987
    assert round(float(metrics["B1"]["sr80"]), 6) == 0.428571
    assert round(float(metrics["EARS"]["sr80"]), 6) == 0.457143
    assert int(metrics["B1"]["errors_at_80"]) == 30
    assert int(metrics["EARS"]["errors_at_80"]) == 32


def test_phase4_primary_intervals_and_conclusion_are_unchanged() -> None:
    contrasts = rows("reports/phase3b/paired_comparisons.csv")
    aurc, r80 = contrasts
    assert round(float(aurc["paired_difference"]), 6) == -0.035846
    assert round(float(aurc["ci_lower_95"]), 6) == -0.076087
    assert round(float(aurc["ci_upper_95"]), 6) == -0.003447
    assert round(float(r80["paired_difference"]), 6) == 0.028571
    assert round(float(r80["ci_lower_95"]), 6) == 0.0
    assert round(float(r80["ci_upper_95"]), 6) == 0.063492
    assert {row["preregistered_h1_status"] for row in contrasts} == {"INCONCLUSIVE"}


def test_phase4_public_narrative_preserves_result_boundaries() -> None:
    paths = [
        ROOT / "paper/EARS_selective_prediction_paper.md",
        ROOT / "release/github/README.md",
        ROOT / "release/github/LIMITATIONS.md",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "H1 INCONCLUSIVE" in text
        assert "Not Evaluated" in text
    readme = paths[1].read_text(encoding="utf-8")
    assert "0.300833" in readme and "0.264987" in readme
    assert "0.428571" in readme and "0.457143" in readme
    assert "not a fact-checking service" in readme.casefold()


def test_phase4_application_description_is_exactly_150_words() -> None:
    text = (ROOT / "application/PROJECT_DESCRIPTION_150_WORDS.md").read_text(encoding="utf-8")
    body = text.split("\n\n", 1)[1]
    assert len(body.split()) == 150


def test_phase4_pdf_lengths_and_figures() -> None:
    assert len(PdfReader(ROOT / "output/pdf/EARS_selective_prediction_paper.pdf").pages) == 8
    assert len(PdfReader(ROOT / "output/pdf/EARS_one_page_research_summary.pdf").pages) == 1
    for stem in (
        "figure_1_risk_coverage_fit_vs_test",
        "figure_2_aurc_and_r80_comparison",
        "figure_3_primary_bootstrap_intervals",
        "figure_4_no_relation_sensitivity",
        "table_1_representative_failure_cases",
    ):
        assert (ROOT / "reports/phase4/figures" / f"{stem}.png").stat().st_size > 10_000
        assert (ROOT / "reports/phase4/figures" / f"{stem}.svg").stat().st_size > 1_000


def test_phase4_release_candidate_excludes_private_artifacts() -> None:
    release = ROOT / "release/github"
    forbidden_names = {
        "claims_train.jsonl", "claims_dev.jsonl", "claims_test.jsonl",
        "corpus.jsonl", ".env", "secrets.toml",
    }
    forbidden_suffixes = {".joblib", ".pt", ".ckpt", ".safetensors"}
    files = [path for path in release.rglob("*") if path.is_file()]
    assert not [path for path in files if path.name in forbidden_names]
    assert not [path for path in files if path.suffix in forbidden_suffixes]
