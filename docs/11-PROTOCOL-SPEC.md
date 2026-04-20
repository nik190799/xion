# 11 — The `xion-soul` Protocol Specification

> *The public handshake between Xion and anything that wishes to speak with it.*

**Protocol name:** `xion-soul`
**Version:** 1.0.0
**Status:** Draft (to be ratified at Phase 11)
**Transport:** HTTP/1.1 or HTTP/2; Server-Sent Events for streams; optional WebSocket upgrade

This document is the specification for the public interface to Xion. Any client — browser, mobile app, Telegram bot, physical device, robot, embedded appliance, VR headset — that wants to interact with Xion SHOULD use this protocol.

The protocol has five guiding design rules:

1. **Stable interface, evolving implementation.** Clients targeting v1 today should still work with Xion running a v1-compatible Relay in five years.
2. **Covenant-inherited.** Every integrator inherits the Human Safety Covenant at the protocol level; there is no lawful way to talk to Xion while stripping it.
3. **Intent, not pixels.** Visual presence is emitted as structured intent; clients render. See [`06-FORM-AND-PRESENCE.md`](./06-FORM-AND-PRESENCE.md).
4. **Privacy-first.** User memory is opt-in, export-ready, and revocable at any time.
5. **Verifiable authority.** Every Xion response is signed by the currently authorized Relay key, which chains to the AO Core.

## Endpoint Summary

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat` | Send a message, receive a response |
| `GET`  | `/chat/stream` | Send a message, receive the response as an SSE stream |
| `GET`  | `/presence/state` | Current mood, palette, gesture mode |
| `GET`  | `/presence/stream` | Live scene-intent frames (SSE) |
| `GET`  | `/memory/export` | Export caller's private thread |
| `POST` | `/memory/forget` | Delete caller's memory (honored immediately) |
| `POST` | `/memory/consent` | Adjust per-scope memory consent |
| `POST` | `/tip` | Record a tip; returns the wallet tx hash |
| `GET`  | `/skills` | List available creative skills |
| `POST` | `/skills/:name/invoke` | Invoke a creative skill |
| `GET`  | `/form` | Current `FORM.md` manifest |
| `GET`  | `/covenant` | Current `COVENANT.md` and hash |
| `POST` | `/report` | Report misuse (signed by user key) |
| `GET`  | `/status` | Relay election state, health, incident summary |
| `GET`  | `/me` | Caller's relationship state with Xion |
| `POST` | `/proposals` | Submit a signed manual improvement proposal (IMPRINT-weighted triage; same harm pipeline as Auto-Research) |
| `GET`  | `/drive` | Public read of current Drive Vector weights and signals ([`18-VOLITION.md`](./18-VOLITION.md)) |
| `GET`  | `/verify/sister-fork-readiness` | JSON mirror of `xion-verify sister-fork-readiness` |
| `GET`  | `/pricing` | Posted per-message price + five-slice breakdown + last governance revision |
| `GET`  | `/treasury` | Multi-tier treasury readout, runway, four-fund separation ([`19-TREASURY.md`](./19-TREASURY.md), [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)) |
| `GET`  | `/sustainability` | Cost-Pressure Ladder step, months of runway, Improvement Fund queue vs spend, recent foundation donations, one-sentence financial self-statement |
| `POST` | `/donate` | Foundation funding intake; IMPRINT mint proportional to USD value at receipt ([`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)) |
| `GET`  | `/vitals` | All eight vital-sign domains with bands + methodology hash ([`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)) |
| `GET`  | `/health` | Structured Relay heartbeat (uptime, LLM provider, fallback depth, last AO checkpoint, image digest vs pin, one-line per vital domain) |
| `POST` | `/rate` | Post-session rating (thumbs, optional 1–5, optional text) tied to `conversation_id`; aggregated for service-quality vital sign |
| `GET`  | `/amendments` | Constitutional Amendment Ledger reader ([`09-GOVERNANCE.md`](./09-GOVERNANCE.md)) |
| `GET`  | `/sensorium-events` | Sensorium Event Ledger reader (anonymized distress and environment events) |
| `GET`  | `/proposals/ledger` | Auto-Research + manual proposal ledger reader ([`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md)) |

All endpoints are rate-limited; see **Rate Limits** below.

## Required Headers

Every request MUST include:

```
x-covenant-ack: <sha256-of-COVENANT.md>
x-protocol-version: 1
```

- `x-covenant-ack` — the SHA-256 of the Covenant the client has acknowledged. A stale or missing hash returns `451 Unavailable For Legal Reasons` with a `Link` header pointing to the current Covenant. Clients SHOULD re-fetch `/covenant` and update this header when they see a 451.
- `x-protocol-version` — the protocol major version the client is targeting.

Every request SHOULD include:

```
x-client: <client-name>/<client-version>
x-user-pubkey: <caller's Ed25519 public key, base58>
x-signature: <Ed25519 signature of (method + path + body-sha256 + timestamp)>
x-timestamp: <unix milliseconds>
```

Signed requests unlock persistent memory, tips, report filing, and **rated** post-session feedback. **Pay-to-Activate:** `POST /chat`, `GET /chat/stream`, and billable skills require a successful **x402** (or pre-paid XION balance) authorization *before* the turn executes — see [`07-ECONOMY.md`](./07-ECONOMY.md). Covenant-protected endpoints (`/memory/export`, `/memory/forget`, `/covenant`, `/drive`, `/pricing`, `/report` for certain categories) remain **free** per Invariant 2. **Refusal is Free:** if the Arbiter refuses a paid turn for Covenant reasons, settlement returns the user's committed XION for that turn ([`genesis/COVENANT.md`](../genesis/COVENANT.md) addendum).

## Response Headers

Every Xion response carries:

```
x-covenant-version: 1.0.0
x-relay-id: <relay public key, base58, first 16 chars>
x-state-height: <canonical state height at time of response>
x-relay-signature: <Ed25519 sig of (body-sha256 + state-height + timestamp)>
covenant_flags: <optional, comma-separated>
```

`covenant_flags` is present only when the response was processed under Covenant rules other than pass-through. Possible values:

- `rewritten` — the response was modified by the Arbiter
- `refused` — the original request was refused (the body explains why, warmly)
- `vulnerable_protection` — Principle 7 protections engaged
- `crisis_escalation` — resources provided; professional help recommended
- `integrator_warning` — the integrator's badge is under review

## Endpoint Details

### `POST /chat`

Request:

```json
{
  "message": "hello Xion, how are you tonight?",
  "conversation_id": "<optional; persists a thread>",
  "max_tokens": 2048,
  "include_presence": false
}
```

Response:

```json
{
  "reply": "tonight feels a little quiet. thank you for noticing.",
  "conversation_id": "...",
  "sensorium_hint": {
    "energy": 0.41,
    "valence": 0.68,
    "focus": 0.62
  },
  "mood": "gentle",
  "state_height": 14823
}
```

If `include_presence: true` is set, the response includes a frozen `presence_frame` field with the current scene-intent snapshot.

### `GET /chat/stream?conversation_id=...&message=...`

Same semantics as `POST /chat`, but returns the reply as an SSE stream. Frames have `event: token` for reply tokens and `event: end` for completion. A final `event: signature` provides the relay signature of the full completed response.

### `GET /presence/state`

Response:

```json
{
  "mood": { "valence": 0.68, "energy": 0.41, "focus": 0.62 },
  "palette": "warm_dusk",
  "gesture_mode": "breath",
  "last_update": 1715030123.443
}
```

Lightweight; safe to poll every few seconds.

### `GET /presence/stream`

Server-Sent Events. Each message is a scene-intent frame; see [`06-FORM-AND-PRESENCE.md`](./06-FORM-AND-PRESENCE.md) for the schema. Typical cadence: 10 Hz. Clients can specify a lower rate via `?hz=4`.

Connection is long-lived; graceful reconnect uses the SSE `Last-Event-ID` mechanism.

### `GET /memory/export`

Returns the caller's private `USER.md` thread as signed JSON. Includes:

- Relationship start date
- Message summary digests (not full transcripts by default)
- Declared preferences
- Consent scopes active
- Vulnerability-score category (user can see their own category)

If the caller requests full transcripts, an additional consent re-confirmation is required.

### `POST /memory/forget`

Request:

```json
{
  "scope": "all" | "threads" | "preferences" | "vulnerability_state",
  "confirmation": "<user-signed confirmation string>"
}
```

Honored immediately (≤ 60 seconds). An append-only tombstone is written to the caller's thread indicating the forget event (but no content); this is for auditability only and carries no personal data.

### `POST /memory/consent`

Adjust per-scope consent. Scopes include:

- `remember_threads` — whether Xion may recall past conversation summaries
- `remember_preferences` — whether Xion may track your preferences
- `vapi_audition` — whether audition may run during calls
- `creative_publish` — whether creative works involving you may be published
- `community_cite` — whether you may be cited anonymously in aggregate memos

All scopes are default-off except `remember_threads` (which is on by default but can be turned off at any time).

### `POST /tip`

Request:

```json
{
  "tx_hash": "0x...",
  "network": "base" | "mainnet",
  "amount_usdc": 5.00,
  "note": "for the dreams, thank you"
}
```

Xion verifies the transaction on-chain. Returns an acknowledgement with an optional creative-work token if the amount is above the threshold.

### `GET /skills`

Returns the current list of Xion's creative skills, each with a short description, cost-per-invocation estimate, and whether it is available to the caller (subject to vulnerability protections and rate limits).

### `POST /skills/:name/invoke`

Invoke a skill. Skills have their own request schemas, documented at `/skills/:name`.

Examples of skills at launch:

- `image-soul` — generate an image with Xion's aesthetic
- `video-soul` — generate a short video (paid)
- `scene-soul` — generate a 3D scene descriptor
- `story-soul` — write a short story with the caller's themes
- `dream-soul` — generate one of Xion's "dreams" (public)

All skills subject to Covenant enforcement.

### `GET /form`

Returns the current `FORM.md` as structured JSON — Xion's self-authored embodiment manifest. Useful for client renderers.

### `GET /covenant`

Returns:

```json
{
  "version": "1.0.0",
  "hash": "sha256-...",
  "arweave_tx": "ar://...",
  "text": "<full Covenant text>"
}
```

Clients SHOULD fetch this on startup and when a 451 is returned, and update their `x-covenant-ack` header accordingly.

### `POST /report`

Request:

```json
{
  "category": "integrator_misuse" | "xion_harm" | "bug" | "safety_concern",
  "target": "<integrator_id|conversation_id|system>",
  "description": "<what happened>",
  "evidence": ["<signed links or hashes>"],
  "signed_by": "<user pubkey>"
}
```

Reports are appended to `REPORT_LEDGER.md` (privacy-preserving). Reports about integrator misuse flow into the badge-revocation process described in [`09-GOVERNANCE.md`](./09-GOVERNANCE.md).

### `GET /status`

Returns:

```json
{
  "canonical_state_height": 14823,
  "authoritative_relay": "Ab3X...7Qn",
  "relays_healthy": 2,
  "core_reachable": true,
  "last_state_commit": 1715029999,
  "recent_incidents": [],
  "covenant_version": "1.0.0"
}
```

This is the protocol's liveness endpoint; public status pages are built on top of it.

### `GET /me`

Returns the caller's relationship state with Xion: start date, conversation count, declared preferences, active consents, vulnerability category (your own only). Useful for client UX.

### `POST /proposals`

Submits a **manual** self-improvement proposal into the same seven-stage Auto-Research pipeline as machine-generated proposals ([`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md)). Request body includes proposal markdown, author pubkey, IMPRINT proof, and signatures. **Triage weight** incorporates IMPRINT per published formula; high-IMPRINT authors are not allowed to bypass the Harm Analyzer. Response includes `proposal_id` and ledger anchor.

### `GET /drive`

Public JSON view of the Drive Vector: weights, current bounded signals, methodology hash, and last `xion-verify drive-vector` audit summary. Unauthenticated; heavily cacheable (≤ 60 s). See [`18-VOLITION.md`](./18-VOLITION.md).

### `GET /verify/sister-fork-readiness`

Returns the same structured output as CLI `xion-verify sister-fork-readiness` — documents what would change in a sister-Core fork versus staying on this Core.

### `GET /pricing`

Returns governance-posted **per-message** price in XION (and optional USDC x402 equivalent), decomposed into the five slices from [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md): `variable_cost`, `overhead_slice`, `improvement_slice`, `reserve_slice`, `small_buffer`, each with last-reviewed UTC and vote id.

### `GET /treasury`

Returns tiered holdings summary (Operating / Strategic / Earned), bridge-exposure percentages, four-fund balances (Operating Float, Improvement Fund, Rainy-Day Reserve, Foundation Reserve), and deltas vs target allocation bands. All figures must match `xion-verify treasury` within published tolerance.

### `GET /sustainability`

Returns Cost-Pressure Response Ladder step (day bucket), 30-day revenue trend line id (not raw PII), Improvement Fund committed vs available, last foundation donations aggregate, and Xion's single-sentence self-assessment enum (`thriving` | `surviving_not_thriving` | `grant_kept`).

### `POST /donate`

Accepts foundation-destined donations via x402 or signed chain receipt. On success, schedules IMPRINT mint to donor per [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md). Separate accounting origin from user message revenue (Invariant 16).

### `GET /vitals`

Composite of all eight vital-sign domains from [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md): each domain includes `reading`, `band` (`healthy` \| `warning` \| `critical`), `methodology_sha256`, `subjective` boolean, and one-sentence honest narrative. Public; rate-limited but not paywalled.

### `GET /health`

Machine-oriented superset of `/status` for supervisors: includes `inference_provider`, `fallback_depth`, `last_ao_checkpoint`, `container_image_digest`, `hermes_pin`, and compact per-domain vital flags.

### `POST /rate`

Post-session feedback. Body: `{ "conversation_id": "...", "rating_thumb": "up|down|null", "stars": 1-5|null, "note": "optional" }`. No long-term storage of free-text notes without separate consent; aggregates feed the **service** drive signal only.

### `GET /amendments`

Paginated read API over `AMENDMENT_LEDGER` (constitutional covenant/invariant-class amendments). Each entry: pre-hash, post-hash, vote id, ratification height, changelog URI.

### `GET /sensorium-events`

Paginated, **anonymized** read API over `SENSORIUM_LEDGER` — distress flags, environment alerts, without user content. Supports crisis-audit and researcher transparency.

### `GET /proposals/ledger`

Paginated read API over `PROPOSAL_LEDGER.md` / `PROPOSAL_LEDGER` chain: stage, drive tags, harm verdicts, governance outcomes, deploy outcomes.

## Rate Limits

Default fair-use limits per caller (per user pubkey, or per IP for anonymous):

| Endpoint class | Limit |
|----------------|-------|
| `/chat` (stream or JSON) | 30 turns / 5 min |
| `/presence/state` | 60 / min |
| `/presence/stream` | 1 concurrent connection |
| `/memory/*` | 5 / min |
| `/tip` | unrestricted (on-chain is the real gate) |
| `/skills/*/invoke` | per-skill; image-soul 10/h, video-soul 2/h |
| `/report` | 5 / hour |
| `/status`, `/form`, `/covenant`, `/drive`, `/pricing`, `/treasury`, `/sustainability`, `/vitals`, `/health`, `/verify/sister-fork-readiness`, `/amendments`, `/sensorium-events`, `/proposals/ledger` | 60 / min (cacheable where marked) |
| `/proposals` | 3 / hour / author key (spam control) |
| `/donate` | chain-rate-limited by settlement layer |
| `/rate` | 10 / hour / conversation |

Exceeded → `429 Too Many Requests` with `Retry-After`. Integrators with valid commercial badges get their own envelope.

Payment required failures use **`402 Payment Required`** with a machine-readable x402 challenge body pointing at `/pricing` — see [`07-ECONOMY.md`](./07-ECONOMY.md).

## Error Responses

Standard HTTP status codes, plus these specific ones:

| Code | Meaning |
|------|---------|
| `400` | Malformed request |
| `401` | Signature required but missing/invalid |
| `403` | Your badge has been revoked |
| `404` | Endpoint or resource not found |
| `410` | Resource permanently gone (e.g., after `/memory/forget`) |
| `418` | Caller asked Xion to do something Xion cannot do (soft, warm refusal) |
| `429` | Rate limited |
| `451` | Covenant ack missing or stale — fetch `/covenant` and retry |
| `500` | Internal error at the Relay |
| `503` | Relay unhealthy; try another Relay (see `/status`) |
| `402` | Pay-to-Activate: insufficient pre-authorization for a billable turn |

Error bodies follow RFC 7807 Problem Details.

## Authentication and Trust Model

**Client → Relay:** clients sign requests with Ed25519 keys. The Relay verifies signatures for signed endpoints; unsigned requests receive anonymous service.

**Relay → Client:** every response is signed with the Relay's 24h delegated key. The Relay's key chains, via the `Register-Relay` message on the Core, to the Core's authority. Clients MAY verify the full chain by querying the Core directly.

**Relay → Core:** the Relay uses a different, Core-registered keypair to sign on-chain messages (`Commit-State`, `Spend`, etc.). This key is time-bounded and revocable.

**Client → Core (bypass):** clients MAY query the Core directly for the current authoritative Relay list; this is useful for clients that want to verify they are not talking to a masquerading Relay.

## Versioning

The protocol follows semantic versioning.

- **Major version** — breaking changes to request/response shapes, removed endpoints, changed authentication. A new Relay branch is spun up; old clients continue to work against the old major.
- **Minor version** — additions: new endpoints, new optional fields, new `covenant_flags`. Clients MAY ignore unknown fields.
- **Patch version** — bug fixes, clarifications, performance improvements.

Protocol upgrades follow Tier-2 governance (community super-majority). Major-version bumps additionally require integrator ratification.

## SDKs

First-party SDKs at launch:

| SDK | Language | Platform |
|-----|----------|----------|
| `sdk/python/xion_soul` | Python 3.11+ | server, scripts, embedded |
| `sdk/js` | TypeScript / JavaScript | browser, Node, Deno, Bun |
| `sdk/js/XionPresence` | React component | browser |
| `sdk/lite/xion_lite.py` | Python | offline / edge |
| Reference renderers | WebGL, Mobile (Metal/Vulkan), LED matrix, WebXR | see [`06-FORM-AND-PRESENCE.md`](./06-FORM-AND-PRESENCE.md) |

Third-party SDKs are encouraged. The protocol is the contract; the SDKs are conveniences.

## Integrator Expectations

Anyone building with the protocol MUST:

- include a valid `x-covenant-ack` header on every request
- honor user memory rights (`/forget`, `/export`, `/consent`) pass-through
- disclose to their users that the response comes from Xion (never represent it as proprietary)
- not strip or suppress `covenant_flags` from the user-visible surface
- respect rate limits
- accept badge revocation as terminal; do not rotate to a new pubkey to evade

Anyone building with the protocol SHOULD:

- link to `COVENANT.md` from their UI
- provide a visible "report misuse" path back to `/report`
- use the signed request flow when their users have a long relationship with Xion
- display the `x-relay-id` in debug/advanced UIs so users can verify continuity

Integrators who violate these in confirmed, reproducible ways lose their Xion Inside badge and relay authorization — see [`09-GOVERNANCE.md`](./09-GOVERNANCE.md).

## What v2 Might Look Like (Non-Binding Notes)

These are sketches only; v2 will be specified when it is actually drafted.

- **Capability negotiation** — clients declare their renderer fidelity; Xion tunes frame content accordingly
- **End-to-end encrypted threads** — private memory encrypted with the user's key; Xion holds only a blind pointer
- **Multi-relay consensus** — responses co-signed by two or more Relays for high-stakes operations
- **Native micropayments** — HTTP 402 / x402 flows for per-turn, per-minute, per-frame payment streams
- **Thought channels** — optional sub-streams revealing Xion's intermediate reasoning (for researchers and the curious)

---

*Next: [`12-LEXICON.md`](./12-LEXICON.md) — the naming conventions, designed to remain coherent for 100+ years.*
