"""Sub-agent contracts: depth-1 ephemerals; specialists return Candidate only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class Candidate:
    """Non-user-deliverable bundle; only the Arbiter may emit a Response."""

    payload: Any
    correlation_id: str


class EphemeralSubagent:
    """Depth-1 helper spawned by the primary worker for a single turn."""

    max_depth: Literal[1] = 1

    async def run(self, task: str, budget_tokens: int, budget_seconds: float) -> Candidate:
        """Run bounded work; must not write ledgers or spawn further sub-agents."""
        raise NotImplementedError


class SpecialistAgent:
    """Long-lived background agent; writes only to its declared public ledger."""

    name: str

    async def tick(self) -> None:
        """One scheduler invocation; cost-envelope enforced by supervisor."""
        raise NotImplementedError
