# V3.1 Third-Party Notices and Redistribution Boundary

This directory does not redistribute raw benchmark datasets, scientific-paper corpora, model weights, private prediction artifacts, or third-party source repositories.

## SciFact and S2ORC

- Official SciFact repository: <https://github.com/allenai/scifact>
- SciFact claims and evidence annotations: CC BY 4.0, according to the official release.
- SciFact corpus abstracts derive from S2ORC material under ODC-By 1.0.
- Official SciFact code: Apache-2.0.

The CSV files in `data/` contain identifiers, mappings, labels, limited claim text, and derived evaluation fields needed to audit the reported sensitivity analysis. Dataset-originated content remains subject to its source terms; the repository's Apache-2.0 license does not override them.

## Proposed SciFact corrections

- Source: <https://github.com/Kefez/scifact-audit-bionlp2026>
- Frozen source commit used by V3.1: `5711f3fdf2305552df2b6e700dca2ebd7c8806e1` (`v1.0-bionlp2026`)
- Proposed Dev correction SHA-256: `c45ff40e3a8906192595462596dd56146e476aafa5b39fb3cf5a367b80a62b23`

The source repository states that its corrections, manual-review CSVs, and annotator packets are CC BY 4.0 and derived from SciFact. V3.1 treats these as third-party, independently unratified proposals.

## Check-COVID and CORD-19

- Check-COVID: <https://github.com/posuer/Check-COVID>
- CORD-19: <https://github.com/allenai/cord19>

V3.1 audited Check-COVID feasibility but did not run or publish an external evaluation. No Check-COVID claim files or CORD-19 abstracts are redistributed in this package. The feasibility reports link to official sources and record the applicable source-specific terms and uncertainty.

## Models and software

No NLI model weights or serialized trained models are included in `research/v3.1/`. The Python script depends on NumPy; tests additionally use pytest. These dependencies retain their own licenses. Matplotlib-generated figures contain aggregate project results and record Matplotlib provenance in SVG metadata.

This is a technical provenance review, not legal advice. Users remain responsible for checking current upstream terms before redistribution or reuse.
