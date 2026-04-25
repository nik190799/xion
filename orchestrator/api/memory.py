"""Phase 6.4: Memory & Consent.

User-directed consent adjustments over the four modalities.
"""
import os
from pathlib import Path
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from typing import Annotated

from orchestrator.api.admission import admission_dependency
from orchestrator.consent.store import write_consent, read_consent

router = APIRouter()

# Four scopes, warm defaults, extra='forbid'
class ModalityConsent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    visual: bool = True
    vitals: bool = True
    voice: bool = True
    memory: bool = True

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
    
    return consent

__all__ = ["router", "ModalityConsent"]
