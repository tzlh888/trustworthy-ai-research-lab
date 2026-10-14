#!/usr/bin/env python3
"""Label-blind inference for the Research Upgrade v2 study.

The loader extracts only claim IDs and claim strings from labeled JSONL before
scoring. Full retrieval and pair records are kept under the ignored .cache
directory; the public result directory receives only compact, label-free rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from demo.cloud_artifacts import load_verified_numeric_models, score_frozen_models
from trustworthy_ai_lab.data import load_json, load_jsonl, write_json, write_jsonl
from trustworthy_ai_lab.nli import NLIEngine
from trustworthy_ai_lab.phase2_protocol import extract_features
from trustworthy_ai_lab.phase3b import (
    build_blind_retrieval_records,
    finalize_e1_blind,
    load_claim_texts_only,
    sha256_file,
)
from trustworthy_ai_lab.pipeline import build_e1_pairs
from trustworthy_ai_lab.retrieval import BM25Retriever
from trustworthy_ai_lab.sentence_selection import IDFOverlapSentenceSelector


VERIFIERS = {
    "e1": (
        "cross-encoder/nli-distilroberta-base",
        "b14d131f9d32668a5e6a982729b57ff6ed5dfcbd",
    ),
    "e1_v2": (
        "cross-encoder/nli-deberta-v3-small",
        "e9890682d9e4279b7ae6d0fcfb435a43206280ec",
    ),
}


def _partition_ids(root: Path, verifier: str) -> dict[str, set[int]]:
    split = load_json(root / "splits/train_split_manifest.json")
    result = {
        "fit": set(map(int, split["outer_splits"]["fit"]["claim_ids"])),
        "dev": {int(row["id"]) for row in load_jsonl(root / "data/raw/scifact/claims_dev.jsonl")},
    }
    if verifier == "e1":
        result["calibration"] = set(
            map(int, split["outer_splits"]["calibration"]["claim_ids"])
        )
        result["internal_test"] = set(
            map(int, split["outer_splits"]["internal_test"]["claim_ids"])
        )
    return result


def _claim_rows(root: Path, partition_ids: dict[str, set[int]]) -> list[dict[str, Any]]:
    train_ids = set().union(
        *(ids for name, ids in partition_ids.items() if name != "dev")
    )
    train = load_claim_texts_only(
        root / "data/raw/scifact/claims_train.jsonl", train_ids
    ) if train_ids else []
    dev = load_claim_texts_only(
        root / "data/raw/scifact/claims_dev.jsonl", partition_ids["dev"]
    )
    owner = {
        claim_id: partition
        for partition, ids in partition_ids.items()
        for claim_id in ids
    }
    rows = [{**row, "partition": owner[int(row["id"])]} for row in train + dev]
    if len(rows) != len({(row["partition"], int(row["id"])) for row in rows}):
        raise ValueError("Partitioned claims must be unique")
    return sorted(rows, key=lambda row: (row["partition"], int(row["id"])))


def _injected_document(
    claim_id: int,
    retrieved_ids: set[int],
    corpus: list[dict[str, Any]],
) -> dict[str, Any]:
    digest = hashlib.sha256(f"20261014:inject:{claim_id}".encode()).digest()
    start = int.from_bytes(digest[:8], "big") % len(corpus)
    for offset in range(len(corpus)):
        candidate = corpus[(start + offset) % len(corpus)]
        if int(candidate["doc_id"]) not in retrieved_ids:
            return candidate
    raise RuntimeError("No deterministic injection document available")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--verifier", choices=sorted(VERIFIERS), required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    root = args.root.resolve()
    protocol = root / "configs/research_upgrade_v2_protocol.json"
    protocol_hash = sha256_file(protocol)
    if protocol_hash != "70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301":
        raise RuntimeError("Research Upgrade v2 protocol changed after freeze")
    expected = load_json(protocol)["primary_new_evaluation"]
    for path, digest in (
        (root / "data/raw/scifact/claims_dev.jsonl", expected["claims_sha256"]),
        (root / "data/raw/scifact/corpus.jsonl", expected["corpus_sha256"]),
    ):
        if sha256_file(path) != digest:
            raise RuntimeError(f"Input hash mismatch: {path.name}")

    started = datetime.now(timezone.utc).isoformat()
    partition_ids = _partition_ids(root, args.verifier)
    claims = _claim_rows(root, partition_ids)
    corpus = load_jsonl(root / "data/raw/scifact/corpus.jsonl")
    retriever = BM25Retriever(corpus, k1=1.5, b=0.75, epsilon=0.25)
    selector = IDFOverlapSentenceSelector(corpus)
    blind = build_blind_retrieval_records(
        [{"id": row["id"], "claim": row["claim"]} for row in claims],
        retriever,
        selector,
        top_k=20,
        top_sentences=3,
    )
    partition_by_id = {(row["partition"], int(row["id"])) for row in claims}
    # SciFact train/dev IDs overlap numerically, so restore partition by claim text.
    partition_by_key = {(row["claim"], int(row["id"])): row["partition"] for row in claims}
    for record in blind:
        record["partition"] = partition_by_key[(record["claim_text"], int(record["claim_id"]))]

    pairs = build_e1_pairs(blind)
    model_id, revision = VERIFIERS[args.verifier]
    engine = NLIEngine(model_id, revision, device="cpu", max_length=512)
    device = "cpu"
    device_note = "MPS unavailable"
    if torch.backends.mps.is_available():
        try:
            engine.move_to("mps")
            device = "mps"
            device_note = "MPS selected after successful model transfer"
        except Exception as exc:
            engine.move_to("cpu")
            device_note = f"MPS transfer failed: {type(exc).__name__}: {exc}"
    predictions, stats = engine.predict(
        pairs, batch_size=args.batch_size if device == "mps" else min(4, args.batch_size)
    )
    final = finalize_e1_blind(blind, predictions)

    # Precompute the injected-evidence perturbation only for Dev. The deterministic
    # document is absent from the original top-20 and receives no artificial score.
    injection_pairs: list[dict[str, Any]] = []
    injection_meta: dict[int, dict[str, Any]] = {}
    if args.verifier == "e1":
        corpus_sorted = sorted(corpus, key=lambda row: int(row["doc_id"]))
        for record in blind:
            if record["partition"] != "dev":
                continue
            doc = _injected_document(
                int(record["claim_id"]),
                {int(item["doc_id"]) for item in record["retrieved_documents"]},
                corpus_sorted,
            )
            shell = {
                "doc_id": int(doc["doc_id"]),
                "title": doc["title"],
                "abstract": doc["abstract"],
            }
            selected = selector.select(record["claim_text"], shell, top_n=3)
            injection_meta[int(record["claim_id"])] = {
                "doc_id": int(doc["doc_id"]), "selected_sentences": selected
            }
            for chosen in selected:
                injection_pairs.append({
                    "pair_id": f"inject:{record['claim_id']}:{doc['doc_id']}:{chosen['sentence_index']}",
                    "experiment": "research_upgrade_v2_injected_irrelevant_document",
                    "claim_id": int(record["claim_id"]),
                    "doc_id": int(doc["doc_id"]),
                    "doc_rank": 5,
                    "document_title": doc["title"],
                    "sentence_index": chosen["sentence_index"],
                    "selected_sentence_rank": chosen["selected_rank"],
                    "sentence_selection_score": chosen["selection_score"],
                    "premise": chosen["sentence_text"],
                    "hypothesis": record["claim_text"],
                    "provenance": "deterministic synthetic irrelevant-evidence perturbation",
                })
    injection_predictions: list[dict[str, Any]] = []
    injection_stats = None
    if injection_pairs:
        injection_predictions, injection_stats = engine.predict(
            injection_pairs,
            batch_size=args.batch_size if device == "mps" else min(4, args.batch_size),
        )

    cache = root / ".cache/research_upgrade_v2" / args.verifier
    cache.mkdir(parents=True, exist_ok=True)
    write_jsonl(cache / "retrieval.jsonl", blind)
    write_jsonl(cache / "pair_predictions.jsonl", predictions)
    write_jsonl(cache / "injection_predictions.jsonl", injection_predictions)
    write_json(cache / "injection_meta.json", injection_meta)

    retrieval_by_key = {
        (row["partition"], int(row["claim_id"])): row for row in blind
    }
    compact = []
    for row in final:
        partition = partition_by_key[(row["claim_text"], int(row["claim_id"]))]
        retrieval = retrieval_by_key[(partition, int(row["claim_id"]))]
        values = {
            "claim_id": int(row["claim_id"]),
            "partition": partition,
            "predicted_label": row["predicted_claim_label"],
            "support_contradict_conflict": bool(row["support_contradict_conflict"]),
            "non_neutral_candidate_count": int(row["non_neutral_candidate_count"]),
            **extract_features(row, retrieval),
        }
        compact.append(values)
    if args.verifier == "e1":
        numeric = load_verified_numeric_models(root)
        risks = score_frozen_models(numeric, compact)
        for index, row in enumerate(compact):
            row["risk_frozen_B1"] = risks["B1"][index]
            row["risk_frozen_EARS"] = risks["EARS"][index]

    output = root / "reports/research_upgrade_v2/results"
    output.mkdir(parents=True, exist_ok=True)
    compact_path = cache / f"blind_{args.verifier}_features.jsonl"
    write_jsonl(compact_path, compact)
    manifest = {
        "status": "PREDICTIONS_FROZEN_BEFORE_V2_EVALUATION_LABEL_ACCESS",
        "verifier": args.verifier,
        "model_id": model_id,
        "revision": revision,
        "protocol_sha256": protocol_hash,
        "partition_counts": {name: len(ids) for name, ids in partition_ids.items()},
        "claim_count": len(compact),
        "pair_count": len(predictions),
        "injected_pair_count": len(injection_predictions),
        "device": device,
        "device_note": device_note,
        "inference_stats": stats.__dict__,
        "injection_stats": None if injection_stats is None else injection_stats.__dict__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "private_cache_artifact_sha256": {
            f"blind_{args.verifier}_features.jsonl": sha256_file(compact_path)
        },
        "gold_labels_deserialized_for_scoring": False,
    }
    write_json(output / f"blind_{args.verifier}_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
