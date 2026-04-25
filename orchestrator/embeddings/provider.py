"""Embedding provider substrate for Phase 6.9 retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class EmbeddingBatch:
    model_id: str
    vectors: list[list[float]]
    provider_fingerprint: str


@runtime_checkable
class EmbeddingProvider(Protocol):
    provider_id: str
    model_id: str

    def health(self) -> bool: ...

    def embed(self, texts: list[str]) -> EmbeddingBatch: ...


def l2_normalize(vector: list[float]) -> list[float]:
    norm = sum(v * v for v in vector) ** 0.5
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


__all__ = ["EmbeddingBatch", "EmbeddingProvider", "l2_normalize"]
