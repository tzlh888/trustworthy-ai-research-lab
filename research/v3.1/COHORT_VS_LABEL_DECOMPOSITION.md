# Cohort Composition Versus Label Correction Decomposition

## Estimands

Four deterministic evaluations isolate the available effects:

- **A — original:** 188 eligible claims, original labels.
- **B0 — common/original:** the 182 claims eligible under both scenarios, original labels.
- **B1 — common/corrected:** the same 182 claims, proposed primary claim labels.
- **C — corrected eligible:** eligibility recomputed after correction, corrected labels; here C and B1 contain the same 182 claims.
- **A1 — original membership/corrected where defined:** 188 claims retained while applying label changes; used only to obtain the reverse-order decomposition.

The six claims excluded under corrected eligibility are `343`, `770`, `847`, `1216`, `1274`, and `1368`. Every one was an error for the frozen verifier under the original labels. Removing errors therefore mechanically lowers both absolute AURCs and R80s; this is not evidence about a causal mechanism.

## Point estimates

| Metric | A original | B0 common/original | B1 common/corrected = C |
|---|---:|---:|---:|
| B1 AURC | 0.2815753254 | 0.2667842014 | 0.2644840803 |
| EARS AURC | 0.2883553020 | 0.2740863869 | 0.2659469542 |
| ΔAURC | +0.0067799766 | +0.0073021854 | +0.0014628740 |
| B1 R80 | 0.4133333333 | 0.3972602740 | 0.3904109589 |
| EARS R80 | 0.4000000000 | 0.3835616438 | 0.3767123288 |
| ΔR80 | -0.0133333333 | -0.0136986301 | -0.0136986301 |

Composition-first path (`A → B0 → B1`) attributes ΔAURC change `+0.0005222088` to removing the six claims and `-0.0058393115` to retained-claim label changes. Because the attribution is path-dependent, Study A+ also computed the label-first path (`A → A1 → C`) and reports a two-factor symmetric Shapley average.

## Symmetric decomposition

| Metric | Total A→C change | composition contribution | label contribution |
|---|---:|---:|---:|
| B1 AURC | -0.0170912451 | -0.0147462441 | -0.0023450011 |
| EARS AURC | -0.0224083478 | -0.0142829015 | -0.0081254462 |
| ΔAURC | -0.0053171026 | +0.0004633425 | -0.0057804452 |
| B1 R80 | -0.0229223744 | -0.0161643836 | -0.0067579909 |
| EARS R80 | -0.0232876712 | -0.0165296804 | -0.0067579909 |
| ΔR80 | -0.0003652968 | -0.0003652968 | approximately 0 |

Thus most of the reduction in each method's absolute AURC comes from composition—the deliberate exclusion of six frozen-model errors. In contrast, most of the reduction in paired ΔAURC comes from retained-claim label corrections, especially the highly differential influence of claim `1385`. The composition contribution to ΔAURC is small and positive.

## Group structure

The original cohort contains 164 sampling groups; the common/corrected cohort contains 159. Lost group IDs are `343`, `770`, `847`, `1216`, and `1274`; claim `1368` shares a group linkage such that six claim removals produce five lost groups. The evidence-group graph was **not rebuilt** after correction.

This affects the dependence structure used by the paired group bootstrap. It does not alter deterministic AURC or R80, which operate on ordered claim rows. Consequently, the group-count change must not be counted as an additional point-estimate effect. A fresh graph construction based on corrected evidence would be a different analysis and was not silently introduced.

## Interpretation

The decomposition is descriptive and conditional. It shows which arithmetic operation changes the reported metrics; it does not show why EARS or B1 behaves differently, and it supplies no controlled causal identification. In particular, lower AURC after excluding known errors is partly a selection effect created by the eligibility rule.
