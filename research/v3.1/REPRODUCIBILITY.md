# V3.1 Reproducibility

## Reproduction levels

| Level | Public status | Meaning |
|---|---|---|
| Frozen V2 integrity | Verified | V3.1 was prepared from V2 commit `6bca11589fb35f4dc8ef5bf9ac642e3369741351`; historical V2 files were not rewritten. |
| Study A artifact replay | Partial | Deterministic when the official SciFact inputs, proposed-correction source, and hash-identified compact E1 artifact are supplied. The compact E1 artifact is not public. |
| Study A+ mathematics | Reproducible | The public synthetic tests verify direct/weighted AURC equivalence and exact one-label/paired influence. |
| Independent end-to-end scientific reproduction | Not verified | No independent institution or qualified human adjudication reproduced the study. |

## Verify the package

From `research/v3.1/`:

```bash
shasum -a 256 -c MANIFEST.sha256
```

The manifest is relative to this directory and excludes itself.

## Run the public mathematical tests

Python 3.12 is the recorded interpreter. In a fresh environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install numpy==2.5.4 pytest==9.1.1
PYTHONPATH=scripts python -m pytest -q -p no:cacheprovider scripts/test_study_a_plus.py
```

The test file uses synthetic inputs only. It enumerates all binary error sequences through length 8, exhaustively checks paired permutations through length 6, and runs 10,000 randomized cases.

## Replay the real artifact-based analysis

The portable driver takes paths as arguments and rejects any required source whose SHA-256 differs from the frozen record:

```bash
python scripts/study_a_plus.py \
  --root <PROJECT_ROOT> \
  --source-v2 <PROJECT_ROOT> \
  --private-v2 <AUTHORIZED_V2_ARTIFACT_ROOT> \
  --audit <SCIFACT_AUDIT_ROOT> \
  --output-dir <OUTPUT_DIR>
```

Required inputs and expected SHA-256 values:

| Input | SHA-256 |
|---|---|
| SciFact Dev claims | `86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217` |
| SciFact corpus | `b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62` |
| compact frozen E1 artifact | `3c1ea9104569f18882881d5ff2861696c06ed723fff208f66fd0e7a60f35c941` |
| proposed Dev corrections | `c45ff40e3a8906192595462596dd56146e476aafa5b39fb3cf5a367b80a62b23` |
| V2 protocol | `70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301` |

The official SciFact data and the correction audit must be acquired from their official repositories under their respective terms. The compact E1 artifact is deliberately not redistributed here. Therefore this command documents the complete gate but is not advertised as runnable from the public checkout alone.

## Recorded clean-environment verification

The closure run used CPython 3.12.15 on ARM64 macOS. The Study A+ tests passed, the frozen V2 suite reported 39 passed and 61 skipped, and clean-environment Study A+ CSV/JSON outputs were byte-identical to the audited originals. Exact transitive packages are listed in [`environment/requirements-freeze.txt`](environment/requirements-freeze.txt).

This was an isolated virtual-environment replay on the same host, not an independent-machine or human replication.

## Source adaptation record

The public `scripts/study_a_plus.py` is byte-identical to the closure script. It replaced the restricted historical Study A driver for publication because the historical driver contained owner-machine paths. Public report copies carry a note wherever path or release-boundary wording was adapted. Scientific values were not regenerated or changed for publication.
