"""Hybrid retrieval for ``UserContext`` (vector + keyword + recency)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orchestrator.cognition.user_context import UserContext


class JournalIndex:
    """Content-addressed index over ``RESEARCH_JOURNAL`` and ``BELIEF_LOG`` appends."""

    def rebuild_if_stale(self, max_seconds_since_append: float = 60.0) -> None:
        """Rebuild within the cognition SLA (see docs/24-COGNITION.md)."""
        raise NotImplementedError


def retrieve_for_turn(user_ctx: UserContext, query: str, sensorium_tick: str) -> list[Any]:
    """Ranked snippets for prompt injection; deterministic given pinned index state."""
    raise NotImplementedError
