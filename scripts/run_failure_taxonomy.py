from __future__ import annotations

import argparse
import json
from pathlib import Path

from trustworthy_ai_lab.failure_taxonomy import classify_case, summarize


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rule-based candidate failure categories")
    parser.add_argument("--input", type=Path, required=True, help="JSONL case records")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unblind-labels", action="store_true")
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [classify_case(case, label_blind=not args.unblind_labels) for case in cases]
    payload = {"records": [record.to_dict() for record in records], "summary": summarize(records)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
