# Research Decision Log v2

All entries describe actions taken during this upgrade on 14 October 2026 (Europe/Budapest). They are not attributed retroactively to the project owner.

1. The specified working directory contained no repository. The public GitHub repository was cloned; no remote write was made.
2. Git HEAD, status, hardware, Python versions, tracked files, configurations, aggregate results, tests, and Git history were recorded before modification.
3. Python 3.12 was selected because the project excludes 3.14. A local virtual environment was created.
4. The v2 protocol was written and hashed before SciFact Dev performance-label evaluation. Existing historical labels and conclusions were not edited.
5. Official SciFact data were downloaded only through the repository's SHA-256-verifying script.
6. Original V2 scoring used only claim IDs/text downstream, but the Dev ID-discovery step deserialized full annotation-bearing records. This historical access is now disclosed; no scoring dependence on annotations was detected.
7. On 14 October 2026 a restricted projection parser was implemented and adversarially tested. Corrective E1 and E1-v2 replay produced exact equality for predictions, F1-F5, and frozen risks. This is post-study engineering verification, not renewed unseen-data status.
7. DeBERTa-v3-small was chosen as an isolated NLI replacement with the same retrieval, selection, and aggregation. It was not described as scientific-domain trained.
8. After blind manifests were verified, labels were opened for evaluation. All eligible examples were retained.
9. F4/F5 comparisons used fixed logistic settings and identical samples. Group bootstrap used the prespecified unit and 10,000 replicates.
10. SciFact-Open was downloaded for schema and overlap audit. Because all 279 claims duplicate original SciFact claims and no strict clean subset exists, performance evaluation was rejected.
11. HealthVer was rejected for the full comparison because its pair-level Neutral label and missing retrieval corpus make F4/E1 semantics non-equivalent.
12. E1-v2 was retained despite worse accuracy. The post-hoc interaction result was retained but labeled exploratory.
13. Claim/evidence text and raw files were kept out of public results. Aggregate CSV/JSON, hashes, and derived case labels were retained.
14. Historical H1 remained INCONCLUSIVE; historical H2/H3 remained NOT EVALUATED.
