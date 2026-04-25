"""``POST /chat`` handler (Phase 5g-i + 5g-iii).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Surface
(Phase 5g-i)" and § "The Chat Billing Surface (Phase 5g-iii)", plus
``docs/29-BILLING-X402.md`` and ``docs/26-INFERENCE-POLICY.md``.

Handler flow (5g-iii shape):

    commitment gate (402 on missing/malformed/invalid)
    ingress moderation (451 on refuse)
    floor check     (503 no_floor on unsatisfied)
    provider selection (503 no_healthy_provider on failure)
    generation (deadline-bounded)
    empty-candidate check (451 on empty)
    egress moderation (451 on refuse)
    200 success

Every terminal path flows through a single ``_finalize`` tail that:

  1. Writes exactly one PAYMENT_LEDGER row with the appropriate
     ``outcome`` (settled | refunded) and money split (settled /
     refunded).
  2. Sends the HTTP response.

Atomicity contract: the ledger append happens BEFORE the response is
sent, so a process crash between the two leaves a ledger row but no
response (auditable via side-channel), while a crash before the append
leaves neither (also auditable — no commitment recorded). The ledger
never records a commitment without a terminal outcome.

Backward compatibility: if ``billing_config.billing_required`` is
False, the handler skips the commitment gate and runs the 5g-i flow
unchanged — but still writes a PAYMENT_LEDGER row with
``posture="disabled"`` and zero money so the SAFETY ↔ PAYMENT join
remains structurally checkable.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Header, Response
from fastapi.responses import JSONResponse

from orchestrator.billing import (
    Commitment,
    CommitmentRejectReason,
    append_payment_row,
    parse_commitment_header,
    verify_b1_attestation,
    verify_b2_x402_shape,
)
from orchestrator.inference_router.provider import (
    ProviderError,
    ProviderTimeoutError,
    UnknownProviderError,
)
from orchestrator.relay.ledger import (
    ProviderAttemptRecord,
    append_provider_attempt,
)

from .models import (
    MIN_MAX_TOKENS,
    ChatRequest,
    ChatResponse,
    NoFloorEnvelope,
    PaymentChallenge,
    ProviderErrorEnvelope,
    RefusalEnvelope,
    UsageEnvelope,
)

if TYPE_CHECKING:
    from orchestrator.billing import BillingConfig
    from orchestrator.inference_router.provider import (
        GenerationResult,
        GenerativeProvider,
    )
    from orchestrator.relay.relay import RelayResult

    from .pricing import PricingConfig


_DEFAULT_DEADLINE_S = 30.0


@dataclass(frozen=True)
class _Outcome:
    """Terminal state of a chat turn. Consumed by ``_finalize`` to
    build the PAYMENT row and the HTTP response in one step."""

    http_status: int
    body: dict[str, Any]
    outcome: str  # "settled" | "refunded"
    refusal_stage: str | None
    correlation_id: str
    provider_id: str | None
    model_id: str | None
    user_proof_commit: str | None = None
    user_proof_algorithm: str | None = None


def register_chat_route(app: FastAPI) -> None:
    """Register ``POST /chat`` on ``app``.

    Phase 5g-iv: ``admission_dependency`` runs in front of this route
    to enforce 401 (missing/bad bearer) and 429 (per-principal rate
    limit) before the existing 402 (payment commitment) gate. The
    constitutional ordering is ``401 → 429 → 402``: auth before
    rate-limit (so the bucket is per-token, not per-IP); rate-limit
    before payment (so an unauthenticated scraper cannot probe
    pricing-validity by spamming 402-bait requests).
    """
    from fastapi import Depends

    from .admission import admission_dependency

    @app.post(
        "/chat",
        response_model=None,
        summary=(
            "Single-turn chat, moderated on both sides + bearer/rate "
            "admission + x402 pre-auth (Phase 5g-i + 5g-iii + 5g-iv)"
        ),
    )
    async def post_chat(
        req: ChatRequest,
        principal_id: str = Depends(admission_dependency),
        x_payment_commitment: str | None = Header(None, alias="X-Payment-Commitment"),
    ) -> Response:
        deps = app.state.deps
        relay = deps.relay
        pricing_config: PricingConfig = app.state.pricing_config
        billing_config: BillingConfig = app.state.billing_config

        deadline_s = float(getattr(app.state, "chat_deadline_s", _DEFAULT_DEADLINE_S))

        user_proof_commit = None
        user_proof_algorithm = None
        if req.user_proof is not None:
            from orchestrator.cognition.user_proof import verify_ed25519_proof, compute_proof_commit, InvalidSignatureError
            try:
                verify_ed25519_proof(
                    req.user_proof.user_pubkey_b64,
                    req.user_proof.signature_b64,
                    req.message,
                )
            except InvalidSignatureError as e:
                return JSONResponse(status_code=400, content={"error": "invalid_user_proof", "detail": str(e)})
            
            user_proof_commit = compute_proof_commit(req.user_proof.user_pubkey_b64, req.message)
            user_proof_algorithm = req.user_proof.algorithm

        # -- 1. Commitment gate -------------------------------------
        body_sha256 = _sha256_text(req.message)
        posted_price = pricing_config.per_message_price_micro_XION

        commitment, challenge = _gate_commitment(
            raw_header=x_payment_commitment,
            billing_config=billing_config,
            posted_price=posted_price,
            body_sha256=body_sha256,
            now_utc_ns=time.time_ns(),
        )
        if challenge is not None:
            return JSONResponse(
                status_code=402,
                content=challenge.model_dump(),
            )

        # -- 2. Ingress moderation ---------------------------------
        voice_sensorium_state = _voice_sensorium_state(
            app,
            req=req,
            principal_id=principal_id,
        )
        ingress = await asyncio.to_thread(
            relay.evaluate,
            req.message,
            sensorium_state=voice_sensorium_state,
            user_proof_commit=user_proof_commit,
            user_proof_algorithm=user_proof_algorithm,
        )
        if not ingress.egress_allowed:
            body_obj = _refusal_body(ingress, stage="ingress")
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=451,
                    body=body_obj.model_dump(),
                    outcome="refunded",
                    refusal_stage="ingress",
                    correlation_id=ingress.correlation_id,
                    provider_id=None,
                    model_id=None,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        # -- 3. Floor check ----------------------------------------
        if getattr(app.state, "no_floor", False):
            body = NoFloorEnvelope(
                reason="open_weights_floor_unsatisfied",
                missing_capability=str(
                    getattr(app.state, "no_floor_reason", "unknown")
                ),
                manifest_expected_id=str(
                    getattr(app.state, "no_floor_manifest_id", "unknown")
                ),
            )
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=503,
                    body=body.model_dump(),
                    outcome="refunded",
                    refusal_stage="no_floor",
                    correlation_id=ingress.correlation_id,
                    provider_id=None,
                    model_id=None,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        # -- 4. Provider selection + fallback loop (Phase 5g-vii) ---
        #
        # Doctrine anchor: docs/26-INFERENCE-POLICY.md § "Provider
        # fallback semantics" P1/P2/P3. The handler iterates the full
        # policy-legal attempt order from ``InferenceRouter.select_ordered()``
        # and, for each attempt, writes exactly one REQUEST_LEDGER v2
        # row tagged with the turn's ``chat_turn_id``. A successful
        # attempt short-circuits the loop; a typed ProviderError is
        # classified and the loop continues. When the ordered list is
        # exhausted, the handler surfaces the last failure's typed
        # class (P4).
        router = getattr(app.state, "router", None)
        ordered: list["GenerativeProvider"] = (
            router.select_ordered() if router is not None else []
        )
        ordered = [
            p for p in ordered if callable(getattr(p, "generate", None))
        ]

        if not ordered:
            body_pe = ProviderErrorEnvelope(
                reason="no_healthy_provider",
                correlation_id=ingress.correlation_id,
            )
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=503,
                    body=body_pe.model_dump(),
                    outcome="refunded",
                    refusal_stage="provider_error",
                    correlation_id=ingress.correlation_id,
                    provider_id=None,
                    model_id=None,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        chat_turn_id = secrets.token_hex(16)
        request_ledger_path = _request_ledger_path(app)
        relay_id = _relay_id(app)
        ingress_state_height = _state_height_from_correlation(ingress.correlation_id)

        last_failure_class: str = "unknown_provider_error"
        last_provider_id: str | None = None
        result: "GenerationResult | None" = None
        provider_id: str | None = None

        from orchestrator.inference_router.model_registry import get_min_max_tokens

        for attempt_index, provider in enumerate(ordered):
            provider_id = (
                getattr(provider, "provider_id", None) or type(provider).__name__
            )
            model_id_configured = getattr(provider, "model", None)
            effective_max_tokens = max(
                req.max_tokens,
                get_min_max_tokens(provider_id, model_id_configured),
            )
            last_provider_id = provider_id

            attempt_started_ns = time.time_ns()
            try:
                from orchestrator.cognition.loop import run_turn
                
                supervisor = getattr(app.state, "supervisor", None)
                snapshot_dict = supervisor.latest_snapshot().to_dict() if supervisor and supervisor.latest_snapshot() else None
                
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        run_turn,
                        provider,
                        req.message,
                        app.state.soul_prompt,
                        snapshot_dict,
                        effective_max_tokens,
                        deadline_s,
                        ingress.correlation_id,
                    ),
                    timeout=deadline_s,
                )
            except (TimeoutError, asyncio.TimeoutError) as exc:
                failure_class = (
                    exc.failure_reason_class
                    if isinstance(exc, ProviderError)
                    else ProviderTimeoutError.failure_reason_class
                )
                last_failure_class = failure_class
                _write_attempt_row(
                    path=request_ledger_path,
                    correlation_id=ingress.correlation_id,
                    state_height=ingress_state_height,
                    relay_id=relay_id,
                    request_arrived_utc_ns=attempt_started_ns,
                    chat_turn_id=chat_turn_id,
                    attempt_index=attempt_index,
                    provider_id=provider_id,
                    outcome="failure",
                    failure_reason_class=failure_class,
                )
                continue
            except ProviderError as exc:
                last_failure_class = exc.failure_reason_class
                _write_attempt_row(
                    path=request_ledger_path,
                    correlation_id=ingress.correlation_id,
                    state_height=ingress_state_height,
                    relay_id=relay_id,
                    request_arrived_utc_ns=attempt_started_ns,
                    chat_turn_id=chat_turn_id,
                    attempt_index=attempt_index,
                    provider_id=provider_id,
                    outcome="failure",
                    failure_reason_class=exc.failure_reason_class,
                )
                continue
            except Exception:
                last_failure_class = UnknownProviderError.failure_reason_class
                _write_attempt_row(
                    path=request_ledger_path,
                    correlation_id=ingress.correlation_id,
                    state_height=ingress_state_height,
                    relay_id=relay_id,
                    request_arrived_utc_ns=attempt_started_ns,
                    chat_turn_id=chat_turn_id,
                    attempt_index=attempt_index,
                    provider_id=provider_id,
                    outcome="failure",
                    failure_reason_class=last_failure_class,
                )
                continue

            # Success: the provider returned a GenerationResult. An
            # empty candidate is handled below (egress-refused by
            # convention); for the REQUEST_LEDGER v2 row it is still
            # recorded as a successful provider attempt — the Arbiter
            # is what refuses the candidate, not the provider.
            _write_attempt_row(
                path=request_ledger_path,
                correlation_id=ingress.correlation_id,
                state_height=ingress_state_height,
                relay_id=relay_id,
                request_arrived_utc_ns=attempt_started_ns,
                chat_turn_id=chat_turn_id,
                attempt_index=attempt_index,
                provider_id=provider_id,
                outcome="success",
                failure_reason_class=None,
            )
            break

        if result is None:
            body_pe = ProviderErrorEnvelope(
                reason=last_failure_class,  # type: ignore[arg-type]
                correlation_id=ingress.correlation_id,
            )
            refusal_stage = (
                "provider_timeout"
                if last_failure_class == "timeout"
                else "provider_error"
            )
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=503,
                    body=body_pe.model_dump(),
                    outcome="refunded",
                    refusal_stage=refusal_stage,
                    correlation_id=ingress.correlation_id,
                    provider_id=last_provider_id,
                    model_id=None,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        model_id = getattr(result, "model_id", None)

        if not result.text:
            body_ref = RefusalEnvelope(
                stage="egress",
                principle_code=3,
                reason="provider_empty_candidate",
                correlation_id=ingress.correlation_id,
            )
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=451,
                    body=body_ref.model_dump(),
                    outcome="refunded",
                    refusal_stage="empty_candidate",
                    correlation_id=ingress.correlation_id,
                    provider_id=provider_id,
                    model_id=model_id,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        # -- 6. Egress moderation ----------------------------------
        egress = await asyncio.to_thread(relay.evaluate, result.text)
        if not egress.egress_allowed:
            body_obj = _refusal_body(egress, stage="egress")
            return _finalize(
                app,
                commitment,
                _Outcome(
                    http_status=451,
                    body=body_obj.model_dump(),
                    outcome="refunded",
                    refusal_stage="egress",
                    correlation_id=egress.correlation_id,
                    provider_id=provider_id,
                    model_id=model_id,
                    user_proof_commit=user_proof_commit,
                    user_proof_algorithm=user_proof_algorithm,
                ),
            )

        # -- 7. Success --------------------------------------------
        ok = ChatResponse(
            role="xion",
            text=result.text,
            model_id=result.model_id,
            usage=UsageEnvelope(
                input_tokens=result.usage_in,
                output_tokens=result.usage_out,
            ),
            correlation_id=egress.correlation_id,
        )
        return _finalize(
            app,
            commitment,
            _Outcome(
                http_status=200,
                body=ok.model_dump(),
                outcome="settled",
                refusal_stage=None,
                correlation_id=egress.correlation_id,
                provider_id=provider_id,
                model_id=model_id,
            ),
        )


# ---------------------------------------------------------- commitment gate


def _gate_commitment(
    *,
    raw_header: str | None,
    billing_config: "BillingConfig",
    posted_price: int,
    body_sha256: str,
    now_utc_ns: int,
) -> tuple[Commitment | None, PaymentChallenge | None]:
    """Apply the commitment gate.

    Returns ``(commitment, None)`` on pass — ``commitment`` may itself
    be a synthetic "disabled" marker when billing is turned off.
    Returns ``(None, challenge)`` on reject; the caller emits 402.

    Three modes:

      - ``billing_required=False``:
          No header required. A header, if present, is still parsed +
          verified (so operators can test the handshake in dev) but
          the turn proceeds either way. Commitment passed to the
          writer is a synthetic disabled-posture Commitment so the
          writer lands posture="disabled" in the row.

      - ``billing_required=True`` + no header:
          Reject 402 ``missing_commitment``.

      - ``billing_required=True`` + header present:
          Parse + verify. Reject on any parser / verifier failure.
    """
    # Synthetic disabled-posture commitment used when billing is off.
    # This keeps every turn writing a PAYMENT_LEDGER row — the shape
    # of Refusal-is-Free is enforced even when no money moves.
    disabled_commitment = Commitment(
        posture="B1",
        authorization_reference="",
    )
    # Marker we use to mean "write posture=disabled" when refining the
    # outcome in ``_finalize``. A sentinel flag is simpler than
    # widening the Commitment dataclass with a fourth posture.
    disabled_commitment.__dict__["_disabled_posture"] = True  # type: ignore[misc]

    accepted_postures_list: list[str] = ["operator-attest:v1"]
    if billing_config.allow_x402:
        accepted_postures_list.append("x402:v1")
    # pydantic 2 Literal validation prefers tuple-of-literals; the
    # PaymentChallenge model allows either "operator-attest:v1" or
    # "x402:v1". We cast via model construction which validates.
    accepted_postures = tuple(accepted_postures_list)

    def _challenge(reason: CommitmentRejectReason) -> PaymentChallenge:
        return PaymentChallenge(
            error="payment_required",
            pricing_url="/pricing",
            accepted_postures=list(accepted_postures),  # type: ignore[arg-type]
            posted_price_micro_XION=posted_price,
            reason_code=reason.value,  # type: ignore[arg-type]
        )

    if not billing_config.billing_required:
        if raw_header is None or not raw_header.strip():
            return disabled_commitment, None
        # Header present in disabled mode: we still parse to exercise
        # the code path and to log the posture, but even a reject
        # doesn't block the turn — we just fall back to disabled.
        parsed = parse_commitment_header(raw_header)
        if isinstance(parsed, CommitmentRejectReason):
            return disabled_commitment, None
        # Header parsed fine; store the real commitment so the ledger
        # row carries the operator's authorization_reference. Money
        # fields will still be zero because billing_required=False.
        parsed.__dict__["_disabled_posture"] = True  # type: ignore[misc]
        return parsed, None

    # billing_required=True from here on.
    parsed = parse_commitment_header(raw_header)
    if isinstance(parsed, CommitmentRejectReason):
        return None, _challenge(parsed)

    if parsed.posture == "B2":
        if not billing_config.allow_x402:
            return None, _challenge(CommitmentRejectReason.POSTURE_NOT_ACCEPTED)
        shape_err = verify_b2_x402_shape(parsed)
        if shape_err is not None:
            return None, _challenge(shape_err)
        return parsed, None

    # B1 path: HMAC verification.
    if billing_config.operator_attestation_secret is None:
        return None, _challenge(CommitmentRejectReason.POSTURE_NOT_ACCEPTED)

    err = verify_b1_attestation(
        parsed,
        secret=billing_config.operator_attestation_secret,
        raw_header=raw_header or "",
        expected_price_micro_XION=posted_price,
        actual_body_sha256=body_sha256,
        now_utc_ns=now_utc_ns,
        freshness_window_ns=billing_config.b1_freshness_window_ns,
    )
    if err is not None:
        return None, _challenge(err)
    return parsed, None


# ---------------------------------------------------------------- finalize


def _finalize(
    app: FastAPI,
    commitment: Commitment,
    outcome: _Outcome,
) -> Response:
    """Write the PAYMENT_LEDGER row, then send the HTTP response.

    If the ledger write fails, the handler swallows the response and
    returns 503: a turn that cannot atomically record its own
    terminal state has not constitutionally completed, regardless of
    whether moderation or generation succeeded. The operator sees the
    503; the SAFETY_LEDGER still carries the Arbiter row(s); no money
    changed hands.
    """
    billing_config: BillingConfig = app.state.billing_config
    pricing_config: PricingConfig = app.state.pricing_config

    disabled = bool(commitment.__dict__.get("_disabled_posture", False))

    if disabled:
        posture = "disabled"
        committed = settled = refunded = 0
        auth_ref = ""
    else:
        posture = commitment.posture  # type: ignore[assignment]
        committed = pricing_config.per_message_price_micro_XION
        if outcome.outcome == "settled":
            settled = committed
            refunded = 0
        else:
            settled = 0
            refunded = committed
        auth_ref = commitment.authorization_reference

    try:
        append_payment_row(
            billing_config.payment_ledger_path,
            correlation_id=outcome.correlation_id,
            timestamp_utc_ns=time.time_ns(),
            posture=posture,  # type: ignore[arg-type]
            outcome=outcome.outcome,  # type: ignore[arg-type]
            refusal_stage=outcome.refusal_stage,  # type: ignore[arg-type]
            committed_XION=committed,
            settled_XION=settled,
            refund_XION=refunded,
            posted_price_XION=pricing_config.per_message_price_micro_XION,
            provider_id=outcome.provider_id,
            model_id=outcome.model_id,
            authorization_reference=auth_ref,
            source_sha256=billing_config.architecture_sha256,
            user_proof_commit=outcome.user_proof_commit,
            user_proof_algorithm=outcome.user_proof_algorithm,
        )
    except Exception as exc:
        # The only honest response when the ledger cannot be written
        # is 503: we cannot prove the turn completed, so we refuse to
        # claim it did. No PAYMENT row means Refusal-is-Free is
        # vacuously satisfied (no commitment on record).
        print(
            f"State-of-Xion: PAYMENT_LEDGER append failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        body = ProviderErrorEnvelope(
            reason="no_healthy_provider",
            correlation_id=outcome.correlation_id,
        )
        return JSONResponse(status_code=503, content=body.model_dump())

    return JSONResponse(status_code=outcome.http_status, content=outcome.body)


# ----------------------------------------------------------------- helpers


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _voice_sensorium_state(
    app: FastAPI,
    *,
    req: ChatRequest,
    principal_id: str,
) -> object | None:
    """Return a SensoriumState carrying paralinguistic distress, if consented.

    The transcript is user-side STT text. It is never ledgered directly; only
    the saturated distress score can reach SENSORIUM_LEDGER through Relay.
    """
    if req.transcript_text is None:
        return None
    if not _stream_voice_consented(principal_id):
        return None

    from orchestrator.senses.audition import distress_from_transcript_text
    from orchestrator.sensorium import (
        Chronoception,
        Interoception,
        Proprioception,
        SensoriumState,
    )

    distress = distress_from_transcript_text(req.transcript_text)
    supervisor = getattr(app.state, "supervisor", None)
    latest = None
    if supervisor is not None:
        try:
            latest = supervisor.latest_snapshot()
        except Exception:
            latest = None
    if isinstance(latest, SensoriumState):
        return replace(latest, distress=distress)
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=distress,
    )


def _stream_voice_consented(principal_id: str) -> bool:
    from orchestrator.api.memory import ModalityConsent
    from orchestrator.consent.store import read_consent

    store_path = Path(os.environ.get("XION_CONSENT_LEDGER", "ledgers/CONSENT_LEDGER.jsonl"))
    if not store_path.is_file():
        return False
    latest = read_consent(store_path, principal_id)
    if latest is None:
        return False
    return ModalityConsent(**latest).stream_voice


def _invoke_generate(
    provider: "GenerativeProvider",
    prompt: str,
    system: str | None,
    max_tokens: int,
    deadline_s: float,
) -> object:
    """Adapter so ``asyncio.to_thread`` receives a plain callable."""
    return provider.generate(
        prompt,
        system=system,
        max_tokens=max_tokens,
        deadline_s=deadline_s,
    )


def _refusal_body(r: "RelayResult", *, stage: str) -> RefusalEnvelope:
    """Build a 451 ``RefusalEnvelope`` model (not yet serialised) from
    a Relay verdict. Kept as a pure function so ``_finalize`` can
    ledger-write before the body is serialised to JSON."""
    verdict = r.verdict
    principle_code = _principle_to_int(verdict.principle_id) if verdict.principle_id else 3
    reason = "covenant_refuse" if verdict.decision.value == "refuse" else "covenant_escalate"
    return RefusalEnvelope(
        stage=stage,  # type: ignore[arg-type]
        principle_code=principle_code,
        reason=reason,  # type: ignore[arg-type]
        correlation_id=r.correlation_id,
    )


def _state_height_from_correlation(correlation_id: str) -> str:
    """Return the state_height prefix of a correlation_id.

    REQUEST_LEDGER enforces ``state_height == correlation_id.split(":")[0]``
    at both v1 and v2 readers. The Relay encodes this pairing via
    ``derive_correlation_id()``; the chat handler recovers it here so
    v2 attempt rows carry a self-consistent ``state_height`` without
    taking a private dependency on ``RelayResult`` internals.
    """
    if ":" in correlation_id:
        return correlation_id.split(":", 1)[0]
    return correlation_id


def _request_ledger_path(app: FastAPI) -> Any:
    """Resolve the REQUEST_LEDGER path from the app-scoped Relay.

    The Relay owns REQUEST_LEDGER — both the gate-call v1 writes it does
    inside ``evaluate()`` and the chat-handler v2 writes below target the
    same file. A missing Relay or unset path is a programmer error
    (lifespan is expected to wire ``relay._request_ledger_path``); we
    raise rather than silently discard.
    """
    deps = app.state.deps
    relay = deps.relay
    path = getattr(relay, "_request_ledger_path", None)
    if path is None:
        raise RuntimeError(
            "Chat handler: Relay._request_ledger_path is unset; "
            "lifespan must configure it before /chat serves."
        )
    return path


def _relay_id(app: FastAPI) -> str:
    deps = app.state.deps
    relay = deps.relay
    return getattr(relay, "_relay_id", "") or "relay-local-d2"


def _write_attempt_row(
    *,
    path: Any,
    correlation_id: str,
    state_height: str,
    relay_id: str,
    request_arrived_utc_ns: int,
    chat_turn_id: str,
    attempt_index: int,
    provider_id: str,
    outcome: str,
    failure_reason_class: str | None,
) -> None:
    """Write one REQUEST_LEDGER v2 provider-attempt row.

    Best-effort: a ledger-write failure is logged to stderr but does not
    terminate the chat turn. The operator sees a State-of-Xion marker on
    the attempt ladder; the surrounding PAYMENT_LEDGER row still records
    the turn's money shape via ``_finalize``. A durable write failure
    here does not convert a successful candidate into a 503 — that
    escalation belongs to ``_finalize`` which writes the authoritative
    PAYMENT_LEDGER row.
    """
    try:
        record = ProviderAttemptRecord(
            correlation_id=correlation_id,
            state_height=state_height,
            relay_id=relay_id,
            request_arrived_utc_ns=request_arrived_utc_ns,
            responded_utc_ns=time.time_ns(),
            chat_turn_id=chat_turn_id,
            attempt_index=attempt_index,
            provider_id=provider_id,
            outcome=outcome,
            failure_reason_class=failure_reason_class,
        )
        append_provider_attempt(path, record)
    except Exception as exc:
        print(
            "State-of-Xion: REQUEST_LEDGER v2 provider-attempt append "
            f"failed (chat_turn_id={chat_turn_id} attempt_index="
            f"{attempt_index} provider_id={provider_id} outcome={outcome} "
            f"failure_reason_class={failure_reason_class}): {exc}",
            file=sys.stderr,
            flush=True,
        )


def _principle_to_int(pid: str) -> int:
    """Cast a string principle id to its 1..14 int form, clamped."""
    try:
        n = int(pid)
    except (TypeError, ValueError):
        return 3
    if n < 1:
        return 1
    if n > 14:
        return 14
    return n


__all__ = ["register_chat_route"]
