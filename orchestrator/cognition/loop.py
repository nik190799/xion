"""Phase 5h/6.9: Bounded agentic loop."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from typing import Any

from orchestrator.inference_router.provider import Message
from orchestrator.tools import PythonToolResolver

from .context import assemble_context
from .hermes.depth import DepthEnforcer
from .journal import Journal
from .retrieval import retrieve_context

_JOURNAL: Journal | None = None
_DEPTH_ENFORCER = DepthEnforcer(max_depth=1)
_TOOL_RESOLVER: PythonToolResolver | None = None


@dataclass(frozen=True)
class CognitionLoopBudget:
    delegation_depth: int = 1
    iteration_count: int = 3
    tool_rounds: int = 3
    reasoning_tokens: int = 4096
    wall_clock_s: float = 8.0


DEFAULT_BUDGET = CognitionLoopBudget()


def chat_cognition_budget() -> CognitionLoopBudget:
    """Live chat budget; env may extend wall-clock for cold local inference.

    ``DEFAULT_BUDGET`` stays pinned for ``xion-verify cognition-loop-bounded``.
    """
    raw = os.environ.get("XION_COGNITION_WALL_S", "").strip()
    if not raw:
        return DEFAULT_BUDGET
    return replace(DEFAULT_BUDGET, wall_clock_s=float(raw))


def run_turn(
    provider: Any,
    prompt: str,
    soul_prompt: str,
    sensorium_snapshot: dict[str, Any] | None,
    max_tokens: int,
    deadline_s: float,
    correlation_id: str,
    principal_id: str = "global",
    budget: CognitionLoopBudget = DEFAULT_BUDGET,
) -> Any:
    """Run a single turn of the agentic loop synchronously."""
    _DEPTH_ENFORCER.check_depth(budget.delegation_depth)
    started = time.monotonic()
    effective_deadline_s = min(deadline_s, budget.wall_clock_s)

    journal = _journal()
    journal.append(correlation_id, "user", prompt, principal_id=principal_id)

    retrieved = retrieve_context(journal, prompt, principal_id=principal_id)
    recent = journal.get_recent(limit=5)

    full_system_prompt = assemble_context(
        soul_prompt=soul_prompt,
        sensorium_snapshot=sensorium_snapshot,
        recent_journal=recent,
        retrieved_context=retrieved,
        user_prompt=prompt,
        correlation_id=correlation_id,
    )

    result = None
    for _iteration in range(budget.iteration_count):
        remaining_s = (
            effective_deadline_s
            if _iteration == 0
            else effective_deadline_s - (time.monotonic() - started)
        )
        if remaining_s <= 0:
            raise TimeoutError("cognition loop wall-clock budget exceeded")
        if callable(getattr(provider, "generate_messages", None)):
            result = provider.generate_messages(
                [
                    Message.text("system", full_system_prompt),
                    Message.text("user", prompt),
                ],
                max_tokens=min(max_tokens, budget.reasoning_tokens),
                tools=_chat_tools()[: budget.tool_rounds],
                response_format={"type": "text"},
                reasoning_effort="high",
                deadline_s=remaining_s,
            )
        else:
            result = provider.generate(
                prompt,
                system=full_system_prompt,
                max_tokens=min(max_tokens, budget.reasoning_tokens),
                deadline_s=remaining_s,
            )
        break

    if result and getattr(result, "text", None):
        journal.append(correlation_id, "xion", result.text, principal_id=principal_id)

    return result

async def stream_run_turn(
    provider: Any,
    prompt: str,
    soul_prompt: str,
    sensorium_snapshot: dict[str, Any] | None,
    max_tokens: int,
    deadline_s: float,
    correlation_id: str,
    stream_generate_func: Any,
    principal_id: str = "global",
    budget: CognitionLoopBudget = DEFAULT_BUDGET,
) -> AsyncIterator[Any]:
    """Async streaming variant of the agentic loop."""
    _DEPTH_ENFORCER.check_depth(budget.delegation_depth)

    journal = _journal()
    journal.append(correlation_id, "user", prompt, principal_id=principal_id)

    retrieved = retrieve_context(journal, prompt, principal_id=principal_id)
    recent = journal.get_recent(limit=5)

    full_system_prompt = assemble_context(
        soul_prompt=soul_prompt,
        sensorium_snapshot=sensorium_snapshot,
        recent_journal=recent,
        retrieved_context=retrieved,
        user_prompt=prompt,
        correlation_id=correlation_id,
    )

    gen = stream_generate_func(
        provider,
        prompt,
        system=full_system_prompt,
        max_tokens=min(max_tokens, budget.reasoning_tokens),
        deadline_s=min(deadline_s, budget.wall_clock_s),
    )

    full_text = []
    async for chunk in gen:
        if isinstance(chunk, str):
            full_text.append(chunk)
        elif getattr(chunk, "text", None):
            full_text.append(chunk.text)
        yield chunk

    if full_text:
        journal.append(correlation_id, "xion", "".join(full_text), principal_id=principal_id)


def _chat_tools() -> list[dict[str, Any]]:
    return [spec.to_oai_compat_tool() for spec in _tool_resolver().list_tools()]


def _journal() -> Journal:
    global _JOURNAL
    if _JOURNAL is None:
        _JOURNAL = Journal()
    return _JOURNAL


def _tool_resolver() -> PythonToolResolver:
    global _TOOL_RESOLVER
    if _TOOL_RESOLVER is None:
        _TOOL_RESOLVER = PythonToolResolver()
    return _TOOL_RESOLVER


__all__ = [
    "DEFAULT_BUDGET",
    "CognitionLoopBudget",
    "chat_cognition_budget",
    "run_turn",
    "stream_run_turn",
]
