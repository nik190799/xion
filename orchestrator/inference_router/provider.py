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


# --------------------------------------------------------------------------
# Typed provider exceptions (Phase 5g-vii).
#
# Doctrine anchor: ``docs/26-INFERENCE-POLICY.md`` § "Provider fallback
# semantics (Phase 5g-vii)" property P5 (failure-reason classes are typed
# and frozen).
#
# Design:
#   * ``ProviderError`` is the shared base for every provider-side
#     generate()/generate_stream() failure. It extends ``RuntimeError`` so
#     existing catchers written against ``RuntimeError`` or ``Exception``
#     continue to work. A ``provider_id`` attribute identifies the origin
#     (``"openrouter"``, ``"ollama"``, etc.) so the chat handler can log
#     + ledger without importing each provider's scoped class.
#   * Six typed subclasses pin the six failure classes enumerated in
#     docs/26. Each carries a ``failure_reason_class`` class attribute
#     whose string value is the exact token the ``REQUEST_LEDGER`` v2
#     row writes. Adding a subclass requires a doctrine amendment — the
#     full enumerated set is frozen and any drift between this module
#     and docs/26's P5 table is a verifier failure (closure bar on
#     KW-INFER-003).
#   * Existing provider-scoped classes (``OpenRouterProviderError``,
#     ``OllamaProviderError``) are retrofitted to subclass
#     ``ProviderError`` in their own modules. Existing ``except
#     OpenRouterProviderError:`` catchers — all at construction-time in
#     lifespan.py — keep working because construction-time raises still
#     use those classes directly. Generate-site raises use the typed
#     subclasses below.
# --------------------------------------------------------------------------


class ProviderError(RuntimeError):
    """Base class for generative-provider failures (Phase 5g-vii).

    Carries a ``provider_id`` so a catcher that does not know which
    provider it imports can still log the origin. The
    ``failure_reason_class`` class attribute names the value that
    ``REQUEST_LEDGER`` v2 rows record for attempts raising this class
    (or a subclass thereof).

    The default ``failure_reason_class`` is ``"unknown_provider_error"``
    — the P5-enumerated residual bucket. Typed subclasses override it.
    """

    failure_reason_class: str = "unknown_provider_error"

    def __init__(self, message: str, *, provider_id: str | None = None) -> None:
        super().__init__(message)
        self.provider_id = provider_id


class InsufficientCreditsError(ProviderError):
    """Upstream refused the request for billing reasons.

    Typical triggers: OpenRouter ``HTTP 402 Insufficient credits`` when
    the operator's balance is exhausted; upstream-vendor-specific 402s
    forwarded through the gateway. Never triggered by the floor
    provider (Ollama does not bill).
    """

    failure_reason_class = "insufficient_credits"


class RateLimitedUpstreamError(ProviderError):
    """Upstream accepted the credential but refused on rate limit.

    Distinct from the orchestrator's own per-principal rate-limit
    (``429`` from ``admission_dependency``) — that's handled at the
    FastAPI layer and never reaches a provider. This class is raised
    only when the **provider-side** quota is exceeded.
    """

    failure_reason_class = "rate_limited_upstream"


class ProviderUnreachableError(ProviderError):
    """Network surface could not be reached.

    Triggers: DNS failures, connection refused, TLS handshake failure,
    HTTP 502/503/504 gateway-class errors. For bounded-timeout failures
    (the socket read did not return in time) prefer
    ``ProviderTimeoutError`` which is more specific.
    """

    failure_reason_class = "provider_unreachable"


class ProviderTimeoutError(ProviderError):
    """Provider did not respond within the per-attempt deadline.

    Per-attempt, not per-turn — the chat handler's fallback loop may
    give the floor a fresh deadline after a hosted-provider timeout.
    """

    failure_reason_class = "timeout"


class ModerationRefusalError(ProviderError):
    """Upstream's own content filter refused the request.

    Distinct from Xion's Arbiter, which evaluates a returned candidate
    inside the orchestrator. This class is raised when the *upstream*
    (OpenRouter's gateway, a hosted partner's guardrail, Ollama's
    local safety layer) refuses to generate before any candidate
    exists. Typical trigger: HTTP 403 with a moderation reason code.
    """

    failure_reason_class = "moderation_refusal"


class UnknownProviderError(ProviderError):
    """Residual bucket for failures outside the typed classes.

    Examples: HTTP 400 on a slug rotation mid-flight, HTTP 200 with a
    body that cannot be parsed, library-level exceptions that escape
    the provider module's own error-wrapping.

    Operators discovering recurring failures that land here are
    signalled to open a KW and extend the typed enumeration (doctrine
    amendment to docs/26 § "Provider fallback semantics" P5).
    """

    failure_reason_class = "unknown_provider_error"


# --------------------------------------------------------------------------
# Structural invariant: doctrine ↔ code coupling.
#
# The set of ``failure_reason_class`` values below MUST equal the P5
# enumeration in docs/26-INFERENCE-POLICY.md. The ``xion-verify
# refund-fidelity`` extension (C5) reads this tuple at import time and
# asserts equality with its own parse of docs/26. Drift is a verifier
# failure — silent addition/removal of a class is blocked.
# --------------------------------------------------------------------------
FAILURE_REASON_CLASSES: tuple[str, ...] = (
    "insufficient_credits",
    "rate_limited_upstream",
    "provider_unreachable",
    "timeout",
    "moderation_refusal",
    "unknown_provider_error",
)


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
    "FAILURE_REASON_CLASSES",
    "GenerationResult",
    "GenerativeProvider",
    "InsufficientCreditsError",
    "ModerationRefusalError",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderUnreachableError",
    "RateLimitedUpstreamError",
    "UnknownProviderError",
    "stream_generate",
]
