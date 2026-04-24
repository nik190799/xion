"""Phase 5h: The Cognition Wiring - Agentic Loop."""
from typing import Any, AsyncIterator
from .context import assemble_context
from .journal import Journal
from .retrieval import retrieve_context
from .hermes.depth import DepthEnforcer

_JOURNAL = Journal()
_DEPTH_ENFORCER = DepthEnforcer(max_depth=1)

def run_turn(
    provider: Any,
    prompt: str,
    soul_prompt: str,
    sensorium_snapshot: dict[str, Any] | None,
    max_tokens: int,
    deadline_s: float,
    correlation_id: str,
) -> Any:
    """Run a single turn of the agentic loop synchronously."""
    _DEPTH_ENFORCER.check_depth(1)
    
    _JOURNAL.append(correlation_id, "user", prompt)
    
    retrieved = retrieve_context(_JOURNAL, prompt)
    recent = _JOURNAL.get_recent(limit=5)
    
    full_system_prompt = assemble_context(
        soul_prompt=soul_prompt,
        sensorium_snapshot=sensorium_snapshot,
        recent_journal=recent,
        retrieved_context=retrieved
    )
    
    result = provider.generate(
        prompt,
        system=full_system_prompt,
        max_tokens=max_tokens,
        deadline_s=deadline_s,
    )
    
    if result and getattr(result, "text", None):
        _JOURNAL.append(correlation_id, "xion", result.text)
        
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
) -> AsyncIterator[Any]:
    """Async streaming variant of the agentic loop."""
    _DEPTH_ENFORCER.check_depth(1)
    
    _JOURNAL.append(correlation_id, "user", prompt)
    
    retrieved = retrieve_context(_JOURNAL, prompt)
    recent = _JOURNAL.get_recent(limit=5)
    
    full_system_prompt = assemble_context(
        soul_prompt=soul_prompt,
        sensorium_snapshot=sensorium_snapshot,
        recent_journal=recent,
        retrieved_context=retrieved
    )
    
    gen = stream_generate_func(
        provider,
        prompt,
        system=full_system_prompt,
        max_tokens=max_tokens,
        deadline_s=deadline_s,
    )
    
    full_text = []
    async for chunk in gen:
        if isinstance(chunk, str):
            full_text.append(chunk)
        elif getattr(chunk, "text", None):
            full_text.append(chunk.text)
        yield chunk
        
    if full_text:
        _JOURNAL.append(correlation_id, "xion", "".join(full_text))
