#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import torch

from trustworthy_ai_lab.data import load_json, load_jsonl, write_json, write_jsonl
from trustworthy_ai_lab.nli import NLIEngine
from trustworthy_ai_lab.phase2_protocol import extract_features
from trustworthy_ai_lab.phase3b import (
    build_blind_retrieval_records,
    finalize_e1_blind,
    load_claim_texts_only,
    score_bundle,
    score_numeric_spec,
    sha256_file,
)
from trustworthy_ai_lab.pipeline import build_e1_pairs
from trustworthy_ai_lab.retrieval import BM25Retriever
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
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


def assert_label_blind(value: Any) -> None:
    forbidden = {"evidence", "gold", "correct", "eligible", "failure"}
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.casefold()
            if any(token in lowered for token in forbidden):
                raise RuntimeError(f"Label-derived field leaked into pre-label artifact: {key}")
            assert_label_blind(child)
    elif isinstance(value, list):
        for child in value:
            assert_label_blind(child)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    reports = root / "reports/phase3b"
    models = root / "models/phase3b"
    freeze_path = reports / "prediction_freeze_manifest.json"
    if freeze_path.exists():
        raise RuntimeError("Prediction freeze already exists; refusing to rerun or replace test predictions")

    model_manifest = load_json(models / "final_model_manifest.json")
    if model_manifest["status"] != "FINAL_MODELS_FROZEN_BEFORE_TEST_ACCESS" or model_manifest["internal_test_content_accessed_before_freeze"]:
        raise RuntimeError("Final model is not validly frozen")
    verify_map(root, model_manifest["code_sha256"])
    verify_map(root, model_manifest["artifact_sha256"])
    phase3a = load_json(root / "reports/phase3a/protocol_manifest.json")
    verify_map(root, phase3a["sha256"])
    if sha256_file(root / "reports/phase3a/protocol_manifest.json") != model_manifest["phase3a_protocol_manifest_sha256"]:
        raise RuntimeError("Phase 3A manifest changed after model freeze")

    split = load_json(root / "splits/train_split_manifest.json")
    test_ids = {int(value) for value in split["outer_splits"]["internal_test"]["claim_ids"]}
    if len(test_ids) != 141:
        raise RuntimeError("Internal Test membership is not exactly 141 unique IDs")
    train_path = root / "data/raw/scifact/claims_train.jsonl"
    corpus_path = root / "data/raw/scifact/corpus.jsonl"
    # This loader decodes only id and claim string; it never deserializes evidence.
    claims = load_claim_texts_only(train_path, test_ids)
    corpus = load_jsonl(corpus_path)
    config = load_json(root / "configs/phase1_baseline.json")
    started = time.perf_counter()
    torch.manual_seed(int(config["seed"]))
    retriever = BM25Retriever(corpus, **{key: config["bm25"][key] for key in ("k1", "b", "epsilon")})
    selector = IDFOverlapSentenceSelector(corpus)
    retrieval = build_blind_retrieval_records(claims, retriever, selector, top_k=20, top_sentences=3)
    pairs = build_e1_pairs(retrieval)
    if len(pairs) != 141 * 15:
        raise RuntimeError(f"Expected 2115 E1 pairs, found {len(pairs)}")

    nli = config["nli"]
    engine = NLIEngine(nli["model_id"], nli["revision"], device="cpu", max_length=nli["max_length"])
    smoke = [{"pair_id": "phase3b-smoke", "premise": "A trial reported no benefit.", "hypothesis": "The trial reported a benefit."}]
    cpu_smoke, cpu_stats = engine.predict(smoke, batch_size=1)
    formal_device = "cpu"
    mps_smoke = None
    fallback = None
    if torch.backends.mps.is_available():
        try:
            engine.move_to("mps")
            result, stats = engine.predict(smoke, batch_size=1)
            mps_smoke = {"prediction": result[0]["predicted_nli_label"], "elapsed_seconds": stats.elapsed_seconds}
            formal_device = "mps"
        except Exception as exc:
            fallback = f"MPS smoke failed: {type(exc).__name__}: {exc}"
            engine.move_to("cpu")
    else:
        fallback = "MPS unavailable; frozen fallback used CPU"
    pair_predictions, inference_stats = engine.predict(pairs, batch_size=nli["formal_batch_size"] if formal_device == "mps" else 4)
    baseline = finalize_e1_blind(retrieval, pair_predictions)
    if len(baseline) != 141 or {int(row["claim_id"]) for row in baseline} != test_ids:
        raise RuntimeError("Incomplete label-blind E1 results")
    retrieval_by_id = {int(row["claim_id"]): row for row in retrieval}
    feature_rows = [{"claim_id": int(row["claim_id"]), **extract_features(row, retrieval_by_id[int(row["claim_id"])])} for row in baseline]

    numeric = load_json(models / "final_model_numeric_spec.json")
    risk_rows = []
    max_delta = 0.0
    for row in feature_rows:
        risk_rows.append({"claim_id": int(row["claim_id"]), "risk_B0": 1.0 - float(row["F1_decision_confidence"])})
    for method in ("B1", "B2", "EARS"):
        bundle = joblib.load(models / f"final_{method.lower()}_model_bundle.joblib")
        joblib_scores = score_bundle(bundle, feature_rows)
        json_scores = score_numeric_spec(numeric["methods"][method], feature_rows)
        for target, left, right in zip(risk_rows, joblib_scores, json_scores):
            max_delta = max(max_delta, abs(left - right))
            target[f"risk_{method}"] = left
    if max_delta > 1e-12:
        raise RuntimeError(f"Test serialization mismatch: {max_delta}")

    assert_label_blind(retrieval)
    assert_label_blind(baseline)
    assert_label_blind(feature_rows)
    assert_label_blind(risk_rows)
    write_jsonl(reports / "test_retrieval_results_label_blind.jsonl", retrieval)
    write_jsonl(reports / "test_baseline_predictions.jsonl", baseline)
    write_csv(reports / "test_feature_matrix.csv", feature_rows)
    write_csv(reports / "test_risk_scores_prelabel.csv", risk_rows)
    metadata = {
        "completed_at_utc": utc_now(), "scope": "141 Internal Test claim texts; labels/evidence not deserialized",
        "claim_count": 141, "pair_count": len(pairs), "nli_model_id": nli["model_id"], "nli_revision": nli["revision"],
        "formal_device": formal_device, "mps_built": torch.backends.mps.is_built(), "mps_available": torch.backends.mps.is_available(),
        "cpu_smoke_prediction": cpu_smoke[0]["predicted_nli_label"], "cpu_smoke_elapsed_seconds": cpu_stats.elapsed_seconds,
        "mps_smoke": mps_smoke, "fallback": fallback, "formal_inference": dict(inference_stats.__dict__),
        "wall_seconds_including_retrieval": time.perf_counter() - started,
        "process_max_rss_bytes_macos": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "joblib_json_max_absolute_difference": max_delta,
    }
    write_json(reports / "inference_metadata.json", metadata)
    frozen_names = ["test_retrieval_results_label_blind.jsonl", "test_baseline_predictions.jsonl", "test_feature_matrix.csv", "test_risk_scores_prelabel.csv", "inference_metadata.json"]
    freeze = {
        "protocol_version": "phase3a-v1.0.0", "created_at_utc": utc_now(), "status": "PREDICTIONS_FROZEN_BEFORE_LABEL_ACCESS",
        "labels_or_gold_evidence_accessed": False, "claim_texts_accessed": True, "claims": 141,
        "model_manifest_sha256": sha256_file(models / "final_model_manifest.json"),
        "artifact_sha256": {f"reports/phase3b/{name}": sha256_file(reports / name) for name in frozen_names},
        "source_code_sha256": model_manifest["code_sha256"],
    }
    write_json(freeze_path, freeze)
    print(json.dumps({"status": freeze["status"], "claims": 141, "pairs": len(pairs), "device": formal_device, "freeze_sha256": sha256_file(freeze_path)}, indent=2))


if __name__ == "__main__":
    main()
