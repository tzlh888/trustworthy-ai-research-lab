# Trustworthy AI Research Lab — Project Final Closure Report

**Report date:** 2026-10-14

**Final research version:** V2 contribution-integrated publication candidate

**GitHub:** https://github.com/tzlh888/trustworthy-ai-research-lab

**Publication state:** VERIFIED WHEN THIS REPORT IS PRESENT ON `origin/main`

**Final publication commit SHA:** the commit containing this report; its immutable SHA is recorded in GitHub history and the final delivery response (a commit cannot embed its own hash)

## Project and research outcome

The project studies whether an error-risk ranker that combines evidence-pipeline signals with NLI-derived uncertainty can improve selective prediction for scientific claim verification. It is a **solo-human-owner, substantially AI-assisted research project**. AI assistance materially supported method discussion, programming, experiment execution, statistical analysis, technical auditing, figures, and writing. The human owner retains responsibility for public claims, authorship, licensing, and release. No unaided implementation or completed personal technical verification is claimed.

The frozen results are:

| Evaluation | Eligible claims / groups | B1 AURC | EARS AURC | B1 R80 | EARS R80 | Conclusion |
|---|---:|---:|---:|---:|---:|---|
| Historical Internal Test | 88 / 39 | 0.300833 | 0.264987 | 0.428571 | 0.457143 | H1 INCONCLUSIVE |
| SciFact Dev | 188 / 164 | 0.281575 | 0.288355 | 0.413333 | 0.400000 | Both paired intervals cross zero; no stable EARS advantage |

Historical H2 and H3 remain **NOT EVALUATED**. Risk scores are not validated error probabilities. SciFact Dev is same-dataset-family evidence, not independent cross-dataset replication. The project does not establish deployment readiness, clinical validity, or general superiority of EARS over B1.

The frozen V2 protocol SHA-256 is:

`70ae8596df22c22131f895dc888a545b9e3f3512a845f0735977cc46250d2301`

## Final publication artifacts

- Research paper source: `paper/Trustworthy_AI_Research_Lab_V2_Final.md`
- Research paper PDF: `paper/Trustworthy_AI_Research_Lab_V2_Final.pdf`
- One-page summary: `paper/Trustworthy_AI_Research_Lab_V2_One_Page.pdf`
- Research ownership and AI disclosure: `RESEARCH_OWNERSHIP.md`
- Personal contribution statement: `docs/PERSONAL_RESEARCH_CONTRIBUTION.md`
- Contribution paragraph: `portfolio/RESEARCH_CONTRIBUTION_PARAGRAPH.md`
- Corrective research-integrity audit: `reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md`
- Reproducibility verification: `reports/research_upgrade_v2/FINAL_REPRODUCIBILITY_VERIFICATION.md`
- Streamlit entry point: `demo/app.py`

The private `INTERVIEW_REENTRY_GUIDE.md` is intentionally outside the public repository. The unfinished owner-verification worksheet is not part of the public package.

## License and third-party status

The root `LICENSE` is byte-identical to the official Apache License 2.0 text, SHA-256:

`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`

This technical check does not replace the owner's authorization to license original project code. SciFact data, S2ORC abstracts, pretrained models, and dependencies remain under their separate terms as recorded in `THIRD_PARTY_NOTICES.md`.

## Final local acceptance record

The final candidate was independently extracted into a clean temporary directory and checked on 2026-10-14:

- full public suite: **39 passed, 61 skipped, 0 failed**;
- V2-specific suite: **23 passed, 0 failed**;
- Demo regression suite: **3 passed, 0 failed**;
- CPU Streamlit end-to-end smoke test: **PASS** — verified corpus, five traceable papers, 15 NLI pairs, finite B1/EARS scores, and required limitation text;
- ZIP CRC, safe-path, sorted-membership, byte-count, and per-file SHA-256 verification: **PASS**;
- frozen protocol and scientific-result consistency: **PASS**;
- Apache-2.0 byte-for-byte comparison with the official text: **PASS**;
- README/local Markdown link check: **PASS**;
- public safety scan: **228 files scanned, 0 findings**;
- raw/private data, model binaries, caches, credentials, private paths, private chats, and owner worksheet exclusion: **PASS**.

Skipped tests are not counted as passes. Public reproducibility remains **PARTIAL** because intentionally excluded historical private/raw artifacts are required for the complete old workflow.

## Release archive identity

- ZIP: `trustworthy-ai-research-lab-v2-contribution-integrated.zip`
- ZIP files: 228
- ZIP SHA-256: `64ccfe1eff943159b0654b437d19c9c0e87b80c504d3a3cb991ff1d09e5ff05f`
- Sidecar manifest SHA-256: `3a83a23e19b85e8629729f34b5540ca571517fcad162f328ec354c998ae095c2`

The public working tree matches every file, byte count, and SHA-256 entry in that manifest. This closure report is a post-candidate administrative record and is not represented as one of the 228 archive members.

## GitHub publication verification

The GitHub repository exists publicly and uses `main`. Before V2 publication, local `HEAD` and `origin/main` were both `e5d6c56b0b5b4723bf5cd3aa08625e2bce381aab`. Before owner authorization, the V2 files were prepared and audited locally without staging, committing, or pushing them.

On 2026-10-14, the owner explicitly confirmed the public identity and contribution/AI-assistance disclosure, authorized Apache-2.0 publication of owner-controlled original code subject to third-party terms, and authorized commit and push of the audited V2 files to `main`. The release workflow stages only the audited file list, inspects the staged diff, reruns safety checks, commits, pushes without bypassing repository policy, and verifies the remote commit. The immutable commit SHA is necessarily recorded outside the commit that it identifies: in GitHub history and the final delivery response.

No GitHub Release, tag, or new deployment was authorized or created.

No public Streamlit application URL is recorded in the repository. The source entry point is ready, but online deployment must not be reported as verified until a real remote URL completes an end-to-end claim run.

## Remaining release blocker

There is no remaining authorization blocker for the GitHub repository publication. The owner confirmed that:

1. `Zeluohe Tang` is the approved public author identity and the contribution/AI-assistance disclosure is accurate;
2. the owner has authority to license the original code under Apache-2.0 while preserving third-party terms; and
3. the owner authorizes commit and push of the audited final file set.

No further research, model training, personal testing, or document optimization is required. The absence of an independently deployed Streamlit URL remains an operational limitation, not a repository-publication blocker.

## Final closure status

`RESEARCH COMPLETE: YES`

`SCIENTIFIC INTEGRITY: PASS`

`AI DISCLOSURE: PASS`

`LICENSE TEXT INTEGRITY: PASS`

`LICENSE AUTHORIZATION: CONFIRMED BY OWNER`

`FINAL TESTS: 39 PASSED / 61 SKIPPED / 0 FAILED; V2 23 PASSED; DEMO 3 PASSED`

`GITHUB PUBLICATION: VERIFIED WHEN THIS REPORT IS PRESENT ON ORIGIN/MAIN`

`PROJECT STATUS: COMPLETE`

`RESEARCH DEVELOPMENT: FROZEN`

`SCIENTIFIC RESULTS: FROZEN`

`DOCUMENTATION: FINAL`

`PUBLICATION: VERIFIED`

`FUTURE RESEARCH UPGRADES: NOT PLANNED`

`INTERVIEW PREPARATION: DEFERRED`

`FURTHER SCIENTIFIC MODIFICATION REQUIRED: NO`
