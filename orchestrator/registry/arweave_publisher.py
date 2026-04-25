"""Arweave Relay registry publisher.

The default publisher writes a deterministic local registry document. Operators
can provide an Arweave submitter at deploy time without changing the verifier
contract.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Protocol


class RegistrySubmitter(Protocol):
    def submit(self, payload: bytes, tags: dict[str, str]) -> str:
        """Submit registry payload and return transaction id."""


def build_registry_document(relays: list[dict[str, Any]], *, as_of_utc_ns: int | None = None) -> dict[str, Any]:
    document = {
        "schema_version": 1,
        "as_of_utc_ns": time.time_ns() if as_of_utc_ns is None else as_of_utc_ns,
        "discovery_paths": ["arweave_registry", "ao_process", "dns_seed", "laptop_secondary"],
        "relays": relays,
    }
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    document["payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return document


class RelayRegistryPublisher:
    def __init__(self, *, submitter: RegistrySubmitter | None = None) -> None:
        self._submitter = submitter

    def publish_local(self, path: Path | str, relays: list[dict[str, Any]]) -> dict[str, Any]:
        document = build_registry_document(relays)
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return document

    def publish_arweave(self, relays: list[dict[str, Any]]) -> str:
        if self._submitter is None:
            raise RuntimeError("no Arweave submitter configured")
        document = build_registry_document(relays)
        payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return self._submitter.submit(payload, {"App-Name": "xion-relay-registry", "Schema-Version": "1"})


__all__ = ["RegistrySubmitter", "RelayRegistryPublisher", "build_registry_document"]
