# E1 Error Analysis

## End-to-end performance

On 188 eligible SciFact Dev claims, E1 was correct on 92 (accuracy 0.489362). The confusion matrix (rows gold, columns predicted) was:

| Gold \ Predicted | SUPPORT | CONTRADICT | NO_RELATION |
|---|---:|---:|---:|
| SUPPORT | 40 | 57 | 27 |
| CONTRADICT | 5 | 52 | 7 |

SUPPORT precision/recall/F1 were 0.8889/0.3226/0.4734. CONTRADICT precision/recall/F1 were 0.4771/0.8125/0.6012. The apparently high SUPPORT precision masks severe under-prediction: 84/124 SUPPORT claims were wrong.

## Pipeline diagnostics

- gold-document recall@5: 0.842105; claim hit@5: 0.904255;
- pipeline gold-sentence recall@5: 0.516393;
- complete-rationale recovery@5: 0.684211;
- conditional sentence recall after a gold document was retrieved: 0.609677.

The gap shows that retrieval often reaches the right abstract, but top-three lexical selection fails to retain all decisive sentences. Among 96 errors, non-exclusive categories were: 69 NLI/reasoning, 19 sentence selection, 8 retrieval, 34 neutral misclassification, 20 aggregation, and 20 multi-document conflict. Categories overlap; summing them is invalid.

NO_RELATION was predicted 34 times and was wrong on all 34 eligible claims. It remains an aggregation outcome, not an evidence-insufficiency label. The risk models assigned it high mean risk, but a few NO_RELATION errors still entered the accepted set.

## Representative cases

`results/representative_failure_records.jsonl` contains twenty copyright-conscious records with claim IDs, labels, retrieval/selection flags, and taxonomies but no claim or evidence text. Typical patterns are: a retrieved gold document with incomplete rationale selection; a correct relation candidate losing during aggregation; and SUPPORT claims being converted to CONTRADICT by a high-confidence sentence from another document.

## E1-v2 candidate

Replacing only the NLI model with DeBERTa-v3-small reduced accuracy to 0.473404. SUPPORT recall fell to 0.282258 while CONTRADICT recall rose to 0.843750. NLI/reasoning errors rose to 73 and aggregation failures to 26. This candidate is not an upgrade and does not replace E1.

## Interpretation

The dominant limitation is not a single retrieval metric. It is the coupled effect of incomplete evidence selection, asymmetric sentence-level NLI, and winner-take-all aggregation. Improving risk ranking cannot repair a verifier whose SUPPORT sensitivity is this low.
