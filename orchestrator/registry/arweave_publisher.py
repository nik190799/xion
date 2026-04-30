"""Arweave Relay registry publisher.

The default publisher writes a deterministic local registry document. Operators
can provide an Arweave submitter at deploy time without changing the verifier
contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

from orchestrator.vault import get_vault


class RegistrySubmitter(Protocol):
    def submit(self, payload: bytes, tags: dict[str, str]) -> str:
        """Submit registry payload and return transaction id."""


class ArweaveRegistrySubmitter:
    """Arweave-backed registry submitter.

    Wallet custody follows the safety-anchor pattern: the operator passes a
    path to a JWK file via environment, never inline secret material.
    """

    _DEFAULT_GATEWAY = "https://arweave.net"
    _JWK_PATH_ENV = "XION_REGISTRY_WALLET_JWK_PATH"
    _GATEWAY_ENV = "XION_REGISTRY_ARWEAVE_GATEWAY"

    def __init__(
        self,
        *,
        jwk_path: str | Path | None = None,
        gateway: str | None = None,
    ) -> None:
        self._jwk_path = (
            str(jwk_path)
            if jwk_path is not None
            else get_vault().unlock(self._JWK_PATH_ENV)
            or os.environ.get(self._JWK_PATH_ENV)
        )
        self._gateway = gateway or os.environ.get(self._GATEWAY_ENV, self._DEFAULT_GATEWAY)

    def submit(self, payload: bytes, tags: dict[str, str]) -> str:
        try:
            import arweave  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "ArweaveRegistrySubmitter requires `arweave-python-client` "
                "to publish the Relay registry."
            ) from exc

        if not self._jwk_path:
            raise RuntimeError(
                f"ArweaveRegistrySubmitter: no JWK path configured "
                f"(set {self._JWK_PATH_ENV} or pass jwk_path=)"
            )
        jwk_file = Path(self._jwk_path)
        if not jwk_file.is_file():
            raise RuntimeError(f"ArweaveRegistrySubmitter: JWK file not found: {jwk_file}")

        wallet = arweave.Wallet(str(jwk_file))
        tx = arweave.Transaction(wallet, data=payload)
        for key, value in tags.items():
            tx.add_tag(key, value)
        tx.add_tag("Xion-Artifact", "RELAY_REGISTRY")
        tx.add_tag("Content-Type", "application/json")
        tx.sign()
        tx.send()
        return str(tx.id)


def arweave_submitter_from_env() -> ArweaveRegistrySubmitter:
    return ArweaveRegistrySubmitter()


def build_registry_document(relays: list[dict[str, Any]], *, as_of_utc_ns: int | None = None) -> dict[str, Any]:
    document = {
        "schema_version": 1,
        "as_of_utc_ns": time.time_ns() if as_of_utc_ns is None else as_of_utc_ns,
        "discovery_paths": ["arweave_registry", "ao_process", "dns_seed", "akash_secondary"],
        "relays": relays,
    }
    payload = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    document["payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return document


class ArweaveRelayRegistryPublisher:
    provider_id = "arweave"

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

    def publish_remote(self, relays: list[dict[str, Any]]) -> str:
        return self.publish_arweave(relays)


__all__ = [
    "ArweaveRegistrySubmitter",
    "ArweaveRelayRegistryPublisher",
    "RegistrySubmitter",
    "arweave_submitter_from_env",
    "build_registry_document",
]
