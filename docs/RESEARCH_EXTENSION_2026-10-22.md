# Failure-Mechanism and Validation-Readiness Extension

## Boundary and provenance

This AI-assisted extension starts from commit
`f4f37d340a4ee809ab4e2e0ecc2cea44eacafff6`. It adds software checks and
synthetic fixtures without changing frozen B1/EARS models, F4/F5 formulas,
historical predictions, reports, or the `INCONCLUSIVE` finding. No external
validation or new natural-model experiment was performed.

## Failure taxonomy

`failure_taxonomy.py` emits structured candidate records for Retrieval,
Evidence Selection, NLI, Aggregation/Decision, Annotation Ambiguity, or
Multiple/Unresolved failure. Rules localize only what the supplied pipeline
evidence supports. Label-blind mode masks the reference label, final
correctness, and reference-conditioned NLI fields. Every automated result uses
`deterministic_rule_candidate` and `PENDING`; it is never called human truth.

The command-line validator accepts JSONL and emits records plus a summary:

```bash
PYTHONPATH=src python scripts/run_failure_taxonomy.py \
  --input cases.jsonl --output failure_report.json
```

## Independent metric implementation

`metrics_validation.py` independently implements a low-to-high risk ordering,
discrete AURC (mean prefix selective risk), fixed R80 selection using
`floor(0.8*n+0.5)`, risk-coverage curves, tie-aware error-detection AUROC, and
paired group bootstrap intervals. Ties use a fixed hash and seed. Invalid and
empty inputs raise; AUROC returns `None` when only one error class exists.

MAE is intentionally absent: the historical scores are risk-ranking values,
not calibrated error probabilities, so probability-error MAE would answer a
different question.

## F4/F5 mechanism analysis

`feature_analysis.py` keeps the frozen definitions from
`phase2_protocol.py`. It reports per-candidate-category counts, groups, means,
medians, EARS-minus-B1 risk shifts, missingness, disputed/outlier sensitivity,
and insufficient-stratum warnings. F4 is a retrieval-score gap, not evidence
correctness. F5 zero is ambiguous because it can mean either no conflict or no
non-neutral evidence. Any interpretation formed on historical Dev data remains
post-hoc exploratory.

The public repository does not expose all required historical case-level
records for a new complete taxonomy/feature analysis. Individual records were
not reconstructed from aggregates, so the executable analysis is verified on
deterministic fixtures only.

```bash
PYTHONPATH=src python scripts/analyze_failure_features.py \
  --input examples/feature_cases.jsonl --output feature_report.json
```

## External-validation readiness

`validation_readiness.py` canonicalizes and hashes frozen configurations, and
checks evaluation licenses plus duplicate/overlapping claims, groups, and
documents. The preserved configuration is
`configs/independent_validation_readiness_v1.json`. A clean audit means only
`READY BUT NOT EXTERNALLY VALIDATED`; comparable label definitions still
require protocol-level human review before an external run.

```bash
PYTHONPATH=src python scripts/audit_independent_validation.py \
  --config configs/independent_validation_readiness_v1.json \
  --development development.jsonl --evaluation evaluation.jsonl \
  --expected-license CC-BY-4.0 --output readiness.json
```

## Technical competency lab

The AI-assisted reference implementation is in `metrics_validation.py`.
Future owner-performed exercises must be created separately and recorded with
commands, Git diff, test output, date, and reviewer identity; no completion is
pre-filled.

1. Derive discrete AURC from five `(error, risk)` pairs by hand, then reproduce it from base inputs.
2. Explain why R80 accepts `floor(0.8*n+0.5)` cases and construct a boundary-tie example.
3. Prove F4 lies in `[0, 1]` when BM25 scores are ordered and non-negative; identify the denominator edge case.
4. Show why F5 returns zero both for one-sided evidence and for no non-neutral evidence, and propose a separate missingness indicator without changing the frozen feature.
5. Implement paired group resampling and explain why resampling claims would understate uncertainty when claims share evidence groups.

## Evidence levels and limitations

| Item | Status |
|---|---|
| deterministic taxonomy and masking tests | VERIFIED after recorded local run |
| independent metric edge/reference tests | VERIFIED after recorded local run |
| historical suite | VERIFIED or skipped only as reported by the actual command |
| full case-level historical taxonomy | NOT RUN — public artifacts insufficient |
| new licensed external dataset | BLOCKED — none selected and protocol-approved |
| external generalization | NOT VERIFIED |
| human technical competency | NOT VERIFIED |

Passing software tests establishes software behavior, not EARS superiority,
scientific validity, external generalization, or unaided human authorship.
