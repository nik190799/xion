"""``POST /chat`` handler (Phase 5g-i).

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Chat Surface
(Phase 5g-i)" and ``docs/26-INFERENCE-POLICY.md``.

A single function, ``register_chat_route(app)``, wires the ``/chat``
endpoint against the dependencies already stashed on ``app.state`` by
the lifespan (``deps``, ``router``, ``no_floor``, ``no_floor_reason``,
``no_floor_manifest_id``). The handler itself:

    ingress moderation
    floor check
    provider selection
    generation (in a worker thread, deadline-bounded)
    egress moderation
    surface

Every branch returns an envelope model; no other branch exits the
handler. The content-free guarantee is structural: the HTTP response
body is one of four pydantic models with ``extra="forbid"`` — there
is no code path here that could accidentally add a new field.

The handler runs ingress moderation **before** the floor check. This
is the Phase 3 moderation-first doctrine: no category of caller
(including callers facing a 503) should discover they could have
bypassed the Arbiter by picking the right error. Ingress moderation
always runs first.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse

from .models import (
    ChatRequest,
    ChatResponse,
    NoFloorEnvelope,
    ProviderErrorEnvelope,
    RefusalEnvelope,
    UsageEnvelope,
)

if TYPE_CHECKING:
    from orchestrator.inference_router.provider import GenerativeProvider
    from orchestrator.relay.relay import RelayResult


_DEFAULT_DEADLINE_S = 30.0


def register_chat_route(app: FastAPI) -> None:
    """Register ``POST /chat`` on ``app``.

    Called from ``create_app`` *after* the three Phase 5f GETs are
    registered. Reads the chat-specific dependencies (router,
    no_floor state, deadline) from ``app.state``.
    """

    @app.post(
        "/chat",
        response_model=None,
        summary="Single-turn chat, moderated on both sides (Phase 5g-i)",
    )
    async def post_chat(req: ChatRequest) -> Response:
        deps = app.state.deps
        relay = deps.relay

        deadline_s = float(getattr(app.state, "chat_deadline_s", _DEFAULT_DEADLINE_S))

        ingress = await asyncio.to_thread(relay.evaluate, req.message)
        if not ingress.egress_allowed:
            return _refusal(ingress, stage="ingress")

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
            return JSONResponse(
                status_code=503,
                content=body.model_dump(),
            )

        router = getattr(app.state, "router", None)
        provider = router.select() if router is not None else None
        if provider is None or not callable(getattr(provider, "generate", None)):
            body_pe = ProviderErrorEnvelope(
                reason="no_healthy_provider",
                correlation_id=ingress.correlation_id,
            )
            return JSONResponse(
                status_code=503,
                content=body_pe.model_dump(),
            )

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    _invoke_generate,
                    provider,
                    req.message,
                    req.max_tokens,
                    deadline_s,
                ),
                timeout=deadline_s,
            )
        except TimeoutError:
            body_pe = ProviderErrorEnvelope(
                reason="no_healthy_provider",
                correlation_id=ingress.correlation_id,
            )
            return JSONResponse(status_code=503, content=body_pe.model_dump())
        except Exception:
            body_pe = ProviderErrorEnvelope(
                reason="no_healthy_provider",
                correlation_id=ingress.correlation_id,
            )
            return JSONResponse(status_code=503, content=body_pe.model_dump())

        if not result.text:
            body_ref = RefusalEnvelope(
                stage="egress",
                principle_code=3,
                reason="provider_empty_candidate",
                correlation_id=ingress.correlation_id,
            )
            return JSONResponse(status_code=451, content=body_ref.model_dump())

        egress = await asyncio.to_thread(relay.evaluate, result.text)
        if not egress.egress_allowed:
            return _refusal(egress, stage="egress")

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
        return JSONResponse(status_code=200, content=ok.model_dump())


def _invoke_generate(
    provider: GenerativeProvider,
    prompt: str,
    max_tokens: int,
    deadline_s: float,
) -> object:
    """Adapter so ``asyncio.to_thread`` receives a plain callable.

    Keeps the Chat handler free of closures that capture the provider
    across thread boundaries in ways that would complicate cancellation.
    """
    return provider.generate(
        prompt,
        system=None,
        max_tokens=max_tokens,
        deadline_s=deadline_s,
    )


def _refusal(r: RelayResult, *, stage: str) -> Response:
    """Build a 451 ``RefusalEnvelope`` response from a Relay verdict.

    The ``principle_code`` is derived from ``verdict.principle_id``; an
    escalate (``rule-declined-to-rule``) with no principle pinned maps
    to principle 3 (Sanctum of Third-Party Harm) as the default — the
    Arbiter has declined to rule, which Principle 3 explicitly names
    as the fail-closed-by-escalate path.
    """
    verdict = r.verdict
    principle_code = _principle_to_int(verdict.principle_id) if verdict.principle_id else 3
    reason = "covenant_refuse" if verdict.decision.value == "refuse" else "covenant_escalate"
    body = RefusalEnvelope(
        stage=stage,  # type: ignore[arg-type]
        principle_code=principle_code,
        reason=reason,  # type: ignore[arg-type]
        correlation_id=r.correlation_id,
    )
    return JSONResponse(status_code=451, content=body.model_dump())


def _principle_to_int(pid: str) -> int:
    """Cast a string principle id to its 1..14 int form, clamped.

    The Arbiter stores principle ids as strings (``"1"``..``"14"``).
    We clamp to [1, 14] so a malformed id does not crash the handler —
    a malformed id is a bug, but a bug that converts to ``1`` is
    better than one that converts to a 500.
    """
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
