"""Concrete ``GenerativeProvider`` implementations (Phase 5g-i).

Doctrine anchor: ``docs/26-INFERENCE-POLICY.md``.

Two providers ship in Phase 5g-i:

- ``KimiGenerativeProvider`` — hosted-API (Moonshot's OpenAI-compatible
  ``/v1/chat/completions``), ``category="hosted_api"``. Registered only
  when ``XION_KIMI_API_KEY`` is set in the environment.

- ``OllamaGenerativeProvider`` — self-hosted open-weights floor via a
  local Ollama daemon, ``category="open_weights_self_hostable"``.
  Registered unconditionally; ``health()`` reflects whether the daemon
  is reachable and whether the floor model is pulled locally.

Both implementations are stdlib-only (``http.client`` + ``json``) and
are designed to run inside ``asyncio.to_thread`` from the Chat handler.
"""

from __future__ import annotations

from orchestrator.inference_router.providers.kimi import KimiGenerativeProvider
from orchestrator.inference_router.providers.ollama import OllamaGenerativeProvider

__all__ = [
    "KimiGenerativeProvider",
    "OllamaGenerativeProvider",
]
