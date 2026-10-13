"""Public-repository test boundary.

The public checkout intentionally excludes raw SciFact claims, claim-level
predictions, full Phase 1/2/3 reports, and joblib bundles. Their frozen tests
remain executable in the private reproducibility package. Public CI exercises
the deployable code and aggregate-result checks without recreating excluded
artifacts.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ARTIFACT_MODULES = {
    "test_phase0.py",
    "test_phase1.py",
    "test_phase2a.py",
    "test_phase2b.py",
    "test_phase2c.py",
    "test_phase3a.py",
    "test_phase3b.py",
}


def pytest_collection_modifyitems(config, items) -> None:
    full_requested = os.environ.get("RUN_FULL_RESEARCH_TESTS") == "1"
    private_ready = (
        (ROOT / "data/raw/scifact/claims_train.jsonl").is_file()
        and (ROOT / "reports/phase1/e1_fit_predictions.jsonl").is_file()
        and (ROOT / "models/phase3b/final_b1_model_bundle.joblib").is_file()
    )
    if full_requested and not private_ready:
        raise pytest.UsageError(
            "RUN_FULL_RESEARCH_TESTS=1 requires the complete private reproducibility artifacts."
        )
    if private_ready:
        return
    marker = pytest.mark.skip(
        reason="requires intentionally excluded private/full research artifacts"
    )
    for item in items:
        if Path(str(item.fspath)).name in PRIVATE_ARTIFACT_MODULES:
            item.add_marker(marker)
