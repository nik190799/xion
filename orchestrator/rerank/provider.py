"""Reranking provider substrate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RerankCandidate:
    text: str
    score: float = 0.0
    record_id: str | None = None


@dataclass(frozen=True)
class RerankResult:
    text: str
    score: float
    record_id: str | None = None


@runtime_checkable
class Reranker(Protocol):
    provider_id: str
    model_id: str

    def health(self) -> bool: ...

    def rerank(self, query: str, candidates: list[RerankCandidate], *, top_k: int) -> list[RerankResult]: ...


class IdentityReranker:
    provider_id = "identity-reranker"
    model_id = "identity"

    def health(self) -> bool:
        return True

    def rerank(self, query: str, candidates: list[RerankCandidate], *, top_k: int) -> list[RerankResult]:
        ordered = sorted(candidates, key=lambda c: c.score, reverse=True)
        return [RerankResult(text=c.text, score=c.score, record_id=c.record_id) for c in ordered[:top_k]]


__all__ = ["IdentityReranker", "RerankCandidate", "RerankResult", "Reranker"]
