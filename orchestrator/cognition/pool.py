"""Sticky-routed worker pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.cognition.worker import CognitionWorker


class WorkerPool:
    """Routes users to workers by ``UserContext.id`` for cache locality only."""

    def __init__(self, workers: list[CognitionWorker]) -> None:
        self._workers = workers

    def route(self, user_context_id: str) -> CognitionWorker:
        """Return the worker sticky for this user; implementation deferred to D2."""
        raise NotImplementedError

    async def broadcast_forget(self, user_context_id: str) -> None:
        """Notify every worker to drop ephemeral caches for this user (Invariant 2)."""
        raise NotImplementedError
