# F4/F5 Feature Contribution

## Fair comparison

All four models used the same 329 fit claims, error target, grouped folds, continuous-feature scaling, L2 logistic learner, `C=0.1`, and 188 Dev claims. F3 is two dummy columns (`is_CONTRADICT`, `is_NO_RELATION`), so B1 has four effective columns and Full EARS has six.

## Results

On fit-only group cross-fitting, B1/F4/F5/EARS AURCs were 0.277892, 0.279638, 0.270241, and 0.271344. On SciFact Dev they were 0.281575, 0.290272, 0.281007, and 0.288355. Thus F5 looked useful during fit cross-validation but supplied essentially zero AURC gain on Dev; F4 degraded Dev AURC.

The 10,000-replicate paired group bootstrap gave:

- F4: ΔAURC +0.008697 [−0.000368, +0.019294];
- F5: ΔAURC −0.000568 [−0.023399, +0.024382];
- F4+F5: ΔAURC +0.006780 [−0.016939, +0.033066].

All R80 contrasts were small and their intervals included zero.

## Conditional information and stability

F4's Dev permutation importance within B1+F4 was −0.00661 mean AUROC change, consistent with harmless or adverse noise. F5's importance within B1+F5 was +0.04673, suggesting conditional information, but it did not translate into a stable endpoint improvement. F4–F5 Pearson correlation was only −0.0293. Maximum VIF was 3.06 (F2); F4 VIF was 1.02 and F5 VIF 2.08. Severe multicollinearity is therefore not the main failure mechanism.

F5 shifted upward from fit mean 0.1147 to Dev mean 0.1629 (standardized mean difference 0.165). Coefficient tables show fold-to-fold variation and must not be treated as causal effects. In the full-fit EARS model, the standardized F4 coefficient was small and negative, while F5 was negative; these signs describe error association conditional on the other columns, not a mechanism guarantee.

## Interaction analysis

A post-hoc model adding F4×F5, F1×F4, and F1×F5 achieved Dev AURC 0.265280 and R80 0.393333. This result is explicitly exploratory: the exact interactions were not a confirmatory endpoint, multiplicity was not controlled, and the same Dev labels had already been accessed. It cannot replace the four-model comparison or support a new success claim.

## Conclusion

F5 contains some conditional signal, especially when the verifier changes, but the preregistered-style matched Dev comparison does not establish reliable incremental value. F4 shows no useful Dev contribution. The correct scientific conclusion is limited evidence, not feature causality or general superiority.
