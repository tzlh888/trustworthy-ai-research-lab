#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from trustworthy_ai_lab.data import (
    load_json,
    load_phase1_data,
    sha256,
    write_json,
    write_jsonl,
)
from trustworthy_ai_lab.metrics import (
    classification_metrics,
    error_breakdown,
    probability_summary,
    retrieval_metrics,
    sentence_selection_metrics,
)
from trustworthy_ai_lab.nli import NLIEngine
from trustworthy_ai_lab.pipeline import (
    build_e0_pairs,
    build_e1_pairs,
    build_retrieval_records,
    finalize_e0,
    finalize_e1,
)
from trustworthy_ai_lab.retrieval import BM25Retriever
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


PACKAGES = [
    "torch",
    "transformers",
    "sentence-transformers",
    "scikit-learn",
    "numpy",
    "pandas",
    "scipy",
    "rank-bm25",
    "pytest",
]


def dataclass_dict(value: Any) -> dict[str, Any]:
    return dict(value.__dict__)


def verify_phase0_hashes(root: Path) -> dict[str, str]:
    frozen = load_json(root / "reports" / "phase0_frozen_hashes.json")["sha256"]
    mismatches = {}
    for relative, expected in frozen.items():
        actual = sha256(root / relative)
        if actual != expected:
            mismatches[relative] = f"expected {expected}, got {actual}"
    if mismatches:
        raise RuntimeError(f"Frozen Phase 0 artifact mismatch: {mismatches}")
    return frozen


def fold_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    result = {}
    for fold in sorted({row["fit_fold"] for row in records}):
        result[fold] = classification_metrics(
            [row for row in records if row["fit_fold"] == fold]
        )
    return result


def artifact_hashes(output_dir: Path) -> dict[str, str]:
    return {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file() and path.name != "run_manifest.json"
    }


def main() -> None:
    started_at = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    config = load_json(args.config)
    if config["data_policy"]["allowed_claim_partition"] != "fit":
        raise ValueError("Phase 1 only permits fit")
    frozen_hashes = verify_phase0_hashes(root)

    claims, corpus, folds, manifest = load_phase1_data(
        root / "splits" / "train_split_manifest.json",
        root / "data" / "raw" / "scifact" / "claims_train.jsonl",
        root / "data" / "raw" / "scifact" / "corpus.jsonl",
    )
    if len(claims) != config["data_policy"]["allowed_claim_count"]:
        raise ValueError("Unexpected fit claim count")
    fit_ids = set(manifest["outer_splits"]["fit"]["claim_ids"])
    if {row["id"] for row in claims} != fit_ids:
        raise ValueError("Loaded claim IDs are not exactly fit")

    torch.manual_seed(config["seed"])
    retriever = BM25Retriever(corpus, **{
        key: config["bm25"][key] for key in ("k1", "b", "epsilon")
    })
    selector = IDFOverlapSentenceSelector(corpus)
    retrieval_records, retrieval_timing = build_retrieval_records(
        claims,
        folds,
        retriever,
        selector,
        top_k=20,
        sentences_per_document=config["sentence_selection"]["selected_sentences_per_document"],
    )
    retrieval_report = {
        "scope": "fit only",
        "parameters": config["bm25"],
        "timing": retrieval_timing,
        "metrics": retrieval_metrics(retrieval_records),
        "sentence_selection_at_5": sentence_selection_metrics(retrieval_records, 5),
        "sentence_selection_at_20": sentence_selection_metrics(retrieval_records, 20),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output_dir / "fit_retrieval_results.jsonl", retrieval_records)
    write_json(args.output_dir / "retrieval_metrics.json", retrieval_report)

    nli_config = config["nli"]
    engine = NLIEngine(
        nli_config["model_id"],
        nli_config["revision"],
        device="cpu",
        max_length=nli_config["max_length"],
    )
    smoke_pairs = [
        {
            "pair_id": "smoke_entailment",
            "premise": "A man is eating pizza.",
            "hypothesis": "A man eats something.",
        },
        {
            "pair_id": "smoke_contradiction",
            "premise": "The trial found no reduction in mortality.",
            "hypothesis": "The trial reduced mortality.",
        },
    ]
    cpu_predictions, cpu_stats = engine.predict(
        smoke_pairs, batch_size=nli_config["cpu_smoke_batch_size"]
    )
    hardware = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "torch": torch.__version__,
        "mps_built": torch.backends.mps.is_built(),
        "mps_available": torch.backends.mps.is_available(),
        "cpu_smoke": {
            "stats": dataclass_dict(cpu_stats),
            "predicted_labels": [row["predicted_nli_label"] for row in cpu_predictions],
        },
        "mps_smoke": None,
        "fallback": None,
    }
    formal_device = "cpu"
    if torch.backends.mps.is_available():
        try:
            engine.move_to("mps")
            mps_predictions, mps_stats = engine.predict(
                smoke_pairs, batch_size=nli_config["cpu_smoke_batch_size"]
            )
            max_difference = max(
                abs(
                    cpu_predictions[index]["probabilities"][label]
                    - mps_predictions[index]["probabilities"][label]
                )
                for index in range(len(smoke_pairs))
                for label in ("contradiction", "entailment", "neutral")
            )
            hardware["mps_smoke"] = {
                "stats": dataclass_dict(mps_stats),
                "predicted_labels": [row["predicted_nli_label"] for row in mps_predictions],
                "max_absolute_probability_difference_from_cpu": max_difference,
            }
            formal_device = "mps"
        except Exception as exc:  # recorded fallback is preferable to a false MPS claim
            hardware["fallback"] = f"MPS smoke failed: {type(exc).__name__}: {exc}"
            engine.move_to("cpu")
    else:
        hardware["fallback"] = "MPS unavailable; formal inference used CPU"
    hardware["formal_inference_device"] = formal_device

    corpus_by_id = {row["doc_id"]: row for row in corpus}
    e0_pairs = build_e0_pairs(claims, corpus_by_id)
    e0_predictions, e0_stats = engine.predict(
        e0_pairs, batch_size=nli_config["formal_batch_size"] if formal_device == "mps" else 4
    )
    e0_records = finalize_e0(e0_predictions, folds)
    e0_report = {
        "scope": "fit-only oracle diagnostic; gold rationale text; not end-to-end",
        "metrics": classification_metrics(e0_records),
        "fold_metrics": fold_metrics(e0_records),
        "inference": dataclass_dict(e0_stats),
    }
    write_jsonl(args.output_dir / "e0_gold_evidence_predictions.jsonl", e0_records)
    write_json(args.output_dir / "e0_metrics.json", e0_report)

    e1_pairs = build_e1_pairs(retrieval_records)
    e1_pair_predictions, e1_stats = engine.predict(
        e1_pairs, batch_size=nli_config["formal_batch_size"] if formal_device == "mps" else 4
    )
    e1_records = finalize_e1(retrieval_records, e1_pair_predictions)
    if {row["claim_id"] for row in e1_records} != fit_ids:
        raise ValueError("E1 output is not exactly fit")
    e1_report = {
        "scope": "fit-only end-to-end baseline; empty-evidence claims excluded from label metrics",
        "metrics": classification_metrics(e1_records),
        "fold_metrics": fold_metrics(e1_records),
        "probability_summary_uncalibrated": probability_summary(e1_records),
        "error_breakdown": error_breakdown(e1_records),
        "inference": dataclass_dict(e1_stats),
    }
    write_jsonl(args.output_dir / "e1_fit_predictions.jsonl", e1_records)
    write_json(args.output_dir / "e1_metrics.json", e1_report)

    hardware["formal_e0"] = dataclass_dict(e0_stats)
    hardware["formal_e1"] = dataclass_dict(e1_stats)
    hardware["process_max_rss_bytes_macos"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if formal_device == "mps":
        hardware["mps_current_allocated_bytes_after_runs"] = torch.mps.current_allocated_memory()
        hardware["mps_driver_allocated_bytes_after_runs"] = torch.mps.driver_allocated_memory()
    write_json(args.output_dir / "hardware_report.json", hardware)

    run_manifest = {
        "run_id": config["run_id"],
        "phase": 1,
        "scope": "fit only",
        "config_sha256": sha256(args.config),
        "phase0_frozen_hashes_verified": frozen_hashes,
        "data_hashes": {
            "claims_train.jsonl": sha256(root / "data/raw/scifact/claims_train.jsonl"),
            "corpus.jsonl": sha256(root / "data/raw/scifact/corpus.jsonl"),
            "train_split_manifest.json": sha256(root / "splits/train_split_manifest.json"),
        },
        "seed": config["seed"],
        "model_id": nli_config["model_id"],
        "model_revision": nli_config["revision"],
        "dependencies": {name: importlib.metadata.version(name) for name in PACKAGES},
        "fit_claim_ids_sha256": hashlib.sha256(
            json.dumps(sorted(fit_ids)).encode("utf-8")
        ).hexdigest(),
        "sealed_partitions_predicted": [],
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_sha256": artifact_hashes(args.output_dir),
    }
    write_json(args.output_dir / "run_manifest.json", run_manifest)


if __name__ == "__main__":
    main()
