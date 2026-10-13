# Limitations and Non-Deployment Statement

The confirmatory result is **H1 INCONCLUSIVE under the preregistered joint criterion**. H2 and H3 were **Not Evaluated**.

## Statistical limits

Only 88 eligible Internal Test claims and 39 eligible connected groups informed H1. Grouped bootstrap reflects known dependence but cannot compensate for the small sample or unknown topical relationships.

## Dataset limits

The Internal Test is a held-out subset of official SciFact Train, not an external benchmark. Fifty-three test claims lacked annotated evidence and could not support the primary error label. Official SciFact Test has no local ground truth, and no official Test F1 is claimed.

## Verifier limits

The E1 verifier achieved 0.488636 accuracy and made 45 errors among 88 eligible claims. It uses lexical sentence selection and a general-domain sentence-level NLI model, not a state-of-the-art scientific full-document verifier. Risk ranking does not repair these errors.

## Uncertainty limits

EARS and B1 outputs are uncalibrated ranking scores. They are not probabilities of error and have no selected deployment threshold. AURC improved while R80 worsened, so no general EARS superiority claim is justified.

## Semantic limits

NO_RELATION means no non-neutral sentence candidate survived frozen aggregation. It is not a validated evidence-insufficiency label. The system does not detect missing literature or judge study quality.

## Safety boundary

This project is not suitable for medicine, diagnosis, treatment, clinical research decisions, policy decisions, literature-review automation without expert checking, or other high-stakes use. A retrieved abstract and NLI output cannot establish scientific truth.

