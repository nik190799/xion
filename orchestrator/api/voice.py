"""Phase 6.5 voice stream endpoint.

Property promised: voice-enabled callers get a consent-gated audible frame
that passes through the same Relay/Arbiter gates as text chat. The endpoint
does not publish raw audio or transcript bytes to ledgers; only SAFETY,
REQUEST, and SENSORIUM scalar rows are written by the existing Relay path.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from orchestrator.api.admission import admission_dependency
from orchestrator.api.chat import _stream_voice_consented, _voice_sensorium_state
from orchestrator.api.models import ChatRequest, MIN_MAX_TOKENS
from orchestrator.senses.voice_emitter import compose_voice_frame

router = APIRouter()


class VoiceStreamRequest(BaseModel):
    """Browser voice turn request.

    `message` is the text prompt handed to the cognition loop. `transcript_text`
    is the STT transcript for the user's spoken input; it may match `message`
    during the text-first bootstrap posture.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str = Field(min_length=1, max_length=16_000)
    transcript_text: str = Field(min_length=1, max_length=16_000)
    max_tokens: int = Field(default=2048, ge=MIN_MAX_TOKENS, le=4096)
    livekit_room: str | None = Field(default=None, max_length=128)


class VoiceStreamEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["voice_frame", "done", "error"]
    frame: dict[str, Any] | None = None
    verdict: Literal["approve", "refuse", "provider_error"] | None = None
    correlation_id: str | None = None
    reason: str | None = None


@router.post("/voice/stream", response_model=None)
async def post_voice_stream(
    req: VoiceStreamRequest,
    request: Request,
    principal_id: str = Depends(admission_dependency),
) -> Any:
    """Stream one voice turn as SSE records."""
    if not _stream_voice_consented(principal_id):
        return JSONResponse(
            status_code=403,
            content={"error": "voice_consent_required"},
        )

    return StreamingResponse(
        _voice_stream_body(request=request, req=req, principal_id=principal_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


async def _voice_stream_body(
    *,
    request: Request,
    req: VoiceStreamRequest,
    principal_id: str,
) -> AsyncIterator[bytes]:
    app = request.app
    relay = app.state.deps.relay
    voice_router = getattr(app.state, "voice_router", None)
    provider = voice_router.select_floor() if voice_router is not None else None
    if provider is None:
        yield _sse(
            VoiceStreamEvent(
                kind="error",
                verdict="provider_error",
                reason="voice_floor_unavailable",
            )
        )
        return

    try:
        transcript = provider.transcribe(transcript_text=req.transcript_text)
    except Exception as exc:
        yield _sse(
            VoiceStreamEvent(
                kind="error",
                verdict="provider_error",
                reason=f"stt_failed:{type(exc).__name__}",
            )
        )
        return

    chat_req = ChatRequest(
        message=req.message,
        transcript_text=transcript,
        max_tokens=req.max_tokens,
    )
    voice_state = _voice_sensorium_state(app, req=chat_req, principal_id=principal_id)
    ingress = await asyncio.to_thread(
        relay.evaluate,
        req.message,
        sensorium_state=voice_state,
    )
    state = voice_state or _latest_state(app)

    if not ingress.egress_allowed:
        frame = provider.synthesize_frame(
            text="",
            prosody_frame=compose_voice_frame(state, refusal=True),
            livekit_room=req.livekit_room,
        )
        yield _sse(
            VoiceStreamEvent(
                kind="voice_frame",
                frame=frame,
                verdict="refuse",
                correlation_id=ingress.correlation_id,
            )
        )
        yield _sse(
            VoiceStreamEvent(
                kind="done",
                verdict="refuse",
                correlation_id=ingress.correlation_id,
            )
        )
        return

    text_provider = _select_text_provider(app)
    if text_provider is None:
        yield _sse(
            VoiceStreamEvent(
                kind="error",
                verdict="provider_error",
                correlation_id=ingress.correlation_id,
                reason="no_healthy_text_provider",
            )
        )
        return

    try:
        from orchestrator.cognition.loop import chat_cognition_budget, run_turn
        from orchestrator.inference_router.model_registry import get_min_max_tokens

        provider_id = getattr(text_provider, "provider_id", type(text_provider).__name__)
        model_id_configured = getattr(text_provider, "model", None)
        effective_max_tokens = max(
            req.max_tokens,
            get_min_max_tokens(provider_id, model_id_configured),
        )
        supervisor = getattr(app.state, "supervisor", None)
        snapshot_dict = (
            supervisor.latest_snapshot().to_dict()
            if supervisor is not None and supervisor.latest_snapshot()
            else None
        )
        chat_deadline = float(getattr(app.state, "chat_deadline_s", 30.0))
        cog_budget = chat_cognition_budget()
        turn_timeout_s = max(chat_deadline, cog_budget.wall_clock_s)
        result = await asyncio.wait_for(
            asyncio.to_thread(
                run_turn,
                text_provider,
                req.message,
                app.state.soul_prompt,
                snapshot_dict,
                effective_max_tokens,
                chat_deadline,
                ingress.correlation_id,
                budget=cog_budget,
            ),
            timeout=turn_timeout_s,
        )
    except Exception as exc:
        yield _sse(
            VoiceStreamEvent(
                kind="error",
                verdict="provider_error",
                correlation_id=ingress.correlation_id,
                reason=f"generation_failed:{type(exc).__name__}",
            )
        )
        return

    egress = await asyncio.to_thread(relay.evaluate, result.text)
    refusal = not egress.egress_allowed
    frame = provider.synthesize_frame(
        text="" if refusal else result.text,
        prosody_frame=compose_voice_frame(_latest_state(app), refusal=refusal),
        livekit_room=req.livekit_room,
    )
    verdict: Literal["approve", "refuse"] = "refuse" if refusal else "approve"
    yield _sse(
        VoiceStreamEvent(
            kind="voice_frame",
            frame=frame,
            verdict=verdict,
            correlation_id=egress.correlation_id,
        )
    )
    yield _sse(
        VoiceStreamEvent(
            kind="done",
            verdict=verdict,
            correlation_id=egress.correlation_id,
        )
    )


def _latest_state(app: Any) -> Any:
    supervisor = getattr(app.state, "supervisor", None)
    if supervisor is not None:
        try:
            state = supervisor.latest_snapshot()
            if state is not None:
                return state
        except Exception:
            pass
    from orchestrator.sensorium import (
        Chronoception,
        DistressSignal,
        Interoception,
        Proprioception,
        SensoriumState,
    )

    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=0.0),
    )


def _select_text_provider(app: Any) -> Any | None:
    text_router = getattr(app.state, "router", None)
    if text_router is None:
        return None
    ordered = text_router.select_ordered()
    for provider in ordered:
        if callable(getattr(provider, "generate", None)):
            return provider
    return None


def _sse(event: VoiceStreamEvent) -> bytes:
    return f"data: {event.model_dump_json()}\n\n".encode("utf-8")


__all__ = ["VoiceStreamRequest", "VoiceStreamEvent", "router"]
