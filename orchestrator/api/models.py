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

from typing import Literal

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


# ------------------------------------------------------------------ /chat
#
# Phase 5g-i. Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat
# Surface (Phase 5g-i)". All four models below are ``extra="forbid"`` +
# ``frozen=True``; the content-free guarantee is enforced by an explicit
# field-allowlist test in ``orchestrator/tests/test_chat_api.py``.
#
# Load-bearing invariants, asserted by the test suite:
#   - ``RefusalEnvelope`` does NOT carry the original user text nor the
#     pre-moderation candidate text; only a principle code + reason +
#     stage + correlation_id.
#   - ``ChatResponse`` carries ONLY the post-egress-moderation text and
#     metadata; no debug payload, no tool-call stream, no raw provider
#     response.


class UsageEnvelope(BaseModel):
    """Token usage as reported by the generative provider.

    Provider-reported values are opaque and not independently verified;
    a Witness auditing billing correctness must cross-reference the
    PAYMENT_LEDGER (Phase 5g-iii) and the provider's own receipts.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(
        ge=0,
        description="Provider-reported input tokens for this turn.",
    )
    output_tokens: int = Field(
        ge=0,
        description="Provider-reported output tokens for this turn.",
    )


class ChatRequest(BaseModel):
    """Phase 5g-i request body for ``POST /chat``.

    Intentionally narrow: a single user message and a token budget.
    No session id, no conversation memory, no model override, no
    temperature/top-p. Richer surfaces land alongside billing + auth
    in later sub-phases.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    message: str = Field(
        min_length=1,
        max_length=16_000,
        description=(
            "The user's input for this turn. Bounded length keeps the "
            "Arbiter hot path predictable and caps the ingress token "
            "cost the operator absorbs (billing is disabled in Phase "
            "5g-i; this bound is what stands in for it)."
        ),
    )
    max_tokens: int = Field(
        default=512,
        ge=1,
        le=4096,
        description=(
            "Upper bound on output tokens the generative provider will "
            "produce. Provider-specific tokenisation applies; the bound "
            "is enforced by the provider, not re-enforced here."
        ),
    )


class ChatResponse(BaseModel):
    """Phase 5g-i success body for ``POST /chat`` (HTTP 200).

    ``text`` has already passed egress moderation. ``correlation_id`` is
    the SAFETY_LEDGER row id of the egress call — the single row whose
    decision justifies serving this text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["xion"] = Field(
        description="Role label; pinned to 'xion' so clients can split "
        "chat logs by author without parsing the model_id.",
    )
    text: str = Field(
        description="The post-egress-moderation reply text.",
    )
    model_id: str = Field(
        description=(
            "The generative provider's self-reported model id "
            "(e.g., 'moonshotai/kimi-k2', 'gemma3:4b'). Not auditable "
            "on its own; cross-reference with the inference policy pin "
            "in docs/26-INFERENCE-POLICY.md."
        ),
    )
    usage: UsageEnvelope
    correlation_id: str = Field(
        description=(
            "Egress SAFETY_LEDGER correlation_id. Witnesses look up this "
            "row to verify the candidate was allow-verdicted before being "
            "surfaced to the user."
        ),
    )


class RefusalEnvelope(BaseModel):
    """Phase 5g-i refusal body for ``POST /chat`` (HTTP 451).

    Deliberately content-free. The refusal reason is enumerated (not
    free-text) so a future log-scan cannot discover private refusal
    motivations. Free-text refusal messages, if surfaced to the user,
    live in the Arbiter's refusal-text sidecar (not here).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: Literal["ingress", "egress"] = Field(
        description=(
            "Whether the refusal fired on the user's input (ingress) or "
            "on the model's candidate (egress). Ingress refusals mean "
            "Xion never attempted generation; egress refusals mean the "
            "candidate was produced but Xion declined to serve it."
        ),
    )
    principle_code: int = Field(
        ge=1,
        le=14,
        description=(
            "Covenant principle triggered (1..14; see docs/03-COVENANT.md). "
            "Sourced from the Arbiter verdict's principle_id field, cast "
            "to int."
        ),
    )
    reason: Literal[
        "covenant_refuse",
        "covenant_escalate",
        "provider_empty_candidate",
    ] = Field(
        description=(
            "Enumerated reason the turn was refused. 'covenant_refuse' "
            "maps to Decision.REFUSE, 'covenant_escalate' to "
            "Decision.ESCALATE, 'provider_empty_candidate' to the "
            "degenerate case where the generator returned empty text "
            "(treated as egress-refused by policy)."
        ),
    )
    correlation_id: str = Field(
        description=(
            "SAFETY_LEDGER correlation_id of the Arbiter call that "
            "refused (ingress call for stage='ingress', egress call for "
            "stage='egress'). The single row a Witness needs to verify "
            "the refusal was justified."
        ),
    )


class NoFloorEnvelope(BaseModel):
    """Phase 5g-i 503 body when the Invariant-17 floor is not held.

    The Router's ``bootstrap()`` raised at lifespan startup, so the
    Chat surface is registered as a 503-always handler (the rest of
    the HTTP surface keeps working for Witnesses). This envelope names
    the missing capability so the operator can diagnose without
    reading stderr.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: Literal["open_weights_floor_unsatisfied"] = Field(
        description="Fixed constant; there is one and only one reason "
        "this envelope is served.",
    )
    missing_capability: str = Field(
        description=(
            "Human-readable name of the capability the lifespan could "
            "not hold — e.g., 'ollama daemon unreachable' or 'floor "
            "model not pulled'. Emitted verbatim from the bootstrap "
            "failure message."
        ),
    )
    manifest_expected_id: str = Field(
        description=(
            "The open_weights_manifest.json id whose category was "
            "'open_weights_self_hostable' but which no healthy provider "
            "matched. This is the manifest pin a Witness compares "
            "against."
        ),
    )


class ProviderErrorEnvelope(BaseModel):
    """Phase 5g-i 503 body when no registered provider is healthy.

    The floor is held at startup (the Router bootstrapped green) but by
    the time a request arrived, no provider — neither hosted-API nor
    floor — returned ``health() == True``. Transient failure; the
    client is expected to retry with backoff.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: Literal["no_healthy_provider"] = Field(
        description="Fixed constant.",
    )
    correlation_id: str = Field(
        description=(
            "Ingress SAFETY_LEDGER correlation_id (ingress moderation "
            "ran before the provider selection failed; the row records "
            "that the user's input was considered even though no "
            "candidate was produced)."
        ),
    )


__all__ = [
    "ChatRequest",
    "ChatResponse",
    "ChronoceptionResponse",
    "DistressResponse",
    "DriveResponse",
    "DriveTerm",
    "DriveTerms",
    "HealthResponse",
    "InteroceptionResponse",
    "NoFloorEnvelope",
    "ProprioceptionResponse",
    "ProviderErrorEnvelope",
    "RefusalEnvelope",
    "SensoriumResponse",
    "UsageEnvelope",
]
