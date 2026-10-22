from __future__ import annotations

import argparse
import json
from pathlib import Path

from trustworthy_ai_lab.feature_analysis import analyze_features


def main() -> None:
    parser = argparse.ArgumentParser(description="Exploratory F4/F5 analysis by candidate failure type")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    result = analyze_features(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
