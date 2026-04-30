"""Public status publisher gateway Protocol and provider loader."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from orchestrator.registry.arweave_publisher import arweave_submitter_from_env


@runtime_checkable
class StatusPublisher(Protocol):
    """Stable boundary for publishing public status snapshots."""

    provider_id: str

    def publish(self, snapshot: dict[str, Any]) -> str:
        """Publish a status snapshot and return a locator."""


@dataclass(frozen=True, slots=True)
class LocalFileStatusPublisher:
    """Publish status snapshots to a local JSON file."""

    provider_id: str = "local-file"
    path: Path = field(
        default_factory=lambda: Path(
            os.environ.get("XION_STATUS_LOCAL_PATH", "ledgers/STATUS_SNAPSHOT.json")
        )
    )

    def publish(self, snapshot: dict[str, Any]) -> str:
        payload = _normalize_snapshot(snapshot)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return str(self.path)


@dataclass(frozen=True, slots=True)
class ArweaveStatusPublisher:
    """Publish status snapshots to Arweave through the registry wallet path."""

    provider_id: str = "arweave"

    def publish(self, snapshot: dict[str, Any]) -> str:
        submitter = arweave_submitter_from_env()
        payload = json.dumps(
            _normalize_snapshot(snapshot),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return submitter.submit(
            payload,
            {"App-Name": "xion-status", "Schema-Version": "1"},
        )


@dataclass(frozen=True, slots=True)
class StatusPublisherSettings:
    backend: str = "local-file"

    @classmethod
    def from_env(cls) -> StatusPublisherSettings:
        return cls(
            backend=os.environ.get("XION_STATUS_BACKEND", "local-file")
            .strip()
            .lower()
            or "local-file"
        )


def get_status_publisher(
    settings: StatusPublisherSettings | None = None,
) -> StatusPublisher:
    resolved = settings or StatusPublisherSettings.from_env()
    if resolved.backend in {"", "local", "local-file", "file"}:
        return LocalFileStatusPublisher()
    if resolved.backend == "arweave":
        return ArweaveStatusPublisher()
    raise ValueError(
        f"unsupported XION_STATUS_BACKEND={resolved.backend!r}; "
        "expected local-file or arweave"
    )


def _normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "as_of_utc_ns": int(snapshot.get("as_of_utc_ns") or time.time_ns()),
        "source": snapshot.get("source", "xion-status-publisher"),
        "status": snapshot.get("status", "unknown"),
        "details": snapshot.get("details", {}),
    }


__all__ = [
    "ArweaveStatusPublisher",
    "LocalFileStatusPublisher",
    "StatusPublisher",
    "StatusPublisherSettings",
    "get_status_publisher",
]
