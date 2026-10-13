#!/usr/bin/env python3
"""Tokenizer/config-only audit; does not download weights or run predictions."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import transformers
from transformers import AutoConfig, AutoTokenizer


MINILM_ID = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MINILM_SENTENCE_TRANSFORMER_MAX = 256
NLI_ID = "cross-encoder/nli-distilroberta-base"
NLI_REVISION = "b14d131f9d32668a5e6a982729b57ff6ed5dfcbd"
NLI_MAX = 512


def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def summarize(lengths: list[int], limit: int) -> dict[str, float | int]:
    ordered = sorted(lengths)

    def percentile(fraction: float) -> int:
        return ordered[max(0, int(fraction * len(ordered)) - 1)]

    over = sum(length > limit for length in lengths)
    return {
        "n": len(lengths),
        "median": statistics.median(lengths),
        "p90_nearest_rank": percentile(0.90),
        "p95_nearest_rank": percentile(0.95),
        "max": max(lengths),
        "limit": limit,
        "over_limit_count": over,
        "over_limit_fraction": over / len(lengths),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    corpus_rows = load_jsonl(args.data_dir / "corpus.jsonl")
    train_rows = load_jsonl(args.data_dir / "claims_train.jsonl")
    corpus = {row["doc_id"]: row for row in corpus_rows}

    mini = AutoTokenizer.from_pretrained(MINILM_ID, revision=MINILM_REVISION)
    nli = AutoTokenizer.from_pretrained(NLI_ID, revision=NLI_REVISION)
    nli_config = AutoConfig.from_pretrained(NLI_ID, revision=NLI_REVISION)

    corpus_lengths = [
        len(mini(row["title"] + " " + " ".join(row["abstract"]), truncation=False)["input_ids"])
        for row in corpus_rows
    ]
    full_pair_lengths: list[int] = []
    rationale_pair_lengths: list[int] = []
    for claim in train_rows:
        for doc_key, rationales in claim["evidence"].items():
            document = corpus[int(doc_key)]
            full_text = document["title"] + " " + " ".join(document["abstract"])
            full_pair_lengths.append(
                len(nli(full_text, claim["claim"], truncation=False)["input_ids"])
            )
            indices = sorted(
                {index for rationale in rationales for index in rationale["sentences"]}
            )
            rationale_text = " ".join(document["abstract"][index] for index in indices)
            rationale_pair_lengths.append(
                len(nli(rationale_text, claim["claim"], truncation=False)["input_ids"])
            )

    report = {
        "scope": "tokenizer and config only; Train and corpus only; no weights, predictions, or metrics",
        "transformers_version": transformers.__version__,
        "minilm": {
            "model_id": MINILM_ID,
            "revision": MINILM_REVISION,
            "source_url": f"https://huggingface.co/{MINILM_ID}/tree/{MINILM_REVISION}",
            "model_card_license": "apache-2.0",
            "sentence_transformer_max_seq_length": MINILM_SENTENCE_TRANSFORMER_MAX,
            "title_plus_full_abstract_lengths": summarize(
                corpus_lengths, MINILM_SENTENCE_TRANSFORMER_MAX
            ),
        },
        "nli": {
            "model_id": NLI_ID,
            "revision": NLI_REVISION,
            "source_url": f"https://huggingface.co/{NLI_ID}/tree/{NLI_REVISION}",
            "model_card_license": "apache-2.0",
            "id2label": {str(key): value for key, value in nli_config.id2label.items()},
            "pair_direction": "evidence premise first; claim hypothesis second",
            "max_length": NLI_MAX,
            "train_gold_document_pair_lengths": summarize(full_pair_lengths, NLI_MAX),
            "train_gold_rationale_pair_lengths": summarize(rationale_pair_lengths, NLI_MAX),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
