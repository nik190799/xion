"""Concrete embedding providers."""

from __future__ import annotations

from .chutes_embedding import ChutesEmbeddingProvider
from .local_bge_m3 import LocalBgeM3EmbeddingProvider

__all__ = ["ChutesEmbeddingProvider", "LocalBgeM3EmbeddingProvider"]
