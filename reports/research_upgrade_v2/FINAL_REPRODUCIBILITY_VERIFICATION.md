# Final Reproducibility Verification

## Verified identities and boundaries

- Starting repository HEAD: `e5d6c56b0b5b4723bf5cd3aa08625e2bce381aab`.
- Frozen V2 protocol SHA-256: `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`.
- Corrective specification SHA-256: `fa36b25b01ea28f0b6c4be7153c4a14868e05c9fff06dd0d25940983503db60d`.
- Python 3.12.15; macOS 27.0 arm64; corrected inference used MPS.
- The V2 protocol and historical outputs were not overwritten. Corrective outputs use a dated directory.

The corrected replay is not an untouched confirmatory evaluation: the earlier Dev results were already observed. It verifies engineering equivalence and prevents future annotation-field materialization.

## Corrective inference executed

```bash
PYTHONPATH=. .venv/bin/python scripts/run_upgrade_v2_inference.py \
  --root . --verifier e1 --batch-size 32 \
  --cache-dir .cache/research_upgrade_v2_correction/2026-10-14 \
  --output-dir reports/research_upgrade_v2/corrections/2026-10-14/results

PYTHONPATH=. .venv/bin/python scripts/run_upgrade_v2_inference.py \
  --root . --verifier e1_v2 --batch-size 24 \
  --cache-dir .cache/research_upgrade_v2_correction/2026-10-14 \
  --output-dir reports/research_upgrade_v2/corrections/2026-10-14/results

PYTHONPATH=. .venv/bin/python scripts/analyze_research_upgrade_v2.py \
  --root . \
  --cache-dir .cache/research_upgrade_v2_correction/2026-10-14 \
  --output-dir reports/research_upgrade_v2/corrections/2026-10-14/results
```

E1 processed 1,109 claims and 16,635 main claim-document pairs plus 900 injected pairs, with zero truncations. Main/injected elapsed times were 58.631/3.087 seconds. E1-v2 processed 827 claims and 12,405 pairs in 81.645 seconds, also with zero truncations.

The corrected compact E1 artifact SHA-256 is `3c1ea9104569f18882881d5ff2861696c06ed723fff208f66fd0e7a60f35c941`; E1-v2 is `e508ae3574534f9a5541058c978685b89876abe3548e0d59d6d2e8d4ca35774f`. Each exactly matches its historical private compact artifact. For both verifiers, claim keys/counts match, predicted-label differences are zero, scoring rows with any difference are zero, and maximum absolute numeric difference is 0.0.

## Analysis verification

The corrected analysis completed with 188 eligible Dev claims, 164 eligible connected groups, 329 eligible Fit claims, and 88 eligible historical Internal Test claims. Its manifest hashes every current corrected result. The corrected output contains `marginal_permutation_importance.csv`, not a conditional-importance claim, and uses the exact descriptive perturbation label `inject_deterministically_sampled_out_of_retrieval_document`.

The overlap sensitivity retained the original fixed scores. Normalized text exclusion removed Dev IDs 870 and 1292 at claim level; neither was eligible, so the primary metrics were unchanged. Shared-cited-document exclusion retained 104/300 Dev claims, 64 eligible claims, and 53 eligible connected groups. All reported paired 95% intervals for EARS-minus-B1 AURC and R80 crossed zero.

## Tests and independent release verification

The required command form was executed:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q -p no:cacheprovider
git diff --check
```

Actual results:

- Dedicated Phase 3B/V2 integrity suite: **22 passed, 9 skipped, 0 failed**.
- Full working-tree command: **37 passed, 61 skipped, 1 failed**. The sole failure was the intentional release-safety assertion detecting ignored raw SciFact files retained only in the research checkout.
- Working-tree regression with that release-context assertion deselected: **37 passed, 61 skipped, 1 deselected, 0 failed**.
- Full suite in the final publication-corrected, newly extracted release ZIP: **38 passed, 61 skipped, 0 failed**.
- Extracted-candidate cloud/privacy audit: **PASS**, 226 files scanned, zero findings; public numeric-model integrity passed.
- ZIP CRC/integrity, sorted entry, safe-path, required-file, sensitive-source, and per-file hash checks: **PASS**.

The 61 skips require private/full-research inputs intentionally excluded from a public candidate. The research checkout legitimately contains ignored downloaded raw data, so the authoritative release-safety result is the full suite in the clean extraction. Skipped tests are not counted as passes.

## PDF verification

The final manuscript PDF and one-page PDF were generated from the current authoritative Markdown content. All manuscript pages and the summary page were rendered to PNG and visually inspected for clipping, overlap, unreadable fonts, table/figure defects, missing content, and bad page breaks. Page count, text extraction, file hashes, and Markdown-source equality are independently checked in the final verification pass and recorded in `FINAL_V2_HANDOFF.md`.

## Public reproduction boundary

The release candidate includes source, protocols, tests, aggregate corrected outputs, numeric model specifications, reports, and publications. It excludes raw SciFact downloads, model weights, per-claim private inference caches, virtual environments, and temporary/cache files. Official inputs must be downloaded and hash-verified locally before inference.

The public checkout still lacks parts of the original private historical workflow, including private phase manifests, claim-level artifacts, joblib bundles, and a historically referenced helper. Therefore the complete historical workflow is **PARTIAL**, even though the corrected V2 inference and analysis are executable and the corrected replay achieved exact artifact equality in this environment.

## Remaining reproducibility risk

Exact transformer inference in a different hardware/software stack can be affected by upstream model availability or backend numerical behavior. The fixed revisions, package pins, hashes, machine-readable outputs, and equality comparison make such differences detectable; they do not guarantee bitwise identity on every future platform.
