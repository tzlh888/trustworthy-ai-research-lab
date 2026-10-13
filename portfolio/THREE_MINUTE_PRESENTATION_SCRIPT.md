# Three-Minute English Research Presentation Script

Hello. My project asks a simple trustworthy-AI question: when a scientific claim verifier is likely to be wrong, can the system recognize that risk before its answer is used?

I studied this with SciFact, a dataset of scientific claims linked to supporting or contradicting evidence. My base pipeline first retrieves abstracts with BM25, selects evidence sentences without using gold labels, and applies a pinned natural-language-inference model. This pipeline is intentionally lightweight, but it can fail at retrieval, sentence selection, reasoning, or aggregation.

The standard selective-prediction baseline accepts examples with high model confidence. I compared that idea with Evidence-Aware Risk Scoring, or EARS. EARS is not a new neural architecture. It is a small logistic-regression error model using frozen inference-time features: decision confidence, the support-versus-contradiction margin, predicted category, BM25 score separation, and evidence conflict.

The main methodological challenge was preventing leakage. I divided SciFact Train into fit, calibration, and Internal Test partitions using connected cited-document groups. I trained the final risk models only on 329 eligible fit claims. I froze model hashes, then generated and hashed all 141 test predictions before opening the test labels. Eighty-eight test claims had authentic SUPPORT or CONTRADICT labels and entered the primary evaluation.

The result was mixed. The base verifier itself was weak, with 48.9 percent accuracy. EARS improved area under the risk-coverage curve from 0.3008 to 0.2650 compared with the matched NLI-only risk model. The paired 95 percent interval for that improvement excluded zero. But at the preregistered 80 percent coverage point, EARS was worse: it accepted 32 errors, while the NLI-only model accepted 30.

My protocol required both metrics to improve, so the final conclusion was H1 inconclusive. I did not hide the unfavorable endpoint or retrain after seeing it.

The most important lesson is that uncertainty results depend on the exact question. Better average ranking does not guarantee a better operating point. A high softmax score is not proof that a scientific claim is true, and an EARS score is not a calibrated error probability. The small test set, weak verifier, and lack of external data also prevent deployment claims.

I view the project's main contribution as methodological: a reproducible evaluation that makes leakage controls, negative results, and limitations first-class research outputs.

