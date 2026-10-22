# Synthetic extension outputs

These JSON files were generated from `examples/` to verify executable behavior.
They are deterministic mechanism tests, not observations from SciFact, a real
LLM, an independent dataset, or human reviewers. No scientific performance
claim may be inferred from their values.

Commands:

```bash
PYTHONPATH=src python scripts/run_failure_taxonomy.py \
  --input examples/failure_cases.jsonl \
  --output reports/research_extension_2026-10-22/synthetic_failure_taxonomy.json
PYTHONPATH=src python scripts/analyze_failure_features.py \
  --input examples/feature_cases.jsonl \
  --output reports/research_extension_2026-10-22/synthetic_feature_analysis.json
```
