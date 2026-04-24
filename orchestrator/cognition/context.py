"""Phase 5h: The Cognition Wiring - Context Assembly."""
import json
from typing import Any

def assemble_context(
    soul_prompt: str,
    sensorium_snapshot: dict[str, Any] | None,
    recent_journal: list[str],
    retrieved_context: list[str]
) -> str:
    """Assemble the multi-part context window.
    
    The SOUL_PROMPT is structurally guaranteed to be the first element.
    """
    parts = [soul_prompt.strip()]
    
    if sensorium_snapshot:
        parts.append("--- SENSORIUM STATE ---\n" + json.dumps(sensorium_snapshot, indent=2))
        
    if retrieved_context:
        parts.append("--- RETRIEVED MEMORY ---\n" + "\n".join(retrieved_context))
        
    if recent_journal:
        parts.append("--- RECENT JOURNAL ---\n" + "\n".join(recent_journal))
        
    return "\n\n".join(parts)
