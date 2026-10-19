# Trustworthy-AI V3.1 Final Limitations

> Sanitized public copy. Local-machine path descriptions were replaced with public-package terminology; scientific limitations are unchanged from the restricted closure source.

## Scientific limitations

- The formal Check-COVID evaluation was not run and remains scientifically NO-GO; external validation is not established.
- SciFact Dev was previously inspected and reused. Study A/A+ is not a blind, prospective, or independent test.
- The proposed corrections come from a third-party single-auditor workflow. No qualified independent human adjudicators were available for V3.1 closure.
- Claim 597 remains unresolved between a document-level correction and a literal claim-level NEI interpretation. Both are preserved.
- Corrected paired ΔAURC and ΔR80 confidence intervals include zero. EARS superiority is not statistically established.
- Two documented label changes can reverse the ΔAURC point ordering, but a point reversal near zero is not evidence of significance or practical superiority.
- Scenario enumeration represents a set of admissible assumptions, not a probability distribution over annotation truth.
- Bootstrap intervals measure sampling uncertainty conditional on fixed labels; they do not incorporate annotation uncertainty.
- Six proposed NEI corrections remove observations that are all frozen-model errors. The resulting absolute metric improvement is partly a cohort-selection effect.
- Evidence-group structure was preserved rather than reconstructed after correction. This affects bootstrap dependence assumptions, not deterministic point estimates.
- R80 is discontinuous and uses the pre-specified half-up prefix rule `floor(0.8n + 0.5)`.
- The deterministic hash tie-break makes results reproducible but does not average uncertainty within tied-score blocks. No reported point cohort contained an exact B1/EARS score tie.
- Results concern one verifier, two frozen risk rankings, one same-family development split, and one correction proposal set. Mechanism and broad generalization claims are unsupported.

## Novelty and publication limitations

- The weighted finite-sample AURC identity is a finite-sum rearrangement and is not claimed as a novel theorem.
- Selective prediction, AURC, annotation auditing, and benchmark-instability analysis have prior literature.
- The annotation proposals themselves are third-party contributions, not original V3.1 discoveries.
- Study A+ adds exact influence, exhaustive scenario bounds, and decomposition for this case, but this is modest methodological integration rather than a new general theory.
- The work has not been externally peer-reviewed, accepted, or published. It is not presently sufficient for a standalone performance paper.

## Reproducibility limitations

- Artifact-based replay succeeds in a fresh Python 3.12 environment on the same ARM64 macOS host; this is not a separate-machine or independent-institution replication.
- The exact compact E1 claim-level artifact is hash-verified locally but intentionally absent from the public V2 repository. Full public replay is therefore incomplete unless an authorized release path is established.
- Historical model training/inference was not repeated in Study A+; scores were frozen by design.
- Direct dependencies were pinned, while complete transitive versions are preserved in [`environment/requirements-freeze.txt`](environment/requirements-freeze.txt). Future platform availability is not guaranteed.
- The existing V2 suite produced 39 passes, 61 skips and upstream SWIG deprecation warnings. Skips were not reclassified as passes.
- Public V2 deployment validation did not include a new cloud smoke test or concurrency/load test.

## Documentation, privacy, and release limitations

- Historical `STUDY_A_METRICS.json` contains five absolute macOS paths with a personal username and Codex workspace name.
- The restricted historical Study A driver contains two hard-coded local roots. Its recorded hash is part of Study A provenance, so it was not published or rewritten.
- These two files must remain restricted or be replaced by a separately generated, clearly marked sanitized derivative before public packaging. The originals must remain available in the restricted audit record.
- Some historical documents refer to source files by basename rather than clickable paths. These are provenance descriptions, not Markdown links; a release README should map them to authorized package locations.
- Binary inspection covered PNG textual metadata and SVG XML metadata. No PDF is part of the V3.1 public package; third-party source PDFs were not treated as V3.1 release artifacts.
- All external links returned HTTP 200 during closure, but future link persistence cannot be guaranteed.

## Human and AI contribution limitations

- OpenAI Codex provided substantive assistance with auditing, programming, execution, mathematical verification, and writing. The project must not be represented as entirely unaided work.
- No AI output constitutes biomedical expertise, independent annotation, institutional approval, or peer review.
- A human owner must check the application summary, authorship wording, licenses, and release contents before use.
- No fabricated reviewer approval or adjudication has been added. Independent annotation ratification remains not completed.

## Terminal constraint

V3.1 is closed. Further model development is NO-GO. Any future annotation adjudication would be a separately authorized, pre-specified activity and must not silently reopen or overwrite these frozen results.
