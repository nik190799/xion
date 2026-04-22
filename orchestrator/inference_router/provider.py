"""Generative-provider Protocol extension (Phase 5g-i).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Surface (Phase 5g-i)".

The Phase-4 / 5-Invariant-17 slice defines a ``Provider`` Protocol with
``provider_id``, ``category``, and ``health()`` — enough to satisfy the
open-weights-floor bootstrap without committing to any particular
inference API. Phase 5g-i needs one more capability: the provider must
be able to actually *generate* text when the Chat Surface calls on it.

``GenerativeProvider`` is the Protocol for those providers. It extends
``Provider`` (so every GenerativeProvider is still a Provider for
floor-bootstrap purposes) and adds a single ``generate`` method that
returns a ``GenerationResult``. Everything else — streaming, tool use,
vision, function calling — is deliberately out of scope; the Protocol
is kept narrow so a new provider takes ~150 lines of stdlib HTTP to
implement.

This module pulls no third-party dependency. The concrete Kimi and
Ollama providers that live alongside it use stdlib ``http.client`` in
``asyncio.to_thread``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from orchestrator.inference_router.router import Category


@dataclass(frozen=True)
class GenerationResult:
    """The return value of ``GenerativeProvider.generate(...)``.

    Deliberately coarse: what the Chat Surface needs to surface a turn
    and log it, nothing more. A future streaming provider returns one
    ``GenerationResult`` per final chunk; the intermediate deltas live
    outside this type.

    Fields:
      text: The generated candidate, to be fed *into* the egress
        ``Relay.evaluate()`` call. May be empty (the model refused, the
        model returned stop-immediately, etc.); the Chat handler treats
        empty text as egress-refused by convention.
      model_id: The provider's self-reported model id (echoed in the
        ``ChatResponse`` so the caller can tell which model spoke).
        Not trusted for auditability — the auditable record is the
        SAFETY_LEDGER row plus the provider manifest.
      usage_in: Input tokens charged by the provider (0 for providers
        that do not report usage, e.g., stubs).
      usage_out: Output tokens produced.
      finish_reason: Provider-reported finish reason (``"stop"``,
        ``"length"``, ``"error"``, provider-specific strings). Opaque
        to the Chat Surface; logged verbatim for diagnostics.
      latency_ms: Wall-clock latency of the generate call, measured
        by the provider from just-before-request to just-after-response
        on a monotonic clock. The Chat Surface reports this in its
        response so a caller can bound their own timeouts.
    """

    text: str
    model_id: str
    usage_in: int
    usage_out: int
    finish_reason: str
    latency_ms: int


@runtime_checkable
class GenerativeProvider(Protocol):
    """A registered inference provider capable of turn-serving generation.

    Implements the base ``Provider`` Protocol (``provider_id``,
    ``category``, ``health()``) plus a ``generate`` method.

    Implementations MUST:
      - Be side-effect-free except for the outbound HTTP call.
      - Not retain the prompt, the response, or the API key in any
        process-local cache, file, or log after ``generate`` returns.
      - Strip ``Authorization`` headers and other credential-bearing
        values from any error message that might be logged.

    Implementations SHOULD:
      - Use stdlib ``http.client`` in ``asyncio.to_thread`` — no new
        runtime dependency under the ``[api]`` extra.
      - Surface transient failures as raised exceptions the Chat
        handler catches and maps to ``503 ProviderErrorEnvelope``.
    """

    provider_id: str
    category: Category

    def health(self) -> bool: ...

    def generate(
        self,
        prompt: str,
        *,
        system: str | None,
        max_tokens: int,
        deadline_s: float,
    ) -> GenerationResult: ...


__all__ = [
    "GenerationResult",
    "GenerativeProvider",
]
