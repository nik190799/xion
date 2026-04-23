"""Concrete ``GenerativeProvider`` implementations (Phase 5g-i.1).

Doctrine anchor: ``docs/26-INFERENCE-POLICY.md``.

Two providers ship in Phase 5g-i.1:

- ``OpenRouterGenerativeProvider`` — hosted-API gateway (OpenRouter's
  OpenAI-compatible ``/v1/chat/completions``), ``category="hosted_api"``.
  Registered only when ``XION_OPENROUTER_API_KEY`` is set in the
  environment. The Genesis Default upstream model slug served through
  the gateway is ``moonshotai/kimi-k2``; operators rotate via
  ``XION_OPENROUTER_MODEL`` with no code change.

- ``OllamaGenerativeProvider`` — self-hosted open-weights floor via a
  local Ollama daemon, ``category="open_weights_self_hostable"``.
  Registered unconditionally; ``health()`` reflects whether the daemon
  is reachable and whether the floor model is pulled locally.

Both implementations are stdlib-only (``http.client`` + ``json``) and
are designed to run inside ``asyncio.to_thread`` from the Chat handler.
"""

from __future__ import annotations

from orchestrator.inference_router.providers.ollama import OllamaGenerativeProvider
from orchestrator.inference_router.providers.openrouter import (
    OpenRouterGenerativeProvider,
)

__all__ = [
    "OllamaGenerativeProvider",
    "OpenRouterGenerativeProvider",
]
