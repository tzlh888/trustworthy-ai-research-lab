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
    load_claim_projections,
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
        "dev": {
            int(row["id"])
            for row in load_claim_projections(
                root / "data/raw/scifact/claims_dev.jsonl", expected_count=300
            )
        },
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
    train_owner = {
        claim_id: partition
        for partition, ids in partition_ids.items()
        if partition != "dev"
        for claim_id in ids
    }
    rows = [
        {**row, "partition": train_owner[int(row["id"])]}
        for row in train
    ] + [{**row, "partition": "dev"} for row in dev]
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
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Corrective manifest directory; defaults to the dated correction tree.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Private corrective cache root; defaults outside the historical V2 cache.",
    )
    parser.add_argument("--replace-corrective-output", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = (
        args.output_dir.resolve()
        if args.output_dir
        else root / "reports/research_upgrade_v2/corrections/2026-10-14/results"
    )
    cache_root = (
        args.cache_dir.resolve()
        if args.cache_dir
        else root / ".cache/research_upgrade_v2_correction/2026-10-14"
    )
    historical_output = (root / "reports/research_upgrade_v2/results").resolve()
    historical_cache = (root / ".cache/research_upgrade_v2").resolve()
    if output == historical_output or cache_root == historical_cache:
        raise ValueError("Corrective inference must not overwrite historical V2 artifacts")
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
                    "experiment": "research_upgrade_v2_injected_deterministically_sampled_out_of_retrieval_document",
                    "claim_id": int(record["claim_id"]),
                    "doc_id": int(doc["doc_id"]),
                    "doc_rank": 5,
                    "document_title": doc["title"],
                    "sentence_index": chosen["sentence_index"],
                    "selected_sentence_rank": chosen["selected_rank"],
                    "sentence_selection_score": chosen["selection_score"],
                    "premise": chosen["sentence_text"],
                    "hypothesis": record["claim_text"],
                    "provenance": (
                        "deterministically sampled corpus document outside the original "
                        "retrieval set; semantic irrelevance was not established"
                    ),
                })
    injection_predictions: list[dict[str, Any]] = []
    injection_stats = None
    if injection_pairs:
        injection_predictions, injection_stats = engine.predict(
            injection_pairs,
            batch_size=args.batch_size if device == "mps" else min(4, args.batch_size),
        )

    cache = cache_root / args.verifier
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

    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / f"corrected_blind_{args.verifier}_manifest.json"
    compact_path = cache / f"corrected_blind_{args.verifier}_features.jsonl"
    if (manifest_path.exists() or compact_path.exists()) and not args.replace_corrective_output:
        raise FileExistsError(
            "Corrective artifacts already exist; pass --replace-corrective-output to rerun"
        )
    write_jsonl(compact_path, compact)
    correction_spec = root / "configs/research_upgrade_v2_correction_2026-10-14.json"
    manifest = {
        "status": "CORRECTIVE_REPLAY_COMPLETE",
        "evidence_class": "post_study_corrective_replay_not_fresh_confirmation",
        "verifier": args.verifier,
        "model_id": model_id,
        "revision": revision,
        "protocol_sha256": protocol_hash,
        "correction_spec_sha256": sha256_file(correction_spec),
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
            compact_path.name: sha256_file(compact_path)
        },
        "historical_v2_dev_results_previously_observed": True,
        "historical_v2_full_record_dev_json_deserialization_disclosed": True,
        "corrected_projection_fields": ["id", "claim"],
        "non_projection_annotation_values_materialized_for_scoring": False,
        "semantic_irrelevance_of_injected_document_established": False,
    }
    write_json(manifest_path, manifest)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
