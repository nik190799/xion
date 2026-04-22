"""Pydantic response models for the Phase 5f HTTP read-only surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The HTTP Surface
(Phase 5f)".

These models exist to give FastAPI a schema to serialise from (and
OpenAPI a schema to expose) — they do NOT re-express the ledger schemas
in `docs/schemas/`. Ledger schemas are constitutional; HTTP response
shapes are advisory: re-derivable at any time from the underlying
dataclasses (`RelayHealth`, `Volition.snapshot()` dict, `SensoriumState.to_dict()`).

Property promised (verified in ``orchestrator/tests/test_api.py``):
    ``Model.model_validate(<existing dict>).model_dump() == <existing dict>``
for every endpoint. If a future commit adds a field to the underlying
dataclass without updating the matching model here, the round-trip
assertion FAILs, forcing the author to make one of three choices
explicitly:

  1. add the field to the model (legitimate expansion),
  2. strip it at the API boundary (content-free guarantee),
  3. document a deliberate field exception in this module's docstring.

``SensoriumResponse`` also asserts an *explicit field allowlist* in the
test — this is Phase 5f's structural guarantee that the HTTP surface
cannot accidentally leak candidate text, user ids, or any future
content-bearing field added to ``SensoriumState``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------- /health


class HealthResponse(BaseModel):
    """Mirrors ``orchestrator.relay.relay.RelayHealth`` (frozen dataclass).

    Fields are deliberately coarse — booleans and a single rolling
    count — so that ``GET /health`` is an O(1) dict copy of the Relay's
    live counters, not a recomputation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    relay_healthy: bool = Field(
        description=(
            "True iff watchdog_fires_recent is below the Relay's "
            "configured threshold (Genesis Default: 3 fires in 10 minutes)."
        ),
    )
    arbiter_healthy: bool = Field(
        description=(
            "True iff a successful gate() verdict has been observed "
            "within the last arbiter_quiet_window_s (Genesis Default: 60s), "
            "OR the Relay is within bootstrap grace."
        ),
    )
    watchdog_fires_recent: int = Field(
        ge=0,
        description=(
            "Count of wall-clock watchdog timeouts over the rolling "
            "watchdog_fire_window_seconds (Genesis Default: 600s)."
        ),
    )
    as_of_monotonic_ns: int = Field(
        ge=0,
        description=(
            "Monotonic timestamp at snapshot time. Supervisor uses this "
            "to detect stalled Relays (a snapshot whose monotonic age "
            "grows unboundedly means the Relay's health-lock is wedged)."
        ),
    )


# ----------------------------------------------------------------- /drive


class DriveTerm(BaseModel):
    """One of the three Volition drives (survive / serve / meaning)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_signal: float = Field(
        ge=0.0,
        le=1.0,
        description="Saturated [0.0, 1.0] reading for this drive at snapshot time.",
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Current weight in [WEIGHT_FLOOR, WEIGHT_CEILING]. Sum of "
            "three weights is pinned to 1.0 by Invariant 15 (doctrine "
            "source: docs/18-VOLITION.md)."
        ),
    )
    weight_band: tuple[float, float] = Field(
        description=(
            "Constitutional band [floor, ceiling] this weight is pinned "
            "into — constants pinned in orchestrator/volition.py and "
            "validated by xion-verify drive."
        ),
    )


class DriveTerms(BaseModel):
    """The three Volition drive terms, keyed by name."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    survive: DriveTerm
    serve: DriveTerm
    meaning: DriveTerm


class DriveResponse(BaseModel):
    """Mirrors ``orchestrator.volition.Volition.snapshot(state, methodology_hash=...)``.

    schema_version is pinned in ``orchestrator/volition.py`` at "1.0.0";
    the model's default exists so that a round-trip of a v1.0.0 dict
    does not FAIL the round-trip test (pydantic requires all non-default
    fields to be present on ``model_validate``).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(
        description=(
            "Drive-readout schema version. Pinned by orchestrator/volition.py; "
            "a Volition shape change bumps this and breaks the round-trip "
            "test until the pydantic model is bumped in the same commit."
        ),
    )
    as_of_utc_ns: int = Field(
        ge=0,
        description="UTC ns at SensoriumState snapshot time (mirrored from state.as_of_utc_ns).",
    )
    terms: DriveTerms
    methodology_hash: str | None = Field(
        default=None,
        description=(
            "Optional sha256 of docs/18-VOLITION.md Part III. Present iff "
            "the process was constructed with a methodology_hash in AppDeps; "
            "absent otherwise (Phase 5f does NOT compute this on the fly — "
            "the callback responsibility stays with xion-verify drive)."
        ),
    )


# -------------------------------------------------------------- /sensorium


class InteroceptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    survival_pressure: float = Field(ge=0.0, le=1.0)
    treasury_stress: float = Field(ge=0.0, le=1.0)
    cost_pressure: float = Field(ge=0.0, le=1.0)
    as_of_utc_ns: int = Field(ge=0)


class ChronoceptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    as_of_utc_ns: int = Field(ge=0)
    checkpoint_staleness_s: float = Field(ge=0.0)
    time_in_degraded_mode_s: float = Field(ge=0.0)
    monotonic_drift_ns: int


class ProprioceptionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    as_of_utc_ns: int = Field(ge=0)
    relay_healthy: bool
    arbiter_healthy: bool
    watchdog_fires_recent: int = Field(ge=0)


class DistressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text_distress_score: float = Field(ge=0.0, le=1.0)
    source: str = Field(
        description="Enum {textual, paralinguistic}; Phase 5f always writes textual.",
    )
    as_of_utc_ns: int = Field(ge=0)


class SensoriumResponse(BaseModel):
    """Mirrors ``orchestrator.sensorium.sensorium.SensoriumState.to_dict()``.

    Load-bearing property for the Phase 5f content-free guarantee:
    every sub-model is ``extra="forbid"`` — the pydantic layer refuses
    any field the underlying dict carries that this model does not
    explicitly enumerate. A future commit that adds a candidate-text
    field to ``SensoriumState`` breaks the round-trip test first, and
    the field-allowlist test second; both are structural, not promised.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    interoception: InteroceptionResponse
    chronoception: ChronoceptionResponse
    proprioception: ProprioceptionResponse
    distress: DistressResponse
    as_of_utc_ns: int = Field(ge=0)


__all__ = [
    "ChronoceptionResponse",
    "DistressResponse",
    "DriveResponse",
    "DriveTerm",
    "DriveTerms",
    "HealthResponse",
    "InteroceptionResponse",
    "ProprioceptionResponse",
    "SensoriumResponse",
]
