"""Multisig bridge attestor scaffold."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .attestor import BridgeAttestation, canonical_payload_hash, now_ns


@dataclass(frozen=True)
class MultisigBridgeAttestor:
    attestor_id: str = "multisig-attestor"
    signer_set_id: str = "genesis-bridge-multisig"
    threshold: int = 2

    def attest(self, *, source_chain: str, target_chain: str, event_id: str, payload: dict[str, Any]) -> BridgeAttestation:
        payload_hash = canonical_payload_hash(payload)
        signature = hashlib.sha256(f"{self.signer_set_id}:{self.threshold}:{event_id}:{payload_hash}".encode("utf-8")).hexdigest()
        return BridgeAttestation(
            source_chain=source_chain,
            target_chain=target_chain,
            event_id=event_id,
            payload_hash=payload_hash,
            attestor_id=self.attestor_id,
            signature=f"multisig:{self.signer_set_id}:{self.threshold}:{signature}",
            observed_utc_ns=now_ns(),
        )

    def verify(self, attestation: BridgeAttestation, *, payload: dict[str, Any]) -> bool:
        expected = self.attest(
            source_chain=attestation.source_chain,
            target_chain=attestation.target_chain,
            event_id=attestation.event_id,
            payload=payload,
        )
        return (
            attestation.payload_hash == expected.payload_hash
            and attestation.attestor_id == self.attestor_id
            and attestation.signature == expected.signature
        )


__all__ = ["MultisigBridgeAttestor"]
