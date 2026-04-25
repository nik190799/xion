"""Provider conformance kit (Phase 6.9).

The registration-time path is deliberately structural and side-effect
free: it must not make live network calls or generate billable tokens.
Deeper round-trip tests can be run in provider-specific suites with
test doubles or operator-supplied credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestrator.inference_router.router import Category


class ProviderConformanceError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderConformanceTestKit:
    tee_required: bool = False

    def assert_registerable(self, provider: Any) -> None:
        provider_id = getattr(provider, "provider_id", None)
        if not isinstance(provider_id, str) or not provider_id:
            raise ProviderConformanceError("provider_id must be a non-empty string")
        category = getattr(provider, "category", None)
        if category not in ("hosted_api", "open_weights_self_hostable", "unknown"):
            raise ProviderConformanceError(f"{provider_id}: invalid category {category!r}")
        if not callable(getattr(provider, "health", None)):
            raise ProviderConformanceError(f"{provider_id}: missing health()")
        # Manifest floor stubs are allowed to register so bootstrap can
        # verify the floor manifest even when the local daemon is not a
        # turn-serving test double. Turn-serving selection still filters
        # on callable(generate).
        is_manifest_stub = type(provider).__name__ == "OpenWeightsFloorStub"
        if category != "unknown" and not is_manifest_stub and not callable(getattr(provider, "generate", None)):
            raise ProviderConformanceError(f"{provider_id}: missing generate()")
        if bool(getattr(provider, "tee_required", False)):
            attestation = getattr(provider, "tee_attestation", None)
            confidential = bool(getattr(provider, "confidential_compute", False))
            if confidential and not attestation:
                raise ProviderConformanceError(
                    f"{provider_id}: confidential_compute providers must expose tee_attestation"
                )

    def assert_generation_result(self, result: Any, *, tee_required: bool = False) -> None:
        for field in (
            "text",
            "model_id",
            "usage_in",
            "usage_out",
            "finish_reason",
            "latency_ms",
            "provider_fingerprint",
            "model_version",
            "reasoning_tokens",
            "cache_hit_ratio",
            "tee_attestation",
        ):
            if not hasattr(result, field):
                raise ProviderConformanceError(f"GenerationResult missing {field}")
        if tee_required and not getattr(result, "tee_attestation", None):
            raise ProviderConformanceError("TEE-required result missing tee_attestation")


def assert_provider_registerable(provider: Any) -> None:
    ProviderConformanceTestKit().assert_registerable(provider)


__all__ = [
    "ProviderConformanceError",
    "ProviderConformanceTestKit",
    "assert_provider_registerable",
]
