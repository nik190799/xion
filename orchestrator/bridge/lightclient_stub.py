"""Reserved AO light-client bridge attestor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .attestor import BridgeAttestation, canonical_payload_hash


@dataclass(frozen=True)
class LightClientBridgeAttestor:
    """Stub for future trust-minimized AO light-client verification."""

    attestor_id: str = "lightclient-stub"
    not_yet_sealed_reason: str = "NOT_YET_SEALED: AO light-client proof verification is reserved for post-Genesis hardening."

    def attest(self, *, source_chain: str, target_chain: str, event_id: str, payload: dict[str, Any]) -> BridgeAttestation:
        raise NotImplementedError("lightclient bridge attestation is NOT_YET_SEALED")

    def verify(self, attestation: BridgeAttestation, *, payload: dict[str, Any]) -> bool:
        return attestation.payload_hash == canonical_payload_hash(payload) and False


__all__ = ["LightClientBridgeAttestor"]
