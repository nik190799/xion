"""FastAPI factory for the Phase 5f HTTP read-only surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The HTTP Surface (Phase 5f)".

This module is a thin seam — 3 routes, 1 factory, 1 deps dataclass.
No computation lives here beyond a dict/dataclass copy of the
``Supervisor``'s ``latest_snapshot()``. The lifespan does the real
coordination work (see ``orchestrator/api/lifespan.py``).

Property promised. While the FastAPI app is serving (lifespan has
yielded, shutdown has not started):

  - ``GET /health`` returns 200 with the current ``RelayHealth`` shape.
  - ``GET /drive`` returns 200 with ``Volition.snapshot(state, methodology_hash=deps.methodology_hash)``
    where ``state`` is the Supervisor's latest tick.
  - ``GET /sensorium`` returns 200 with ``state.to_dict()`` for the
    same ``state``.

The endpoints never return 503-warming-up: the lifespan pre-seeds the
Supervisor with one synchronous ``tick_once()`` before yielding, so
``latest_snapshot()`` is guaranteed non-``None`` for every request.

Usage (operators):
    uvicorn orchestrator.api.app:create_app --factory

For that call to work, AppDeps must be resolvable with no arguments —
which it is not, by construction (Relay is required). Operators
wishing to run this as a stand-alone server write a small launcher
module that constructs the Relay + AppDeps and calls create_app(deps).
The doctrine refuses to bake an implicit Relay constructor here so
that the factory stays a pure seam.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI

from orchestrator.volition import Volition

from .admission import admission_dependency
from .chat import register_chat_route
from .chat_stream import register_chat_stream_route
from .lifespan import lifespan
from .me import router as me_router
from .memory import router as memory_router
from .presence import router as presence_router
from .models import DriveResponse, HealthResponse, SensoriumResponse, VitalsResponse
from .pricing import register_pricing_route
from .web_client import (
    WebClientConfig,
    load_web_client_config_from_env,
    mount_web_client,
)

if TYPE_CHECKING:
    from orchestrator.billing import BillingConfig
    from orchestrator.inference_router.router import InferenceRouter
    from orchestrator.relay import Relay

    from .admission import AdmissionConfig
    from .pricing import PricingConfig


@dataclass(frozen=True)
class AppDeps:
    """Construction-time dependencies for the Phase 5f FastAPI app.

    Frozen because the app captures a reference at ``create_app`` time
    and the lifespan mutates ``relay._sensorium_source`` — the deps
    themselves must not be rebound mid-flight.

    Fields:
      relay: The in-process ``Relay`` the Supervisor will probe on
        every tick. The lifespan also wires this Relay's
        ``_sensorium_source`` to the Supervisor so in-process
        ``evaluate()`` calls share the same snapshot the HTTP surface
        publishes. Required.

      tick_cadence_s: Passed to the Supervisor. Genesis Default 10.0;
        tests usually pass much smaller values (0.01s) so the run
        loop does not dominate test runtime.

      methodology_hash: Optional sha256 of ``docs/18-VOLITION.md``
        Part III. If provided, ``GET /drive`` includes
        ``methodology_hash`` in its response; if None, the field is
        absent. Operators compute this once at deployment boot (it is
        stable across the lifetime of a Volition spec) and pass it in.

      sensorium_ledger_path: Optional explicit path for the
        SENSORIUM_LEDGER file the Supervisor writes ``tick_commit``
        rows to. If None, the Supervisor resolves it from
        ``XION_SENSORIUM_LEDGER`` env var or the repo default. Tests
        MUST pass this to keep themselves hermetic (the autouse
        conftest fixture redirects the env-var default to tmp_path).
    """

    relay: Relay
    tick_cadence_s: float = 10.0
    methodology_hash: str | None = None
    sensorium_ledger_path: Path | None = None

    # --- Phase 5g-i additions --------------------------------------
    # The Inference Router the lifespan will ``bootstrap()``; if None,
    # the lifespan constructs a default one from
    # ``orchestrator.inference_router.load_router()``. Tests usually
    # pass an explicit one so the provider set is hermetic.
    router: InferenceRouter | None = None
    # Per-turn generation deadline for POST /chat. Genesis Default 30s;
    # tests typically pass smaller values to keep runtime low.
    chat_deadline_s: float = 30.0

    # --- Phase 5g-iii additions ------------------------------------
    # Posted-pricing snapshot the lifespan stashes on
    # ``app.state.pricing_config``. If None, the lifespan constructs it
    # from the ``XION_*`` env vars via
    # ``orchestrator.api.pricing.load_pricing_config_from_env()``. Tests
    # usually pass an explicit one so the posted price is hermetic
    # (the autouse conftest does NOT zero the pricing env vars; tests
    # that want a fixed config pass ``pricing_config=`` explicitly).
    pricing_config: PricingConfig | None = None

    # Billing-surface config the lifespan stashes on
    # ``app.state.billing_config``. Controls whether /chat enforces a
    # commitment, which postures are accepted, the B1 operator shared
    # secret, the PAYMENT_LEDGER file path, and the architecture
    # sha256 anchored into every PAYMENT row. If None, the lifespan
    # constructs it from env vars via
    # ``orchestrator.billing.load_billing_config_from_env()``.
    billing_config: BillingConfig | None = None

    # --- Phase 5g-iv additions -------------------------------------
    # Admission-control config the lifespan stashes on
    # ``app.state.admission_config``. Controls bearer-token gating on
    # /drive, /sensorium, /chat; the per-principal sliding-window
    # rate-limit; the per-IP /health bucket; and the bind-host /
    # TLS knobs the launcher reads. If None, the lifespan constructs
    # it from env vars via
    # ``orchestrator.api.admission.load_admission_config_from_env()``.
    # The autouse conftest fixture sets XION_API_REQUIRE_BEARER=false
    # so existing test suites do not regress; tests that exercise the
    # gate pass an explicit AdmissionConfig here.
    admission_config: AdmissionConfig | None = None

    # --- Phase 5g-v additions --------------------------------------
    # Web-client mount config. Controls whether the FastAPI app mounts
    # the static SPA at /app/* and redirects / to /app/. If None, the
    # factory loads it from env vars via
    # ``orchestrator.api.web_client.load_web_client_config_from_env()``;
    # the env loader defaults to disabled (XION_WEB_CLIENT_ENABLED=false).
    # Tests that want the mount exercised pass an explicit
    # ``WebClientConfig(enabled=True, dist_path=...)`` pointing at a
    # tmp_path-built SPA; tests that do NOT want it pass
    # ``WebClientConfig(enabled=False)`` to skip the env lookup.
    web_client_config: WebClientConfig | None = None


def create_app(deps: AppDeps) -> FastAPI:
    """Construct a FastAPI app wired against ``deps``.

    The app's lifespan owns the Supervisor; the Supervisor is NOT a
    construction-time argument because its lifecycle (pre-seed +
    run() task + stop() on shutdown) is inseparable from the app's
    own lifecycle. Callers that want to reuse a pre-constructed
    Supervisor should write a second factory — not a common case.
    """
    app = FastAPI(
        title="Xion HTTP surface",
        description=(
            "Phase 5f read-only observation endpoints — /health, /drive, "
            "/sensorium — the Phase 5g-i Chat Surface (POST /chat), and "
            "the Phase 5g-iii pricing transparency endpoint (GET /pricing). "
            "Chat billing is pre-authorization-gated under commit 3 of "
            "Phase 5g-iii; until that lands, /pricing is live but /chat "
            "remains the 5g-i no-billing flow. See "
            "docs/04-ARCHITECTURE.md § 'The HTTP Surface (Phase 5f)', "
            "§ 'The Chat Surface (Phase 5g-i)', § 'The Chat Billing Surface "
            "(Phase 5g-iii)', and docs/26-INFERENCE-POLICY.md."
        ),
        version="0.3.0",
        lifespan=lifespan,
    )
    # Expose deps + a Volition singleton to the routes and to the
    # lifespan via ``app.state``. The lifespan attaches ``supervisor``,
    # ``supervisor_task``, ``router``, and the ``no_floor*`` fields to
    # the same namespace; the routes read these at request time.
    app.state.deps = deps
    app.state.volition = Volition()
    app.state.chat_deadline_s = deps.chat_deadline_s
    app.state.soul_prompt = ""

    # Phase 5g-iv admission ordering. ``admission_dependency`` runs
    # 401 → 429 in front of every route below; routes do not need to
    # know whether bearer is required (the dependency consults
    # ``app.state.admission_config`` and short-circuits in the
    # require_bearer=false 5g-i compat mode). The dependency returns
    # the matched ``principal_id`` (or ``"unauth-public"`` for /health
    # and /pricing); routes ignore it at 5g-iv (KW-AUTH-001 closes
    # promotion to PAYMENT_LEDGER in Phase 6).
    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Relay self-reported health (Phase 5f)",
        dependencies=[Depends(admission_dependency)],
    )
    def get_health() -> dict[str, Any]:
        health = deps.relay.health_snapshot()
        return {
            "relay_healthy": health.relay_healthy,
            "arbiter_healthy": health.arbiter_healthy,
            "watchdog_fires_recent": health.watchdog_fires_recent,
            "as_of_monotonic_ns": health.as_of_monotonic_ns,
        }

    @app.get(
        "/drive",
        response_model=DriveResponse,
        # Drop the optional ``methodology_hash`` field entirely when
        # unset, so the HTTP wire shape matches ``Volition.snapshot()``
        # byte-for-byte rather than inserting a spurious
        # ``"methodology_hash": null``.
        response_model_exclude_none=True,
        summary="Volition drive-vector readout (Phase 5f)",
        dependencies=[Depends(admission_dependency)],
    )
    def get_drive() -> dict[str, Any]:
        state = _require_snapshot(app)
        return app.state.volition.snapshot(
            state,
            methodology_hash=deps.methodology_hash,
        )

    @app.get(
        "/sensorium",
        response_model=SensoriumResponse,
        summary="Sensorium senses readout (Phase 5f)",
        dependencies=[Depends(admission_dependency)],
    )
    def get_sensorium() -> dict[str, Any]:
        state = _require_snapshot(app)
        return state.to_dict()

    @app.get(
        "/vitals",
        response_model=VitalsResponse,
        summary="Eight-domain vital signs readout (Phase 6+)",
        dependencies=[Depends(admission_dependency)],
    )
    def get_vitals() -> dict[str, Any]:
        from orchestrator.vitals import get_composite_vitals
        domains = get_composite_vitals()
        return {"domains": [d.__dict__ for d in domains]}

    register_pricing_route(app)
    register_chat_route(app)
    register_chat_stream_route(app)
    app.include_router(me_router)
    app.include_router(memory_router)
    app.include_router(presence_router)
    app.include_router(presence_router)

    # --- Phase 5g-v: optional web-client mount ---------------------
    # Registered last so /app/* cannot shadow any admission-gated API
    # route (FastAPI routes are resolved in registration order). The
    # loader is fail-closed: WebClientConfig.__post_init__ raises if
    # XION_WEB_CLIENT_ENABLED=true but the dist directory / index.html
    # is missing, and the raise propagates out of create_app so the
    # operator sees the failure at startup — not at first /app/ GET.
    if deps.web_client_config is not None:
        web_client_config = deps.web_client_config
    else:
        web_client_config = load_web_client_config_from_env()
    mount_web_client(app, web_client_config)
    app.state.web_client_config = web_client_config

    return app


def _require_snapshot(app: FastAPI) -> Any:
    """Fetch the Supervisor's latest snapshot; raise 500 if absent.

    The lifespan pre-seeds ``latest_snapshot`` via ``tick_once()``
    before yielding, so a ``None`` here is a doctrine-violating bug,
    not an expected state. We fail fast with 500 rather than return
    an empty payload so the bug surfaces immediately in tests and in
    operator logs.
    """
    supervisor = getattr(app.state, "supervisor", None)
    if supervisor is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail="supervisor not wired (lifespan did not run?)",
        )
    state = supervisor.latest_snapshot()
    if state is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=500,
            detail="supervisor has no snapshot (pre-seed tick failed?)",
        )
    return state


__all__ = ["AppDeps", "create_app"]
