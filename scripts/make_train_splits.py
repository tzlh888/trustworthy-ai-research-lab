#!/usr/bin/env python3
"""Create deterministic, document-grouped SciFact Train-only splits.

Raw Dev and official Test are never read. Groups are connected components over
shared cited documents plus normalized duplicate claim text. A deterministic
greedy/local-search allocator approximately stratifies the protocol-derived
Train labels without splitting a group.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SEED = 20261012
LABELS = ("SUPPORT", "CONTRADICT", "NO_ANNOTATED_EVIDENCE_DERIVED")


def normalize_claim(text: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def derived_label(row: dict[str, Any]) -> str:
    labels = {
        rationale["label"]
        for rationales in row["evidence"].values()
        for rationale in rationales
    }
    if not labels:
        return "NO_ANNOTATED_EVIDENCE_DERIVED"
    if len(labels) != 1:
        raise ValueError(f"Claim {row['id']} has mixed labels: {sorted(labels)}")
    return next(iter(labels))


class DisjointSet:
    def __init__(self, values: list[int]):
        self.parent = {value: value for value in values}

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            smaller, larger = sorted((left_root, right_root))
            self.parent[larger] = smaller


@dataclass(frozen=True)
class Group:
    key: int
    claim_ids: tuple[int, ...]
    label_counts: tuple[int, ...]

    @property
    def size(self) -> int:
        return len(self.claim_ids)


def make_groups(rows: list[dict[str, Any]]) -> list[Group]:
    dsu = DisjointSet([row["id"] for row in rows])
    buckets: dict[tuple[str, Any], list[int]] = collections.defaultdict(list)
    for row in rows:
        for doc_id in row["cited_doc_ids"]:
            buckets[("cited_doc", doc_id)].append(row["id"])
        buckets[("claim_text", normalize_claim(row["claim"]))].append(row["id"])
    for members in (buckets[key] for key in sorted(buckets, key=str)):
        first = min(members)
        for member in sorted(members):
            dsu.union(first, member)

    row_by_id = {row["id"]: row for row in rows}
    components: dict[int, list[int]] = collections.defaultdict(list)
    for claim_id in sorted(row_by_id):
        components[dsu.find(claim_id)].append(claim_id)

    groups: list[Group] = []
    for members in components.values():
        counts = collections.Counter(derived_label(row_by_id[claim_id]) for claim_id in members)
        groups.append(
            Group(
                key=min(members),
                claim_ids=tuple(sorted(members)),
                label_counts=tuple(counts[label] for label in LABELS),
            )
        )
    return sorted(groups, key=lambda group: group.key)


def allocate_groups(
    groups: list[Group],
    split_names: tuple[str, ...],
    ratios: tuple[float, ...],
    rng: random.Random,
    improvement_steps: int = 30_000,
) -> dict[int, str]:
    total = sum(group.size for group in groups)
    total_labels = [sum(group.label_counts[i] for group in groups) for i in range(len(LABELS))]
    target_sizes = {name: ratio * total for name, ratio in zip(split_names, ratios)}
    target_labels = {
        name: [ratio * count for count in total_labels]
        for name, ratio in zip(split_names, ratios)
    }

    def score(assignment: dict[int, str]) -> float:
        sizes: collections.Counter[str] = collections.Counter()
        for index, name in assignment.items():
            sizes[name] += groups[index].size
        label_counts = {name: [0] * len(LABELS) for name in split_names}
        for index, name in assignment.items():
            for label_index, count in enumerate(groups[index].label_counts):
                label_counts[name][label_index] += count
        size_error = sum(
            3.0 * ((sizes[name] - target_sizes[name]) / max(1.0, target_sizes[name])) ** 2
            for name in split_names
        )
        label_error = sum(
            (
                (label_counts[name][label_index] - target_labels[name][label_index])
                / max(1.0, target_labels[name][label_index])
            )
            ** 2
            for name in split_names
            for label_index in range(len(LABELS))
        )
        return size_error + label_error

    order = list(range(len(groups)))
    rng.shuffle(order)
    order.sort(key=lambda index: groups[index].size, reverse=True)
    assignment: dict[int, str] = {}
    for index in order:
        candidates: list[tuple[float, float, str]] = []
        for name in split_names:
            trial = dict(assignment)
            trial[index] = name
            candidates.append((score(trial), rng.random(), name))
        assignment[index] = min(candidates)[2]

    best = score(assignment)
    for _ in range(improvement_steps):
        index = rng.randrange(len(groups))
        old_name = assignment[index]
        new_name = rng.choice([name for name in split_names if name != old_name])
        assignment[index] = new_name
        trial_score = score(assignment)
        if trial_score <= best:
            best = trial_score
        else:
            assignment[index] = old_name

    for _ in range(improvement_steps):
        left, right = rng.sample(range(len(groups)), 2)
        if assignment[left] == assignment[right]:
            continue
        assignment[left], assignment[right] = assignment[right], assignment[left]
        trial_score = score(assignment)
        if trial_score <= best:
            best = trial_score
        else:
            assignment[left], assignment[right] = assignment[right], assignment[left]
    return assignment


def summarize(
    rows_by_id: dict[int, dict[str, Any]], groups: list[Group], assignment: dict[int, str]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in sorted(set(assignment.values())):
        indices = [index for index, assigned in assignment.items() if assigned == name]
        ids = sorted(claim_id for index in indices for claim_id in groups[index].claim_ids)
        labels = collections.Counter(derived_label(rows_by_id[claim_id]) for claim_id in ids)
        result[name] = {
            "claim_count": len(ids),
            "group_count": len(indices),
            "derived_label_counts": {label: labels[label] for label in LABELS},
            "claim_ids": ids,
        }
    return result


def validate_no_group_leakage(groups: list[Group], assignment: dict[int, str]) -> None:
    seen: dict[int, str] = {}
    for index, name in assignment.items():
        for claim_id in groups[index].claim_ids:
            if claim_id in seen:
                raise AssertionError(f"Claim {claim_id} assigned twice")
            seen[claim_id] = name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    rows = load_jsonl(args.train_file)
    rows_by_id = {row["id"]: row for row in rows}
    if len(rows_by_id) != len(rows):
        raise ValueError("Duplicate claim IDs in Train")
    groups = make_groups(rows)
    rng = random.Random(args.seed)
    assignment = allocate_groups(
        groups,
        ("fit", "calibration", "internal_test"),
        (0.65, 0.175, 0.175),
        rng,
    )
    validate_no_group_leakage(groups, assignment)
    outer = summarize(rows_by_id, groups, assignment)

    fit_group_indices = [index for index, name in assignment.items() if name == "fit"]
    fit_groups = [groups[index] for index in fit_group_indices]
    crossfit_rng = random.Random(args.seed + 1)
    crossfit_assignment = allocate_groups(
        fit_groups,
        tuple(f"fold_{number}" for number in range(1, 6)),
        (0.2,) * 5,
        crossfit_rng,
        improvement_steps=15_000,
    )
    crossfit = summarize(rows_by_id, fit_groups, crossfit_assignment)

    manifest = {
        "manifest_version": 1,
        "source": {
            "filename": args.train_file.name,
            "sha256": sha256(args.train_file),
            "raw_train_only": True,
            "raw_dev_used": False,
            "official_test_used": False,
        },
        "seed": args.seed,
        "rules": {
            "outer_ratios_requested": {"fit": 0.65, "calibration": 0.175, "internal_test": 0.175},
            "grouping": "connected components over shared cited_doc_ids and normalized exact claim text",
            "stratification": "protocol-derived Train labels; empty evidence becomes NO_ANNOTATED_EVIDENCE_DERIVED",
            "allocator": "deterministic greedy assignment plus seeded local moves/swaps",
            "crossfit": "five document-grouped folds inside fit only",
        },
        "outer_splits": outer,
        "crossfit_validation_folds_within_fit": crossfit,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
