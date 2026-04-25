"""Primary cognition worker: one stateless Hermes-backed turn executor."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from orchestrator.cognition.loop import run_turn as run_agentic_turn
from orchestrator.cognition.subagent import Candidate

if TYPE_CHECKING:
    from orchestrator.cognition.user_context import UserContext


class CognitionWorker:
    """A single interchangeable worker in the pool.

    Property: reports the same constitutional hashes as every sibling worker;
    holds no identity-bearing persistent state across restarts.
    """

    def __init__(
        self,
        worker_id: str,
        *,
        provider: Any | None = None,
        soul_prompt: str = "",
        sensorium_snapshot: dict[str, Any] | None = None,
        max_tokens: int = 2048,
        deadline_s: float = 30.0,
    ) -> None:
        self.worker_id = worker_id
        self.provider = provider
        self.soul_prompt = soul_prompt
        self.sensorium_snapshot = sensorium_snapshot
        self.max_tokens = max_tokens
        self.deadline_s = deadline_s

    async def build_prompt(self, user_ctx: UserContext, user_message: str) -> str:
        """Assemble prompt including Sensorium, doctrinal pins, and journal surfaces."""
        return user_message

    async def run_turn(
        self,
        user_ctx: UserContext,
        user_message: str,
        *,
        provider: Any | None = None,
        correlation_id: str | None = None,
    ) -> Candidate:
        """Execute one user turn through agent runtime; return Candidate for Arbiter."""
        selected_provider = provider or self.provider
        if selected_provider is None:
            raise ValueError("CognitionWorker requires a provider to run a turn")

        prompt = await self.build_prompt(user_ctx, user_message)
        cid = correlation_id or getattr(user_ctx, "correlation_id", None) or f"{self.worker_id}:{uuid4().hex}"
        result = await asyncio.to_thread(
            run_agentic_turn,
            selected_provider,
            prompt,
            self.soul_prompt,
            self.sensorium_snapshot,
            self.max_tokens,
            self.deadline_s,
            cid,
        )
        return Candidate(payload=result, correlation_id=cid)
