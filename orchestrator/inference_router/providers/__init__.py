"""Concrete ``GenerativeProvider`` implementations (Phase 5g-i.1).

Doctrine anchor: ``docs/26-INFERENCE-POLICY.md``.

Two providers ship after the centralized-provider purge:

- ``ChutesGenerativeProvider`` — hosted-API gateway on Bittensor Subnet 64
  (Chutes' OAI-compatible ``/v1/chat/completions``), ``category="hosted_api"``.
  Registered when ``XION_CHUTES_API_KEY`` is set. The Phase 6.9 Genesis
  Default hosted model is ``moonshotai/Kimi-K2.6-TEE``.

- ``OllamaGenerativeProvider`` — self-hosted open-weights floor via a
  local Ollama daemon, ``category="open_weights_self_hostable"``.
  Registered unconditionally; ``health()`` reflects whether the daemon
  is reachable and whether the floor model is pulled locally.

Both implementations keep runtime dependencies narrow and
are designed to run inside ``asyncio.to_thread`` from the Chat handler.
"""

from __future__ import annotations

from orchestrator.inference_router.providers.chutes import ChutesGenerativeProvider
from orchestrator.inference_router.providers.ollama import OllamaGenerativeProvider

__all__ = [
    "ChutesGenerativeProvider",
    "OllamaGenerativeProvider",
]
