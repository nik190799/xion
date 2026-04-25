"""Embedding substrate exports."""

from __future__ import annotations

from .provider import EmbeddingBatch, EmbeddingProvider, l2_normalize
from .providers import ChutesEmbeddingProvider, LocalBgeM3EmbeddingProvider

__all__ = [
    "ChutesEmbeddingProvider",
    "EmbeddingBatch",
    "EmbeddingProvider",
    "LocalBgeM3EmbeddingProvider",
    "l2_normalize",
]
