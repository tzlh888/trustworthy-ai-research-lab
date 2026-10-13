# Cloud Security, Privacy, and Research-Integrity Audit

## Audit Conclusion

**PASS for a GitHub/Streamlit deployment candidate, subject to owner review and an actual cloud smoke test after push.** The candidate contains no raw SciFact corpus, claim files, Internal Test claim-level truth, joblib/pickle bundles, Hugging Face weights, secrets, or local cache. It does contain two small, self-authored frozen numeric model records whose source hashes and behavior were independently checked.

## Data and Model Supply Chain

### SciFact

The loader accepts only the Phase 0 audited official archive. It enforces a 16 MiB download ceiling, exact archive byte count, archive SHA-256, exact member name, member type, member byte count, extracted-corpus byte count, and corpus SHA-256. Extraction streams only the named member and uses an atomic replacement after verification, avoiding general archive extraction and path traversal.

If a configured, repository-layout, or cached corpus is present but fails validation, execution stops. The app does not substitute an unverified mirror, synthetic corpus, or third-party conversion. User-facing errors state whether download or integrity verification failed without exposing local paths or a traceback.

### Frozen risk models

The public app never deserializes pickle or joblib. The manifest and numeric JSON are checked against hard-coded SHA-256 values and byte counts before parsing. Additional semantic checks cover the freeze status, source hash linkage, training counts, binary classes, convergence, feature dimensions, finite positive scales, and finite output scores.

The separate audit script can compare against private joblib bundles, but only after their known Phase 3B hashes match. This optional local-audit behavior is not called by the Streamlit application.

### NLI model

The model ID and immutable revision are frozen in the checked configuration. Transformers loads the tokenizer and model from that revision. The public repository does not redistribute the weights. The upstream model uses Apache-2.0 licensing according to its pinned model repository. A pinned Git revision reduces version drift but does not eliminate external-host availability or all upstream supply-chain risk.

## Privacy Review

The public scanner checks text for user-home absolute paths, private tool-workspace markers, common assigned-secret patterns, OpenAI-like keys, and GitHub-like tokens. It also rejects raw SciFact filenames and serialized model/weight suffixes outside ignored cache and version-control metadata.

No scanner finding remained after the final audit. The application does not call a project-operated inference API. A user's claim remains within the Streamlit process; on a cold start, Transformers may contact Hugging Face to obtain pinned model files. Normal Streamlit hosting logs and platform telemetry are outside this repository's control and should be considered before entering sensitive text.

## Public-Repository Exclusions

The following remain excluded by `.gitignore` and the release policy:

- raw SciFact claims and corpus;
- Phase 3B joblib bundles and other executable serialized models;
- claim-level Internal Test predictions and labels;
- downloaded NLI weights;
- `.env` files, Streamlit secrets, caches, build products, and local virtual environments.

The release candidate does not contain an API token and does not need a Streamlit secret.

## Scientific-Integrity Controls

- Phase 0-3B read-only hash verification passed across all recorded sections.
- The model freeze predates Internal Test access according to the original manifest.
- The public numeric scorer agrees with the trusted original model below the 1e-12 gate.
- No training, calibration, feature selection, or deployment-threshold selection occurs in the app.
- The demo's percentile language is descriptive context only and explicitly states that no deployment threshold was selected.
- The UI simultaneously reports lower EARS AURC and worse EARS R80, preserving the H1 INCONCLUSIVE conclusion.
- H2 and H3 remain NOT EVALUATED.
- `NO_RELATION`, Neutral, evidence insufficiency, and abstention are not conflated.
- The safety banner prohibits medical and other high-stakes use and reports the weak base-verifier accuracy.

## License and Attribution Review

The repository's third-party notice and demo attribution distinguish SciFact claims/annotations (CC BY 4.0), S2ORC abstracts (ODC-By 1.0), upstream SciFact code (Apache-2.0), and the pinned NLI model (Apache-2.0). The raw corpus is downloaded at runtime rather than committed. Repository code licensing does not override dataset or model terms.

## Residual Risks

- A cloud cold start depends on two external hosts and can fail even though the code is correct.
- Disk cache persistence is platform-dependent; eviction causes another checksum-verified download.
- A future dependency compromise is not prevented solely by Python version pins. The repository pins direct packages and the NLI revision but does not ship a fully hashed transitive lockfile.
- Peak CPU memory and concurrency behavior have not been measured on Community Cloud.
- The NLI model's scientific-domain mismatch, truncation, weak E1 accuracy, and limited independent sample remain research limitations, not deployment bugs.
- Streamlit infrastructure privacy and logging are governed by the hosting provider, not by this code.

These residual risks do not justify calling the system reliable, calibrated, or deployment-ready. They should remain visible in any public presentation.
