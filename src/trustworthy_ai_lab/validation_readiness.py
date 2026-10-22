from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def freeze_configuration(configuration: dict[str, Any]) -> dict[str, Any]:
    required = {"model", "features", "thresholds", "metrics", "protocol_recorded_at"}
    missing = sorted(required - configuration.keys())
    if missing:
        raise ValueError(f"missing frozen configuration fields: {', '.join(missing)}")
    return {"configuration": configuration, "sha256": canonical_sha256(configuration)}


def audit_dataset(
    development: list[dict[str, Any]], evaluation: list[dict[str, Any]], *, expected_license: str
) -> dict[str, Any]:
    for name, rows in (("development", development), ("evaluation", evaluation)):
        if any("claim_id" not in row or "group_id" not in row or "document_ids" not in row for row in rows):
            raise ValueError(f"{name} rows require claim_id, group_id, and document_ids")
    dev_claims = {str(row["claim_id"]) for row in development}
    eval_claim_counts = Counter(str(row["claim_id"]) for row in evaluation)
    dev_groups = {str(row["group_id"]) for row in development}
    eval_groups = {str(row["group_id"]) for row in evaluation}
    dev_documents = {str(doc) for row in development for doc in row["document_ids"]}
    eval_documents = {str(doc) for row in evaluation for doc in row["document_ids"]}
    license_failures = [
        str(row["claim_id"]) for row in evaluation if row.get("license") != expected_license
    ]
    overlaps = {
        "claim_ids": sorted(dev_claims & set(eval_claim_counts)),
        "group_ids": sorted(dev_groups & eval_groups),
        "document_ids": sorted(dev_documents & eval_documents),
        "duplicate_evaluation_claim_ids": sorted(key for key, count in eval_claim_counts.items() if count > 1),
    }
    ready = bool(evaluation) and not any(overlaps.values()) and not license_failures
    return {
        "status": "READY BUT NOT EXTERNALLY VALIDATED" if ready else "BLOCKED",
        "development_count": len(development), "evaluation_count": len(evaluation),
        "overlaps": overlaps, "license_failures": license_failures,
        "label_definition_check": "REQUIRES_HUMAN_PROTOCOL_REVIEW",
        "external_validation_performed": False,
    }
