# Robustness and Calibration

## Evidence perturbation study

Four perturbations were frozen before evaluation. They are synthetic stress tests, not estimates of natural distribution shift.

| Perturbation | B1 Spearman | EARS Spearman | B1 accepted-set Jaccard | EARS Jaccard |
|---|---:|---:|---:|---:|
| Drop top retrieved document | 0.5354 | 0.5340 | 0.7857 | 0.7857 |
| Remove lowest-ranked selected sentence per document | 0.9364 | 0.9380 | 0.9108 | 0.9108 |
| Replace rank-5 evidence with a deterministically sampled document outside the original retrieval set | 0.8859 | 0.8831 | 0.8987 | 0.8868 |
| Perturb top-two BM25 scores by 5% | 1.0000 | 0.9992 | 1.0000 | 1.0000 |

Dropping the strongest retrieved document causes major instability for both models. EARS is not consistently more stable than B1. The small F4-only score perturbation barely matters, whereas evidence-content changes propagate through NLI features and dominate ranking changes. The sampled document was outside the original retrieval set and was not known cited evidence, but semantic irrelevance was not established.

## Calibration study

Platt scaling was fit on 88 eligible claims from the historical Calibration partition and evaluated on 188 SciFact Dev claims. No Dev labels were used to fit the calibrator.

| Method | Score | Brier ↓ | Log loss ↓ | ECE-10 ↓ |
|---|---|---:|---:|---:|
| B1 | raw ranking score | 0.18738 | 0.55659 | 0.05659 |
| B1 | Platt | 0.18626 | 0.55114 | 0.04341 |
| EARS | raw ranking score | 0.19128 | 0.56128 | 0.07779 |
| EARS | Platt | 0.19458 | 0.56740 | 0.06885 |

B1 improves slightly on all three metrics. EARS improves ECE but worsens Brier score and log loss. With only 88 calibration examples, these estimates are unstable. ECE also depends on binning and should not override proper scoring rules.

## Status

- New perturbation question: **EVALUATED, robustness limited**.
- New calibration question: **EVALUATED, mixed and insufficient for probability claims**.
- Historical H2: **NOT EVALUATED**, unchanged.
- Historical H3: **NOT EVALUATED**, unchanged.

Neither B1 nor EARS output should be displayed as a validated probability of error.
