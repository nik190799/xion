"""Per-user context handle (not identity); loaded from USER-scoped storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class UserContext:
    """Sticky routing key plus layered memory assembly inputs.

    Episodic and semantic layers honor ``genesis/MEMORY.md`` and ``/forget`` SLA.
    """

    id: str
    consent_scopes: frozenset[str]

    def load_layers(self) -> dict[str, Any]:
        """Return episodic, semantic, and doctrinal slices for retrieval."""
        raise NotImplementedError
