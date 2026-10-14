# Reproducibility Audit

> **Correction notice (14 October 2026):** This earlier V2 audit is preserved as a historical record. The authoritative corrected replay, exact-equivalence evidence, final test totals, PDF verification, and clean-package audit are in `FINAL_REPRODUCIBILITY_VERIFICATION.md` and `FINAL_V2_HANDOFF.md`. The original V2 ID-discovery path deserialized complete Dev JSON records; current code does not.

## Recorded environment

- Source HEAD before changes: `e5d6c56b0b5b4723bf5cd3aa08625e2bce381aab`.
- macOS 27.0, Apple Silicon arm64, 24 GiB memory.
- Python 3.12.15 in `.venv`; the host default Python 3.14 was not used.
- Frozen dependency set from `requirements-phase4.txt`; v2 additionally requires `sentencepiece==0.2.1`.
- E1 inference: MPS, 16,635 main pairs plus 900 perturbation pairs, zero truncations.
- E1-v2 inference: MPS, 12,405 pairs, zero truncations.

## Input integrity

The official SciFact archive passed the recorded SHA-256 gate. Key files matched the repository provenance record: Train `f4c8…372f0`, Dev `86f0…2217`, and corpus `b8d6…de62`. The public numeric model specification matched `c472…d90b`. The v2 protocol hash is `70ae…2301`.

## Reproduction commands

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-research-upgrade-v2.txt -e .
bash scripts/download_scifact.sh data/raw/scifact
PYTHONPATH=. .venv/bin/python scripts/run_upgrade_v2_inference.py --root . --verifier e1 --batch-size 32
PYTHONPATH=. .venv/bin/python scripts/run_upgrade_v2_inference.py --root . --verifier e1_v2 --batch-size 24
PYTHONPATH=. .venv/bin/python scripts/analyze_research_upgrade_v2.py --root .
PYTHONPATH=. .venv/bin/pytest -q
```

Blind claim-level and sentence-level records remain under ignored `.cache/research_upgrade_v2/`; public results contain aggregates and copyright-conscious derived case records. `results/analysis_manifest.json` hashes every public result.

## Historical reproduction boundary

The public repository lacks `reports/phase0_frozen_hashes.json`, `reports/phase3a/protocol_manifest.json`, Phase 1 claim-level artifacts, joblib bundles, and the README-referenced `scripts/build_phase1_reports.py`. Therefore the original staged commands cannot perform a complete private-package replay from a public checkout. This does not invalidate the immutable aggregate evidence, but the old README overstated the clean public reproduction path.

The v2 run independently regenerated E1 predictions and applied the public numeric B1/EARS specification. It exactly reproduced the historical Internal Test point metrics to floating precision, providing a strong existing-result reproduction without pretending that missing private manifests were recovered.

## Test boundary

Public tests intentionally skip private/full research tests. When raw data exist inside the repository, the release-safety test correctly fails because those files must not be published. A clean-copy test must exclude ignored raw data and caches. Test counts and clean-checkout results are recorded in `FINAL_HANDOFF.md` after final execution.

The final clean release-candidate copy passed **23 tests**, skipped **61** private-input tests, and failed **0** tests in 3.30 seconds. The upgrade-specific suite passed all **7** tests. The clean cloud/privacy audit scanned 169 files with zero findings and verified the public numeric-model artifacts. `git diff --check` also passed. Two SWIG deprecation warnings came from third-party bindings and did not affect results.

## Known incidents

1. E1-v2 initially stopped before predictions because `sentencepiece` was missing; the dependency was added and the run restarted.
2. The first robustness aggregation mixed all 300 Dev claims with the 188 label-eligible population and raised `KeyError`; the code was corrected to use the frozen eligible population and the full analysis was rerun.

Neither incident changed labels, eligibility, metrics, or selection rules.
