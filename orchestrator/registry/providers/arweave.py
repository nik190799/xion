"""Arweave Relay registry publisher provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.registry.arweave_publisher import (
    ArweaveRelayRegistryPublisher as _ArweaveRelayRegistryPublisher,
)


class ArweaveRelayRegistryPublisher(_ArweaveRelayRegistryPublisher):
    provider_id = "arweave"

    def publish_local(self, path: Path | str, relays: list[dict[str, Any]]) -> dict[str, Any]:
        return super().publish_local(path, relays)

    def publish_remote(self, relays: list[dict[str, Any]]) -> str:
        return super().publish_remote(relays)

__all__ = ["ArweaveRelayRegistryPublisher"]
