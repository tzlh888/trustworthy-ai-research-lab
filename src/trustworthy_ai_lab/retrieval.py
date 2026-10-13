from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi


TOKEN_PATTERN = re.compile(r"(?u)\b\w+\b")


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return TOKEN_PATTERN.findall(normalized)


def document_text(document: dict[str, Any]) -> str:
    return document["title"] + " " + " ".join(document["abstract"])


class BM25Retriever:
    def __init__(
        self,
        corpus: list[dict[str, Any]],
        *,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25,
    ) -> None:
        self.corpus = sorted(corpus, key=lambda row: int(row["doc_id"]))
        self.doc_ids = np.array([int(row["doc_id"]) for row in self.corpus], dtype=np.int64)
        tokenized = [tokenize(document_text(row)) for row in self.corpus]
        self.index = BM25Okapi(tokenized, k1=k1, b=b, epsilon=epsilon)
        self.parameters = {"k1": k1, "b": b, "epsilon": epsilon}

    def retrieve(self, claim: str, top_k: int = 20) -> list[dict[str, Any]]:
        if top_k < 1 or top_k > len(self.corpus):
            raise ValueError("Invalid top_k")
        scores = self.index.get_scores(tokenize(claim))
        order = sorted(
            range(len(self.corpus)),
            key=lambda index: (-float(scores[index]), int(self.doc_ids[index])),
        )[:top_k]
        results: list[dict[str, Any]] = []
        for rank, index in enumerate(order, 1):
            document = self.corpus[index]
            results.append(
                {
                    "rank": rank,
                    "doc_id": int(document["doc_id"]),
                    "title": document["title"],
                    "abstract": list(document["abstract"]),
                    "structured": bool(document["structured"]),
                    "bm25_score": float(scores[index]),
                    "source_metadata": {
                        "dataset": "SciFact official corpus",
                        "source_file": "corpus.jsonl",
                        "sentence_count": len(document["abstract"]),
                    },
                }
            )
        return results
