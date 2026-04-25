"""``POST /chat/stream`` handler (Phase 5g-ii).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "Streaming the Chat
Surface (Phase 5g-ii)" and ``docs/32-CHAT-STREAMING.md``.

Sibling transport to ``orchestrator/api/chat.py``. Reuses the same
admission gate (Phase 5g-iv bearer + rate-limit), the same x402
commitment gate (Phase 5g-iii), and the same ingress/egress Arbiter
calls as the non-streaming endpoint — the ONLY thing that changes is
the wire format: tokens stream live to the client via Server-Sent
Events while the server buffers the complete candidate server-side,
then runs egress moderation on the full buffer at generation complete.

Constitutional properties (seven, pinned in architecture.md):

  P1. SSE at POST /chat/stream; text/event-stream Content-Type.
  P2. POST /chat stays non-streaming (this module does not touch it).
  P3. Chunks are client-side provisional until done:approve.
  P4. Egress moderation runs on the buffered complete candidate.
  P5. done:refuse retroactively replaces chunks with a RefusalEnvelope.
  P6. Client disconnect propagates to provider as real cancel (Commit 3).
  P7. Ledger rows are written after moderation, never speculatively.

    Phase 5g-ii Commit 2 lands P1–P5 and P7. Commit 3 adds P6:
    ``request.is_disconnected()`` is polled between chunks; when the
    client disconnects, the provider's async generator is closed
    (which propagates ``asyncio.CancelledError`` into its ``httpx``
    request and terminates upstream billing), and a single PAYMENT
    row with ``outcome=cancelled``, ``refund_XION==committed_XION``,
    ``refusal_stage=None`` is written. No ``done`` event is emitted
    on the wire — by doctrine the client is gone; the ``cancelled``
    enum value in ``StreamDoneEvent`` exists only for operator-side
    replay tooling (and is asserted never to reach the wire by the
    Commit 5 fidelity verifier).

Admission and x402 failures are HTTP-level (401/402/429): the client
never sees an SSE stream open in those cases, matching the non-
streaming endpoint's matrix. Ingress refusal, egress refusal,
no-floor, and provider-error are reported INSIDE the stream as a
single ``done`` event with the matching verdict — by that point the
SSE headers are already committed and the only honest reporting
channel is an event.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import sys
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse

from orchestrator.billing import (
    Commitment,
    append_payment_row,
)
from orchestrator.inference_router.provider import (
    GenerationResult,
    stream_generate,
)

from .chat import _gate_commitment, _principle_to_int, _voice_sensorium_state
from .models import (
    MIN_MAX_TOKENS,
    ChatRequest,
    ChatResponse,
    NoFloorEnvelope,
    ProviderErrorEnvelope,
    RefusalEnvelope,
    StreamChunkEvent,
    StreamDoneEvent,
    StreamErrorEvent,
    UsageEnvelope,
)

if TYPE_CHECKING:
    from orchestrator.billing import BillingConfig
    from orchestrator.relay.relay import RelayResult

    from .pricing import PricingConfig


_DEFAULT_DEADLINE_S = 30.0


@dataclass
class _StreamOutcome:
    """Terminal state of a streaming chat turn. Consumed by
    ``_finalize_stream_ledger`` to build the PAYMENT row after the
    stream body has completed.
    """

    outcome: str  # "settled" | "refunded" | "cancelled"
    refusal_stage: str | None
    correlation_id: str
    provider_id: str | None
    model_id: str | None
    stream_id: str  # 32-hex; identifies the streaming turn end-to-end
    user_proof_commit: str | None = None
    user_proof_algorithm: str | None = None


def register_chat_stream_route(app: FastAPI) -> None:
    """Register ``POST /chat/stream`` on ``app``.

    Admission-gate ordering is identical to ``POST /chat``:
    401 (missing/bad bearer) → 429 (rate limit) → 402 (commitment).
    Ingress refusal and later errors ride INSIDE the stream as a
    single ``done`` event because by then the SSE headers are already
    committed.
    """
    from fastapi import Depends

    from .admission import admission_dependency

    @app.post(
        "/chat/stream",
        response_model=None,
        summary=(
            "Streaming chat via SSE; two-sided moderation preserved "
            "from 5g-i (Phase 5g-ii)"
        ),
    )
    async def post_chat_stream(
        req: ChatRequest,
        request: Request,
        principal_id: str = Depends(admission_dependency),
        x_payment_commitment: str | None = Header(None, alias="X-Payment-Commitment"),
    ) -> Any:
        deps = app.state.deps
        pricing_config: PricingConfig = app.state.pricing_config
        billing_config: BillingConfig = app.state.billing_config

        deadline_s = float(getattr(app.state, "chat_deadline_s", _DEFAULT_DEADLINE_S))

        user_proof_commit = None
        user_proof_algorithm = None
        if req.user_proof is not None:
            from orchestrator.cognition.user_proof import verify_ed25519_proof, compute_proof_commit, InvalidSignatureError
            try:
                verify_ed25519_proof(
                    req.user_proof.user_pubkey_b64,
                    req.user_proof.signature_b64,
                    req.message,
                )
            except InvalidSignatureError as e:
                return JSONResponse(status_code=400, content={"error": "invalid_user_proof", "detail": str(e)})
            
            user_proof_commit = compute_proof_commit(req.user_proof.user_pubkey_b64, req.message)
            user_proof_algorithm = req.user_proof.algorithm

        # -- 1. Commitment gate ------------------------------------
        # Shared implementation with POST /chat: same challenge body,
        # same 402 status, same reason-code enum. The streaming
        # endpoint earns no different admission surface — the
        # property "billable turns require commitment" is transport-
        # independent.
        body_sha256 = _sha256_text(req.message)
        posted_price = pricing_config.per_message_price_micro_XION
        commitment, challenge = _gate_commitment(
            raw_header=x_payment_commitment,
            billing_config=billing_config,
            posted_price=posted_price,
            body_sha256=body_sha256,
            now_utc_ns=time.time_ns(),
        )
        if challenge is not None:
            return JSONResponse(
                status_code=402,
                content=challenge.model_dump(),
            )

        # -- 2. Open the SSE stream --------------------------------
        # By this point, 401/429/402 have all cleared. All remaining
        # failure modes (ingress refuse, egress refuse, no_floor,
        # provider_error, deadline) are reported as a single ``done``
        # event inside the stream.
        #
        # Phase 5g-ii Commit 5: allocate a fresh ``stream_id`` (128
        # bits of entropy, lowercase hex) BEFORE the generator runs
        # so it is available to every terminal path. The id stamps
        # the PAYMENT row so the Commit-5 ``xion-verify
        # chat-streaming-fidelity`` verifier can group rows by stream
        # and enforce the stream-level invariants (one row per stream,
        # no cross-talk between streams, cancel-without-paired-SAFETY,
        # retroactive-refuse-with-paired-SAFETY).
        stream_id = secrets.token_hex(16)
        generator = _stream_body(
            app=app,
            relay=deps.relay,
            req=req,
            request=request,
            commitment=commitment,
            billing_config=billing_config,
            pricing_config=pricing_config,
            deadline_s=deadline_s,
            stream_id=stream_id,
            voice_sensorium_state=_voice_sensorium_state(
                app,
                req=req,
                principal_id=principal_id,
            ),
            user_proof_commit=user_proof_commit,
            user_proof_algorithm=user_proof_algorithm,
            principal_id=principal_id,
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                # Discourage proxies from buffering the stream; SSE
                # perceptual liveness depends on chunks flushing
                # immediately. Cache-Control no-store also prevents
                # any intermediary from replaying an old transcript.
                "Cache-Control": "no-store",
                "X-Accel-Buffering": "no",
            },
        )


# ------------------------------------------------------------- stream body


async def _stream_body(
    *,
    app: FastAPI,
    relay: Any,
    req: ChatRequest,
    request: Request,
    commitment: Commitment,
    billing_config: "BillingConfig",
    pricing_config: "PricingConfig",
    deadline_s: float,
    stream_id: str,
    voice_sensorium_state: Any = None,
    user_proof_commit: str | None = None,
    user_proof_algorithm: str | None = None,
    principal_id: str = "global",
) -> AsyncIterator[bytes]:
    """The SSE byte stream.

    Yields canonical ``data: <json>\\n\\n`` records. The handler
    opens the stream (HTTP 200 + text/event-stream) before calling
    this; by the time this generator emits any bytes, HTTP headers
    are already committed — this is why ingress-refuse and every
    later failure ride as ``done`` events rather than as an HTTP
    status change.

    Phase 5g-ii Commit 2 flow:
      - Ingress Arbiter call.
      - Refuse → emit one done:refuse{stage=ingress}, finalize refund.
      - Approve → select provider.
        - No floor → emit one done:no_floor, finalize refund.
        - No healthy provider → emit one done:provider_error, finalize refund.
        - Otherwise → stream chunks from ``stream_generate(provider, ...)``;
          buffer the concatenated text; on terminal, run egress
          Arbiter call; emit one done:refuse{stage=egress} OR
          done:approve; finalize refund or settle.
    """
    # -- Ingress moderation ---------------------------------------
    try:
        ingress = await asyncio.to_thread(
            relay.evaluate,
            req.message,
            sensorium_state=voice_sensorium_state,
        )
    except Exception as exc:
        # Arbiter crash before any generation: report as internal
        # transport error; still write a refunded PAYMENT row (no
        # value delivered). The ingress_correlation_id here is a
        # synthetic empty string since no row was written.
        _log("State-of-Xion: Arbiter.evaluate ingress failed", exc)
        yield _sse(StreamErrorEvent(
            kind="error",
            error="internal",
            correlation_id="",
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="provider_error",
                correlation_id="",
                provider_id=None,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    if not ingress.egress_allowed:
        # Ingress refuse: content-free RefusalEnvelope, zero chunks.
        refusal = _refusal_body(ingress, stage="ingress")
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="refuse",
            refusal=refusal,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="ingress",
                correlation_id=ingress.correlation_id,
                provider_id=None,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    # -- Floor check ----------------------------------------------
    if getattr(app.state, "no_floor", False):
        nf = NoFloorEnvelope(
            reason="open_weights_floor_unsatisfied",
            missing_capability=str(
                getattr(app.state, "no_floor_reason", "unknown")
            ),
            manifest_expected_id=str(
                getattr(app.state, "no_floor_manifest_id", "unknown")
            ),
        )
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="no_floor",
            no_floor=nf,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="no_floor",
                correlation_id=ingress.correlation_id,
                provider_id=None,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    # -- Provider selection ---------------------------------------
    router = getattr(app.state, "router", None)
    provider = router.select() if router is not None else None
    if provider is None:
        pe = ProviderErrorEnvelope(
            reason="no_healthy_provider",
            correlation_id=ingress.correlation_id,
        )
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="provider_error",
            provider_error=pe,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="provider_error",
                correlation_id=ingress.correlation_id,
                provider_id=None,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    provider_id = getattr(provider, "provider_id", None) or type(provider).__name__

    # -- Stream the provider --------------------------------------
    buffered: list[str] = []
    seq = 0
    terminal: GenerationResult | None = None
    turn_deadline_monotonic = time.monotonic() + deadline_s
    
    from orchestrator.inference_router.model_registry import get_min_max_tokens
    model_id_configured = getattr(provider, "model", None)
    effective_max_tokens = max(
        req.max_tokens,
        get_min_max_tokens(provider_id, model_id_configured),
    )
    
    supervisor = getattr(app.state, "supervisor", None)
    snapshot_dict = supervisor.latest_snapshot().to_dict() if supervisor and supervisor.latest_snapshot() else None
    
    from orchestrator.cognition.loop import stream_run_turn
    gen = stream_run_turn(
        provider,
        req.message,
        app.state.soul_prompt,
        snapshot_dict,
        effective_max_tokens,
        deadline_s,
        ingress.correlation_id,
        stream_generate,
        principal_id,
    )
    try:
        # Per-chunk wall-clock deadline check. The individual
        # provider call is ALSO deadline-bounded (``deadline_s``
        # passes through to the httpx client timeout in the
        # streaming providers), so a provider that hangs on a
        # socket read terminates naturally. This outer check
        # protects against a provider that yields chunks slowly
        # enough to accumulate past the per-turn budget.
        while True:
            # P6: client-disconnect check (Phase 5g-ii Commit 3).
            # Starlette's ``Request.is_disconnected()`` polls the
            # underlying ASGI receive channel for an
            # ``http.disconnect`` message. When True, we close
            # ``gen`` (which propagates ``asyncio.CancelledError``
            # into the provider's ``httpx.AsyncClient.stream(...)``
            # context, terminating the upstream socket and its
            # billing), write a PAYMENT row with
            # ``outcome=cancelled``, and return — NO done event
            # goes on the wire because the client is already gone.
            if await request.is_disconnected():
                await gen.aclose()
                _finalize_stream_ledger(
                    app,
                    commitment,
                    pricing_config,
                    billing_config,
                    _StreamOutcome(
                        outcome="cancelled",
                        refusal_stage=None,
                        correlation_id=ingress.correlation_id,
                        provider_id=provider_id,
                        model_id=None,
                        stream_id=stream_id,
                    ),
                )
                return

            remaining = turn_deadline_monotonic - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("turn deadline exceeded")
            try:
                event = await asyncio.wait_for(gen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                break
            if isinstance(event, GenerationResult):
                terminal = event
                break
            # str chunk
            buffered.append(event)
            yield _sse(StreamChunkEvent(
                kind="chunk",
                seq=seq,
                text=event,
            ))
            seq += 1
    except asyncio.CancelledError:
        # The server itself cancelled the task (e.g., the ASGI
        # server tore down the connection before we polled
        # ``is_disconnected()``). Treat this as a cancel: close
        # the provider generator, write a cancelled row, re-
        # raise so ASGI knows we respected the cancel. No ``done``
        # event goes on the wire.
        try:
            await gen.aclose()
        except Exception:
            pass
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="cancelled",
                refusal_stage=None,
                correlation_id=ingress.correlation_id,
                provider_id=provider_id,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        raise
    except (asyncio.TimeoutError, TimeoutError):
        yield _sse(StreamErrorEvent(
            kind="error",
            error="deadline_exceeded",
            correlation_id=ingress.correlation_id,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="provider_timeout",
                correlation_id=ingress.correlation_id,
                provider_id=provider_id,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return
    except Exception as exc:
        _log("State-of-Xion: provider stream raised", exc)
        pe = ProviderErrorEnvelope(
            reason="no_healthy_provider",
            correlation_id=ingress.correlation_id,
        )
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="provider_error",
            provider_error=pe,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="provider_error",
                correlation_id=ingress.correlation_id,
                provider_id=provider_id,
                model_id=None,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    model_id = terminal.model_id if terminal is not None else None
    candidate_text = "".join(buffered)

    # -- Empty-candidate egress refuse ---------------------------
    # Mirrors the Phase 5g-i non-streaming handler's policy: an
    # empty provider output is treated as egress-refused with a
    # content-free envelope.
    if not candidate_text:
        ref = RefusalEnvelope(
            stage="egress",
            principle_code=3,
            reason="provider_empty_candidate",
            correlation_id=ingress.correlation_id,
        )
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="refuse",
            refusal=ref,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="empty_candidate",
                correlation_id=ingress.correlation_id,
                provider_id=provider_id,
                model_id=model_id,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    # -- Egress moderation ---------------------------------------
    try:
        egress = await asyncio.to_thread(relay.evaluate, candidate_text)
    except Exception as exc:
        _log("State-of-Xion: Arbiter.evaluate egress failed", exc)
        pe = ProviderErrorEnvelope(
            reason="no_healthy_provider",
            correlation_id=ingress.correlation_id,
        )
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="provider_error",
            provider_error=pe,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="provider_error",
                correlation_id=ingress.correlation_id,
                provider_id=provider_id,
                model_id=model_id,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    if not egress.egress_allowed:
        ref = _refusal_body(egress, stage="egress")
        yield _sse(StreamDoneEvent(
            kind="done",
            verdict="refuse",
            refusal=ref,
        ))
        _finalize_stream_ledger(
            app,
            commitment,
            pricing_config,
            billing_config,
            _StreamOutcome(
                outcome="refunded",
                refusal_stage="egress",
                correlation_id=egress.correlation_id,
                provider_id=provider_id,
                model_id=model_id,
                stream_id=stream_id,
                user_proof_commit=user_proof_commit,
                user_proof_algorithm=user_proof_algorithm,
            ),
        )
        return

    # -- Approve + settle -----------------------------------------
    # The terminal GenerationResult may be missing if the provider
    # closed the stream without emitting a terminal (shouldn't
    # happen with well-behaved providers; be defensive).
    usage_in = terminal.usage_in if terminal is not None else 0
    usage_out = terminal.usage_out if terminal is not None else 0
    final_model_id = model_id or (provider_id or "")

    ok = ChatResponse(
        role="xion",
        text=candidate_text,
        model_id=final_model_id,
        usage=UsageEnvelope(input_tokens=usage_in, output_tokens=usage_out),
        correlation_id=egress.correlation_id,
    )
    yield _sse(StreamDoneEvent(
        kind="done",
        verdict="approve",
        response=ok,
    ))
    _finalize_stream_ledger(
        app,
        commitment,
        pricing_config,
        billing_config,
        _StreamOutcome(
            outcome="settled",
            refusal_stage=None,
            correlation_id=egress.correlation_id,
            provider_id=provider_id,
            model_id=final_model_id,
            stream_id=stream_id,
            user_proof_commit=user_proof_commit,
            user_proof_algorithm=user_proof_algorithm,
        ),
    )


# -------------------------------------------------------------- finalize


def _finalize_stream_ledger(
    app: FastAPI,
    commitment: Commitment,
    pricing_config: "PricingConfig",
    billing_config: "BillingConfig",
    outcome: _StreamOutcome,
) -> None:
    """Write the PAYMENT_LEDGER row after the stream body has emitted
    its terminal event. Mirrors the non-streaming ``_finalize`` tail
    in ``orchestrator/api/chat.py`` with one difference: because the
    HTTP status is already 200 by the time the stream body runs, a
    ledger-write failure cannot flip the status to 503. All we can do
    is log to stderr and leave the stream closed. The ``done`` event
    was already sent; the caller's UI already reflects the moderation
    verdict. The missing ledger row is the honest record that this
    turn did not complete its constitutional finalize step, and the
    operator learns about it from the stderr emission.

    Commit 3 (cancellation) will extend this to accept
    ``outcome="cancelled"``; Commit 2 only emits ``settled`` /
    ``refunded``.
    """
    disabled = bool(commitment.__dict__.get("_disabled_posture", False))
    if disabled:
        posture = "disabled"
        committed = settled = refunded = 0
        auth_ref = ""
    else:
        posture = commitment.posture  # type: ignore[assignment]
        committed = pricing_config.per_message_price_micro_XION
        if outcome.outcome == "settled":
            settled = committed
            refunded = 0
        else:
            settled = 0
            refunded = committed
        auth_ref = commitment.authorization_reference

    try:
        append_payment_row(
            billing_config.payment_ledger_path,
            correlation_id=outcome.correlation_id,
            timestamp_utc_ns=time.time_ns(),
            posture=posture,  # type: ignore[arg-type]
            outcome=outcome.outcome,  # type: ignore[arg-type]
            refusal_stage=outcome.refusal_stage,  # type: ignore[arg-type]
            committed_XION=committed,
            settled_XION=settled,
            refund_XION=refunded,
            posted_price_XION=pricing_config.per_message_price_micro_XION,
            provider_id=outcome.provider_id,
            model_id=outcome.model_id,
            authorization_reference=auth_ref,
            source_sha256=billing_config.architecture_sha256,
            stream_id=outcome.stream_id,
            user_proof_commit=outcome.user_proof_commit,
            user_proof_algorithm=outcome.user_proof_algorithm,
        )
    except Exception as exc:
        _log(
            "State-of-Xion: PAYMENT_LEDGER append failed on /chat/stream",
            exc,
        )


# ---------------------------------------------------------------- helpers


def _sse(event: StreamChunkEvent | StreamDoneEvent | StreamErrorEvent) -> bytes:
    """Serialise an event as a canonical SSE record.

    One ``data: <json>\\n\\n`` line. No ``event:`` name, no ``id:``,
    no ``retry:`` — the wire format pinned in
    ``docs/32-CHAT-STREAMING.md`` § "SSE wire format".
    """
    payload = event.model_dump_json()
    return f"data: {payload}\n\n".encode("utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _refusal_body(r: "RelayResult", *, stage: str) -> RefusalEnvelope:
    verdict = r.verdict
    principle_code = _principle_to_int(verdict.principle_id) if verdict.principle_id else 3
    reason = "covenant_refuse" if verdict.decision.value == "refuse" else "covenant_escalate"
    return RefusalEnvelope(
        stage=stage,  # type: ignore[arg-type]
        principle_code=principle_code,
        reason=reason,  # type: ignore[arg-type]
        correlation_id=r.correlation_id,
    )


def _log(prefix: str, exc: BaseException) -> None:
    print(f"{prefix}: {exc!r}", file=sys.stderr, flush=True)


__all__ = ["register_chat_stream_route"]
