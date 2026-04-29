"""Shared FastAPI launcher construction for operator and Chutes boots.

Property: construct the live Relay HTTP surface from one AppDeps path so
operator, local, and Chutes deployments cannot drift into different
dependency shapes.

Invariants touched: strengthens Invariant 17 by letting production boots use
the lifespan's provider loader for Chutes plus the local Ollama floor. No
constitutional state is changed here.

Verification: `pytest orchestrator/tests/test_launcher.py` and the existing
`python -m orchestrator.api` launcher path.

Deprecation: when a richer deployment harness exists, keep this module as the
single app-construction boundary and move only process-management code out.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from orchestrator.billing.config import BillingConfig, load_billing_config_from_env
from orchestrator.inference_router import InferenceRouter
from orchestrator.relay import Relay

from .admission import AdmissionConfig, load_admission_config_from_env
from .app import AppDeps, create_app
from .pricing import PricingConfig, load_pricing_config_from_env
from .web_client import WebClientConfig, load_web_client_config_from_env

_TRUE = frozenset({"1", "true", "t", "yes", "y", "on"})
_FALSE = frozenset({"0", "false", "f", "no", "n", "off"})


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    if raw in _TRUE:
        return True
    if raw in _FALSE:
        return False
    return default


def build_app(
    *,
    relay: Relay | None = None,
    billing_required: bool | None = None,
    require_bearer: bool | None = None,
    admission_overrides: dict[str, Any] | None = None,
    admission_config: AdmissionConfig | None = None,
    billing_config: BillingConfig | None = None,
    pricing_config: PricingConfig | None = None,
    web_client_config: WebClientConfig | None = None,
    router: InferenceRouter | None = None,
    tick_cadence_s: float = 10.0,
    methodology_hash: str | None = None,
    sensorium_ledger_path: Path | None = None,
    chat_deadline_s: float = 30.0,
    cast_pool_on_boot: bool | None = None,
) -> tuple[Relay, FastAPI]:
    """Build the production app and return the Relay it owns.

    The defaults mirror the existing operator launcher: load config from env,
    construct a real in-process Relay, and let the lifespan register Chutes
    and the local floor from the `XION_CHUTES_*` / Ollama environment.
    Optional overrides are test seams and Chutes deployment seams.
    """

    relay = relay or Relay()

    raw_cd = os.environ.get("XION_CHAT_DEADLINE_S", "").strip()
    if raw_cd:
        chat_deadline_s = float(raw_cd)

    if admission_config is None:
        admission_config = load_admission_config_from_env()
    if require_bearer is not None:
        admission_config = replace(admission_config, require_bearer=require_bearer)
    if admission_overrides:
        admission_config = replace(admission_config, **admission_overrides)

    if billing_config is None:
        billing_config = load_billing_config_from_env()
    if billing_required is not None:
        billing_config = replace(billing_config, billing_required=billing_required)

    if pricing_config is None:
        pricing_config = load_pricing_config_from_env()

    if web_client_config is None:
        web_client_config = load_web_client_config_from_env()

    if cast_pool_on_boot is None:
        cast_pool_on_boot = _env_bool("XION_CAST_POOL_ON_BOOT", True)

    deps = AppDeps(
        relay=relay,
        tick_cadence_s=tick_cadence_s,
        methodology_hash=methodology_hash,
        sensorium_ledger_path=sensorium_ledger_path,
        router=router,
        chat_deadline_s=chat_deadline_s,
        pricing_config=pricing_config,
        billing_config=billing_config,
        admission_config=admission_config,
        web_client_config=web_client_config,
        cast_pool_on_boot=cast_pool_on_boot,
    )
    app = create_app(deps)
    app.state.xion_relay = relay
    return relay, app


def create_default_app() -> FastAPI:
    """Factory for `uvicorn.run(..., factory=True)` worker processes."""

    _, app = build_app()
    return app


__all__ = ["build_app", "create_default_app"]
