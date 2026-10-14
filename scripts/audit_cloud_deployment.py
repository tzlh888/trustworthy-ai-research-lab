#!/usr/bin/env python3
"""Audit public cloud artifacts and optionally compare trusted Phase 3B models.

The public-only checks never deserialize pickle/joblib data. The optional
``--original-root`` comparison verifies the known Phase 3B SHA-256 digests
before loading those local, project-owned bundles.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from demo.cloud_artifacts import (
    MODEL_MANIFEST_SHA256,
    MODEL_NUMERIC_SPEC_SHA256,
    SCIFACT_CORPUS_BYTES,
    SCIFACT_CORPUS_SHA256,
    load_verified_numeric_models,
    score_frozen_models,
)


DEPLOYMENT_FILES = {
    "configs/phase1_baseline.json": "Pinned NLI model and inference configuration",
    "demo/app.py": "Streamlit entry point",
    "demo/cloud_artifacts.py": "Verified corpus and numeric-model loader",
    "demo/core.py": "Label-free demo retrieval and frozen aggregation helpers",
    "demo/frozen_parameters/final_model_manifest.json": "Original Phase 3B freeze manifest",
    "demo/frozen_parameters/final_model_numeric_spec.json": "Lossless B1/EARS numeric parameters",
    "requirements.txt": "Streamlit Community Cloud dependencies",
}

TRUSTED_JOBLIB_SHA256 = {
    "B1": "d55844a5b75ab11b62772dca4ccc649c5395b1d3f22df4e8b09de7a11087a7cc",
    "EARS": "5034ebf69dcc98eb4c5f275c77451c8d611f730a9369e01bc700d363d3328d11",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deployment_manifest(root: Path) -> dict[str, Any]:
    files = []
    for relative, role in DEPLOYMENT_FILES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        files.append(
            {
                "path": relative,
                "role": role,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "schema_version": 1,
        "scope": "Streamlit Cloud deployment-critical public files",
        "corpus": {
            "included_in_repository": False,
            "runtime_bytes": SCIFACT_CORPUS_BYTES,
            "runtime_sha256": SCIFACT_CORPUS_SHA256,
        },
        "frozen_model_source_hashes": {
            "manifest_sha256": MODEL_MANIFEST_SHA256,
            "numeric_spec_sha256": MODEL_NUMERIC_SPEC_SHA256,
        },
        "files": files,
    }


def privacy_scan(root: Path) -> dict[str, Any]:
    # Local dependency environments are neither deployment inputs nor repository
    # artifacts.  Scanning them creates false positives from third-party package
    # metadata while leaving the project-owned tree fully covered.
    ignored_parts = {
        ".git",
        ".cache",
        ".pytest_cache",
        ".venv",
        "venv",
        "__pycache__",
    }
    forbidden_names = {
        ".env",
        "secrets.toml",
        "corpus.jsonl",
        "claims_train.jsonl",
        "claims_dev.jsonl",
        "claims_test.jsonl",
    }
    forbidden_suffixes = {".joblib", ".pkl", ".pickle", ".pt", ".bin", ".ckpt", ".safetensors"}
    text_suffixes = {".md", ".py", ".toml", ".txt", ".json", ".yaml", ".yml", ".cff", ".csv"}
    patterns = {
        "macOS user path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
        "private tool workspace": re.compile(
            rf"(?:\.{''.join(('co', 'dex'))}|{'-'.join(('codex', 'research', 'task'))})",
            re.IGNORECASE,
        ),
        "OpenAI-like secret": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "GitHub-like token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
        "assigned secret": re.compile(
            r"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"
        ),
    }
    files_scanned = 0
    findings: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.relative_to(root).parts):
            continue
        files_scanned += 1
        relative = path.relative_to(root).as_posix()
        if path.name in forbidden_names or path.suffix.casefold() in forbidden_suffixes:
            findings.append({"path": relative, "finding": "forbidden public artifact"})
        if path.suffix.casefold() in text_suffixes or path.name in {".gitignore", ".env.example"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            for name, pattern in patterns.items():
                if pattern.search(text):
                    findings.append({"path": relative, "finding": name})
    return {"files_scanned": files_scanned, "findings": findings, "passed": not findings}


def compare_trusted_original(root: Path, original_root: Path) -> dict[str, Any]:
    """Compare public numeric scoring to hash-verified, project-owned joblib."""
    import joblib  # Imported only for the explicitly requested trusted-local comparison.

    models = load_verified_numeric_models(root)
    feature_path = original_root / "reports/phase3b/test_feature_matrix.csv"
    with feature_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    numeric = score_frozen_models(models, rows)
    differences = {}
    for method, filename in {
        "B1": "final_b1_model_bundle.joblib",
        "EARS": "final_ears_model_bundle.joblib",
    }.items():
        path = original_root / "models/phase3b" / filename
        actual_hash = sha256_file(path)
        if actual_hash != TRUSTED_JOBLIB_SHA256[method]:
            raise RuntimeError(f"Trusted-local {method} bundle hash mismatch; refusing to deserialize it.")
        bundle = joblib.load(path)
        matrix = bundle["preprocessor"].transform(rows)
        reference = bundle["model"].predict_proba(matrix)[:, 1]
        differences[method] = float(
            np.max(np.abs(reference - np.asarray(numeric[method], dtype=float)))
        )
    return {
        "rows_checked": len(rows),
        "tolerance": 1e-12,
        "max_absolute_difference": differences,
        "passed": all(value <= 1e-12 for value in differences.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    result: dict[str, Any] = {
        "manifest": deployment_manifest(root),
        "privacy_scan": privacy_scan(root),
    }
    load_verified_numeric_models(root)
    result["public_model_integrity"] = {"passed": True}
    if args.original_root:
        result["trusted_original_numeric_comparison"] = compare_trusted_original(
            root, args.original_root.resolve()
        )
    passed = result["privacy_scan"]["passed"] and result["public_model_integrity"]["passed"]
    if "trusted_original_numeric_comparison" in result:
        passed = passed and result["trusted_original_numeric_comparison"]["passed"]
    result["overall_status"] = "PASS" if passed else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
