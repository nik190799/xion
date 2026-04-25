"""Phase 6.4/6.6.b: Memory & Consent.

User-directed consent adjustments over the four modalities.
"""
import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from orchestrator.api.admission import admission_dependency
from orchestrator.cognition.memory_adapter import ForgetScope, MemoryForgetAdapter
from orchestrator.consent.store import read_consent, write_consent

router = APIRouter()

# Four scopes, warm defaults, extra='forbid'
class ModalityConsent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stream_visual: bool = False
    stream_vitals: bool = False
    stream_voice: bool = False
    stream_memory: bool = True


class ForgetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: ForgetScope = ForgetScope.ALL


class RecallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    top_k: int = 5

@router.get("/memory/consent")
def get_consent(
    req: Request,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> ModalityConsent:
    """Read the caller's current consent posture."""
    store_path = Path(os.environ.get("XION_CONSENT_LEDGER", "ledgers/CONSENT_LEDGER.jsonl"))

    # Fast path: no file exists yet
    if not store_path.is_file():
        return ModalityConsent()

    latest = read_consent(store_path, principal_id)
    if latest is None:
        return ModalityConsent()

    return ModalityConsent(**latest)

@router.post("/memory/consent")
def post_consent(
    req: Request,
    consent: ModalityConsent,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> ModalityConsent:
    """Update the caller's consent posture."""
    store_path = Path(os.environ.get("XION_CONSENT_LEDGER", "ledgers/CONSENT_LEDGER.jsonl"))

    # Ensure directory exists
    store_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to append-only JSONL
    write_consent(store_path, principal_id, consent.model_dump())

    bus = getattr(req.app.state, "signal_bus", None)
    if bus is not None:
        from orchestrator.sensorium.receptors._util import sense_signal

        bus.publish(
            [
                sense_signal(
                    kind="governance.consent_change",
                    receptor_id="memory_consent",
                    value=consent.model_dump(),
                    methodology_hash="2222222222222222222222222222222222222222222222222222222222222222",
                )
            ]
        )

    return consent


@router.post("/forget")
def post_forget(
    req: Request,
    body: ForgetRequest,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> dict[str, object]:
    """Propagate user-directed forget requests through the memory adapter."""
    adapter = getattr(req.app.state, "memory_forget_adapter", None)
    if adapter is None:
        backend = getattr(req.app.state, "memory_backend", None)
        if backend is None:
            return {
                "status": "not_configured",
                "principal_id": principal_id,
                "scope": body.scope.value,
                "deleted_records": 0,
                "within_sla": True,
            }
        adapter = MemoryForgetAdapter(backend)
    receipt = adapter.forget(principal_id, body.scope)
    return {
        "status": "forgotten",
        "principal_id": receipt.principal_id,
        "scope": receipt.scope.value,
        "deleted_records": receipt.deleted_records,
        "backend_id": receipt.backend_id,
        "elapsed_ns": receipt.elapsed_ns,
        "within_sla": receipt.within_sla,
    }


@router.post("/memory/recall")
def post_recall(
    req: Request,
    body: RecallRequest,
    principal_id: Annotated[str, Depends(admission_dependency)],
) -> dict[str, object]:
    """Recall consent-scoped memory snippets through the vector backend."""
    backend = getattr(req.app.state, "memory_backend", None)
    if backend is None:
        return {"hits": [], "backend_id": "not_configured"}

    from orchestrator.embeddings.providers.local_bge_m3 import LocalBgeM3EmbeddingProvider

    embedder = LocalBgeM3EmbeddingProvider()
    embedding = embedder.embed([body.query]).vectors[0]
    hits = backend.search(
        embedding,
        top_k=max(1, min(body.top_k, 20)),
        principal_id=principal_id,
    )
    return {
        "backend_id": getattr(backend, "backend_id", "unknown"),
        "hits": [
            {
                "record_id": hit.record_id,
                "text": hit.text,
                "score": hit.score,
                "scope": hit.scope.value,
            }
            for hit in hits
        ],
    }

__all__ = ["ForgetRequest", "ModalityConsent", "RecallRequest", "router"]
