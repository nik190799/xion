"""AO -> EVM treasury-spend bridge event helpers."""

from __future__ import annotations

from typing import Any

from .attestor import BridgeAttestation, BridgeAttestor, canonical_payload_hash


def build_treasury_spend_payload(
    *,
    process_id: str,
    height: int,
    prev_state_root: str,
    state_root: str,
    spend_id: str,
    amount: int,
    asset: str,
    recipient: str,
    purpose_sha256: str,
    chain_id: int,
) -> dict[str, Any]:
    event_id = f"treasury-spend:{spend_id}"
    body: dict[str, Any] = {
        "kind": "treasury-spend",
        "spend_id": spend_id,
        "amount": amount,
        "asset": asset,
        "recipient": recipient,
        "purpose_sha256": purpose_sha256,
        "chain_id": chain_id,
        "bridge_event_id": event_id,
    }
    body_hash = canonical_payload_hash(body)
    return {
        **body,
        "payload_hash": body_hash,
        "ao_checkpoint": {
            "process_id": process_id,
            "height": height,
            "prev_state_root": prev_state_root,
            "state_root": state_root,
            "event_id": event_id,
            "payload_hash": body_hash,
        },
    }


def attest_treasury_spend(attestor: BridgeAttestor, *, payload: dict[str, Any]) -> BridgeAttestation:
    return attestor.attest(
        source_chain="ao",
        target_chain="base",
        event_id=str(payload["bridge_event_id"]),
        payload=payload,
    )


def verify_treasury_spend(attestor: BridgeAttestor, attestation: BridgeAttestation, *, payload: dict[str, Any]) -> bool:
    return attestor.verify(attestation, payload=payload)


__all__ = ["attest_treasury_spend", "build_treasury_spend_payload", "verify_treasury_spend"]
