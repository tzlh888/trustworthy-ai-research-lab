#!/usr/bin/env python3
"""Phase-0-only structural and leakage audit for the official SciFact release.

The dev split is deliberately restricted to schema, identifier, reference, and
cross-split integrity checks. This script does not accept predictions and does
not calculate any dev-set model metric.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


ALLOWED_RATIONALE_LABELS = {"SUPPORT", "CONTRADICT"}
CLAIM_FIELDS_LABELED = {"id", "claim", "evidence", "cited_doc_ids"}
CLAIM_FIELDS_TEST = {"id", "claim"}
CORPUS_FIELDS = {"doc_id", "title", "abstract", "structured"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path.name}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"Expected object in {path.name}:{line_number}")
            rows.append(value)
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_claim(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def duplicate_groups(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[str, list[int]] = collections.defaultdict(list)
    for row in rows:
        index[normalize_claim(row["claim"])].append(row["id"])
    return [
        {"normalized_claim": text, "claim_ids": sorted(ids)}
        for text, ids in sorted(index.items())
        if len(ids) > 1
    ]


def schema_variants(rows: Iterable[dict[str, Any]]) -> list[list[str]]:
    variants = sorted({tuple(sorted(row)) for row in rows})
    return [list(variant) for variant in variants]


def id_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    ids = [row[key] for row in rows]
    return {
        "rows": len(rows),
        "unique_ids": len(set(ids)),
        "duplicate_id_count": len(ids) - len(set(ids)),
        "min_id": min(ids) if ids else None,
        "max_id": max(ids) if ids else None,
    }


def evidence_integrity(
    rows: list[dict[str, Any]], corpus: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    invalid_doc_refs: list[dict[str, int]] = []
    invalid_sentence_refs: list[dict[str, int]] = []
    invalid_labels: list[dict[str, Any]] = []
    mixed_claim_labels: list[int] = []
    evidence_not_cited: list[dict[str, int]] = []
    evidence_doc_links = 0
    rationale_sets = 0
    rationale_sentence_refs = 0

    for claim in rows:
        claim_labels: set[str] = set()
        cited = set(claim["cited_doc_ids"])
        for doc_key, rationales in claim["evidence"].items():
            doc_id = int(doc_key)
            evidence_doc_links += 1
            if doc_id not in cited:
                evidence_not_cited.append({"claim_id": claim["id"], "doc_id": doc_id})
            document = corpus.get(doc_id)
            if document is None:
                invalid_doc_refs.append({"claim_id": claim["id"], "doc_id": doc_id})
                continue
            for rationale in rationales:
                rationale_sets += 1
                label = rationale.get("label")
                claim_labels.add(label)
                if label not in ALLOWED_RATIONALE_LABELS:
                    invalid_labels.append(
                        {"claim_id": claim["id"], "doc_id": doc_id, "label": label}
                    )
                for sentence_index in rationale.get("sentences", []):
                    rationale_sentence_refs += 1
                    if (
                        not isinstance(sentence_index, int)
                        or sentence_index < 0
                        or sentence_index >= len(document["abstract"])
                    ):
                        invalid_sentence_refs.append(
                            {
                                "claim_id": claim["id"],
                                "doc_id": doc_id,
                                "sentence_index": sentence_index,
                            }
                        )
        if len(claim_labels) > 1:
            mixed_claim_labels.append(claim["id"])

    return {
        "evidence_document_links": evidence_doc_links,
        "rationale_sets": rationale_sets,
        "rationale_sentence_references": rationale_sentence_refs,
        "invalid_document_references": invalid_doc_refs,
        "invalid_sentence_references": invalid_sentence_refs,
        "invalid_rationale_labels": invalid_labels,
        "mixed_rationale_label_claim_ids": sorted(mixed_claim_labels),
        "evidence_document_not_in_cited_doc_ids": evidence_not_cited,
    }


def derived_train_label(claim: dict[str, Any]) -> str:
    """Derive a protocol label; this is not a field present in the raw JSONL."""
    labels = {
        rationale["label"]
        for rationales in claim["evidence"].values()
        for rationale in rationales
    }
    if not labels:
        return "NO_ANNOTATED_EVIDENCE_DERIVED"
    if len(labels) != 1:
        raise ValueError(f"Claim {claim['id']} has mixed evidence labels: {sorted(labels)}")
    return next(iter(labels))


def train_annotation_statistics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    label_counts = collections.Counter(derived_train_label(row) for row in rows)
    rationale_label_counts: collections.Counter[str] = collections.Counter()
    evidence_doc_counts: collections.Counter[int] = collections.Counter()
    for row in rows:
        evidence_doc_counts[len(row["evidence"])] += 1
        for rationales in row["evidence"].values():
            for rationale in rationales:
                rationale_label_counts[rationale["label"]] += 1
    return {
        "derived_claim_label_counts": dict(sorted(label_counts.items())),
        "raw_rationale_label_counts": dict(sorted(rationale_label_counts.items())),
        "empty_evidence_claim_count": label_counts["NO_ANNOTATED_EVIDENCE_DERIVED"],
        "evidence_document_count_per_claim": {
            str(key): value for key, value in sorted(evidence_doc_counts.items())
        },
        "mean_evidence_documents_per_claim": sum(
            count * frequency for count, frequency in evidence_doc_counts.items()
        )
        / len(rows),
    }


def cross_split_claim_overlap(
    left_name: str,
    left: list[dict[str, Any]],
    right_name: str,
    right: list[dict[str, Any]],
) -> dict[str, Any]:
    left_index: dict[str, list[int]] = collections.defaultdict(list)
    right_index: dict[str, list[int]] = collections.defaultdict(list)
    for row in left:
        left_index[normalize_claim(row["claim"])].append(row["id"])
    for row in right:
        right_index[normalize_claim(row["claim"])].append(row["id"])
    overlaps = [
        {
            "normalized_claim": text,
            f"{left_name}_claim_ids": sorted(left_index[text]),
            f"{right_name}_claim_ids": sorted(right_index[text]),
        }
        for text in sorted(left_index.keys() & right_index.keys())
    ]
    return {
        "pair": [left_name, right_name],
        "shared_claim_id_count": len(
            {row["id"] for row in left} & {row["id"] for row in right}
        ),
        "normalized_text_overlap_count": len(overlaps),
        "normalized_text_overlaps": overlaps,
    }


def document_overlap(
    train: list[dict[str, Any]], dev: list[dict[str, Any]]
) -> dict[str, int]:
    train_evidence = {int(doc) for row in train for doc in row["evidence"]}
    dev_evidence = {int(doc) for row in dev for doc in row["evidence"]}
    train_cited = {doc for row in train for doc in row["cited_doc_ids"]}
    dev_cited = {doc for row in dev for doc in row["cited_doc_ids"]}
    return {
        "train_unique_evidence_documents": len(train_evidence),
        "dev_unique_evidence_documents": len(dev_evidence),
        "train_dev_shared_evidence_documents": len(train_evidence & dev_evidence),
        "train_unique_cited_documents": len(train_cited),
        "dev_unique_cited_documents": len(dev_cited),
        "train_dev_shared_cited_documents": len(train_cited & dev_cited),
    }


def within_train_document_sharing(train: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for field in ("evidence", "cited_doc_ids"):
        inverted: dict[int, list[int]] = collections.defaultdict(list)
        for row in train:
            values = map(int, row["evidence"].keys()) if field == "evidence" else row[field]
            for doc_id in values:
                inverted[doc_id].append(row["id"])
        result[f"{field}_documents_used_by_multiple_claims"] = sum(
            len(claim_ids) >= 2 for claim_ids in inverted.values()
        )
        result[f"max_claims_sharing_one_{field}_document"] = max(
            map(len, inverted.values()), default=0
        )
    return result


def official_cross_validation_audit(data_dir: Path, train_ids: set[int], dev_ids: set[int]) -> dict[str, Any]:
    cv_dir = data_dir / "cross_validation"
    folds: list[dict[str, Any]] = []
    validation_appearances: collections.Counter[int] = collections.Counter()
    for fold_number in range(1, 6):
        fold_dir = cv_dir / f"fold_{fold_number}"
        train_rows = load_jsonl(fold_dir / f"claims_train_{fold_number}.jsonl")
        dev_rows = load_jsonl(fold_dir / f"claims_dev_{fold_number}.jsonl")
        fold_train_ids = {row["id"] for row in train_rows}
        fold_dev_ids = {row["id"] for row in dev_rows}
        validation_appearances.update(fold_dev_ids)
        folds.append(
            {
                "fold": fold_number,
                "train_rows": len(train_rows),
                "dev_rows": len(dev_rows),
                "train_validation_id_overlap": len(fold_train_ids & fold_dev_ids),
                "union_equals_raw_train_plus_dev": (fold_train_ids | fold_dev_ids)
                == (train_ids | dev_ids),
                "contains_raw_dev_claim_ids": bool((fold_train_ids | fold_dev_ids) & dev_ids),
            }
        )
    return {
        "folds": folds,
        "unique_claim_ids_across_validation_folds": len(validation_appearances),
        "each_combined_train_dev_claim_appears_once_as_validation": set(
            validation_appearances.values()
        )
        == {1}
        and set(validation_appearances) == (train_ids | dev_ids),
        "phase0_policy": "DO_NOT_USE: official folds merge the frozen raw dev split into development data",
    }


def audit(data_dir: Path) -> dict[str, Any]:
    required = {
        "train": data_dir / "claims_train.jsonl",
        "dev": data_dir / "claims_dev.jsonl",
        "test": data_dir / "claims_test.jsonl",
        "corpus": data_dir / "corpus.jsonl",
    }
    missing = [path.name for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    train = load_jsonl(required["train"])
    dev = load_jsonl(required["dev"])
    test = load_jsonl(required["test"])
    corpus_rows = load_jsonl(required["corpus"])
    corpus = {row["doc_id"]: row for row in corpus_rows}

    expected_schemas = {
        "train": sorted(CLAIM_FIELDS_LABELED),
        "dev": sorted(CLAIM_FIELDS_LABELED),
        "test": sorted(CLAIM_FIELDS_TEST),
        "corpus": sorted(CORPUS_FIELDS),
    }
    actual_schemas = {
        "train": schema_variants(train),
        "dev": schema_variants(dev),
        "test": schema_variants(test),
        "corpus": schema_variants(corpus_rows),
    }

    title_counts = collections.Counter(row["title"] for row in corpus_rows)
    abstract_counts = collections.Counter(" ".join(row["abstract"]) for row in corpus_rows)
    train_ids = {row["id"] for row in train}
    dev_ids = {row["id"] for row in dev}

    return {
        "audit_scope": {
            "phase": 0,
            "dev_restriction": "integrity and metadata only; no predictions or performance metrics",
            "test_restriction": "unlabeled official split; no performance claim possible",
        },
        "files": {
            name: {"filename": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
            for name, path in required.items()
        },
        "schema": {
            "expected_fields": expected_schemas,
            "observed_field_variants": actual_schemas,
            "matches_expected": all(
                variants == [expected_schemas[name]]
                for name, variants in actual_schemas.items()
            ),
        },
        "identifiers": {
            "train": id_summary(train, "id"),
            "dev": id_summary(dev, "id"),
            "test": id_summary(test, "id"),
            "corpus": id_summary(corpus_rows, "doc_id"),
        },
        "train_annotations": train_annotation_statistics(train),
        "integrity": {
            "train": evidence_integrity(train, corpus),
            "dev_metadata_only": evidence_integrity(dev, corpus),
            "test_has_only_id_and_claim": all(set(row) == CLAIM_FIELDS_TEST for row in test),
        },
        "duplicates": {
            "within_train": duplicate_groups(train),
            "within_dev": duplicate_groups(dev),
            "within_test": duplicate_groups(test),
            "cross_split": [
                cross_split_claim_overlap("train", train, "dev", dev),
                cross_split_claim_overlap("train", train, "test", test),
                cross_split_claim_overlap("dev", dev, "test", test),
            ],
            "corpus_duplicate_title_extra_rows": sum(
                count - 1 for count in title_counts.values() if count > 1
            ),
            "corpus_duplicate_abstract_extra_rows": sum(
                count - 1 for count in abstract_counts.values() if count > 1
            ),
            "corpus_empty_abstract_count": sum(not row["abstract"] for row in corpus_rows),
        },
        "document_sharing": {
            **document_overlap(train, dev),
            **within_train_document_sharing(train),
        },
        "official_cross_validation": official_cross_validation_audit(
            data_dir, train_ids, dev_ids
        ),
        "label_semantics": {
            "raw_labels": ["SUPPORT", "CONTRADICT"],
            "derived_label": "NO_ANNOTATED_EVIDENCE_DERIVED when evidence is empty",
            "warning": "The derived label is not a raw annotation and is not interchangeable with NLI neutral or model abstention.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.data_dir)
    serialized = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
