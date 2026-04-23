"""Primary cognition worker: one stateless Hermes-backed turn executor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orchestrator.cognition.user_context import UserContext


class CognitionWorker:
    """A single interchangeable worker in the pool.

    Property: reports the same constitutional hashes as every sibling worker;
    holds no identity-bearing persistent state across restarts.
    """

    def __init__(self, worker_id: str) -> None:
        self.worker_id = worker_id

    async def build_prompt(self, user_ctx: UserContext, user_message: str) -> Any:
        """Assemble prompt including Sensorium, doctrinal pins, and journal surfaces."""
        raise NotImplementedError

    async def run_turn(self, user_ctx: UserContext, user_message: str) -> Any:
        """Execute one user turn through agent runtime; return Candidate for Arbiter."""
        raise NotImplementedError
