"""Chutes Qwen3 embedding provider."""

from __future__ import annotations

import http.client
import json
import os
from dataclasses import dataclass, field
from urllib.parse import urlparse

from orchestrator.embeddings.provider import EmbeddingBatch, l2_normalize
from orchestrator.inference_router.providers.chutes import ChutesProviderError

_DEFAULT_BASE_URL = "https://llm.chutes.ai/v1"
_DEFAULT_MODEL = "Qwen/Qwen3-Embedding-8B"


@dataclass
class ChutesEmbeddingProvider:
    provider_id: str = "chutes-embedding"
    model_id: str = field(default_factory=lambda: os.environ.get("XION_CHUTES_EMBED_MODEL", _DEFAULT_MODEL))
    base_url: str = field(default_factory=lambda: os.environ.get("XION_CHUTES_BASE_URL", _DEFAULT_BASE_URL))
    _api_key: str = field(default_factory=lambda: os.environ.get("XION_CHUTES_API_KEY", ""), repr=False)

    def __post_init__(self) -> None:
        if not self._api_key:
            raise ChutesProviderError("ChutesEmbeddingProvider requires XION_CHUTES_API_KEY")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ChutesProviderError(f"ChutesEmbeddingProvider base_url is invalid: {self.base_url!r}")

    def health(self) -> bool:
        return bool(self._api_key and self.model_id)

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        parsed = urlparse(self.base_url)
        body = json.dumps({"model": self.model_id, "input": texts}).encode("utf-8")
        conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(parsed.netloc, timeout=30)
        try:
            conn.request(
                "POST",
                f"{parsed.path.rstrip('/')}/embeddings" if parsed.path else "/embeddings",
                body=body,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "xion-os/0.4.0 (+phase-6.9)",
                },
            )
            resp = conn.getresponse()
            raw = resp.read()
        finally:
            conn.close()
        if not (200 <= resp.status < 300):
            raise ChutesProviderError(f"chutes embeddings HTTP {resp.status}: {raw[:256].decode('utf-8', errors='replace')}")
        payload = json.loads(raw.decode("utf-8"))
        data = payload.get("data") or []
        vectors = [l2_normalize([float(v) for v in item.get("embedding", [])]) for item in data]
        if len(vectors) != len(texts):
            raise ChutesProviderError("chutes embeddings response length mismatch")
        return EmbeddingBatch(
            model_id=str(payload.get("model") or self.model_id),
            vectors=vectors,
            provider_fingerprint=f"chutes-sn64:{self.model_id}:embedding",
        )


__all__ = ["ChutesEmbeddingProvider"]
