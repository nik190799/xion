"""Phase 6.4: Presence Surface.

GET /presence/state + /presence/stream SSE.
Enforces modality consent and connection-level overrides.
"""
import asyncio
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import StreamingResponse

from orchestrator.api.admission import admission_dependency
from orchestrator.consent.store import read_consent
from orchestrator.api.memory import ModalityConsent
from orchestrator.senses.visual_emitter import stream_visuals
from orchestrator.senses.vitals_emitter import stream_vitals

router = APIRouter()

def _get_consent(principal_id: str) -> ModalityConsent:
    store_path = Path(os.environ.get("XION_CONSENT_LEDGER", "ledgers/CONSENT_LEDGER.jsonl"))
    if not store_path.is_file():
        return ModalityConsent()
    latest = read_consent(store_path, principal_id)
    return ModalityConsent() if latest is None else ModalityConsent(**latest)

@router.get("/presence/state")
def get_presence_state(
    req: Request,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> dict:
    """Return the current presence capabilities. Not a stream."""
    consent = _get_consent(principal_id)
    return {
        "visual_active": consent.stream_visual,
        "vitals_active": consent.stream_vitals,
        "voice_active": consent.stream_voice,
    }

@router.get("/presence/stream")
async def get_presence_stream(
    req: Request,
    principal_id: Annotated[str, Depends(admission_dependency)],
    visual: int = Query(1, alias="visual", description="Override visual stream (0|1)"),
    vitals: int = Query(1, alias="vitals", description="Override vitals stream (0|1)"),
) -> StreamingResponse:
    """Multiplexed SSE for visual and vitals presence."""
    consent = _get_consent(principal_id)
    presence_bus = req.app.state.presence_bus

    # Server MUST NOT compose frames for off channels
    serve_visual = consent.stream_visual and bool(visual)
    serve_vitals = consent.stream_vitals and bool(vitals)

    async def _multiplexer():
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=8)
        tasks = []

        async def _run_stream(stream_func):
            try:
                async for payload in stream_func(presence_bus):
                    # Drop payloads if queue is full (client is too slow)
                    try:
                        queue.put_nowait(payload)
                    except asyncio.QueueFull:
                        pass
            except asyncio.CancelledError:
                pass

        if serve_visual:
            tasks.append(asyncio.create_task(_run_stream(stream_visuals)))
        if serve_vitals:
            tasks.append(asyncio.create_task(_run_stream(stream_vitals)))

        try:
            while True:
                # Wait for next payload from any active stream
                if not serve_visual and not serve_vitals:
                    yield "event: closed\ndata: {}\n\n"
                    break

                payload = await queue.get()
                # SSE format
                yield f"data: {payload}\n\n"
        finally:
            for t in tasks:
                t.cancel()

    return StreamingResponse(_multiplexer(), media_type="text/event-stream")

__all__ = ["router"]
