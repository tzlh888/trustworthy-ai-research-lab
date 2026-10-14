# Ten Technical Interview Questions with Evidence-Based Answers

`AI-GENERATED PREPARATION MATERIAL — NOT OWNER EVIDENCE`

These project-level reference answers support study. They do not show that the owner has personally answered or independently verified the material. Owner evidence requires the separate dated verification worksheet.

## 1. What exactly does EARS predict?

EARS ranks the probability-like score of the frozen E1 verifier being wrong, using a logistic regression trained on fit-only error labels. The score is not calibrated because historical H3 was not executed, so the project calls it a risk score rather than a true error probability.

## 2. Why is B1 the primary comparator instead of maximum confidence?

B0 maximum confidence is reported, but B1 is the fair ablation for the research question. B1 and EARS use the same 329 training claims, target, logistic-regression class, standardization, regularization, and solver. EARS differs only by adding F4 and F5 evidence features. This isolates their incremental ranking value more cleanly.

## 3. How did you prevent test leakage?

The Phase 3A workflow froze the protocol, trained final risk models only on eligible fit claims, saved model hashes, loaded only test claim text for inference, and hashed E1 predictions, F1-F5, and risk scores before deserializing authentic test evidence labels. The model was never retrained after label access.

## 4. Why use claim groups in splitting and bootstrap?

Claims can share cited documents or identical normalized text. Treating them as independent could leak related evidence across splits and understate uncertainty. The workflow formed connected components using those links before splitting and resampled eligible-containing groups, not individual claims, in the paired bootstrap.

## 5. What is the difference between AURC and R80?

AURC averages selective risk over every accepted-prefix size from one to n, so it measures global ordering. R80 measures one internally prespecified prefix: 70 accepted claims out of 88. EARS can improve many prefixes and therefore AURC while still moving unfavorable errors across the specific R80 boundary.

## 6. Why was H1 inconclusive if the AURC confidence interval excluded zero?

The internally frozen joint rule required both the AURC and R80 EARS-minus-B1 95% CI upper bounds to be strictly below zero. The R80 point estimate was positive and its interval was [0, 0.063492], so the joint criterion failed. Changing the rule after seeing results would be outcome-driven analysis.

## 7. What did NO_RELATION mean in this experiment?

It meant that all 15 sentence-level NLI predictions were neutral after the frozen aggregation rule. It was not a human evidence-insufficiency label. Six eligible test claims were predicted NO_RELATION and all were errors. Removing them did not resolve the AURC-versus-R80 conflict.

## 8. What is the strongest evidence that high NLI confidence can be misleading?

Claim 1159 was an incorrect SUPPORT-to-CONTRADICT decision with B0 risk about 0.00194, corresponding to roughly 0.998 winning-class confidence. This is one traced example, not proof that all high-confidence NLI outputs are unreliable. Across the full test, B0 AURC was 0.420457, worse than B1 and EARS.

## 9. What limits the generality of the result?

Only 88 claims and 39 eligible connected groups entered the primary test. The Internal Test came from the same original SciFact Train file rather than an external dataset. The base verifier made 45 errors, the NLI model was not scientific-domain-specific, and no real-world evidence-insufficiency or calibration experiment was performed.

## 10. What would be a scientifically valid next step?

A scientifically valid next step would preregister either an H2 evidence-degradation study, an H3 calibration study using the untouched calibration partition, or an external replication with a stronger scientific verifier. Any modified model must be evaluated on new independent data because the current Internal Test labels have already been used.

