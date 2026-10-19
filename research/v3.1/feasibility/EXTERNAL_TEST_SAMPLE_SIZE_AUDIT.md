# External Test Sample-Size Audit

## Bottom line

The Check-COVID external test is **229 claims**, not 1,504. Under the frozen V2 eligibility definition adapted without changing its binary label semantics, **153 claims are eligible**. Those claims arise from only **50 independent evidence-document groups**. Analyses that use `n=1,504` or treat `n=153` claims as mutually independent are invalid.

## Derivation

The authoritative files at Check-COVID commit `3ae70f8cac4df13a3ce56878e20d8e76790e422d` contain:

| Test subset | Total claims | SUPPORT | REFUTE | NOTENOUGHINFO | V2-eligible |
|---|---:|---:|---:|---:|---:|
| Composed | 180 | 57 | 64 | 59 | 121 |
| Extracted | 49 | 20 | 12 | 17 | 32 |
| Combined | **229** | **77** | **76** | **76** | **153** |

Eligibility is `label in {SUPPORT, REFUTE}`, with REFUTE mapped to V2 CONTRADICT. NOTENOUGHINFO is excluded rather than mapped to the model's NO_RELATION output.

Every claim has exactly one assigned `cord_id`. Shared document identity and normalized claim identity define the V2-style connected graph before eligibility filtering. There are no normalized-text edges crossing documents in test, so groups equal unique assigned documents.

## Dependence structure

All 50 test documents have at least one eligible claim. Eligible claims per group are:

| Eligible claims in a group | Number of groups | Claims contributed |
|---:|---:|---:|
| 2 | 37 | 74 |
| 4 | 8 | 32 |
| 6 | 2 | 12 |
| 8 | 1 | 8 |
| 10 | 1 | 10 |
| 17 | 1 | 17 |
| **Total** | **50** | **153** |

The clustering is structural, not speculative. Claims sharing a source abstract include composed variants, extracted variants, manual negations, and NOTENOUGHINFO constructions. Their errors and risk scores can be correlated through common evidence content and generation procedures.

## Effective-size sensitivity

There is no single defensible scalar “effective n” before outcomes and intraclass dependence are observed. For orientation only, using the unequal-cluster design effect

`DEFF(rho) = 1 + [(sum(m_g^2) / sum(m_g)) - 1] * rho`

with `sum(m_g)=153` and `sum(m_g^2)=801` gives:

| Assumed within-document ICC `rho` | Design effect | Approximate claim-equivalent n |
|---:|---:|---:|
| 0.00 | 1.000 | 153.0 |
| 0.10 | 1.424 | 107.5 |
| 0.25 | 2.059 | 74.3 |
| 0.50 | 3.118 | 49.1 |
| 1.00 | 5.235 | 29.2 |

At perfect within-group dependence, the group-weighted Kish equivalent is `153^2 / 801 = 29.2`, even though 50 document groups exist. This range is descriptive; AURC is nonlinear and requires direct group-aware simulation rather than a simple independent-observation formula.

## Correct analysis unit

- Compute AURC on all 153 eligible claims because the estimand is claim-weighted selective risk.
- Estimate uncertainty and power by resampling the 50 connected document groups, retaining every eligible claim in a sampled group.
- Apply the same resampled groups to B1 and EARS so the comparison remains paired.
- Report both 153 claims and 50 groups everywhere. Do not report 153 as the independent sample size.
- Predefine how repeated sampled groups contribute duplicate claim rows to AURC and how tie keys distinguish repeated occurrences.

## Development population for planning

Check-COVID Dev contains 207 total claims, 139 eligible SUPPORT/REFUTE claims, and 50 document groups. It is suitable for adapter checks and empirical power-model calibration. It must not be pooled with test for model fitting, threshold selection, or power tuning after test access.

## Limits

- The 50-group count reflects the released document mapping, not every latent dependency introduced by common news sources, annotators, templates, or publication topics.
- Corpus construction and manual negation may create cross-group dependence that document grouping does not capture.
- Group bootstrap inference is conditional on the observed groups and fixed models.
- No power value is claimed here because no authorized, frozen-model Check-COVID Dev prediction set exists.

## Decision implication

The sample is much smaller and more clustered than the proposed `n=1,504` framing. Formal external testing is a No-Go until a development-only, paired group simulation demonstrates acceptable type-I error and power under the 153-claim/50-group design.
