"""Inference Router: provider taxonomy, manifest, and floor enforcement.

Phase 5g-i extension: ``GenerativeProvider`` / ``GenerationResult`` for
turn-serving providers; ``PolicyMode`` and ``InferenceRouter.select()``
for policy-aware provider selection (see
``docs/26-INFERENCE-POLICY.md``).
"""

from orchestrator.inference_router.provider import (
    GenerationResult,
    GenerativeProvider,
)
from orchestrator.inference_router.router import (
    DEFAULT_POLICY_MODE,
    Category,
    InferenceRouter,
    OpenWeightsFloorStub,
    PolicyMode,
    Provider,
    default_manifest_path,
    load_router,
)

__all__ = [
    "DEFAULT_POLICY_MODE",
    "Category",
    "GenerationResult",
    "GenerativeProvider",
    "InferenceRouter",
    "OpenWeightsFloorStub",
    "PolicyMode",
    "Provider",
    "default_manifest_path",
    "load_router",
]
