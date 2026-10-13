# Third-Party Notices

This release candidate contains original project code and documentation but does not redistribute raw datasets, model weights, or caches.

## SciFact

- Official source: https://github.com/allenai/scifact
- Claims and evidence annotations: CC BY 4.0.
- Corpus abstracts: S2ORC material under ODC-By 1.0.
- Official SciFact code: Apache-2.0.

Users must preserve the official attribution and license terms when downloading or using these materials.

## NLI model

- Model ID: `cross-encoder/nli-distilroberta-base`
- Frozen revision: `b14d131f9d32668a5e6a982729b57ff6ed5dfcbd`
- Source: https://huggingface.co/cross-encoder/nli-distilroberta-base

Model files are downloaded independently by Transformers and are not included. Verify the model card and license at the pinned revision before public deployment or redistribution.

## Python dependencies

The project depends on PyTorch, Transformers, sentence-transformers, scikit-learn, NumPy, SciPy, pandas, rank-bm25, Matplotlib, Streamlit, ReportLab, pdfplumber, pypdf, and their transitive dependencies. Each remains under its own license. The local Apache-2.0 candidate license does not relicense third-party components or data.

