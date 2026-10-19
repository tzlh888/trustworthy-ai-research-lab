# Claim 597 Resolution Report

## Decision status

Claim 597 is **not independently adjudicated**. For the primary Study A analysis, the BioNLP audit proposal is interpreted as a **document-level** correction affecting SciFact document `12779444` only. The claim-level label remains `SUPPORT` because documents `25742130` and `36355784` independently contain incidence evidence. A separate sensitivity analysis applies the machine-readable JSON literally and treats the entire claim as `NEI`.

This is an analytic scope decision, not a declaration that the proposed correction is ground truth.

## Source record

SciFact Dev Claim 597 states: “Incidence rates of cervical cancer have decreased.” Its original evidence contains three documents, each labeled `SUPPORT`:

| Document | Source content relevant to the claim | Study A interpretation |
|---|---|---|
| `12779444` | Mortality in England and Wales; the assigned rationale concerns women dying and mortality trends. | Proposed `NEI` for this claim–document pair because mortality is not incidence. |
| `25742130` | Reports that incidence and mortality rates declined more in Finland. | Retains proposed `SUPPORT`. |
| `36355784` | Reports cervical-carcinoma incidence falling from 15.4 to 2.7 per 100,000 woman-years. | Retains proposed `SUPPORT`. |

The relevant official SciFact files have SHA-256 values:

- `claims_dev.jsonl`: `86f0435d08fdb65d1aa41d1472684f57e6e71930626497bdf4d7a9ec1a632217`
- `corpus.jsonl`: `b8d6c89624cb2ed74dee8938effc4f5d8bd2086887880af8110d64be4ceade62`

## Contradictory audit artifacts

The audit repository is internally inconsistent about scope:

1. `corrections/dev_corrections.json` gives Claim 597 `doc_id: null` and `corrected_label: "NEI"`. Its documented application example applies corrections at claim level. A literal implementation therefore excludes Claim 597 from binary evaluation.
2. `corrections/README.md` calls this a “per-document outcome mismatch” and says only one of three evidence documents is mismatched.
3. The paper states that Claim 597 has “one additional per-document error” and that the mismatched document concerns mortality rather than incidence.
4. The manual-review CSV contains the mortality abstract and identifies the outcome mismatch.
5. The blind-packet unblinding key marks all three Claim 597 pairs as `is_confirmed_error_in_paper=True`, including the two documents that explicitly discuss incidence decline. That flag cannot be reconciled with the paper's one-document description without further author clarification.

The JSON does not identify the affected document. Document `12779444` is inferred from the claim, corpus, paper description, and manual-review record. The inference is strong but remains an inference.

Source hashes:

- audit correction JSON: `c45ff40e3a8906192595462596dd56146e476aafa5b39fb3cf5a367b80a62b23`
- audit corrections README: `bdd98405b6c5e188b10f72b115b23d6cf4116bebc1ece51035b110a3a63c8eb6`
- audit paper source: `eebcc98f78c89b66cb045e09303ef3865e2326355f4b9a3df02885624e056841`
- unblinding key: `e00d75f3c75eed590df88b83f329d03c7c4cff6df70fab27b172dc7ab56bb179`

## Effect on Study A

Under the primary document-level interpretation:

- Claim 597 remains in Cohorts A, B, and C as `SUPPORT`.
- Its frozen prediction is `SUPPORT`, so its correctness remains unchanged.
- Its group is group `597`, which also contains Claim 598; group membership is unchanged.
- Removing a gold-evidence association does not change the already frozen E1 prediction or B1/EARS scores.

Under the literal-JSON sensitivity:

- Claim 597 becomes `NEI` and is excluded by the original V2 binary eligibility rule.
- The population changes from 182 to 181 claims but remains 159 connected groups because Claim 598 retains group `597`.
- ΔAURC changes from `+0.001463` to `+0.002937`; ΔR80 changes from `−0.013699` to `−0.013793`.
- The paired 95% connected-group bootstrap intervals still include zero for both endpoints.

## Independent adjudication protocol

No reviewer approval has been obtained. A defensible adjudication should occur before treating any correction as established:

1. Freeze a claim–document annotation manual based on the original SciFact semantics. The permitted labels are `SUPPORT`, `CONTRADICT`, and `NEI`; the judgment must be grounded only in the assigned abstract and rationale.
2. Use Claim 597 as three separate claim–document units. Do not expose the original label, the BioNLP proposal, model predictions, correction status, or other reviewers' decisions.
3. Recruit at least two independent human reviewers with appropriate biomedical-literature competence. Record label, confidence, cited sentences, and a short rationale for every document.
4. Have a third independent reviewer adjudicate disagreements using the frozen manual. Preserve pre-adjudication decisions and report agreement; do not overwrite them with a consensus-only record.
5. Derive the claim-level label only after document-level adjudication. Under the V2 rule, exactly one authentic claim-level label must be derivable from non-empty evidence; mixed labels must be surfaced rather than silently collapsed.
6. Predefine the treatment of multiple documents: if at least one document supports the claim while another is `NEI`, the `NEI` document is removed from supporting evidence but does not erase valid support. If reviewers instead adopt a different aggregation rule, rerun all cohorts and label it as a separate scenario.
7. Hash the packet, completed annotations, adjudication log, and derivation code. Record reviewer qualifications and conflicts without fabricating identities or approval.

Until that protocol is completed, both the document-level primary interpretation and the literal-JSON alternative remain sensitivity scenarios around a third-party, single-annotator proposal.
