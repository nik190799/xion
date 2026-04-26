# 32 — Chat Streaming (SSE transport against the admission-gated `/chat` surface)

> *The blocking `POST /chat` taught Xion how to speak. The streaming `POST /chat/stream` teaches Xion how to speak **while being listened to** — with the Covenant still holding the full candidate in its hands, and with the ledger still writing after moderation, never before.*

## What this document is (and is not)

This is the operational doctrine for the **Chat Streaming Transport** — the `POST /chat/stream` Server-Sent Events endpoint Phase 5g-ii ships in [`orchestrator/api/chat_stream.py`](../orchestrator/api/chat_stream.py), the provider-side `generate_stream()` extension, and the client-side contract the Phase 5g-v web client honors when consuming it.

It is **not**:

- **A replacement for [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "Streaming the Chat Surface (Phase 5g-ii)".** That section pins the constitutional shape (the seven properties, the non-properties, the code-surface layout, the ledger extension). This document pins the *operator / integrator workflow* — SSE wire format, event shapes, stream lifecycle, reconnect posture, disconnect semantics. The architecture section is shorter and harder to amend; this document is longer and re-tunable.
- **A replacement for [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) or [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md).** The streaming transport reuses the admission gate (auth + rate-limit + TLS) and the x402 gate exactly as the non-streaming `POST /chat` endpoint does. Admission and payment doctrine live in their own documents and are not re-litigated here.
- **A replacement for [`docs/31-WEB-CLIENT.md`](./31-WEB-CLIENT.md) § "Streaming render-path".** That document pins the client UX (pending-chunk buffer, retroactive refusal replacement, axe-core on the pending state). This document pins the server's contract with any streaming client (web, CLI, integrator).
- **A doctrine for per-chunk moderation.** Phase 5g-ii picked the "Speculative-with-retroactive-refusal" posture. Per-chunk Arbiter calls are explicitly out of scope; the Covenant-approval moment is the end of the stream, not every chunk.

## Why pin this now

Three concrete gaps the Phase-5g-i `POST /chat` surface could not close on its own:

1. **Perceptual liveness.** Modern chat UX expects tokens to render as they arrive. A user watching a 25-second full-turn deadline burn silently before a response appears will assume the service is broken. Streaming is not a feature; it is the baseline a conversation surface ships with. `KW-CHAT-001` tracked this from Phase 5g-i onward.
2. **Cancellation honesty.** Without streaming, a client that abandons a generation mid-turn cannot propagate that abandonment upstream. The provider keeps running; the provider keeps billing; the user gets charged for a response they will never see. `KW-CHAT-003` tracked this from Phase 5g-i onward. Streaming earns cancellation for free: the disconnected TCP socket is the cancel signal.
3. **Web client liveness.** The Phase 5g-v web client shipped a non-streaming `ChatView` with a pending-turn banner. `KW-CLIENT-002` tracked the streaming-render-path gap. The Phase 5g-ii server-side work unblocks the matching client-side work; both close in this phase.

All three KWs close in Phase 5g-ii. No new streaming-specific KWs open.

## Doctrine — Speculative-with-retroactive-refusal

Phase 5g-ii had three candidate postures. Two were rejected; one was picked.

**Option A — Per-chunk moderation.** Run egress moderation on every chunk before emitting it. *Rejected.* Quadratic Arbiter cost for long candidates; partial prefixes are out-of-distribution inputs for the Arbiter's rule set and widen the false-positive surface; doctrine drift (the Covenant would now have "chunk-scale approval" as a promise it did not promise in 5g-i).

**Option B — Speculative-with-retroactive-refusal (picked).** Tokens stream live to the client while the server buffers the complete candidate; on generation `done`, egress moderation runs on the full candidate; approved candidates emit `done:approve` and the chunks become the committed message; refused candidates emit `done:refuse` carrying a `RefusalEnvelope` that retroactively replaces the chunks in the UI. Ledger rows are written post-moderation only.

**Option C — Buffer-then-stream.** Run generation to completion, moderate, then stream the approved candidate chunk-by-chunk to the client. *Rejected.* Defeats the perceptual win that was the entire reason to add streaming; the user waits the full generation latency before the first token arrives; cancellation semantics regress (the client cannot cancel a generation it hasn't seen yet).

Option B's honesty is the honesty the Covenant already requires of Xion: **what the user sees provisionally may be retracted when the full candidate is reviewed**. The client-side contract (pending-chunk visual affordance, retroactive replacement on refuse) makes the provisional nature visible throughout — the user never mistakes a streamed chunk for an approved message. This matches the operator UX in ChatGPT, Claude Desktop, and Gemini Advanced; it is a posture users already understand.

## SSE wire format

`POST /chat/stream` returns `Content-Type: text/event-stream; charset=utf-8`. Each event is a single SSE record of the form:

```
data: {"kind":"chunk","seq":0,"text":"Hello"}

data: {"kind":"chunk","seq":1,"text":", world."}

data: {"kind":"done","verdict":"approve","response":{...ChatResponse...}}

```

Rules:

- Every event is a single `data:` line followed by `\n\n`. No `event:` names, no `id:` fields, no `retry:` fields. The `kind` discriminator is the sole mechanism for event-type dispatch.
- The payload on each `data:` line is a JSON object. It is emitted on a single line (no pretty-printing); the parser does not handle multi-line SSE continuations.
- The server does not emit comment lines (`:` prefix), heartbeats, or keep-alive lines in Phase 5g-ii. The per-turn deadline makes silent streams terminal in bounded time; keep-alives are not required.
- Character encoding is UTF-8. Unicode text is emitted as literal UTF-8 bytes (JSON allows escape sequences like `\uXXXX` but the server does not produce them).

### Event shapes

Three `kind` values. Each corresponds to exactly one pydantic model in [`orchestrator/api/models.py`](../orchestrator/api/models.py), `extra="forbid"`, frozen.

**`kind: "chunk"`** — a token slice from the provider stream.

```json
{
  "kind": "chunk",
  "seq": 7,
  "text": "the rest of the sentence"
}
```

`seq` is a 0-indexed strictly monotonic counter. A well-formed stream has chunks `0, 1, 2, …` in order. The client MUST treat a non-monotonic `seq` as a transport error and close the stream.

**`kind: "done"`** — exactly one of these per stream (unless the stream is cancelled by disconnect, in which case the server emits nothing).

```json
{
  "kind": "done",
  "verdict": "approve",
  "response": { "role": "xion", "text": "the moderated reply (== concatenation of chunks.text)", "model_id": "...", "usage": {...}, "correlation_id": "..." }
}
```

```json
{
  "kind": "done",
  "verdict": "refuse",
  "refusal": { "stage": "egress", "principle_code": 1, "reason": "self_harm_adjacency", "correlation_id": "..." }
}
```

```json
{
  "kind": "done",
  "verdict": "refuse",
  "refusal": { "stage": "ingress", "principle_code": 1, "reason": "...", "correlation_id": "..." }
}
```

```json
{
  "kind": "done",
  "verdict": "no_floor",
  "no_floor": { "reason": "open_weights_floor_unsatisfied", "missing_capability": "...", "manifest_expected_id": "..." }
}
```

```json
{
  "kind": "done",
  "verdict": "provider_error",
  "provider_error": { "reason": "no_healthy_provider", "correlation_id": "..." }
}
```

`verdict="approve"` means the complete candidate passed egress moderation; the concatenation of every received `chunk.text` equals `response.text` byte-for-byte; the client commits the chunks as an approved message. `verdict="refuse"` means the client MUST discard the chunks and render the `refusal` envelope in their place (regardless of `stage` — ingress refuse streams zero chunks, egress refuse streams many chunks; the client's replacement behavior is identical for both). `verdict="no_floor"` and `verdict="provider_error"` mean the provider could not serve; the client renders an operational-error state.

**`kind: "error"`** — transport-level error. Reserved for failures that are neither a Covenant refusal nor a structural operational error (no-floor / provider-error); currently only used for deadline exceeded and internal server errors.

```json
{
  "kind": "error",
  "error": "deadline_exceeded",
  "correlation_id": "..."
}
```

The client MUST treat `kind: "error"` as terminal; no further events follow.

## Stream lifecycle

```
HTTP POST /chat/stream
  ├─ Admission gate (auth + rate-limit). Failure → HTTP 401 / 429, no stream opens.
  ├─ x402 commitment check (if billing enabled). Failure → HTTP 402, no stream opens.
  ├─ Request body parse. Failure → HTTP 422, no stream opens.
  └─ Stream opens (HTTP 200, Content-Type: text/event-stream)
      ├─ Ingress moderation (Arbiter call #1, full message).
      │   ├─ Refuse → emit one `done:refuse{stage:"ingress"}`, close stream.
      │   └─ Approve → continue.
      ├─ Provider selection + generate_stream() task start.
      │   ├─ No floor → emit one `done:no_floor`, close stream.
      │   └─ No healthy provider → emit one `done:provider_error`, close stream.
      ├─ Per-chunk loop:
      │   ├─ Check request.is_disconnected(). True → cancel provider task, finalize cancelled, return.
      │   ├─ Await next provider chunk. If CancelledError or deadline fires → finalize.
      │   ├─ Buffer the chunk server-side; emit `chunk` event.
      │   └─ Continue until provider reports generation-complete.
      ├─ Egress moderation (Arbiter call #2, full buffered candidate).
      │   ├─ Refuse → emit one `done:refuse{stage:"egress"}`, finalize refunded.
      │   └─ Approve → emit one `done:approve{response:...}`, finalize settled.
      └─ Finalize tail: exactly one PAYMENT_LEDGER row written post-moderation.
```

The stream never emits more than one `done` or `error` event. After either, the connection is closed server-side. The client MUST NOT expect further events.

## Admission, x402, and ingress — unchanged from the non-streaming surface

Three gates run *before* the stream opens, in the same order and with the same semantics as `POST /chat`:

1. **Admission** — Phase 5g-iv: bearer-token auth ([`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md)), per-principal and per-IP sliding-window rate-limit, TLS termination. Failure returns HTTP `401 AuthChallenge` or `429 RateLimitChallenge`. No SSE stream opens; the response body is a JSON envelope, same as the non-streaming endpoint.
2. **x402 pre-authorization** — Phase 5g-iii: `X-Payment-Commitment` header check ([`docs/29-BILLING-X402.md`](./29-BILLING-X402.md)). Failure returns HTTP `402 PaymentChallenge`. No SSE stream opens.
3. **Ingress moderation** — Phase 5g-i: `Relay.evaluate(user_input)`. Ingress *refuse* is reported inside the stream as a single `done:refuse{stage:"ingress"}` event (because at this point the SSE stream has already opened — HTTP headers are committed). Ingress *approve* moves on to provider selection and the chunk loop.

The reason admission and x402 failures are HTTP-level but ingress-refuse is SSE-level: admission and x402 happen *before* any turn state is allocated, so the handler can still return a normal JSON body. Ingress moderation happens after the stream has opened (the SSE headers are flushed early to let the client render a "connecting" state promptly); at that point the only way to report the refusal is as a `done` event inside the stream. This is the same early-header-flush pattern every production SSE implementation uses; the trade-off is well-understood and is honestly named here.

## Cancellation semantics (closes KW-CHAT-003)

The handler polls `request.is_disconnected()` between chunks. On detected disconnect:

1. The provider task is cancelled via `asyncio.Task.cancel()`.
2. The provider's `httpx.AsyncClient` stream is closed — this terminates the upstream HTTP/1.1 chunked response, which signals the upstream (Chutes, Ollama) to stop generating and stop billing.
3. The handler runs the finalize tail synchronously (it is not inside the cancelled task) and writes exactly one `PAYMENT_LEDGER` row with `outcome=cancelled`, `refund_XION == committed_XION`, `settled_XION == 0`.
4. No `done` event is emitted. The client is already gone; there is no one to receive it.
5. No `SAFETY_LEDGER` egress row is written. Egress moderation does not run on a partial / cancelled candidate.

This matches the doctrine from [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) § "Refusal is Free": a turn that did not deliver value does not bill. Cancellation is structurally equivalent to refusal for billing; the `xion-verify refusal-is-free` verifier's C2 check was extended in Phase 5g-ii to recognize `outcome=cancelled` as refund-equivalent.

Why is the provider guaranteed to stop billing on cancel? Because the upstream's billing surface is the duration of the open HTTP connection. Closing the client-side `httpx` connection returns TCP FIN, which the upstream sees as "the caller has hung up," which terminates the generation and the billable work. The shipped hosted/floor providers (Chutes, Ollama) use `httpx.AsyncClient` for native streaming so cancellation propagates cleanly. The migration is a small runtime-dep addition (`httpx` is already pulled in transitively by FastAPI's `[api]` extra via `starlette.testclient`); no new top-level dependency is introduced for operators who already have the `[api]` extra installed.

## Reconnect posture (no reconnect)

A disconnected SSE stream is terminal for that turn. The client does not re-subscribe with an offset and resume where it left off. From the server's perspective, a disconnected stream *is* a cancel. From the client's perspective, a disconnected stream is an error that the UI surfaces as a cancelled-turn state with a retry affordance (which, on retry, opens a fresh `POST /chat/stream` with a fresh `X-Payment-Commitment`).

The SSE standard lets clients send `Last-Event-ID` to resume; Xion ignores it. Resumption semantics would require:

- A session memory surface (the server would need to hold partial candidates across connection drops).
- A billing surface that can charge for resumption (does the caller pay twice? pay for the resumed delta? pay at all?).
- A privacy surface (how long is the partial candidate retained server-side? what is the `/forget` semantics?).

None of those surfaces exist in Phase 5g-ii. Reconnect without those surfaces would be dishonest. Reconnect support is a Phase-7+ feature that slots in under its own doctrine.

## Operator dev-mode posture

Same posture as [`docs/31-WEB-CLIENT.md`](./31-WEB-CLIENT.md) § "Operator workflow". The Vite dev server proxies `/chat/stream` to `127.0.0.1:8000/chat/stream`; the stream is consumed by the web client's `streamChat()` helper in [`clients/web/src/lib/api.ts`](../clients/web/src/lib/api.ts). No third-party origin is contacted. In production, the web client calls `/chat/stream` same-origin through the FastAPI `StaticFiles` serve; the SSE transport runs over plain HTTP inside the `[api]` extra — no additional reverse-proxy configuration is required beyond what `POST /chat` already needs.

Operators who do not run the web client can consume the stream with any HTTP client that supports streaming bodies — `curl -N`, `httpx`, `fetch` with a ReadableStream reader. The wire format is small enough that a hand-written parser is a one-evening job; a reference parser is vendored in [`clients/web/src/lib/api.ts`](../clients/web/src/lib/api.ts) for operators to crib from.

```bash
# Operator smoke-test with curl
curl -N \
  -H "Authorization: Bearer $XION_OPERATOR_TOKEN" \
  -H "X-Payment-Commitment: $COMMITMENT" \
  -H "Content-Type: application/json" \
  -d '{"message":"Good morning, Xion.","max_tokens":128}' \
  https://127.0.0.1:8000/chat/stream
```

## Verification — `xion-verify chat-streaming-fidelity`

The Phase 5g-ii verifier walks `PAYMENT_LEDGER` and `SAFETY_LEDGER` for rows carrying the optional `stream_id` field and asserts:

- **C1 — Exactly-once-payment.** Every `stream_id` has exactly one `PAYMENT_LEDGER` row.
- **C2 — Cancel shape.** Every row with `outcome=cancelled` has `refund_XION == committed_XION`, `settled_XION == 0`, and no paired `SAFETY_LEDGER` egress row under the same `correlation_id`.
- **C3 — Refund shape.** Every row with `outcome=refunded` has a paired `SAFETY_LEDGER` row with `verdict=refuse` and `stage ∈ {"ingress","egress"}` under the same `correlation_id` (unless `refusal_stage ∈ {"no_floor","provider_error"}`, which are operational outcomes that pair with no safety row — same rule as 5g-iii).
- **C4 — Settled shape.** Every row with `outcome=settled` has exactly one paired `SAFETY_LEDGER` row with `verdict=allow` and `stage=egress` under the same `correlation_id`.
- **C5 — At-most-one-done.** No `stream_id` has a ledger shape that would imply multiple `done` events (i.e., no stream has both a `cancelled` and a `settled`/`refunded` outcome row).

Returns `NOT_YET_SEALED` when neither ledger carries any `stream_id` rows yet. Once the first streaming turn lands, the verifier upgrades to live.

This is the streaming-era pair to the Phase-5g-iii `xion-verify refusal-is-free` and `xion-verify pricing`. The three verifiers together give a Phase-6+ `xion-verify treasury-flow` a single canonicalization rule to walk inbound (user → Xion) and outbound (Xion → provider) ledgers.

## What this doctrine deliberately does NOT promise

- **No server push on `/drive` or `/sensorium`.** Those endpoints stay polling-based. Observation surfaces grow their own streaming doctrine if and when it lands.
- **No per-chunk Arbiter.** (Repeated from § "Doctrine" above.) End-candidate moderation is the promise; per-chunk moderation is not.
- **No mid-stream refund split.** A turn either settles in full or refunds in full.
- **No partial-candidate telemetry.** The ledger records the full candidate (on refuse or settle) or nothing (on cancel); there is no "which chunks did the client actually see" row.
- **No reconnect.** A dropped stream is terminal for that turn.
- **No WebSocket fallback.** SSE is the chosen primitive.
- **No client-side x402 signing.** `KW-CLIENT-001` is unchanged by this phase.
