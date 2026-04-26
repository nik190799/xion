"""Phase 5g-i.1 token floor registry.

Doctrine anchor: ``KW-INFER-003`` paydown. Provides per-model min_max_tokens
so reasoning models (e.g. Kimi K2.6) get the breathing room they need without
forcing high budgets onto non-reasoning models.
"""

from __future__ import annotations

# The global fallback if a model is not explicitly registered.
GLOBAL_MIN_MAX_TOKENS = 1024

# Keyed by (provider_id, model_id) -> min_max_tokens
_REGISTRY: dict[tuple[str, str], int] = {
    # Chutes' Kimi K2.6 TEE needs enough room for reasoning-token headroom.
    ("chutes", "moonshotai/Kimi-K2.6-TEE"): 1024,
    ("ChutesGenerativeProvider", "moonshotai/Kimi-K2.6-TEE"): 1024,
    # Local fallback doesn't need as much room for system prompts
    ("ollama", "gemma4:e4b-it-q4_K_M"): 1024,
    ("OllamaGenerativeProvider", "gemma4:e4b-it-q4_K_M"): 1024,
}


def get_min_max_tokens(provider_id: str, model_id: str | None) -> int:
    """Return the minimum max_tokens required by the model.
    
    Falls back to GLOBAL_MIN_MAX_TOKENS if unknown.
    """
    if model_id is None:
        return GLOBAL_MIN_MAX_TOKENS
    return _REGISTRY.get((provider_id, model_id), GLOBAL_MIN_MAX_TOKENS)
