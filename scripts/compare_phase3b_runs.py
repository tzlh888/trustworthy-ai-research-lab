#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from trustworthy_ai_lab.data import load_json, write_json
from trustworthy_ai_lab.phase3b import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    first_manifest = load_json(args.first / "experiment_manifest.json")
    second_manifest = load_json(args.second / "experiment_manifest.json")
    names = sorted(first_manifest["deterministic_artifact_sha256"])
    rows = []
    for name in names:
        left, right = sha256_file(args.first / name), sha256_file(args.second / name)
        rows.append({"artifact": name, "first_sha256": left, "second_sha256": right, "byte_identical": left == right})
    result = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "runs_compared": 2,
        "deterministic_artifacts_compared": len(rows), "all_byte_identical": all(row["byte_identical"] for row in rows),
        "comparisons": rows,
        "excluded_nondeterministic": ["data_access_log.json", "experiment_manifest.json", "figures PNG metadata"],
        "note": "Both recalculations used the same already-frozen prediction scores and labels; no model was retrained.",
    }
    write_json(args.output, result)
    if not result["all_byte_identical"]:
        raise RuntimeError("Deterministic Phase 3B recalculation mismatch")


if __name__ == "__main__":
    main()
