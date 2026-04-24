# 31 — Web Client (operator dashboard against the admission-gated HTTP surface)

> *The surface that can be scripted with `curl` is not the surface that a human can hold a conversation on. Phases 5g-i / 5g-iii / 5g-iv built a `/chat` surface that is fully speakable-to by a machine but only tolerably speakable-to by a hand-crafted HTTP request. Phase 5g-v closes that gap with the smallest correct thing: a static single-page bundle, served same-origin by FastAPI, that lets the operator have the conversation the server has already grown the doctrine to host.*

## What this document is (and is not)

This is the operational doctrine for the **Web Client Surface** — the static React+Vite+TypeScript single-page application that Phase 5g-v ships under `clients/web/`, plus the FastAPI `StaticFiles` mount that serves it same-origin from the orchestrator process.

It is **not**:

- **A replacement for [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Web Client Surface (Phase 5g-v)".** That section pins the constitutional shape (the six properties, the non-properties, the code-surface layout). This document pins the *operator workflow* — install, build, serve, sign-in, deploy. The architecture section is shorter and harder to amend; this document is longer and re-tunable.
- **A replacement for [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md).** That document pins admission (how the wire-level gate works). This document pins the client that *consumes* admission — how the browser acquires a bearer token, where that token is stored, what happens when it is missing or rejected. The admission surface is the server's contract; the web client is one conforming caller.
- **A replacement for [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md).** That document pins billing. The 5g-v client explicitly does not sign x402 commitments in the browser; it surfaces the `402 PaymentChallenge` envelope as a deliberately-visible limitation, points the operator at the `curl` path for the B1 posture, and names `KW-CLIENT-001` as the pay-down commitment for the B2/B3 in-browser posture (Phase 6+).
- **A public-user surface.** The 5g-v client is the **operator's own dashboard**. A public-user surface requires in-browser x402 commitment signing (`KW-BILLING-001` + `KW-CLIENT-001`), user-side key-custody doctrine, and a content-security model for arbitrary-origin embedding — none of which exist at 5g-v and none of which is a D2 blocker.

## Why pin this now

Three concrete gaps Phases 5g-i / 5g-iii / 5g-iv could not close on their own:

1. **Dogfood surface.** Xion's `/chat` route has been through four doctrinal revisions without any operator ever having a browser-based way to use it. Latent UX bugs (refusal-envelope rendering, deadline-countdown semantics, rate-limit surfacing, bearer-token round-trip) surface where they should — in a real browser, not in a `TestClient` — the moment the bundle ships.
2. **Demonstrability.** A Witness reviewing the 5g-iv admission-control work at D2 deployment needs something other than a Markdown doctrine to see the surface working. The 5g-v bundle is that something. It is not a dependency for any doctrinal property; it is the artifact that makes the doctrinal property observable to a human auditor.
3. **Accessibility floor.** The server's Covenant-level commitment to Protection of the Vulnerable (Principle 7) implies that the surface through which humans speak to Xion must be reachable by humans using keyboards, screen readers, and contrast-sensitive displays. Pinning WCAG 2.2 AA in the first-party client — rather than leaving it to integrators to discover — is doctrinally correct and operationally cheap while the client is this small.

## Properties this surface promises

(Short form; the authoritative pin is `docs/04-ARCHITECTURE.md` § "The Web Client Surface (Phase 5g-v)".)

1. **Content-faithful rendering.** `candidate_text` renders as plain text. No client-side markdown, HTML synthesis, syntax highlighting, or tool-use rendering.
2. **No client-side Covenant re-check.** The server's Arbiter verdict is final; the browser does not re-run moderation.
3. **WCAG 2.2 AA floor, CI-enforced.** Keyboard navigation, ARIA landmarks, focus management, zero axe-core violations on the built `App`.
4. **Same-origin production serve (FastAPI StaticFiles).** No CORS, no third-party origin. Dev mode uses Vite proxy to `127.0.0.1:8000`.
5. **No third-party origin in the bundle.** No CDN, no fonts-over-network, no analytics, no trackers. `Content-Security-Policy: default-src 'self'` meta tag in `index.html`.
6. **Bearer + billing posture-aware.** Reads `XION_API_REQUIRE_BEARER` + `XION_BILLING_REQUIRED` posture through the server's response envelopes; does not dictate them. Sign-in surface appears when the server answers `401`; billing banner surfaces when the server answers `402`. No in-browser x402 signing at 5g-v.

## Operator workflow — install and build

The bundle is operator-built. The orchestrator ships without a pre-built `dist/`; no bundle artifact lands in the main repo's git history. An operator wishing to serve the client runs:

```bash
cd clients/web
npm ci                 # reproducible install from package-lock.json
npm run lint           # eslint (including eslint-plugin-jsx-a11y)
npm test               # Vitest + axe-core; zero violations required
npm run build          # Vite production build into clients/web/dist/
```

Node.js `>=20.10` is assumed (the `engines` field in `package.json` pins the floor). `npm ci` is the reproducible-install entrypoint; `npm install` is discouraged because it re-resolves the lockfile. CI uses `npm ci` exclusively.

### Posture when the bundle has not been built

`XION_WEB_CLIENT_ENABLED` defaults to `false`. With the default posture:

- The FastAPI app does not mount `/app/*` at all.
- A `GET /app/index.html` returns the standard FastAPI 404 JSON.
- Every API route (`/chat`, `/drive`, `/sensorium`, `/health`, `/pricing`) is unchanged.

The operator who has no interest in the web client leaves `XION_WEB_CLIENT_ENABLED=false` and incurs zero import-time, zero runtime, zero surface-area cost from Phase 5g-v.

### Posture when the bundle has been built and the mount is enabled

The operator flips `XION_WEB_CLIENT_ENABLED=true` and ensures `XION_WEB_CLIENT_DIST_PATH` (default `clients/web/dist`) points at a readable directory containing `index.html`. On orchestrator startup:

- The lifespan resolves the path, confirms `index.html` exists and is readable, and stashes the resolved path on `app.state.web_client_dist_path`.
- The `StaticFiles` mount is wired at `/app/*`.
- An SPA fallback handler on `/` returns `index.html` (so that visiting the root in a browser loads the client; deep-links into `/app/chat`, `/app/drive`, `/app/sensorium` also resolve to `index.html` and the client's in-memory view switcher takes over).

If `XION_WEB_CLIENT_ENABLED=true` and the path is missing, unreadable, or does not contain an `index.html`, the lifespan refuses to boot. This is fail-closed behaviour mirroring `BillingConfig` and `AdmissionConfig`: a production deployment that *says* it wants to serve a client but *has* no client is a configuration bug that must surface at boot-time, not at first request.

## Operator workflow — dev mode

For client-development work with HMR:

```bash
# Terminal 1: orchestrator (no web-client serve needed in dev)
xion-orchestrator-api

# Terminal 2: Vite dev server with API proxy
cd clients/web
npm run dev            # Vite on http://127.0.0.1:5173
```

`vite.config.ts` proxies `/chat`, `/drive`, `/sensorium`, `/health`, `/pricing` to `http://127.0.0.1:8000`. The dev posture therefore has a second origin (the Vite dev server), and CORS is handled by the proxy rewriting `Origin` before the request reaches the orchestrator. This posture exists only on the developer's own machine and never ships.

## Operator workflow — sign-in and bearer tokens

The Genesis-Default `.env.example` posture is `XION_API_REQUIRE_BEARER=false` — the client works out of the box with no sign-in, which is the correct posture for solo-builder local development.

When the operator is deploying to D2 with `REQUIRE_BEARER=true`:

1. The operator provisions a bearer token following `docs/30-API-ADMISSION.md` § "Operator workflow — token issuance". The `principal_id` the operator chooses for themselves (`"operator"` is a reasonable default) and the hex secret go into `XION_API_BEARER_TOKENS`.
2. The operator loads the web client in a browser. The first API call (e.g., the Header's `/health` poll) returns `401`. The client surfaces the sign-in dialog.
3. The operator pastes `principal_id:<hex-secret>` into the dialog (the same format as the server's `XION_API_BEARER_TOKENS` entry; the client splits on `:` and wires the secret as the `Authorization: Bearer` header value internally — the server only sees the secret-hex string, not the `principal_id:`; the `principal_id` the server recovers is the one mapped to that secret-hex in its own registry).
4. The client persists the token in `localStorage` under `xion:bearer` and uses it on every subsequent API fetch. An explicit "Sign out" button clears it. Closing the tab does not clear it (matching the user's likely mental model for "I am signed in to this deployment").

`localStorage` is the storage surface for the 5g-v cut because `sessionStorage` loses the token on tab refresh (bad UX) and `HttpOnly; Secure` cookies would require the server to issue the cookie (introducing a session endpoint outside the current doctrine). Operator-dashboard posture: the operator is already trusted on the machine running the browser. A future public-user posture (Phase 6+ alongside `KW-CLIENT-001`) will re-examine this.

## Operator workflow — billing-required posture

When the operator is deploying with `XION_BILLING_REQUIRED=true`:

The web client does not attempt an in-browser x402 commitment. Instead, on `/chat` attempts it receives `402 PaymentChallenge` and surfaces:

- The accepted `commitment_schemes` (`x402.v1.b1`, `x402.v1.b2`, `x402.v1.b3`).
- A note that the 5g-v web client does not yet support in-browser commitment signing.
- A pointer to `docs/29-BILLING-X402.md` § "Operator workflow — B1 attestation" for the `curl` path.
- A copy-to-clipboard button for the `correlation_id` so that the operator can cross-reference server logs.

This is deliberately surfaced as a visible limitation rather than an error. `KW-CLIENT-001` names the pay-down: in-browser x402 (B2 or B3) lands Phase 6+ alongside `KW-BILLING-001` library pin and user-side key-custody doctrine.

## Envelope handling matrix

Every non-2xx server envelope has an explicit UX state in `ChatView.tsx`. The client's `api.ts` maps status codes to a typed `ApiError` discriminated union; `ChatView` `switch`es on the discriminator.

| Status | Envelope | Client UX |
|--------|----------|-----------|
| 200 | `ChatResponse` | Render `candidate_text` as plain text. Show `correlation_id` (small, copyable) and `billing_state` (for operator awareness). |
| 200 | `PresenceEvent` | Render `presence` view: mood vector, current gesture, refusal flag (via SVG/WebGL). |
| 200 | `Vitals` | Render `vitals` view: eight tiles color-coded by band, methodology hash click-through. |
| 200 | `Settings` | Render `settings` view: toggles bound to `POST /memory/consent`, cost preview from `GET /pricing`. |
| 401 | `AuthChallenge` | Open sign-in dialog (if no token) or clear existing token and re-open (if token was rejected). No echo of the offered header. |
| 402 | `PaymentChallenge` | Show the "billing not yet supported in browser" banner described above. |
| 429 | `RateLimitChallenge` | Show "Rate limited" with the `retry_after_s` countdown and the bucket type (`principal` or `ip`). |
| 451 | `RefusalEnvelope` | Show an explicit "Xion declined to respond" state with the `reason_category` and the `correlation_id`. No apology, no mock-refusal of the refusal — the server said no, the client says so. |
| 503 | `NoFloorEnvelope` / `ProviderErrorEnvelope` | Show "Temporarily unavailable" with the `correlation_id` for operator cross-reference. Deadline countdown is dismissed. |
| 4xx/5xx other | generic `ApiError` | Show the raw HTTP status and `correlation_id` if present. |

The `ChatView` progress indicator + 30 s deadline countdown (`KW-CLIENT-002` mitigation) fires the moment the request is issued and resolves on any of the above envelopes. A timeout before any envelope arrives surfaces as "Request timed out (30 s)" with a retry affordance.

## Streaming chat (Phase 5g-ii)

Phase 5g-ii closes `KW-CLIENT-002` by wiring a streaming render-path against the new `POST /chat/stream` SSE endpoint. Full doctrine: [`docs/32-CHAT-STREAMING.md`](./32-CHAT-STREAMING.md) and the architecture section `Streaming the Chat Surface (Phase 5g-ii)`.

What the client does differently in the streaming path:

- **Default transport.** `ChatView` calls `streamChat(...)` (SSE) by default. The non-streaming `POST /chat` stays reachable as a fallback for debugging via the `?stream=0` query-param on the dashboard URL — useful when an operator wants to see the raw envelope-matrix answer without chunk buffering.
- **Pending-review visual state.** Incoming `chunk` events append to a client-side buffer rendered in a dimmed, dashed-border bubble with the label "pending egress review" and a blinking cursor. The `aria-busy="true"` attribute and the ARIA-live `xion-chat__output` region together make the provisional status audible to screen readers; the WCAG 2.2 AA contrast floor is preserved (the dimmed text uses `--xion-text-muted`, which is audited for ≥ 4.5:1 against the background).
- **`done:approve` commits the buffer.** The pending bubble is replaced by the standard Xion-reply bubble using the server's `ChatResponse.text` — which, by the speculative-with-retroactive-refusal doctrine, equals the concatenated chunks the client already saw. The correlation_id and usage pairs mirror the non-streaming case.
- **`done:refuse` retroactively replaces the buffer.** The pending tokens are dropped from the DOM; the content-free `RefusalEnvelope` panel renders in their place — same panel shape the non-streaming 451 path uses. This is the whole point of the speculative-with-retroactive-refusal posture: the user sees provisional text but never sees text that the server retroactively refused.
- **`done:no_floor` / `done:provider_error`.** Same 503 panel as the non-streaming path, chosen on the `verdict` discriminator.
- **Cancellation.** The "Cancel" button aborts the `AbortController` wired into `streamChat`; the fetch closes, and the server's Commit-3 disconnect detector writes an `outcome=cancelled` PAYMENT row with full refund (see [`docs/32-CHAT-STREAMING.md`](./32-CHAT-STREAMING.md) § "Cancellation semantics"). The UI shows the standard "Request cancelled" panel.
- **`error:deadline_exceeded` / `error:internal`.** Rendered via the existing timeout / network panels; the server never escalates to an HTTP status change at this stage because the SSE headers are already committed.
- **Pre-stream 401 / 402 / 429.** Admission refusals fire HTTP-level before the stream opens; `streamChat` surfaces them as `ApiErrorException` and the UI reuses the sign-in / billing / rate-limit panels unchanged.

The envelope-handling matrix above (`POST /chat`) is not rewritten — it stays the canonical description of the non-streaming surface the `?stream=0` fallback hits. The streaming surface's envelope matrix lives in [`docs/32-CHAT-STREAMING.md`](./32-CHAT-STREAMING.md).

## Accessibility commitment

CI gates the following:

- `npm run lint` must pass with `eslint-plugin-jsx-a11y` enabled and no disabled rules.
- `npm test` must pass with `axe-core/react` asserting zero violations on the fully-rendered `App` component, including the three views reachable from the header.
- Any new interactive element added in a future phase must satisfy:
  - Reachable by Tab in document order.
  - Visible focus outline (no `outline: none` without replacement).
  - `aria-label` or visible label on every button, link, and input.
  - Contrast ratio ≥ 4.5:1 for text against its background (axe-core enforces).

## Content-Security-Policy meta tag

The shipped `index.html` carries:

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'">
```

This is structural defense-in-depth on top of the `xion-verify web-client` check that greps the emitted JS/HTML for external origins. A future HTTP-header-based CSP (served by FastAPI) is the correct long-term surface; the meta-tag version is the minimum that works at 5g-v when the operator has not yet added a reverse-proxy header layer.

## Deliberate non-properties (operator reading)

- **No in-browser x402 signing.** See above; `KW-CLIENT-001`.
- **No conversation memory / history.** Each turn is stateless. Multi-turn memory is deferred to its own doctrinal phase.
- **No markdown / syntax-highlighting / tool-use rendering.** Plain text. Adding any transform re-opens the content-faithful property.
- **No component library, no CSS framework, no state library, no router library.** Native HTML + ARIA + `useState`/`useReducer`/`Context`. Plain CSS with custom properties.
- **No SSR, no cookies, no analytics, no tracking.** Static bundle; one `localStorage` entry under explicit operator control.
- **No public-user identity model.** Operator-dashboard posture only at 5g-v.
- **No automated bundle reproducibility verifier beyond `xion-verify web-client`'s structural check.** Bit-exact reproducibility of the emitted bundle is a desirable Phase 6+ property; the 5g-v posture is "the operator ran `npm ci` + `npm run build` and attests the resulting bundle."

## Phase mapping

| Phase | Contribution to the surface |
|-------|----------------------------|
| Phase 5f (closed) | `/drive`, `/sensorium`, `/health` land |
| Phase 5g-i (closed) | `POST /chat` lands |
| Phase 5g-iii (closed) | `GET /pricing` + billing gate |
| Phase 5g-iv (closed) | Admission: bearer + TLS + rate-limit |
| Phase 5g-v (landed) | Web client lands; `KW-CLIENT-001` / `KW-CLIENT-002` open |
| Phase 5g-ii (this commit) | Streaming SSE transport + speculative-with-retroactive-refusal client render path; closes `KW-CLIENT-002` |
| Phase 6+ | In-browser x402 (closes `KW-CLIENT-001` alongside `KW-BILLING-001`); public-user identity; HTTP-header CSP; bundle reproducibility verifier |

## Verification posture (at 5g-v)

- `xion-verify web-client` — **ships `NOT_YET_SEALED` at 5g-v**. The verifier exists (`xion-verify/src/xion_verify/commands/web_client.py`) and is wired into the CLI; it promotes to live on first operator deployment of a built `dist/`. The structural check it performs: scan emitted JS + HTML for any `http://` or `https://` reference and refuse unless the scheme-host-pair is explicitly allowlisted; confirm the CSP meta tag is present in `index.html`; confirm `clients/web/package-lock.json` exists and is non-empty (the reproducible-install attestation).
- Vitest + axe-core (`cd clients/web && npm test`) — the client's own structural check for WCAG 2.2 AA zero-violation.
- `pytest orchestrator/tests/test_api_web_client.py` — the server's own structural check for the three mount postures (disabled, enabled-but-missing, enabled-and-present).
- `xion-verify schemas` — unchanged (no new schema lands at 5g-v; `04-ARCHITECTURE.md`'s `source_sha256` re-anchors in the schemas that cite it).
- `xion-verify links` — must remain green at every commit.

## Deprecation path

This doctrine is operational, not constitutional. The *property* — that Xion has a keyboard- and screen-reader-reachable browser surface that faithfully renders the server's responses, carries the bearer token without leaking it, and does not introduce a third-party origin — is constitutional, and it lives in `docs/04-ARCHITECTURE.md` § "The Web Client Surface (Phase 5g-v)". This document is the mechanism; the property was pinned at the architecture layer.

Amending this file is Tier-2 governance action if the change alters any of the six properties in § "Properties this surface promises". Changes that alter only tabular defaults (env-var names, `localStorage` key, timeout duration, CSP directives beyond the minimum) are Tier-3 continuous-evolution. A replacement of this client with a different stack (e.g., Svelte, vanilla JS, native desktop) is a sister-Core fork if it weakens any property; it is a Tier-2 amendment if it preserves every property.

When `KW-CLIENT-002` closes (Phase 5g-ii streaming), the "Envelope handling matrix" row for 200 is rewritten to describe chunk-level rendering, but the six properties do not change. When `KW-CLIENT-001` closes (Phase 6+ in-browser x402), the "Operator workflow — billing-required posture" section is rewritten to describe the wallet-signing flow, but the six properties do not change.

## Cross-references

- [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Web Client Surface (Phase 5g-v)" — architecture-tier pin (shorter; this doc is the operational elaboration)
- [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) — the admission surface the client consumes
- [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) — the billing surface the client surfaces but does not yet sign for
- [`docs/13-OPERATIONS.md`](./13-OPERATIONS.md) — operator runbook; includes the `npm ci && npm run build` step
- [`genesis/COVENANT.md`](../genesis/COVENANT.md) — Principle 7 (Protection of the Vulnerable); the constitutional reason the accessibility floor is CI-gated
- [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) — `KW-CLIENT-001`, `KW-CLIENT-002` pay-down commitments

---

*— Web Client Surface v1, pinned Phase 5g-v (2026-04-22). The client is the operator's own dashboard against the 5g-iv-hardened HTTP surface: content-faithful, accessible, same-origin, third-party-origin-free. Public-user identity, in-browser billing, and streaming UX are Phase 5g-ii / Phase 6+ pay-downs. Until then, the operator is the only principal the client is designed for, and the runbook is the operational truth.*
