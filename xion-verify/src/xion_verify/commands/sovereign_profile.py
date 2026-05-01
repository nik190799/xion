"""Verify the sovereign runtime profile."""

from __future__ import annotations

import importlib
import os
import sys

import click

from xion_verify.exit_codes import FAIL, OK

_DELETED_MODULES: tuple[str, ...] = (
    "orchestrator.safety.providers.openai_moderation",
    "orchestrator.inference_router.providers.openrouter",
)
_CENTRALIZED_ENV: tuple[str, ...] = ("OPENAI_API_KEY", "XION_OPENROUTER_API_KEY")
_ALLOWED_ARBITER_PROVIDERS = {"", "deterministic-stub", "chutes-llm-judge"}


@click.command(name="sovereign-profile")
def sovereign_profile() -> None:
    errors: list[str] = []

    try:
        from orchestrator.profile import current_profile

        profile = current_profile()
    except Exception as exc:
        errors.append(f"profile load failed: {type(exc).__name__}: {exc}")
        profile = None

    for module_name in _DELETED_MODULES:
        try:
            importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
        except ImportError:
            continue
        else:
            errors.append(f"centralized module is importable: {module_name}")

    if profile is not None and profile.name == "sovereign":
        for key in _CENTRALIZED_ENV:
            if os.environ.get(key, "").strip():
                errors.append(f"{key} must be unset in sovereign profile")
        provider = os.environ.get("XION_LLM_ARBITER_PROVIDER", "").strip()
        if provider not in _ALLOWED_ARBITER_PROVIDERS:
            errors.append(
                "XION_LLM_ARBITER_PROVIDER must be deterministic-stub or chutes-llm-judge"
            )
        rpc_urls = [
            item.strip()
            for item in os.environ.get("XION_BASE_RPC_URLS", "").split(",")
            if item.strip()
        ]
        if rpc_urls and len(rpc_urls) < 3:
            errors.append("XION_BASE_RPC_URLS must contain at least 3 endpoints")
        arweave_gateways = [
            item.strip()
            for item in os.environ.get("XION_ARWEAVE_GATEWAYS", "").split(",")
            if item.strip()
        ]
        if arweave_gateways and len(arweave_gateways) < 2:
            errors.append("XION_ARWEAVE_GATEWAYS must contain at least 2 gateways")

    try:
        from orchestrator.inference_router import providers as inference_providers
        from orchestrator.safety import providers as safety_providers  # noqa: F401
    except Exception as exc:
        errors.append(f"provider packages failed import: {type(exc).__name__}: {exc}")
    else:
        if "OpenRouterGenerativeProvider" in getattr(inference_providers, "__all__", ()):
            errors.append("OpenRouterGenerativeProvider remains exported")

    if errors:
        for err in errors:
            click.echo(f"sovereign-profile: FAIL: {err}", err=True)
        sys.exit(FAIL)

    profile_name = profile.name if profile is not None else "unknown"
    click.echo(
        "sovereign-profile: OK "
        f"(profile={profile_name}; centralized provider modules absent)"
    )
    sys.exit(OK)


__all__ = ["sovereign_profile"]
