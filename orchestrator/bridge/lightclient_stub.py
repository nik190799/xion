"""Deterministic AO checkpoint bridge attestor."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .attestor import BridgeAttestation, canonical_payload_hash, now_ns

_ZERO_HASH = "0" * 64


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def checkpoint_hash(checkpoint: dict[str, Any]) -> str:
    material = (
        f"{checkpoint['process_id']}:{checkpoint['height']}:{checkpoint['prev_state_root']}:"
        f"{checkpoint['state_root']}:{checkpoint['event_id']}:{checkpoint['payload_hash']}"
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LightClientBridgeAttestor:
    """Verifies bridge payloads against an AO checkpoint header shape.

    This is not a network light client. It is the pre-Genesis deterministic
    verifier for the evidence envelope Xion requires before an EVM-side bridge
    effect can be accepted: the checkpoint must bind the event id, payload hash,
    process id, state roots, and monotonically positive height into a signed
    checkpoint digest.
    """

    attestor_id: str = "ao-checkpoint-lightclient"

    def attest(self, *, source_chain: str, target_chain: str, event_id: str, payload: dict[str, Any]) -> BridgeAttestation:
        checkpoint = self._checkpoint_for(payload=payload, event_id=event_id)
        payload_hash = canonical_payload_hash(payload)
        digest = checkpoint_hash(checkpoint)
        return BridgeAttestation(
            source_chain=source_chain,
            target_chain=target_chain,
            event_id=event_id,
            payload_hash=payload_hash,
            attestor_id=self.attestor_id,
            signature=f"ao-checkpoint:{checkpoint['process_id']}:{checkpoint['height']}:{digest}",
            observed_utc_ns=now_ns(),
        )

    def verify(self, attestation: BridgeAttestation, *, payload: dict[str, Any]) -> bool:
        if attestation.attestor_id != self.attestor_id:
            return False
        if attestation.payload_hash != canonical_payload_hash(payload):
            return False
        try:
            checkpoint = self._checkpoint_for(payload=payload, event_id=attestation.event_id)
        except ValueError:
            return False
        expected_signature = f"ao-checkpoint:{checkpoint['process_id']}:{checkpoint['height']}:{checkpoint_hash(checkpoint)}"
        return attestation.signature == expected_signature

    def _checkpoint_for(self, *, payload: dict[str, Any], event_id: str) -> dict[str, Any]:
        checkpoint = payload.get("ao_checkpoint")
        if not isinstance(checkpoint, dict):
            raise ValueError("payload missing ao_checkpoint object")
        payload_hash = canonical_payload_hash(
            {key: value for key, value in payload.items() if key not in {"ao_checkpoint", "payload_hash"}}
        )
        required = {
            "process_id": str,
            "height": int,
            "prev_state_root": str,
            "state_root": str,
            "event_id": str,
            "payload_hash": str,
        }
        for key, expected_type in required.items():
            if not isinstance(checkpoint.get(key), expected_type):
                raise ValueError(f"ao_checkpoint.{key} has invalid type")
        if checkpoint["height"] <= 0:
            raise ValueError("ao_checkpoint.height must be positive")
        if checkpoint["event_id"] != event_id:
            raise ValueError("ao_checkpoint.event_id does not match bridge event id")
        if checkpoint["payload_hash"] != payload_hash:
            raise ValueError("ao_checkpoint.payload_hash does not match payload body")
        if not _is_hex64(checkpoint["state_root"]):
            raise ValueError("ao_checkpoint.state_root must be hex64")
        if not (_is_hex64(checkpoint["prev_state_root"]) or checkpoint["prev_state_root"] == _ZERO_HASH):
            raise ValueError("ao_checkpoint.prev_state_root must be hex64")
        return checkpoint


__all__ = ["LightClientBridgeAttestor", "checkpoint_hash"]
