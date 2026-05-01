"""Phase 5g-iii: the ``GET /pricing`` endpoint and its config surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface
(Phase 5g-iii)" and ``docs/07-ECONOMY.md`` § "Five-slice posted price
(Genesis Defaults)". Operational anchor: ``docs/29-BILLING-X402.md``.

This module owns three things:

1. ``PricingConfig`` — an immutable, hash-friendly dataclass that
   captures the five-slice posted price, the governance timestamp, and
   the revision id. It is loaded exactly once at lifespan startup and
   stashed on ``app.state.pricing_config``.

2. ``load_pricing_config_from_env()`` — the env-var loader. Reads
   Genesis Defaults from ``docs/07-ECONOMY.md`` when the operator has
   not posted an override. Raises ``PricingConfigError`` if the five
   slices do not sum to 1.0 within float tolerance — the lifespan
   treats this as fail-closed, analogous to a broken ledger chain.

3. ``register_pricing_route(app)`` — wires the ``GET /pricing``
   handler into the FastAPI app. The handler is a pure read from
   ``app.state.pricing_config``; no I/O, no mutation, no side effects.
   The endpoint is HTTP 200 at all times (billing mode does not gate
   pricing transparency — a D1 operator running in no-billing mode
   still serves ``/pricing`` faithfully).

The Genesis Default five-slice values pinned here match
``docs/07-ECONOMY.md`` verbatim where specified (8% / 5% / 3%) and fill
``variable_cost`` and ``overhead_slice`` at plausible values (40% / 44%)
that sum to 1.0. An operator who wants a different split sets the five
``XION_PRICE_SLICE_*`` env vars; governance rotations happen at the
environment layer in 5g-iii and at a governance-ratified config file
in Phase 6+.

Why a separate module for what is effectively one handler: the handler
is trivial, but the config load + validation is load-bearing (a
misconfigured split must fail-closed at startup, not silently serve
wrong numbers). Splitting it out keeps ``app.py`` a thin seam and lets
``lifespan.py`` import just the loader without pulling route code.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .models import FiveSliceBreakdown, PricingResponse

if TYPE_CHECKING:
    from fastapi import FastAPI


# -- Genesis Defaults -----------------------------------------------------
#
# The three slices with explicit doctrinal numbers
# (``docs/07-ECONOMY.md`` § "Five-slice posted price"):
#
#   improvement_slice  : 0.08  (8%)
#   reserve_slice      : 0.05  (5%)
#   small_buffer       : 0.03  (3%; within the 3-5% Genesis Default band)
#
# variable_cost and overhead_slice sum to the remaining 0.84. Genesis
# Default pins them at 0.40 and 0.44 so neither slice dominates; an
# operator may retune freely via env vars. The point of the pin is that
# the default is self-consistent (sums to 1.0), not that these specific
# values are canonical — the doctrine explicitly marks variable_cost as
# "rolling-average" and overhead_slice as "quarterly review", so any
# fixed number here is a placeholder waiting on governance.

_GENESIS_DEFAULT_VARIABLE_COST = 0.40
_GENESIS_DEFAULT_OVERHEAD_SLICE = 0.44
_GENESIS_DEFAULT_IMPROVEMENT_SLICE = 0.08
_GENESIS_DEFAULT_RESERVE_SLICE = 0.05
_GENESIS_DEFAULT_SMALL_BUFFER = 0.03

# Genesis Default posted price: 1000 micro-XION = 0.001 XION per
# message. Symbolic — an operator at D1 does not yet serve real XION,
# and governance has not ratified a numeric launch price. The number
# exists so the property "every chat turn has a posted price" is
# structurally live at 5g-iii; Phase 6 governance will rotate it to a
# real market-calibrated value under unchanged schema.
_GENESIS_DEFAULT_POSTED_PRICE_MICRO_XION = 1000

# Genesis Default governance revision id. An operator with a real
# governance-ratified price posts the vote-tx hash or the governance-
# proposal id here. Until that exists, this string is the honest marker
# that the price is a pre-governance placeholder.
_GENESIS_DEFAULT_GOVERNANCE_REVISION_ID = "genesis-default-v1"

# Sum-to-one tolerance. Floats summed in any order must hit 1.0 within
# ±1e-4 for the config to validate. 1e-4 is generous against IEEE-754
# rounding (which is O(1e-16) per op) but tight enough to catch an
# operator who typed 0.30 when they meant 0.40.
_SUM_TOLERANCE = 1e-4


class PricingConfigError(ValueError):
    """Raised when a posted pricing config is internally inconsistent.

    The lifespan treats this as fail-closed: the app refuses to start
    rather than serve a ``/pricing`` body that does not sum to 1.0 or
    contains a negative slice. A doctrine-violating price is not a
    warning, it is a constitutional violation.
    """


@dataclass(frozen=True)
class PricingConfig:
    """Immutable pricing snapshot held on ``app.state.pricing_config``.

    Constructed once at lifespan startup by ``load_pricing_config_from_env()``
    and never mutated while the process is live. A governance rotation
    in 5g-iii means restarting the process with new env vars.

    Fields mirror ``PricingResponse`` byte-for-byte; this dataclass is
    the server-side source of truth, ``PricingResponse`` is the wire
    shape. Keeping them separate lets the lifespan validate the config
    (sum-to-one, non-negative slices) without importing pydantic at the
    validation call site.
    """

    per_message_price_micro_XION: int
    variable_cost: float
    overhead_slice: float
    improvement_slice: float
    reserve_slice: float
    small_buffer: float
    modality_costs: dict[str, int]
    last_reviewed_utc_ns: int
    governance_revision_id: str

    def __post_init__(self) -> None:
        if self.per_message_price_micro_XION < 0:
            raise PricingConfigError(
                "per_message_price_micro_XION must be non-negative; "
                f"got {self.per_message_price_micro_XION}."
            )
        for name in (
            "variable_cost",
            "overhead_slice",
            "improvement_slice",
            "reserve_slice",
            "small_buffer",
        ):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise PricingConfigError(
                    f"{name} must be in [0.0, 1.0]; got {value!r}."
                )
        total = (
            self.variable_cost
            + self.overhead_slice
            + self.improvement_slice
            + self.reserve_slice
            + self.small_buffer
        )
        if abs(total - 1.0) > _SUM_TOLERANCE:
            raise PricingConfigError(
                "Five-slice split must sum to 1.0 within "
                f"{_SUM_TOLERANCE}; got {total!r} "
                f"(variable_cost={self.variable_cost}, "
                f"overhead_slice={self.overhead_slice}, "
                f"improvement_slice={self.improvement_slice}, "
                f"reserve_slice={self.reserve_slice}, "
                f"small_buffer={self.small_buffer})."
            )
        if self.last_reviewed_utc_ns < 0:
            raise PricingConfigError(
                "last_reviewed_utc_ns must be non-negative; "
                f"got {self.last_reviewed_utc_ns}."
            )
        rid = self.governance_revision_id
        if not rid or len(rid) > 128:
            raise PricingConfigError(
                "governance_revision_id must be non-empty and "
                f"at most 128 characters; got {rid!r}."
            )

    def to_response(self) -> PricingResponse:
        """Project this config to the wire shape.

        Called by the ``GET /pricing`` handler; kept on the dataclass so
        a future change to the wire shape touches exactly one place.
        """
        return PricingResponse(
            per_message_price_micro_XION=self.per_message_price_micro_XION,
            currency_units="micro_XION",
            five_slice=FiveSliceBreakdown(
                variable_cost=self.variable_cost,
                overhead_slice=self.overhead_slice,
                improvement_slice=self.improvement_slice,
                reserve_slice=self.reserve_slice,
                small_buffer=self.small_buffer,
            ),
            modality_costs=self.modality_costs,
            last_reviewed_utc_ns=self.last_reviewed_utc_ns,
            governance_revision_id=self.governance_revision_id,
        )


def _read_float_env(name: str, default: float) -> float:
    """Read a float from env var ``name``, defaulting to ``default``.

    Raises ``PricingConfigError`` on a malformed value — an operator
    who typed a non-float into a pricing env var is making a config
    error that must fail-closed, not silently fall back to the default.
    Empty / unset falls back quietly.
    """
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise PricingConfigError(
            f"{name} must be a float; got {raw!r}."
        ) from exc


def _read_int_env(name: str, default: int) -> int:
    """Like ``_read_float_env`` but for non-negative ints."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise PricingConfigError(
            f"{name} must be an integer; got {raw!r}."
        ) from exc
    if value < 0:
        raise PricingConfigError(
            f"{name} must be non-negative; got {value}."
        )
    return value


def load_pricing_config_from_env(
    *,
    now_utc_ns: int | None = None,
) -> PricingConfig:
    """Load the posted-pricing config from environment variables.

    Env-var vocabulary (all optional; Genesis Defaults apply when unset):

    - ``XION_POSTED_PRICE_MICRO_XION``      posted per-message price (uint, micro-XION)
    - ``XION_PRICE_SLICE_VARIABLE_COST``    float in [0.0, 1.0]
    - ``XION_PRICE_SLICE_OVERHEAD``         float in [0.0, 1.0]
    - ``XION_PRICE_SLICE_IMPROVEMENT``      float in [0.0, 1.0]
    - ``XION_PRICE_SLICE_RESERVE``          float in [0.0, 1.0]
    - ``XION_PRICE_SLICE_SMALL_BUFFER``     float in [0.0, 1.0]
    - ``XION_MODALITY_COST_VISUAL``         uint, micro-XION (Phase 6.4)
    - ``XION_MODALITY_COST_VITALS``         uint, micro-XION (Phase 6.4)
    - ``XION_MODALITY_COST_VOICE``          uint, micro-XION (Phase 6.4)
    - ``XION_PRICING_LAST_REVIEWED_UTC_NS`` uint ns-since-epoch (default: now)
    - ``XION_PRICING_REVISION_ID``          string ≤ 128 chars

    The ``now_utc_ns`` kwarg is a test seam: tests pin the default
    ``last_reviewed_utc_ns`` value so the assertions are deterministic.
    Production callers leave it ``None`` and get ``time.time_ns()``.

    Raises ``PricingConfigError`` on any malformed value or on a
    five-slice sum that does not hit 1.0 within tolerance. The lifespan
    catches this and refuses to start.
    """
    variable_cost = _read_float_env(
        "XION_PRICE_SLICE_VARIABLE_COST",
        _GENESIS_DEFAULT_VARIABLE_COST,
    )
    overhead_slice = _read_float_env(
        "XION_PRICE_SLICE_OVERHEAD",
        _GENESIS_DEFAULT_OVERHEAD_SLICE,
    )
    improvement_slice = _read_float_env(
        "XION_PRICE_SLICE_IMPROVEMENT",
        _GENESIS_DEFAULT_IMPROVEMENT_SLICE,
    )
    reserve_slice = _read_float_env(
        "XION_PRICE_SLICE_RESERVE",
        _GENESIS_DEFAULT_RESERVE_SLICE,
    )
    small_buffer = _read_float_env(
        "XION_PRICE_SLICE_SMALL_BUFFER",
        _GENESIS_DEFAULT_SMALL_BUFFER,
    )
    posted_price = _read_int_env(
        "XION_POSTED_PRICE_MICRO_XION",
        _GENESIS_DEFAULT_POSTED_PRICE_MICRO_XION,
    )
    modality_costs = {
        "stream_visual": _read_int_env("XION_PRICE_VISUAL_MICRO_XION", 0),
        "stream_vitals": _read_int_env("XION_PRICE_VITALS_MICRO_XION", 0),
        "stream_voice": _read_int_env("XION_PRICE_VOICE_MICRO_XION", 0),
        "stream_memory": _read_int_env("XION_PRICE_MEMORY_MICRO_XION", 0),
    }
    if now_utc_ns is None:
        now_utc_ns = time.time_ns()
    last_reviewed = _read_int_env(
        "XION_PRICING_LAST_REVIEWED_UTC_NS",
        now_utc_ns,
    )
    revision_id = os.environ.get(
        "XION_PRICING_REVISION_ID",
        _GENESIS_DEFAULT_GOVERNANCE_REVISION_ID,
    ).strip() or _GENESIS_DEFAULT_GOVERNANCE_REVISION_ID

    return PricingConfig(
        per_message_price_micro_XION=posted_price,
        variable_cost=variable_cost,
        overhead_slice=overhead_slice,
        improvement_slice=improvement_slice,
        reserve_slice=reserve_slice,
        small_buffer=small_buffer,
        modality_costs=modality_costs,
        last_reviewed_utc_ns=last_reviewed,
        governance_revision_id=revision_id,
    )


def register_pricing_route(app: FastAPI) -> None:
    """Wire ``GET /pricing`` into ``app``.

    Reads ``app.state.pricing_config`` (populated by the lifespan) and
    projects it to ``PricingResponse``. No billing mode gate: the
    endpoint is constitutionally free and public per
    ``docs/04-ARCHITECTURE.md`` § "The Chat Billing Surface" — the
    operator posting a price owes the world the transparency to read it.

    Phase 5g-iv: ``admission_dependency`` runs in front but matches
    ``/pricing`` against ``_PUBLIC_ROUTES`` and short-circuits without
    any auth or rate-limit check; the dependency is wired in defense-
    in-depth so a future route added without ``Depends(admission_dependency)``
    is structurally distinguishable from a deliberately-public route.
    """
    from fastapi import Depends

    from .admission import admission_dependency

    @app.get(
        "/pricing",
        response_model=PricingResponse,
        summary="Governance-posted per-message price (Phase 5g-iii)",
        dependencies=[Depends(admission_dependency)],
    )
    def get_pricing() -> dict[str, Any]:
        config: PricingConfig | None = getattr(
            app.state, "pricing_config", None
        )
        if config is None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=500,
                detail="pricing_config not wired (lifespan did not run?)",
            )
        return config.to_response().model_dump()


__all__ = [
    "PricingConfig",
    "PricingConfigError",
    "load_pricing_config_from_env",
    "register_pricing_route",
]
