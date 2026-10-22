from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


CATEGORIES = {
    "Retrieval Failure",
    "Evidence Selection Failure",
    "NLI Inference Failure",
    "Aggregation / Decision Failure",
    "Annotation Ambiguity",
    "Multiple / Unresolved",
}
REVIEW_STATUSES = {"PENDING", "CONFIRMED", "REJECTED", "NOT_REQUIRED"}


@dataclass(frozen=True)
class FailureRecord:
    case_id: str
    group_id: str
    prediction: str
    available_reference_label: str | None
    evidence_references: tuple[str, ...]
    proposed_failure_category: str
    classification_method: str
    reviewer_status: str
    confidence: str
    uncertainty_reason: str | None
    data_provenance: str

    def __post_init__(self) -> None:
        if not self.case_id or not self.group_id or not self.data_provenance:
            raise ValueError("case_id, group_id, and data_provenance are required")
        if self.proposed_failure_category not in CATEGORIES:
            raise ValueError("unsupported failure category")
        if self.reviewer_status not in REVIEW_STATUSES:
            raise ValueError("unsupported reviewer status")
        if self.confidence not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("confidence must be LOW, MEDIUM, or HIGH")
        if self.classification_method == "human_review" and self.reviewer_status != "CONFIRMED":
            raise ValueError("human_review requires confirmed reviewer status")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_references"] = list(self.evidence_references)
        return value


def classify_case(case: dict[str, Any], *, label_blind: bool = True) -> FailureRecord:
    """Propose a category from observable pipeline evidence; never create human truth."""
    required = {"case_id", "group_id", "prediction", "evidence_references", "data_provenance"}
    missing = sorted(required - case.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    reference_label = None if label_blind else case.get("reference_label")
    retrieved = case.get("gold_document_retrieved")
    selected = case.get("complete_reference_evidence_selected")
    nli_correct = None if label_blind else case.get("nli_on_reference_evidence_correct")
    final_correct = None if label_blind else case.get("final_prediction_correct")
    ambiguous = bool(case.get("annotation_ambiguity_flag"))

    candidates: list[str] = []
    reasons: list[str] = []
    if retrieved is False:
        candidates.append("Retrieval Failure")
    elif retrieved is True and selected is False:
        candidates.append("Evidence Selection Failure")
    if not label_blind and selected is True and nli_correct is False:
        candidates.append("NLI Inference Failure")
    if not label_blind and nli_correct is True and final_correct is False:
        candidates.append("Aggregation / Decision Failure")
    if ambiguous:
        candidates.append("Annotation Ambiguity")
    if label_blind:
        reasons.append("reference label, correctness, and reference-conditioned NLI fields were masked")
    if not candidates:
        candidates = ["Multiple / Unresolved"]
        reasons.append("available evidence does not localize a pipeline failure")
    category = candidates[0] if len(candidates) == 1 else "Multiple / Unresolved"
    if len(candidates) > 1:
        reasons.append("multiple candidate mechanisms are consistent with the evidence")
    evidence = case["evidence_references"]
    if not isinstance(evidence, list) or any(not isinstance(item, str) for item in evidence):
        raise ValueError("evidence_references must be a list of strings")
    return FailureRecord(
        case_id=str(case["case_id"]), group_id=str(case["group_id"]),
        prediction=str(case["prediction"]), available_reference_label=reference_label,
        evidence_references=tuple(evidence), proposed_failure_category=category,
        classification_method="deterministic_rule_candidate",
        reviewer_status="PENDING", confidence="MEDIUM" if category != "Multiple / Unresolved" else "LOW",
        uncertainty_reason="; ".join(reasons) or None,
        data_provenance=str(case["data_provenance"]),
    )


def summarize(records: list[FailureRecord]) -> dict[str, Any]:
    counts = {category: 0 for category in sorted(CATEGORIES)}
    for record in records:
        counts[record.proposed_failure_category] += 1
    return {
        "case_count": len(records),
        "group_count": len({record.group_id for record in records}),
        "candidate_category_counts": counts,
        "human_confirmed_count": sum(record.reviewer_status == "CONFIRMED" for record in records),
        "interpretation": "rule-based candidate categories; not human-adjudicated truth",
    }
