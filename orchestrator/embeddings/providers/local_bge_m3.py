"""Local BGE-M3 embedding adapter.

The default implementation is deterministic and dependency-free so the
retrieval substrate is testable without a model daemon. Operators can swap this
provider for a real local BGE-M3 runtime behind the same Protocol.
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field

from orchestrator.embeddings.provider import EmbeddingBatch, l2_normalize


_DEFAULT_MODEL = "BAAI/bge-m3"


@dataclass
class LocalBgeM3EmbeddingProvider:
    provider_id: str = "local-bge-m3"
    model_id: str = field(default_factory=lambda: os.environ.get("XION_LOCAL_EMBED_MODEL", _DEFAULT_MODEL))
    dimensions: int = field(default_factory=lambda: int(os.environ.get("XION_EMBED_DIMENSIONS", "384")))

    def health(self) -> bool:
        return self.dimensions > 0

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        return EmbeddingBatch(
            model_id=self.model_id,
            vectors=[self._embed_one(text) for text in texts],
            provider_fingerprint=f"{self.provider_id}:{self.model_id}:deterministic-local",
        )

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        tokens = [tok for tok in text.lower().split() if tok]
        if not tokens:
            return vec
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = -1.0 if digest[4] & 1 else 1.0
            vec[idx] += sign * (1.0 + math.log1p(len(token)))
        return l2_normalize(vec)


__all__ = ["LocalBgeM3EmbeddingProvider"]
