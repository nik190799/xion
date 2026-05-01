"""Phase 5h/6.9: Context Assembly compatibility wrapper."""

from __future__ import annotations

from typing import Any

from orchestrator.cognition.prompt_composer import IsolatingPromptComposer


def assemble_context(
    soul_prompt: str,
    sensorium_snapshot: dict[str, Any] | None,
    recent_journal: list[str],
    retrieved_context: list[str],
    *,
    user_prompt: str = "",
    correlation_id: str | None = None,
) -> str:
    """Assemble context through the Phase 6.9 isolating composer."""
    return IsolatingPromptComposer().compose(
        soul_prompt=soul_prompt,
        user_prompt=user_prompt,
        sensorium_snapshot=sensorium_snapshot,
        recent_journal=recent_journal,
        retrieved_context=retrieved_context,
        correlation_id=correlation_id,
    )
