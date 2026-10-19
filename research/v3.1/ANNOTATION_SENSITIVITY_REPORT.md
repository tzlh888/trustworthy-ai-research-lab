# Label-Uncertainty Bound Report

## Question and scope

This report asks how many **documented, proposed** SciFact Dev annotation changes would be sufficient to reverse the frozen point-estimate ordering `ΔAURC = AURC_EARS − AURC_B1`. Negative values favor EARS; positive values favor B1. It does not estimate the probability that either system is correct, and it does not treat the proposals as established truth.

The original point estimate is `+0.0067799766`. Under the Study A primary corrected interpretation it is `+0.0014628740`. Both are small relative to the paired sampling interval; the corrected 95% group-bootstrap CI is `[-0.0218161, +0.0269934]`.

## Primary fixed-cohort bound

The primary bound holds membership at the 182-claim common cohort and varies the five retained claim-label proposals (`208`, `593`, `808`, `879`, `1385`). Claims `593`, `597` and `808` do not change claim-level correctness under their primary interpretations; Claim 597 is document-level and stays SUPPORT because two other supporting documents remain. Consequently the five effective label alternatives in the common-cohort enumeration are the retained claim-level proposals, with zero-influence changes retained where documented.

All `2^5 = 32` scenarios were enumerated exactly.

| Result | ΔAURC | Adopted proposals |
|---|---:|---|
| minimum | `-0.0001683752` | `879`, `1385` |
| maximum | `+0.0089334346` | `208` |
| primary all-proposals point | `+0.0014628740` | all five retained proposals |

Four of 32 scenarios reverse the point ordering. The minimum is **two** admissible label modifications: adopting claims `879` and `1385` yields ΔAURC `-0.0001683752`. This is a point-estimate reversal extremely close to zero; it is not statistical significance and is not evidence that those proposals are true.

## Eligibility-aware documented bounds

The broader primary scope enumerates all 11 documented claim-level proposals, allowing the original eligibility rule to remove a claim when its proposed claim label becomes NEI. All `2^11 = 2,048` scenarios were recomputed exactly, including new `n`, ranks, weights and group counts.

- Minimum: `-0.0015161791`, with `879`, `1216`, `1368`, `1385` adopted (`n=186`, 163 groups).
- Maximum: `+0.0098961799`, with `208`, `343`, `770`, `847`, `1274`, `1368` adopted (`n=183`, 160 groups).
- Reversals: 256/2,048 scenarios.
- Minimum modifications: two. The two minimum-cardinality reversals are (`879`,`1385`) → `-0.0004877668` at `n=188`, and (`1216`,`1385`) → `-0.0006264023` at `n=187`.

Claim 597 requires a separate scope because the correction file's `doc_id:null` claim-level entry conflicts with the document-specific evidence record. Under the primary document-only reading, doc `12779444` becomes NEI while the claim remains SUPPORT via docs `25742130` and `36355784`, so its claim-level influence is zero. Under the literal `doc_id:null → NEI` reading, the entire claim is removed. Enumerating this extra alternative gives `2^12 = 4,096` scenarios: the minimum remains `-0.0015161791`; the maximum becomes `+0.0111853012`; 256 scenarios reverse; minimum modifications remains two. The literal reading is a sensitivity case, not the primary resolution.

## Why individual influences do not simply sum after deletion

For label-only fixed-cohort changes, exact influences add because weights and ranks are fixed. For NEI-induced exclusions, deleting an item changes the denominator and all later weights; combinations must be recomputed. The exact enumeration performs that recomputation. It also uses the unchanged evidence-group mapping only to describe the bootstrap sampling structure; grouping does not enter deterministic AURC.

## Secondary adversarial exploration

As a deliberately hypothetical mathematical stress test, arbitrary binary correctness indicators were allowed to flip even without a documented annotation dispute. This is **not** an annotation-error claim.

- Original cohort: flipping claim `124` alone changes ΔAURC by `-0.0121453901`, yielding `-0.0053654135`.
- Common cohort: the analogous flip changes ΔAURC by `-0.0125457875`, yielding `-0.0052436021`.

This demonstrates local fragility of a rank-weighted point statistic, not a plausible real correction scenario.

## Conclusion

The sign of the point comparison is not robust to the documented annotation uncertainty: two proposed changes suffice to cross zero. At the same time, no admissible scenario here establishes a statistically reliable difference. Sampling uncertainty (bootstrap variation under a fixed annotation scenario) and annotation uncertainty (variation across defensible label/eligibility scenarios) are separate; neither can be substituted for the other.
