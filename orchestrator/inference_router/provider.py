"""Generative-provider Protocol extension (Phase 5g-i + 5g-ii).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Surface (Phase 5g-i)"
and § "Streaming the Chat Surface (Phase 5g-ii)".

The Phase-4 / 5-Invariant-17 slice defines a ``Provider`` Protocol with
``provider_id``, ``category``, and ``health()`` — enough to satisfy the
open-weights-floor bootstrap without committing to any particular
inference API. Phase 5g-i added the ``generate()`` method so providers
can turn-serve for the non-streaming ``POST /chat`` surface. Phase 5g-ii
adds ``generate_stream()`` so providers can feed the SSE transport at
``POST /chat/stream`` — and, on client disconnect, accept cancellation
that propagates to the upstream HTTP connection (so upstream billing
stops when Xion stops listening).

``generate_stream()`` is optional at the Protocol level: a provider
that does not implement it is still a valid ``GenerativeProvider`` and
the streaming handler falls back to wrapping ``generate()`` as a
single-chunk async iterator via ``stream_generate(provider, ...)`` —
the module-level helper. Existing providers keep working unchanged;
new providers opt in to streaming by adding the method.

Streaming contract. ``generate_stream()`` yields ``str`` chunks for
each token slice, then yields exactly one terminal ``GenerationResult``
whose ``text`` is the empty string and whose ``model_id``, ``usage_in``,
``usage_out``, ``finish_reason``, ``latency_ms`` fields carry the
turn's final metadata. The handler buffers the text chunks itself (for
egress moderation) and reads the terminal for the ``ChatResponse``
metadata — this is cleaner than returning a union with a custom
terminal type because ``GenerationResult`` is already the shared
metadata shape.

This module pulls no third-party dependency. The concrete OpenRouter
and Ollama providers that live alongside it use stdlib ``http.client``
in ``asyncio.to_thread`` for ``generate()``; for ``generate_stream()``
they use ``httpx.AsyncClient`` (pulled in by the ``[api]`` extra) so
an ``asyncio.CancelledError`` on the handler side can propagate to the
upstream HTTP connection and terminate provider-side billing
immediately.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
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


async def stream_generate(
    provider: object,
    prompt: str,
    *,
    system: str | None,
    max_tokens: int,
    deadline_s: float,
) -> AsyncIterator[str | GenerationResult]:
    """Async-iterate a provider's generation output.

    Yields ``str`` chunks for each token slice (zero or more), then
    exactly one terminal ``GenerationResult`` with the turn's final
    metadata (``text`` on the terminal is the empty string by
    convention; the caller buffered the chunks).

    Dispatch rule:
      - If the provider has a coroutine / async-generator method
        ``generate_stream`` with the expected signature, it is called
        and its yield sequence is forwarded verbatim.
      - Otherwise, the helper calls ``generate()`` via
        ``asyncio.to_thread`` (so the event loop is not pinned on a
        sync HTTP call) and yields the full ``result.text`` as ONE
        ``str`` chunk followed by the ``GenerationResult`` terminal
        with ``text=""``. This lets the streaming handler operate
        against providers that have not yet opted into native
        streaming — the UX degrades to "single big chunk" but the
        contract is preserved.

    Cancellation contract. On ``asyncio.CancelledError``, the helper
    cancels the underlying coroutine / task; implementations are
    required to release their HTTP client (``httpx.AsyncClient``)
    promptly so upstream billing terminates. The fallback path does
    not support cancel — ``asyncio.to_thread`` is uninterruptible by
    design — which is why ``KW-CHAT-003`` only closes for providers
    that implement native streaming.
    """
    native = getattr(provider, "generate_stream", None)
    if callable(native):
        async for event in native(
            prompt,
            system=system,
            max_tokens=max_tokens,
            deadline_s=deadline_s,
        ):
            yield event
        return

    # Fallback: wrap the synchronous generate() call. The handler sees
    # exactly one text chunk followed by the GenerationResult terminal.
    result: GenerationResult = await asyncio.to_thread(
        provider.generate,  # type: ignore[attr-defined]
        prompt,
        system=system,
        max_tokens=max_tokens,
        deadline_s=deadline_s,
    )
    if result.text:
        yield result.text
    # Terminal with text="" by convention — the handler already
    # buffered the chunks.
    yield GenerationResult(
        text="",
        model_id=result.model_id,
        usage_in=result.usage_in,
        usage_out=result.usage_out,
        finish_reason=result.finish_reason,
        latency_ms=result.latency_ms,
    )


__all__ = [
    "GenerationResult",
    "GenerativeProvider",
    "stream_generate",
]
