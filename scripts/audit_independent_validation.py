from __future__ import annotations

import argparse
import json
from pathlib import Path

from trustworthy_ai_lab.validation_readiness import audit_dataset, freeze_configuration


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze configuration and audit external-data readiness")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--development", type=Path, required=True)
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--expected-license", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "frozen_configuration": freeze_configuration(json.loads(args.config.read_text(encoding="utf-8"))),
        "dataset_audit": audit_dataset(_jsonl(args.development), _jsonl(args.evaluation), expected_license=args.expected_license),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
