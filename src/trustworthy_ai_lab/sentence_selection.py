from __future__ import annotations

import collections
import math
from typing import Any

from .retrieval import tokenize


class IDFOverlapSentenceSelector:
    def __init__(self, corpus: list[dict[str, Any]]) -> None:
        self.sentence_count = sum(len(row["abstract"]) for row in corpus)
        document_frequency: collections.Counter[str] = collections.Counter()
        for row in corpus:
            for sentence in row["abstract"]:
                document_frequency.update(set(tokenize(sentence)))
        self.idf = {
            token: math.log((self.sentence_count + 1) / (frequency + 1)) + 1.0
            for token, frequency in document_frequency.items()
        }

    def score(self, claim: str, sentence: str) -> float:
        claim_tokens = set(tokenize(claim))
        sentence_tokens = set(tokenize(sentence))
        if not claim_tokens or not sentence_tokens:
            return 0.0
        numerator = sum(self.idf.get(token, 1.0) for token in claim_tokens & sentence_tokens)
        return numerator / math.sqrt(len(claim_tokens) * len(sentence_tokens))

    def select(
        self, claim: str, document: dict[str, Any], top_n: int = 3
    ) -> list[dict[str, Any]]:
        scored = [
            {
                "sentence_index": index,
                "sentence_text": sentence,
                "selection_score": self.score(claim, sentence),
            }
            for index, sentence in enumerate(document["abstract"])
        ]
        scored.sort(key=lambda row: (-row["selection_score"], row["sentence_index"]))
        selected = scored[: min(top_n, len(scored))]
        for selected_rank, row in enumerate(selected, 1):
            row["selected_rank"] = selected_rank
        return selected
