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

from typing import Any, Literal

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


# ----------------------------------------------------------------- /vitals


class VitalDomainResponse(BaseModel):
    """One of the eight vital domains from docs/22-VITAL-SIGNS.md."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="The domain name (e.g. 'Financial Vitality').")
    band: Literal["healthy", "warning", "critical", "not_yet_sealed"] = Field(
        description="Current health band or not_yet_sealed for unwired domains."
    )
    reading: float | str | None = Field(
        description="The raw reading value, if applicable."
    )
    methodology_sha256: str = Field(
        description="SHA256 of the frozen methodology doc for this domain."
    )
    subjective: bool = Field(
        description="Whether this domain is subjective (requires >=3 independent corroborating sources before critical)."
    )


class VitalsResponse(BaseModel):
    """Phase 6+ response body for GET /vitals."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    domains: list[VitalDomainResponse] = Field(
        description="The eight vital domains."
    )


# ----------------------------------------------------------------- /self


class SelfResponse(BaseModel):
    """Phase 6.4.b self-knowledge aggregate (topography + sensorium + vitals + governance)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    topography: dict[str, Any] = Field(description="Worker, lineage, inference, and API surface signals.")
    sensorium: dict[str, Any] = Field(description="Latest bus-backed legacy sense projections.")
    vitals: dict[str, Any] = Field(description="Composite vitals (domains list).")
    governance: dict[str, Any] = Field(description="Open KW estimate and roadmap pointers.")
    as_of_utc_ns: int = Field(ge=0, description="Wall clock at assembly time.")


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


MIN_MAX_TOKENS = 1024


class UserProof(BaseModel):
    """Client-side Ed25519 proof of the message.

    If present, the orchestrator MUST verify the signature before processing
    the turn. Malformed or invalid signatures fail-closed with HTTP 400.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_pubkey_b64: str
    signature_b64: str
    algorithm: Literal["ed25519"]


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
        default=2048,
        ge=MIN_MAX_TOKENS,
        le=4096,
        description=(
            "Upper bound on output tokens the generative provider will "
            "produce. Provider-specific tokenisation applies; the bound "
            "is enforced by the provider, not re-enforced here. "
            "The floor is set to 1024 (MIN_MAX_TOKENS) so reasoning-posture "
            "models have room to emit visible content (see docs/26-INFERENCE-POLICY.md)."
        ),
    )
    user_proof: UserProof | None = Field(
        default=None,
        description="Optional client-side Ed25519 proof of the message.",
    )
    transcript_text: str | None = Field(
        default=None,
        min_length=1,
        max_length=16_000,
        description=(
            "Optional user-side STT transcript for voice-enabled turns. "
            "Only consumed when the caller has stream_voice consent; used "
            "to derive paralinguistic Sensorium distress, not persisted."
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
            "(e.g., 'moonshotai/kimi-k2.6', 'gemma3:4b'). Not auditable "
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
    """Phase 5g-i 503 body when no provider served the turn.

    Phase 5g-i emitted only the pre-selection value ``no_healthy_provider``.
    Phase 5g-vii (doctrine anchor: `docs/26-INFERENCE-POLICY.md` § "Provider
    fallback semantics" P4) expands ``reason`` to include the six typed
    failure classes. A ``reason`` value is one of:

      - ``no_healthy_provider``      : pre-selection — ``select_ordered()``
                                       returned an empty list, so no
                                       provider was even attempted.
      - ``insufficient_credits``     : upstream refused for billing.
      - ``rate_limited_upstream``    : upstream rate-limit exceeded.
      - ``provider_unreachable``     : network / gateway failure.
      - ``timeout``                  : per-attempt deadline exceeded.
      - ``moderation_refusal``       : upstream content filter refused.
      - ``unknown_provider_error``   : residual bucket (P5).

    On a multi-attempt turn, the value echoes the ``failure_reason_class``
    of the LAST attempted provider (per P4: single-cause envelope; full
    per-attempt ladder lives in the REQUEST_LEDGER v2 rows sharing the
    turn's ``chat_turn_id``). The client is expected to retry with
    backoff for every class except ``moderation_refusal`` (where retry
    is futile).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: Literal[
        "no_healthy_provider",
        "insufficient_credits",
        "rate_limited_upstream",
        "provider_unreachable",
        "timeout",
        "moderation_refusal",
        "unknown_provider_error",
    ] = Field(
        description=(
            "Pre-selection failure (``no_healthy_provider``) OR the "
            "last attempt's typed ``failure_reason_class``."
        ),
    )
    correlation_id: str = Field(
        description=(
            "Ingress SAFETY_LEDGER correlation_id (ingress moderation "
            "ran before the provider selection failed; the row records "
            "that the user's input was considered even though no "
            "candidate was produced)."
        ),
    )


# -------------------------------------------------------------- /pricing
#
# Phase 5g-iii. Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat
# Billing Surface (Phase 5g-iii)" and ``docs/07-ECONOMY.md`` § "Five-slice
# posted price". Constitutional property: the Relay exposes governance-
# posted pricing with the full five-slice breakdown so a Witness can
# verify the posted price matches the governance record.
#
# The five slices are fractions in [0.0, 1.0] summing to exactly 1.0
# (within ±0.0001 float tolerance). The lifespan validates the sum at
# startup; a misconfigured split refuses to start the app (fail-closed,
# analogous to a broken ledger chain).


class FiveSliceBreakdown(BaseModel):
    """The five-slice decomposition of the posted per-message price.

    Doctrine source: ``docs/07-ECONOMY.md`` § "Five-slice posted price
    (Genesis Defaults)". Each slice is a non-negative fraction; the sum
    of all five equals 1.0. ``xion-verify pricing`` enforces both the
    sum-to-one invariant and the Genesis-Default band for each slice.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    variable_cost: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Trailing-30-day marginal per-message cost (LLM tokens, storage, "
            "bandwidth, incremental Akash). Rolling-average; recomputed weekly."
        ),
    )
    overhead_slice: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Arbiter + Sensorium + Arweave checkpoints + operator salary + "
            "bounties + failover + governance ops, amortized across expected "
            "message volume. Quarterly review."
        ),
    )
    improvement_slice: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Funds the Improvement Fund (Auto-Research Loop executions). "
            "Genesis Default: 0.08 (8%). Non-zero existence is protected "
            "structurally — see docs/21-SUSTAINABILITY.md."
        ),
    )
    reserve_slice: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Funds the Rainy-Day Reserve until 6-12 months runway target; "
            "then redirects per governance. Genesis Default: 0.05 (5%)."
        ),
    )
    small_buffer: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Forecast-error padding. Genesis Default: 0.03-0.05 band; "
            "0.03 at lifespan default."
        ),
    )


class PricingResponse(BaseModel):
    """Phase 5g-iii body for ``GET /pricing`` (HTTP 200).

    Constitutional property: this body is the Relay's verifiable claim
    that the posted per-message price is what governance ratified. A
    Witness dumping this JSON and comparing it to the governance record
    can assert ``xion-verify pricing`` equivalence offline.

    All fields are ``extra="forbid"`` + ``frozen=True``; the content-free
    guarantee is the same structural posture as ``/chat`` envelopes.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    per_message_price_micro_XION: int = Field(
        ge=0,
        description=(
            "Posted per-message price in micro-XION (1 XION = 10^6 "
            "micro-XION). Zero is legal (operator may run promotional "
            "or free-tier pricing); negative is a schema violation."
        ),
    )
    currency_units: Literal["micro_XION"] = Field(
        description=(
            "Unit pin. Genesis Default and 5g-iii-only: micro_XION. "
            "Phase 6+ may add optional USDC-equivalent fields; they "
            "will be additive, never replacing this pin."
        ),
    )
    five_slice: FiveSliceBreakdown = Field(
        description="The decomposition of per_message_price into the five doctrinal slices.",
    )
    modality_costs: dict[str, int] = Field(
        default_factory=dict,
        description="Phase 6.4: Extra cost (in micro_XION) added per-modality (stream_visual, stream_vitals, stream_voice, stream_memory).",
    )
    last_reviewed_utc_ns: int = Field(
        ge=0,
        description=(
            "UTC ns since epoch of the last governance review of this "
            "pricing. Genesis Default at 5g-iii: the lifespan-startup "
            "timestamp. A stale value (exceeding the governance cadence "
            "window, Genesis Default 90 days) is flagged by "
            "xion-verify pricing."
        ),
    )
    governance_revision_id: str = Field(
        min_length=1,
        max_length=128,
        description=(
            "Identifier of the governance vote that ratified this "
            "pricing. Genesis Default at 5g-iii: 'genesis-default-v1'. "
            "Phase 6+ governance rotations bump this to a vote-tx hash."
        ),
    )


# ---------------------------------------------------------- /chat billing
#
# Phase 5g-iii. Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat
# Billing Surface (Phase 5g-iii)" and ``docs/29-BILLING-X402.md``.
#
# These models are landed in commit 2 of 5 (alongside PricingResponse)
# so the full billing-surface pydantic layer is coherent before any
# route code reads them. The ``PaymentChallenge`` body is the 402
# machine-readable challenge returned when ``X-Payment-Commitment`` is
# missing, malformed, or (for postures that verify signatures)
# signature-invalid.


class PaymentChallenge(BaseModel):
    """Phase 5g-iii body for ``POST /chat`` HTTP 402 Payment Required.

    Emitted when the request is missing a valid ``X-Payment-Commitment``
    header in a mode that requires one. The body is machine-readable and
    points the client at ``/pricing`` so it can discover the posted
    price and commit.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    error: Literal["payment_required"] = Field(
        description="Fixed constant. Distinguishes from other 4xx bodies.",
    )
    pricing_url: Literal["/pricing"] = Field(
        description=(
            "Relative URL of the endpoint the client reads to discover "
            "the posted price. Pinned to '/pricing' in 5g-iii; a future "
            "phase that introduces per-skill pricing may extend this."
        ),
    )
    accepted_postures: list[Literal["operator-attest:v1", "x402:v1"]] = Field(
        description=(
            "Commitment-header prefixes the Relay accepts. A client that "
            "cannot produce any of these cannot complete the handshake. "
            "The operator may restrict this list via "
            "XION_BILLING_ALLOW_X402=false (which drops 'x402:v1')."
        ),
    )
    posted_price_micro_XION: int = Field(
        ge=0,
        description=(
            "Governance-posted price at the moment this challenge was "
            "emitted. Mirrors GET /pricing for one-shot clients that "
            "do not want a second round-trip."
        ),
    )
    reason_code: Literal[
        "missing_commitment",
        "malformed_commitment",
        "posture_not_accepted",
        "attestation_signature_invalid",
        "attestation_timestamp_expired",
        "attestation_nonce_replayed",
    ] = Field(
        description=(
            "Enumerated reason the challenge was issued. Non-sensitive "
            "by design (does not echo the malformed header content, "
            "does not reveal operator pubkey state)."
        ),
    )


# ----------------------------------------------------------- /chat/stream
#
# Phase 5g-ii. Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "Streaming
# the Chat Surface (Phase 5g-ii)" + ``docs/32-CHAT-STREAMING.md``.
#
# The streaming transport at ``POST /chat/stream`` returns
# ``text/event-stream`` with each SSE record carrying a JSON body of
# one of three discriminated shapes (``kind ∈ {"chunk","done","error"}``).
# The full response envelope types used INSIDE ``done`` events
# (``ChatResponse``, ``RefusalEnvelope``, ``NoFloorEnvelope``,
# ``ProviderErrorEnvelope``) are the Phase 5g-i surface pinned above —
# no new response shapes are introduced, only a new transport.
#
# Serializing rule: each ``StreamChunkEvent`` / ``StreamDoneEvent`` /
# ``StreamErrorEvent`` goes on the wire as ``data: <model.model_dump_json()>\n\n``.
# The SSE parser on the client side reads up to ``\n\n``, strips the
# leading ``data: `` prefix, parses the JSON, and dispatches on
# ``kind``.


class StreamChunkEvent(BaseModel):
    """One token-slice event emitted as a ``kind="chunk"`` SSE record.

    ``seq`` is a 0-indexed strictly monotonic counter; a non-monotonic
    ``seq`` the client sees is a transport error and the client MUST
    close the stream. The server guarantees monotonicity.

    ``text`` is a literal UTF-8 string — NOT JSON-escaped. Empty
    ``text`` is permitted (the provider emitted a no-op delta) and
    contributes zero bytes to the buffered candidate.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["chunk"] = Field(
        description="Discriminator. Always 'chunk' for this shape.",
    )
    seq: int = Field(
        ge=0,
        description=(
            "0-indexed strictly monotonic sequence number. A well-formed "
            "stream has chunks 0, 1, 2, … in order; non-monotonicity is "
            "a transport error."
        ),
    )
    text: str = Field(
        description=(
            "Literal token-slice text from the provider, UTF-8 encoded. "
            "May be empty (rare; the provider emitted a no-op delta). "
            "The concatenation of all chunks' text equals the final "
            "candidate text that egress moderation evaluates."
        ),
    )


class StreamDoneEvent(BaseModel):
    """Terminal event emitted exactly once per stream as a ``kind="done"`` SSE record.

    Exactly one of ``response`` / ``refusal`` / ``no_floor`` /
    ``provider_error`` is non-null, discriminated by ``verdict``:

      - ``verdict="approve"`` → ``response`` non-null, others null.
      - ``verdict="refuse"``  → ``refusal`` non-null, others null.
      - ``verdict="no_floor"`` → ``no_floor`` non-null, others null.
      - ``verdict="provider_error"`` → ``provider_error`` non-null, others null.
      - ``verdict="cancelled"`` → ALL four null (Phase 5g-ii Commit 3;
        see note below).

    Phase 5g-ii Commit 2 uses four verdicts: approve, refuse, no_floor,
    provider_error. The ``cancelled`` verdict enum value is reserved
    here and used starting in Commit 3 (client-disconnect cancel
    propagation). When a stream is ``cancelled`` on the server side,
    the client has already disconnected, so the server emits NO
    ``done`` event at all — the ``cancelled`` verdict exists only so
    operator-side tooling that replays a server-side stream transcript
    can represent the cancel as a terminal event.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["done"] = Field(
        description="Discriminator. Always 'done' for this shape.",
    )
    verdict: Literal["approve", "refuse", "cancelled", "no_floor", "provider_error"] = Field(
        description=(
            "Terminal verdict. 'approve' + 'refuse' + 'no_floor' + "
            "'provider_error' are wire-emitted in Phase 5g-ii Commit 2. "
            "'cancelled' is reserved for Commit 3 operator-side "
            "replay tooling and is never emitted on the live wire "
            "(a cancelled stream's client is already gone)."
        ),
    )
    response: ChatResponse | None = Field(
        default=None,
        description="Non-null iff verdict='approve'; the moderated ChatResponse.",
    )
    refusal: RefusalEnvelope | None = Field(
        default=None,
        description="Non-null iff verdict='refuse'; the content-free RefusalEnvelope.",
    )
    no_floor: NoFloorEnvelope | None = Field(
        default=None,
        description=(
            "Non-null iff verdict='no_floor'; Invariant-17 floor was "
            "not held when the stream was about to select a provider."
        ),
    )
    provider_error: ProviderErrorEnvelope | None = Field(
        default=None,
        description=(
            "Non-null iff verdict='provider_error'; no registered "
            "provider was healthy, or the provider raised during "
            "generation."
        ),
    )


class StreamErrorEvent(BaseModel):
    """Transport-level error event. Reserved for failures that are
    neither a Covenant refusal nor a structural operational error
    (no-floor / provider-error). In Phase 5g-ii this covers only
    ``deadline_exceeded`` and ``internal`` — the latter is a bug-
    class, logged server-side before emission.

    A client seeing ``kind="error"`` MUST treat the stream as
    terminal; no further events follow.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["error"] = Field(
        description="Discriminator. Always 'error' for this shape.",
    )
    error: Literal["internal", "deadline_exceeded"] = Field(
        description=(
            "Enumerated transport error kind. 'internal' means a "
            "server-side bug (also logged with correlation_id to "
            "stderr); 'deadline_exceeded' means the per-turn deadline "
            "fired before generation completed."
        ),
    )
    correlation_id: str = Field(
        description=(
            "SAFETY_LEDGER correlation_id of the ingress Arbiter call "
            "(which always ran before any error could be emitted). "
            "Lets a Witness join the stream-error with the ingress "
            "moderation row."
        ),
    )


# ----------------------------------------------------------- /admission
#
# Phase 5g-iv. Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The
# Admission-Control Surface (Phase 5g-iv)" + ``docs/30-API-ADMISSION.md``.
#
# These two envelopes are the content-free 401 / 429 bodies the
# ``admission_dependency`` (orchestrator/api/admission.py) emits. They
# carry no echo of the offered header, no hint about which token failed,
# no cardinality leak about the token registry — only the structural
# minimum a well-behaved client needs to retry correctly.
#
# Shape parallels with the 5g-iii billing envelopes: ``error`` is a
# Literal-pinned enum (so a client switching on it cannot break on a
# typo), ``extra="forbid"`` + ``frozen=True`` matches every other
# envelope on this surface.


class AuthChallenge(BaseModel):
    """Phase 5g-iv body for HTTP 401 Unauthorized.

    Emitted when ``Authorization`` is missing, not a Bearer token, or
    does not match any entry in the lifespan-loaded token registry.
    The body is intentionally cardinality-free: it does NOT reveal
    how many tokens the registry holds, does not echo the offered
    token, does not name the rejected principal_id (because no
    principal_id has been authenticated). A scraper learns only
    that the Bearer scheme is accepted; everything else is private.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    error: Literal["unauthorized"] = Field(
        description="Fixed constant. Distinguishes from other 4xx bodies.",
    )
    accepted_schemes: list[Literal["Bearer"]] = Field(
        description=(
            "Authentication schemes the Relay accepts. Pinned to "
            "['Bearer'] in 5g-iv; Phase 6+ that adds Sign-In-With-"
            "Wallet / DID / on-chain pubkey extends this additively."
        ),
    )


class RateLimitChallenge(BaseModel):
    """Phase 5g-iv body for HTTP 429 Too Many Requests.

    Emitted when the per-principal sliding-window bucket overflows
    (``bucket="principal"``) or the per-IP /health bucket overflows
    (``bucket="ip"``). ``retry_after_s`` is the integer-rounded-up
    seconds until the oldest in-window timestamp evicts and a budget
    slot frees; always >= 1 so a polite client does not spin.

    The HTTP response also carries a standard ``Retry-After`` header
    with the same value; the body restates it so non-HTTP-aware
    clients (e.g., a JSON-RPC wrapper) get it without parsing
    headers.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    error: Literal["rate_limited"] = Field(
        description="Fixed constant.",
    )
    retry_after_s: int = Field(
        ge=1,
        description=(
            "Seconds until a budget slot frees in the offending "
            "bucket. Mirrors the ``Retry-After`` HTTP header."
        ),
    )
    bucket: Literal["principal", "ip"] = Field(
        description=(
            "Which bucket overflowed: 'principal' for the per-token "
            "rate-limit on /drive /sensorium /chat; 'ip' for the per-"
            "client-IP /health bucket."
        ),
    )


__all__ = [
    "AuthChallenge",
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
    "PricingResponse",
    "ProprioceptionResponse",
    "ProviderErrorEnvelope",
    "RateLimitChallenge",
    "RefusalEnvelope",
    "SensoriumResponse",
    "StreamChunkEvent",
    "StreamDoneEvent",
    "StreamErrorEvent",
    "UsageEnvelope",
    "VitalDomainResponse",
    "VitalsResponse",
]
