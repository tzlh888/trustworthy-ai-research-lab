# Check-COVID Feasibility Audit

**Audit scope:** read-only inspection of the official repository, paper, data files, retrieval artifacts, and license. No model inference or evaluation was run.

## Source identity

- Repository: [posuer/Check-COVID](https://github.com/posuer/Check-COVID)
- Audited commit: `3ae70f8cac4df13a3ce56878e20d8e76790e422d`
- Commit date: 2023-05-30
- No version tag or release was present at the audited commit.
- Root license SHA-256: `ead1a5b6c71fc912da18df21ba3a0a6b713da2b13939cbb2f02fb97c06fb99eb`.

## Actual split and label distribution

The 1,504 figure is the entire dataset, not the external test sample.

| Split | Claims | SUPPORT | REFUTE | NOTENOUGHINFO | Composed | Extracted | Unique assigned documents |
|---|---:|---:|---:|---:|---:|---:|---:|
| Train | 1,068 | 359 | 358 | 351 | 842 | 226 | 247 |
| Dev | 207 | 69 | 70 | 68 | 160 | 47 | 50 |
| Test | 229 | 77 | 76 | 76 | 180 | 49 | 50 |
| Total | 1,504 | 505 | 504 | 495 | 1,182 | 322 | 347 |

The split union exactly equals the 1,504 unique IDs in `Check-COVID_all.json`. Claim IDs do not overlap across splits. Assigned evidence documents do not overlap between train, Dev, and test. In test, composed and extracted subsets share 11 documents and therefore must be analyzed jointly with document-level grouping.

## File checksums

| Artifact | SHA-256 |
|---|---|
| Train combined | `1af4b5e364129631b49a9132cadcd4f1b4937c90bef22ba0c08242be1630858b` |
| Dev combined | `e64723a546c0ace6a6e1b022120664f36fe4c481e4a9f2d24e5dddc044bee717` |
| Test composed | `24e51eef9c9741c7766fd9df60d03faca7494eae695d59d99135067f9916b440` |
| Test extracted | `4e9a903d3e55d1d7121bdf1c82e28d1490bccbe64e4e06b2b8990b900a7b4985` |
| All claims | `008b930570d374530528efa9edc6b2a029189a6d21b844ce1857324039d9e697` |
| Released 347-document corpus | `2a56084b933f28ec02781a9e501082683ca4b9c4c1c6c8530190d6fb0002ce42` |

## Evidence and rationale structure

Each claim record has exactly one assigned evidence document (`cord_id`). The `evidence_set` contains sentence annotations within that document, not additional documents.

| Split | Claims | One / two / three / four / five rationale sentences | Total rationale sentences | PRIMARY | SUPPLEMENTARY |
|---|---:|---|---:|---:|---:|
| Train | 1,068 | 789 / 229 / 46 / 4 / 0 | 1,401 | 1,090 | 311 |
| Dev | 207 | 161 / 39 / 6 / 1 / 0 | 261 | 213 | 48 |
| Test | 229 | 162 / 47 / 14 / 4 / 2 | 324 | 236 | 88 |

NOTENOUGHINFO records are not “missing annotation” in the file. Each has one PRIMARY sentence selected from the assigned abstract; the paper describes these as non-evidence sentences chosen to have lexical/topic overlap. This semantics differs from V2 SciFact, where claims with no annotated evidence are excluded and `NO_RELATION` is a model prediction rather than a gold class.

Under the V2 eligibility rule, retain only SUPPORT/REFUTE claims and map REFUTE to CONTRADICT. That gives 717 eligible Train, 139 eligible Dev, and 153 eligible test claims. The rule must be encoded explicitly; non-empty `evidence_set` alone would incorrectly include NOTENOUGHINFO.

## Public variant inconsistencies

The experiment variants are not exact, complete projections of the authoritative split files:

- the test `noNEI` and Vespa two-class artifacts omit two eligible composed records;
- the composed oracle two-class artifact omits one of those records;
- the test `noNEI` and Vespa two-class artifacts omit one eligible extracted record;
- the extracted oracle two-class artifact contains all 32 eligible extracted records.

Therefore, sample size and eligibility must be derived from the authoritative test claim files, not from the precomputed retrieval or `noNEI` variants. No individual test label is reproduced in this report.

## Retrieval-corpus audit

### What is released

- `corpus.json` contains 347 abstracts: the exact union of assigned evidence documents across the dataset.
- Train, Dev, and test use disjoint document subsets (247, 50, and 50).
- Oracle retrieval artifacts contain the assigned document only.
- Vespa test artifacts contain zero to eight retained documents per claim after filtering. They include document IDs and abstract text but no retrieval scores.

### What the paper's full pipeline used

The paper describes querying the CORD-19 Vespa service, which ranked a changing CORD-19 corpus using BM25. The top results were filtered and passed downstream. The code requested ten hits, then:

- retained only hits whose DOI mapped into the supplied CORD-19 metadata;
- filtered sentence-tokenization lengths;
- accumulated document IDs in a Python `set`;
- emitted `list(set)` without the Vespa scores.

Consequences:

1. Released ID order is not a reliable BM25 ranking and can depend on hash iteration order.
2. Raw BM25 scores, index snapshot, corpus version, and complete candidate set are absent.
3. The remote service was designed to change as CORD-19 changed.
4. V2's normalized top-two BM25 margin F4 cannot be reconstructed from the released artifacts.
5. The paper itself says retrieval precision and NOTENOUGHINFO full-pipeline evaluation are difficult because CORD-19 contains unannotated relevant abstracts.

### Comparability with V2

| Dimension | Frozen V2 SciFact | Official Check-COVID baseline | Consequence |
|---|---|---|---|
| Claim style | scientific claims | news-derived composed/extracted claims | domain and language shift |
| Candidate corpus | fixed 5,183-document SciFact corpus | changing, much larger CORD-19 Vespa index | different retrieval difficulty and IDF |
| Released local corpus | same 5,183 candidates used by BM25 | 347 assigned evidence documents only | local alternative is gold-pool-conditioned |
| Retrieval implementation | local `rank-bm25`, deterministic, scores stored | Vespa BM25, filtered IDs emitted through a set, scores discarded | F4 not comparable from official artifacts |
| Documents passed downstream | top 5 from top 20 | up to three in the paper; released artifacts vary after filtering | F5 and NLI exposure differ |
| Gold semantics | SUPPORT/CONTRADICT; empty evidence excluded | SUPPORT/REFUTE/NOTENOUGHINFO; all have a sentence set | task adapter required |
| Gold evidence coverage | one or more cited documents per claim | exactly one assigned document per claim; other relevant CORD-19 docs may exist | retrieval recall is incompletely labeled |

A V2-style BM25 index over the 347 released documents is technically computable and can yield F4/F5. It would be a new closed-corpus transfer task, not reproduction of the official Vespa pipeline. This distinction must appear in the title, estimand, and conclusions.

## Test-label access

The official test claim files publish `label`, `cord_id`, and `evidence_set` beside claim text. Aggregate label and eligibility fields were inspected in this audit to answer the mandatory feasibility questions. A future run cannot honestly be called blind. It can still be role-separated and pre-specified by producing a claim-only view, denying the model operator annotation-file access, hashing predictions before scoring, and logging every label access.

## Licensing findings

- The Check-COVID repository applies an MIT license and the paper says data and models are released under MIT.
- The embedded abstracts originate from CORD-19. The current official CORD-19 license grants use and derivatives for text and data mining and makes users responsible for source-level copyright and other restrictions.
- Individual articles may carry additional publisher terms. The Check-COVID MIT file does not eliminate those underlying obligations.
- Before redistribution or publication, retain attribution, cite Check-COVID and CORD-19, avoid republishing unnecessary abstract text, and obtain legal review for uses beyond research text/data mining. This is a technical license audit, not legal advice.

## Feasibility conclusion

**Dataset audit: pass. Direct V2-compatible external evaluation: fail at present.** The authoritative split and eligible population are clear, but the official retrieval path is not reproducibly score-compatible with V2 F4/F5. A defensible study must either reconstruct an immutable score-bearing CORD-19 index or explicitly downgrade to a closed-347-document transport study. Test evaluation must remain stopped until that choice and the power gate are resolved.

## Sources

- [Check-COVID repository](https://github.com/posuer/Check-COVID)
- [Check-COVID paper](https://aclanthology.org/2023.findings-acl.888/)
- [CORD-19 repository](https://github.com/allenai/cord19)
- [CORD-19 license](https://github.com/allenai/cord19/blob/master/LICENSE)
