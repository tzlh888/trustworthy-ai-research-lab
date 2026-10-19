# F6 Negative-Control Plan

**Status:** development protocol only. F6 does not exist in frozen V2, and no F6 result is reported.

## Purpose

F6 is a candidate label-free measure of how sensitive the verifier's output is to removal of retrieved documents. It may be useful as an instability signal, but a naïve removal effect is confounded by rank, retrieval score, document length, number of NLI pairs, and generic information loss. The controls below are required before F6 can enter any risk model.

## Freeze the probability object first

The V2 pipeline exposes valid three-class sentence-level NLI vectors but not a naturally calibrated claim-level probability distribution. F6 must not compute KL divergence, Jensen-Shannon divergence, entropy, or total variation on arbitrary non-normalized maxima.

Choose one of two valid objects on development data:

1. **Sentence-set distribution:** aggregate all sentence-level vectors with a prespecified operator, then renormalize once.
2. **Claim-level distribution:** define nonnegative SUPPORT, CONTRADICT, and NO_RELATION masses from the frozen aggregation and divide by their sum.

The exact operator must be frozen before outcome association is examined.

For every base and perturbed vector, assert:

- exact class order is documented;
- length is three;
- all values are finite and in [0,1];
- sum is within `1e-6` of 1 after one declared normalization step;
- no denominator is zero;
- identical inputs return byte-identical vectors in repeated runs;
- a no-op perturbation has distance zero within `1e-12`;
- class-label mapping matches the pinned verifier configuration.

If any assertion fails, F6 is undefined for that record. Missingness must be reported; it cannot be silently imputed from labels.

## Candidate F6 definition

For each claim with retrieved documents `d1...dK`:

1. Run the frozen base pipeline and obtain probability vector `p`.
2. For each document, remove it without rerunning retrieval, preserve the order of all remaining documents, and obtain `p(-j)`.
3. Compute Jensen-Shannon divergence `JSD(p, p(-j))` using a fixed log base and epsilon policy.
4. Define provisional `F6_max` as the maximum divergence across removals and record the argmax rank.

Alternative summaries such as mean JSD or top-1-removal JSD may be compared on development data once. Choose one primary F6 before any external-test prediction. The choice and every candidate considered must be logged to expose researcher degrees of freedom.

F6 is computed without gold labels, gold document IDs, rationales, or eligibility.

## Mandatory negative controls

### C0 — no-op determinism

Re-run the unchanged document list through the same code path. Expected JSD is zero and class prediction is identical. This detects nondeterminism, caching errors, and numerical drift.

### C1 — label-free uniform-rank removal

Remove a rank chosen by a deterministic hash of claim ID from the available ranks. The seed is frozen. This estimates generic deletion sensitivity without using outcomes or gold evidence.

### C2 — rank-matched removal

For each target-removal event, select a control event at the same retrieval rank from another development claim, matched without labels on:

- candidate-set size;
- document sentence-count bin;
- claim-length bin;
- base predicted category.

Apply the selected rank within the recipient claim. Matching is performed before labels are joined.

### C3 — score-matched removal

Match the removed document's normalized BM25 score or within-claim score percentile within a prespecified caliper. Match additionally on rank where overlap permits. If exact rank-and-score matching is sparse, use coarsened strata fixed before outcome analysis and report unmatched rates.

### C4 — replacement control

Replace, rather than merely delete, the selected document with a deterministically selected out-of-retrieval corpus document matched on sentence count and BM25-score bin. Recompute actual NLI inputs. Do not call the replacement semantically irrelevant unless that is independently established; “out-of-retrieval matched replacement” is the permitted description.

### C5 — metadata-only score control

Perturb the top-two BM25 scores while leaving document content and order fixed, using symmetric prespecified factors. This distinguishes direct F4 sensitivity from NLI-content sensitivity. It cannot be interpreted as a natural retrieval intervention.

### C6 — deletion-size control

Remove the same number of sentences or tokens from a non-target document while preserving rank count. This checks whether F6 merely measures less input text.

All random-looking choices use a published SHA-256-based deterministic selector. No control may query gold evidence status.

## Development-only evaluation

Run controls separately on SciFact Dev and Check-COVID Dev. Before joining labels, freeze:

- base and perturbed probability vectors;
- removal/replacement identities and ranks;
- BM25 scores and matching strata;
- F6/control values;
- unmatched/missing indicators;
- artifact hashes.

After the freeze, labels may be joined for:

- paired comparison of F6 versus each matched control;
- association with binary verifier error;
- incremental cross-fitted B1+F6 versus B1 ranking on development data;
- distribution by predicted class, claim type, group size, and retrieval margin.

Use connected-group cross-fitting and paired group bootstrap. Any model selection is development-only and must count all tried definitions.

## Gold-evidence diagnostics — development only

Gold document identity and rationales may be used only after all label-free artifacts are frozen, and only to describe:

- whether the highest-sensitivity removed document was a gold document;
- F6 distributions for removal of gold versus non-gold documents;
- gold-document recall at K;
- whether decisive gold sentences survived sentence selection;
- complete versus partial rationale recovery.

These diagnostics must not:

- choose the target removal;
- set score calipers or thresholds;
- enter F6 or a risk model;
- select a corpus or feature definition;
- be run on the reserved external test for model development.

## Prespecified validity criteria

F6 may advance beyond development only if:

- C0 passes for every claim;
- at least 95% of claims have valid probability vectors and a valid F6 value;
- at least 90% of target removals obtain a rank- and score-matched control, or the protocol is revised before any test use;
- F6 differs from matched controls by a prespecified paired standardized effect and has a group-bootstrap interval that excludes zero on the chosen development dataset;
- any B1+F6 improvement is evaluated with connected-group cross-fitting and is not dependent on one group;
- findings replicate in direction across SciFact Dev and Check-COVID Dev, or the feature is explicitly labeled dataset-specific.

The exact standardized-effect threshold is not yet justified and must be frozen with the power plan. Failure means F6 is omitted; it does not authorize a post-hoc alternative.

## Causal-language restriction

Document removal is a controlled intervention on this software pipeline. It can establish that the output changes when specified input content is removed. It does not establish that retrieval instability caused naturally occurring verification errors, that a gold document is uniquely causal, or that the same mechanism operates in another dataset. Error associations and subgroup differences remain observational.

## Test-set rule

If F6 passes development gates, compute it on the claim-only test run without accessing labels or assigned `cord_id`. Do not run gold-evidence diagnostics on test before the primary prediction hash is frozen. Any later test gold diagnostics are descriptive, one-time, and cannot change the model or interpretation threshold.
