"""Phase 5f HTTP read-only surface — package exports.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The HTTP Surface
(Phase 5f)".

The public surface is deliberately narrow: the app factory and the
deps dataclass. Pydantic response models are re-exported as a
secondary surface for callers that want to validate fixtures or
proxy bodies without spinning up a FastAPI TestClient.

Importing this module pulls FastAPI, uvicorn, and pydantic. Those
live behind the ``[api]`` optional extra in ``pyproject.toml``; a
core-only install (``pip install .``) does NOT install them, and
an accidental top-level import would raise ``ModuleNotFoundError``
early — exactly the signal operators need to install the extra.
"""

from __future__ import annotations

from .app import AppDeps, create_app
from .models import (
    ChatRequest,
    ChatResponse,
    ChronoceptionResponse,
    DistressResponse,
    DriveResponse,
    DriveTerm,
    DriveTerms,
    FiveSliceBreakdown,
    HealthResponse,
    InteroceptionResponse,
    NoFloorEnvelope,
    PaymentChallenge,
    PricingResponse,
    ProprioceptionResponse,
    ProviderErrorEnvelope,
    RefusalEnvelope,
    SensoriumResponse,
    UsageEnvelope,
)
from .pricing import (
    PricingConfig,
    PricingConfigError,
    load_pricing_config_from_env,
)
from .web_client import (
    WebClientConfig,
    WebClientConfigError,
    load_web_client_config_from_env,
)

__all__ = [
    "AppDeps",
    "ChatRequest",
    "ChatResponse",
    "ChronoceptionResponse",
    "DistressResponse",
    "DriveResponse",
    "DriveTerm",
    "DriveTerms",
    "FiveSliceBreakdown",
    "HealthResponse",
    "InteroceptionResponse",
    "NoFloorEnvelope",
    "PaymentChallenge",
    "PricingConfig",
    "PricingConfigError",
    "PricingResponse",
    "ProprioceptionResponse",
    "ProviderErrorEnvelope",
    "RefusalEnvelope",
    "SensoriumResponse",
    "UsageEnvelope",
    "WebClientConfig",
    "WebClientConfigError",
    "create_app",
    "load_pricing_config_from_env",
    "load_web_client_config_from_env",
]
