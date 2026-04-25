"""Bridge attestation substrate for AO -> EVM evidence."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class BridgeAttestation:
    source_chain: str
    target_chain: str
    event_id: str
    payload_hash: str
    attestor_id: str
    signature: str
    observed_utc_ns: int


@runtime_checkable
class BridgeAttestor(Protocol):
    attestor_id: str

    def attest(self, *, source_chain: str, target_chain: str, event_id: str, payload: dict[str, Any]) -> BridgeAttestation: ...

    def verify(self, attestation: BridgeAttestation, *, payload: dict[str, Any]) -> bool: ...


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def now_ns() -> int:
    return time.time_ns()


__all__ = ["BridgeAttestation", "BridgeAttestor", "canonical_payload_hash", "now_ns"]
