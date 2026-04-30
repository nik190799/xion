"""Relay registry publisher gateway Protocol and provider loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from orchestrator.registry.arweave_publisher import arweave_submitter_from_env
from orchestrator.registry.providers import (
    ArweaveRelayRegistryPublisher,
    LocalFileRelayRegistryPublisher,
)


@runtime_checkable
class RelayRegistryPublisher(Protocol):
    """Stable boundary for publishing Relay registry documents."""

    provider_id: str

    def publish_local(self, path: Path | str, relays: list[dict[str, Any]]) -> dict[str, Any]:
        """Write a deterministic local registry document."""

    def publish_remote(self, relays: list[dict[str, Any]]) -> str:
        """Publish remotely and return a tx id or equivalent locator."""


@dataclass(frozen=True, slots=True)
class RelayRegistryPublisherSettings:
    backend: str = "local-file"

    @classmethod
    def from_env(cls) -> RelayRegistryPublisherSettings:
        return cls(
            backend=os.environ.get("XION_REGISTRY_BACKEND", "local-file")
            .strip()
            .lower()
            or "local-file"
        )


def get_relay_registry_publisher(
    settings: RelayRegistryPublisherSettings | None = None,
) -> RelayRegistryPublisher:
    """Load the configured Relay registry publisher."""

    resolved = settings or RelayRegistryPublisherSettings.from_env()
    if resolved.backend in {"", "local", "local-file", "file"}:
        return LocalFileRelayRegistryPublisher()
    if resolved.backend == "arweave":
        return ArweaveRelayRegistryPublisher(submitter=arweave_submitter_from_env())
    raise ValueError(
        f"unsupported XION_REGISTRY_BACKEND={resolved.backend!r}; "
        "expected local-file or arweave"
    )


__all__ = [
    "RelayRegistryPublisher",
    "RelayRegistryPublisherSettings",
    "get_relay_registry_publisher",
]
