"""Local-file Relay registry publisher provider."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from orchestrator.registry.arweave_publisher import build_registry_document


@dataclass(frozen=True, slots=True)
class LocalFileRelayRegistryPublisher:
    """Publish relay registry documents to local files for tests/dev."""

    provider_id: str = "local-file"
    default_path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("XION_REGISTRY_LOCAL_PATH", "ledgers/RELAY_REGISTRY_LOCAL.json")
        )
    )

    def publish_local(self, path: Path | str, relays: list[dict[str, Any]]) -> dict[str, Any]:
        document = build_registry_document(relays)
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return document

    def publish_remote(self, relays: list[dict[str, Any]]) -> str:
        self.publish_local(self.default_path, relays)
        return str(self.default_path)


__all__ = ["LocalFileRelayRegistryPublisher"]
