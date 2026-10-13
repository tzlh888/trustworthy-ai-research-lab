from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


ID_PATTERN = re.compile(r'"id"\s*:\s*(\d+)')


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def load_selected_claims(path: Path, allowed_ids: set[int]) -> list[dict[str, Any]]:
    """Parse only allowed JSONL rows; sealed rows are never deserialized."""
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            match = ID_PATTERN.search(line[:100])
            if match is None:
                raise ValueError(f"Missing leading claim ID at {path.name}:{line_number}")
            claim_id = int(match.group(1))
            if claim_id not in allowed_ids:
                continue
            row = json.loads(line)
            if row.get("id") != claim_id:
                raise ValueError(f"Claim ID mismatch at {path.name}:{line_number}")
            selected.append(row)
            seen.add(claim_id)
    missing = allowed_ids - seen
    if missing:
        raise ValueError(f"Missing allowed claim IDs: {sorted(missing)[:10]}")
    if len(selected) != len(allowed_ids):
        raise ValueError("Duplicate allowed claim IDs")
    return sorted(selected, key=lambda row: row["id"])


def derived_evidence_label(claim: dict[str, Any]) -> str | None:
    labels = {
        rationale["label"]
        for rationales in claim["evidence"].values()
        for rationale in rationales
    }
    if not labels:
        return None
    if len(labels) != 1:
        raise ValueError(f"Claim {claim['id']} has mixed labels: {sorted(labels)}")
    return next(iter(labels))


def fold_lookup(manifest: dict[str, Any]) -> dict[int, str]:
    result: dict[int, str] = {}
    for fold_name, fold in manifest["crossfit_validation_folds_within_fit"].items():
        for claim_id in fold["claim_ids"]:
            if claim_id in result:
                raise ValueError(f"Claim {claim_id} appears in multiple folds")
            result[claim_id] = fold_name
    return result


def load_phase1_data(
    manifest_path: Path, train_path: Path, corpus_path: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[int, str], dict[str, Any]]:
    manifest = load_json(manifest_path)
    if not manifest["source"].get("raw_train_only"):
        raise ValueError("Manifest is not Train-only")
    if sha256(train_path) != manifest["source"]["sha256"]:
        raise ValueError("Frozen Train hash mismatch")

    fit_ids = set(manifest["outer_splits"]["fit"]["claim_ids"])
    sealed_ids = set(manifest["outer_splits"]["calibration"]["claim_ids"]) | set(
        manifest["outer_splits"]["internal_test"]["claim_ids"]
    )
    if fit_ids & sealed_ids:
        raise ValueError("Fit and sealed IDs overlap")
    claims = load_selected_claims(train_path, fit_ids)
    corpus = load_jsonl(corpus_path)
    if len({row["doc_id"] for row in corpus}) != len(corpus):
        raise ValueError("Duplicate corpus doc IDs")
    folds = fold_lookup(manifest)
    if set(folds) != fit_ids:
        raise ValueError("Cross-fit folds do not exactly partition fit")
    return claims, corpus, folds, manifest


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
