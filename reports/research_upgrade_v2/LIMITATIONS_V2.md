# Limitations v2

- SciFact Dev is a same-dataset split with two duplicate normalized claims and 181 shared cited documents, not external replication.
- No valid cross-dataset E1/EARS evaluation was available: SciFact-Open fully overlaps at claim level, while HealthVer changes task granularity and lacks a compatible retrieval corpus.
- E1 accuracy remains below 0.50 and SUPPORT recall is only 0.323. Risk ranking cannot repair predictions.
- Dev contains 188 eligible claims and 164 groups; Calibration contains only 88 eligible claims.
- Fixed-score bootstrap omits training and inference uncertainty.
- F4/F5 ablation models were reconstructed from regenerated E1 outputs; only B1/EARS have public frozen numeric parameters.
- E1-v2 is a general-domain NLI substitution, not a scientific-domain verifier, and performed worse.
- Synthetic perturbations do not estimate real-world distribution shift.
- Calibration results are mixed, and ranking scores remain unsuitable as error probabilities.
- Interaction results are post-hoc and exposed to multiplicity and overfitting.
- Public clean reproduction of the historical phased workflow remains incomplete because private manifests and claim-level artifacts were intentionally excluded and one referenced script is absent.
- No clinical, policy, truth-service, or deployment claim is supported.
