from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer


EXPECTED_ID2LABEL = {0: "contradiction", 1: "entailment", 2: "neutral"}


@dataclass
class NLIRunStats:
    device: str
    batch_size: int
    pair_count: int
    elapsed_seconds: float
    pairs_per_second: float
    truncated_count: int


class NLIEngine:
    def __init__(
        self,
        model_id: str,
        revision: str,
        device: str,
        max_length: int = 512,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.device = torch.device(device)
        self.max_length = max_length
        config = AutoConfig.from_pretrained(model_id, revision=revision)
        actual = {int(key): value.lower() for key, value in config.id2label.items()}
        if actual != EXPECTED_ID2LABEL:
            raise ValueError(f"Unexpected NLI label mapping: {actual}")
        self.id2label = actual
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_id, revision=revision
        )
        self.model.eval()
        self.model.to(self.device)

    def move_to(self, device: str) -> None:
        self.device = torch.device(device)
        self.model.to(self.device)

    def _token_length(self, premise: str, hypothesis: str) -> int:
        encoded = self.tokenizer(
            premise,
            hypothesis,
            add_special_tokens=True,
            truncation=False,
            padding=False,
        )
        return len(encoded["input_ids"])

    def predict(
        self, pairs: list[dict[str, Any]], batch_size: int
    ) -> tuple[list[dict[str, Any]], NLIRunStats]:
        results: list[dict[str, Any]] = []
        if self.device.type == "mps":
            torch.mps.synchronize()
        started = time.perf_counter()
        for offset in range(0, len(pairs), batch_size):
            batch = pairs[offset : offset + batch_size]
            premises = [row["premise"] for row in batch]
            hypotheses = [row["hypothesis"] for row in batch]
            original_lengths = [
                self._token_length(premise, hypothesis)
                for premise, hypothesis in zip(premises, hypotheses)
            ]
            encoded = self.tokenizer(
                premises,
                hypotheses,
                padding=True,
                truncation="longest_first",
                max_length=self.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with torch.inference_mode():
                logits = self.model(**encoded).logits
                probabilities = torch.softmax(logits, dim=-1).detach().cpu()
            for row, length, probability in zip(batch, original_lengths, probabilities):
                predicted_id = int(torch.argmax(probability).item())
                result = dict(row)
                result.update(
                    {
                        "token_length_before_truncation": length,
                        "truncated": length > self.max_length,
                        "probabilities": {
                            "contradiction": float(probability[0]),
                            "entailment": float(probability[1]),
                            "neutral": float(probability[2]),
                        },
                        "predicted_nli_label": self.id2label[predicted_id],
                        "model_id": self.model_id,
                        "model_revision": self.revision,
                        "input_order": "premise=evidence; hypothesis=claim",
                    }
                )
                results.append(result)
        if self.device.type == "mps":
            torch.mps.synchronize()
        elapsed = time.perf_counter() - started
        truncated = sum(row["truncated"] for row in results)
        stats = NLIRunStats(
            device=str(self.device),
            batch_size=batch_size,
            pair_count=len(pairs),
            elapsed_seconds=elapsed,
            pairs_per_second=(len(pairs) / elapsed if elapsed else 0.0),
            truncated_count=truncated,
        )
        return results, stats
