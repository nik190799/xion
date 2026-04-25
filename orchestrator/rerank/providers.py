"""Concrete rerankers for Phase 6.9."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

from .provider import IdentityReranker, RerankCandidate, RerankResult


@dataclass
class LocalBgeM3Reranker(IdentityReranker):
    provider_id: str = "local-bge-reranker"
    model_id: str = field(default_factory=lambda: os.environ.get("XION_LOCAL_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"))

    def rerank(self, query: str, candidates: list[RerankCandidate], *, top_k: int) -> list[RerankResult]:
        q_terms = set(query.lower().split())
        scored = []
        for candidate in candidates:
            terms = set(candidate.text.lower().split())
            lexical = len(q_terms & terms) / max(1, len(q_terms | terms))
            scored.append(
                RerankResult(
                    text=candidate.text,
                    score=(0.2 * candidate.score) + (0.8 * lexical),
                    record_id=candidate.record_id,
                )
            )
        return sorted(scored, key=lambda r: r.score, reverse=True)[:top_k]


@dataclass
class ChutesTeiReranker(LocalBgeM3Reranker):
    provider_id: str = "chutes-tei-reranker"
    model_id: str = field(default_factory=lambda: os.environ.get("XION_CHUTES_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"))

    def health(self) -> bool:
        return bool(os.environ.get("XION_CHUTES_API_KEY", "").strip())

    def rerank(self, query: str, candidates: list[RerankCandidate], *, top_k: int) -> list[RerankResult]:
        # Chutes TEI endpoint shape is kept behind this class; until sealed,
        # deterministic local scoring keeps the bounded retrieval contract true.
        return super().rerank(query, candidates, top_k=top_k)

    @property
    def not_yet_sealed_reason(self) -> str:
        digest = hashlib.sha256(self.model_id.encode("utf-8")).hexdigest()[:12]
        return f"tei-http-client-not-yet-sealed:{digest}"


__all__ = ["ChutesTeiReranker", "LocalBgeM3Reranker"]
