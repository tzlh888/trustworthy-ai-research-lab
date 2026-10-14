# Personal Research Contribution

**Status:** Public contribution statement drafted from repository evidence and owner-provided disclosures; final first-person authorship and release approval remain pending human owner confirmation.

## Research Context

Scientific claim-verification systems can be confidently wrong because failure can occur before or inside natural-language inference: the wrong paper may be retrieved, a decisive sentence may be missed, or conflicting evidence may be aggregated incorrectly. This project studies whether an error-risk model can rank those failures for selective review. The scientific contribution is a bounded test of that question, including leakage controls, mixed and negative results, failure analysis, and explicit limits on generalization.

## My Role as Human Project Owner

I supplied the overarching research objective and integrity requirements for this solo-human-owner, substantially AI-assisted project. I required critical review, preservation of frozen results, disclosure of adverse endpoints, and correction of provenance, label-isolation, statistical-language, licensing, and release-quality problems. I retain responsibility for deciding whether the public claims, authorship, contribution description, license, and release are accurate.

This role is research direction and accountability. I do not claim that I independently invented every method, wrote every line of code, ran every command, or derived every statistic without assistance. Specific technical understanding should be treated as owner-verified only after I personally complete and retain the corresponding verification record.

## Research Findings I Am Responsible for Reporting

I am responsible for presenting the project's evidence without selecting only favorable results:

- On the historical Internal Test, EARS improved AURC from 0.300833 to 0.264987 relative to B1, but worsened R80 from 0.428571 to 0.457143.
- The frozen joint conclusion remains **H1 INCONCLUSIVE**; historical H2 and H3 remain **NOT EVALUATED**.
- On official SciFact Dev, B1 achieved AURC 0.281575 and R80 0.413333, while EARS achieved AURC 0.288355 and R80 0.400000. The endpoint directions reversed relative to the historical result, and both paired confidence intervals crossed zero.
- The evidence does not establish a stable incremental EARS benefit, calibrated error probabilities, deployment readiness, or compatible cross-dataset replication.
- SciFact Dev is a different official split from the same dataset family, not proof of external generalization.

These are findings produced by the project. Reporting responsibility does not by itself prove that I personally performed every calculation or independently designed every analysis.

## AI Assistance and Attribution

AI-assisted systems contributed substantially to literature and method discussions, protocol drafting, implementation and debugging, experiment orchestration and execution, statistical analysis, reproducibility and leakage checks, failure analysis, documentation, figures, PDFs, portfolio drafts, licensing review, and demo development.

AI assistance is not listed as an author or owner, but its technical contribution is material and must remain disclosed. The project is not represented as unaided human implementation.

## Personal Research Evidence Map

| Contribution claim | Evidence | Classification | Public wording boundary |
|---|---|---|---|
| The human owner supplied the research objective and integrity constraints. | `RESEARCH_OWNERSHIP.md`; owner-provided contribution statement | Owner-declared responsibility | May be stated as the owner's role; not third-party identity certification. |
| Critical reviews and corrections were required, including retention of unfavorable results. | `reports/research_upgrade_v2/FINAL_CORRECTION_AUDIT.md`; current release instructions | Documented current owner action plus repository correction record | May describe the owner's integrity requirement; not proof of unaided historical technical design. |
| Historical and Dev findings are reported accurately. | Frozen reports, result CSVs, paper, protocol hash, independent audits | Research finding | May be reported as project results; not as unaided personal derivation. |
| Code, experiments, statistics, and documentation were completed with substantial AI assistance. | `RESEARCH_OWNERSHIP.md`; decision log; correction and reproducibility audits | AI-assisted work | Must retain explicit AI attribution. |
| The owner independently invented EARS or personally coded and ran every component. | No sufficient record | Not independently verified | Must not be claimed. |
| The owner currently understands a specific metric, feature, bootstrap, or failure mechanism. | Dated owner-completed verification record, if later produced | Present-day verification | Remains `NOT VERIFIED` until personally completed; cannot prove historical unaided authorship. |

## Limits of Attribution

This project does not claim that:

- every technical idea was independently originated by the human owner;
- all code was independently written by the human owner;
- all experiments or statistical checks were executed unaided;
- the work was externally peer reviewed, published, or endorsed by a professor or institution;
- EARS is a proven superior algorithm or has demonstrated cross-dataset generalization;
- the owner has personally verified every technical detail merely because this document exists.

The contribution is best understood as human research direction and accountability combined with substantial AI-assisted technical execution, transparent correction, and careful reporting of an inconclusive result.
