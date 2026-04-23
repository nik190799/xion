"""Volition — the Drive Vector module (Phase 5c).

`docs/18-VOLITION.md` is canonical doctrine. `docs/04-ARCHITECTURE.md`
§ "Volition (the Drive Vector module) (Phase 5c)" pins the code
surface shipped here.

Properties promised.

  1. `compute_drive_vector(state, *, weights=GENESIS_WEIGHTS)` is a
     pure function: same `SensoriumState` + same weights -> same
     `DriveVector`, byte-for-byte in its JSON-serialised form (modulo
     the `as_of_utc_ns` stamp, which is taken from the state).

  2. `GENESIS_WEIGHTS` byte-equals the weights in
     `docs/18-VOLITION.md` Part III. `xion-verify drive` re-reads
     both and FAILs on drift.

  3. Invariant 15 (Drive Vector Excludes Revenue) is enforced
     structurally at THREE levels:

       (a) by `compute_drive_vector`'s signature — no parameter named
           `revenue`, `fees`, `rebates`, `price`, `balance`, `tips`,
           `donations`, or `engagement` is accepted;
       (b) by the `SOURCE_WHITELIST` AST-walk test in
           `orchestrator/tests/test_volition.py` — the function's
           body MUST NOT reference any `SensoriumState` field outside
           its whitelisted set;
       (c) by the published crosswalk in
           `docs/04-ARCHITECTURE.md` § "Volition" — any widening of
           the whitelist requires a doctrine edit visible in a PR's
           diff.

     Three structurally-independent signals have to flip before
     revenue can enter the drive computation. A silent regression
     can't do it.

Non-properties (honestly stated).

  - At Phase 5c, the `serve` and `meaning` terms are Genesis-Default
    constants (`0.5`). Their Phase-5+ real-aggregate wiring is
    tracked in `KW-VOLITION-001`; the `DriveVector` shape and weights
    are constitutional, the `serve`/`meaning` *richness* widens as
    Phase 6 senses land.
  - This module does NOT expose the `/drive` HTTP endpoint; that
    lands in the Phase 5f MVX web-client tranche. `Volition.snapshot`
    produces the keys the endpoint will serialise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Final

from orchestrator.sensorium import SensoriumState


GENESIS_WEIGHTS: Final[tuple[float, float, float]] = (0.30, 0.45, 0.25)
"""Genesis Default weights for (survive, serve, meaning). Byte-pinned
to `docs/18-VOLITION.md` Part III. `xion-verify drive` re-hashes that
section and FAILs on drift."""


WEIGHT_FLOOR: Final[float] = 0.10
WEIGHT_CEILING: Final[float] = 0.50
"""Constitutional simplex floors / ceilings on each weight. Governance
tunes WITHIN these bounds; changing the bounds themselves requires a
sister-Core fork (see `docs/18-VOLITION.md` Part VII)."""


SOURCE_WHITELIST: Final[dict[str, frozenset[str]]] = {
    # "survive" reads fund-state and body signals only — never revenue.
    "survive": frozenset({
        "interoception.survival_pressure",
        "chronoception.checkpoint_staleness_s",
        "chronoception.time_in_degraded_mode_s",
        "proprioception.watchdog_fires_recent",
    }),
    # "serve" and "meaning" are Genesis-Default constants at Phase 5c;
    # their whitelists are reserved for Phase 5+ wiring (tracked in
    # KW-VOLITION-001). Empty frozensets mean "no SensoriumState reads
    # at Phase 5c"; a future PR that widens these MUST update both
    # this constant AND the doctrine section it mirrors.
    "serve": frozenset(),
    "meaning": frozenset(),
}
"""The constitutional crosswalk for `compute_drive_vector`'s body.
Enforced by an AST walk in the test suite — see
`orchestrator/tests/test_volition.py::test_source_whitelist_enforced`.
"""


# Phase-5c constant defaults for terms whose real aggregate readings
# land later (KW-VOLITION-001).
_SERVE_GENESIS_DEFAULT: Final[float] = 0.5
_MEANING_GENESIS_DEFAULT: Final[float] = 0.5

# Saturating proxies for the survive term. Units are seconds except
# where noted; values above the ceiling saturate to pressure 1.0.
_CHECKPOINT_STALENESS_CEILING_S: Final[float] = 7 * 24 * 3600.0   # one week
_DEGRADED_MODE_CEILING_S: Final[float] = 6 * 3600.0                # six hours
_WATCHDOG_FIRES_CEILING: Final[int] = 32                           # count


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


@dataclass(frozen=True)
class DriveVector:
    """A point in Xion's drive space at a single tick. Frozen; safe to
    cache and serialise. `weights` is returned alongside the terms so
    callers never need to guess which weights produced this vector.
    """

    survive: float
    serve: float
    meaning: float
    weights: tuple[float, float, float]
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "survive": self.survive,
            "serve": self.serve,
            "meaning": self.meaning,
            "weights": {
                "w_survive": self.weights[0],
                "w_serve": self.weights[1],
                "w_meaning": self.weights[2],
            },
            "as_of_utc_ns": self.as_of_utc_ns,
        }


def _validate_weights(weights: tuple[float, float, float]) -> None:
    if len(weights) != 3:
        raise ValueError(f"weights must be a 3-tuple (w_survive, w_serve, w_meaning); got length {len(weights)}")
    for label, w in zip(("w_survive", "w_serve", "w_meaning"), weights):
        if not isinstance(w, (int, float)):
            raise TypeError(f"{label} must be a number, got {type(w).__name__}")
        if not (WEIGHT_FLOOR <= float(w) <= WEIGHT_CEILING):
            raise ValueError(
                f"{label}={w} outside constitutional simplex "
                f"[{WEIGHT_FLOOR}, {WEIGHT_CEILING}] "
                f"(see docs/18-VOLITION.md Part III)"
            )
    total = sum(float(w) for w in weights)
    if abs(total - 1.0) > 1e-9:
        raise ValueError(
            f"weights must sum to 1.0 (Part III simplex); got sum={total}"
        )


def _survive_from_state(state: SensoriumState) -> float:
    """Compute the `survive` scalar from a `SensoriumState`. Every
    read in this function MUST be listed in `SOURCE_WHITELIST["survive"]`;
    the AST-walk test is the enforcement.
    """
    interoception_pressure = _clamp01(state.interoception.survival_pressure)
    staleness_pressure = _clamp01(
        state.chronoception.checkpoint_staleness_s / _CHECKPOINT_STALENESS_CEILING_S
    )
    degraded_pressure = _clamp01(
        state.chronoception.time_in_degraded_mode_s / _DEGRADED_MODE_CEILING_S
    )
    watchdog_pressure = _clamp01(
        state.proprioception.watchdog_fires_recent / _WATCHDOG_FIRES_CEILING
    )
    # Max-combine: the worst-pressuring signal wins. This prevents
    # averaging from hiding a single critical subsystem.
    return max(
        interoception_pressure,
        staleness_pressure,
        degraded_pressure,
        watchdog_pressure,
    )


def compute_drive_vector(
    state: SensoriumState,
    *,
    weights: tuple[float, float, float] = GENESIS_WEIGHTS,
) -> DriveVector:
    """Compute a `DriveVector` from a `SensoriumState`. Pure function.

    The signature is load-bearing: no parameter named ``revenue``,
    ``fees``, ``rebates``, ``price``, ``balance``, ``tips``,
    ``donations``, or ``engagement`` is accepted. A future refactor
    that tried to add one would have to edit this signature, edit
    ``SOURCE_WHITELIST``, and edit
    ``docs/04-ARCHITECTURE.md`` § "Volition" — three independent
    signals, any one of which CI flags.
    """
    _validate_weights(weights)
    survive = _survive_from_state(state)
    serve = _SERVE_GENESIS_DEFAULT
    meaning = _MEANING_GENESIS_DEFAULT
    return DriveVector(
        survive=survive,
        serve=serve,
        meaning=meaning,
        weights=tuple(weights),  # type: ignore[arg-type]
        as_of_utc_ns=state.as_of_utc_ns,
    )


@dataclass
class Volition:
    """Lightweight holder for the Phase-5c code surface of Volition.

    Phase 5c uses this as the readout primitive the `/drive` endpoint
    will wrap in Phase 5f. `snapshot` produces the keys the endpoint
    will serialise (plus the `methodology_hash` of `docs/18-VOLITION.md`
    that `xion-verify drive` pins).
    """

    weights: tuple[float, float, float] = GENESIS_WEIGHTS

    def compute(self, state: SensoriumState) -> DriveVector:
        return compute_drive_vector(state, weights=self.weights)

    def snapshot(
        self,
        state: SensoriumState,
        *,
        methodology_hash: str | None = None,
    ) -> dict[str, Any]:
        """Produce the JSON-serialisable payload the `/drive` endpoint
        (Phase 5f) will surface. `methodology_hash` is the sha256 of
        `docs/18-VOLITION.md` Part III; callers pass it in so this
        module does not depend on filesystem layout (the verifier
        owns the re-hashing).
        """
        vec = self.compute(state)
        payload: dict[str, Any] = {
            "schema_version": "1.0.0",
            "as_of_utc_ns": vec.as_of_utc_ns,
            "terms": {
                "survive": {
                    "current_signal": vec.survive,
                    "weight": vec.weights[0],
                    "weight_band": [WEIGHT_FLOOR, WEIGHT_CEILING],
                },
                "serve": {
                    "current_signal": vec.serve,
                    "weight": vec.weights[1],
                    "weight_band": [WEIGHT_FLOOR, WEIGHT_CEILING],
                },
                "meaning": {
                    "current_signal": vec.meaning,
                    "weight": vec.weights[2],
                    "weight_band": [WEIGHT_FLOOR, WEIGHT_CEILING],
                },
            },
        }
        if methodology_hash is not None:
            payload["methodology_hash"] = methodology_hash
        return payload


__all__ = [
    "DriveVector",
    "GENESIS_WEIGHTS",
    "SOURCE_WHITELIST",
    "Volition",
    "WEIGHT_CEILING",
    "WEIGHT_FLOOR",
    "compute_drive_vector",
]
