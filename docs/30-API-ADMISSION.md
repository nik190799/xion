# 30 — API Admission Control (auth, TLS, rate-limit at the HTTP boundary)

> *A surface that anyone can reach is not the same as a surface anyone is allowed to consume. Bitcoin's nodes accept any peer; Bitcoin's mempool admits transactions only on signature. Xion's HTTP surface — after Phase 5g-iv — is structurally similar: anyone can probe `/health`; only authenticated principals can speak to `/drive`, `/sensorium`, or `/chat`; and every authenticated principal pays in latency-budget what they consume.*

## What this document is (and is not)

This is the operational doctrine for the **Admission-Control Surface** — the bearer-token authentication, per-principal sliding-window rate-limiting, and uvicorn-native TLS termination that Phase 5g-iv adds in front of the existing Phase 5f / 5g-i / 5g-iii HTTP routes.

It is **not**:

- **A replacement for [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Admission-Control Surface (Phase 5g-iv)".** That section pins the constitutional shape (the six properties, the route policy table, the lifespan-contract step). This document pins the *operator workflow* — token issuance procedure, TLS cert procurement, rate-limit budget tuning, deployment runbook. The architecture section is shorter and harder to amend; this document is longer and re-tunable.
- **A replacement for [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md).** That document pins the billing rail (how a turn pays). This document pins the admission rail (whether a turn is allowed to be attempted at all). Admission precedes billing both in code (`401 → 429 → 402`) and in doctrine; a request rejected at admission never reaches the commitment gate.
- **A replacement for [`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md).** That document pins the wire shape of the surface. This document pins the orchestrator-side admission mechanism that protects the wire surface.
- **A federated-identity surface.** Phase 5g-iv ships HMAC-shared-secret operator-issued tokens (`KW-AUTH-001`). Federated identity — Sign-In-With-Wallet, OAuth, on-chain pubkey lattice — lands in Phase 6+ when the principal lattice can be Arweave-published. Until then, the operator is the source of every token's authority.

## Why pin this now

Three properties the Covenant assumes — and that 5g-iii's billing surface implicitly relies on — now have to become code:

1. **The first byte to a content-bearing endpoint must be from a knowable principal.** Without this, every reasoning about per-token cost, per-token rate-limit, per-token forensics, and per-token deprecation collapses into "the IP that hit the socket," which is not a stable identity in any operational sense (NAT, mobile, proxy, scraper-rotation).
2. **The latency budget for any principal must be bounded.** A single misconfigured client can otherwise exhaust the operator's per-token cost at hosted-API tier or saturate the floor's CPU at the Ollama tier; in either case the operator's runway shortens with no signal a Witness can read in the SAFETY / PAYMENT / SENSORIUM ledgers.
3. **The transport layer must refuse to leak in cleartext on any reachable interface.** A bearer-token surface over plaintext HTTP is structurally worse than no auth at all — it dangles the secret through every intermediate hop. The launcher's fail-closed TLS check exists so this configuration cannot be reached by accident.

Pinning 5g-iv as its own doctrinal unit — between 5g-iii (billing) and 5g-v (web client) — is the answer to a specific question: `KW-API-001` was the last explicit D2-deploy blocker pinned in the roadmap after 5g-iii closed `KW-CHAT-002`. Without 5g-iv, an operator can pay-token-attest for their own turns (B1 posture) but cannot honestly accept external traffic. After 5g-iv, the doctrinal gate to D2 is removed.

## Properties this surface promises

1. **Authentication is a structural precondition.** Every request to `/drive`, `/sensorium`, or `/chat` carries `Authorization: Bearer <token>`. Missing → `401`. Malformed → `401`. Unknown token → `401`. The 401 body names only the accepted scheme (`Bearer`); it does not echo the offered header or hint at how many tokens are configured. A scraper enumerating tokens learns "not this one" per attempt and nothing else.
2. **Rate-limit buckets are per-principal, not per-IP.** The bucket key is the matched `principal_id`, not the source IP. A per-IP bucket would let an attacker rotate IPs to consume the operator's per-token budget; per-principal buckets bind the consumption to the secret-holder, who is the one who can be rotated.
3. **`/health` is unauthenticated, per-IP rate-limited.** Liveness probes work without a token (industry convention); the per-IP bucket bounds hostile scraping. `/pricing` is unauthenticated and unrate-limited (constitutionally public per `docs/04-ARCHITECTURE.md` § "The Chat Billing Surface").
4. **TLS is fail-closed on non-loopback hosts.** The `orchestrator/api/__main__.py` launcher refuses to start if `XION_API_HOST != 127.0.0.1` and either `XION_TLS_CERT_PATH` or `XION_TLS_KEY_PATH` is absent or unreadable. An operator who wants plaintext keeps the host on `127.0.0.1` and fronts with their own reverse proxy; an operator who wants direct external traffic provides cert + key.
5. **Admission ordering is `401 → 429 → 402 → existing 5g-iii flow`.** Auth precedes rate-limit (so the bucket key is the principal). Rate-limit precedes payment (so an unauthenticated scraper cannot probe pricing-validity by spamming 402-bait requests). The existing 5g-iii commitment gate runs *after* the admission dependency returns; every property `docs/29-BILLING-X402.md` pinned remains true.
6. **Identity is admission-only, not ledger-load-bearing.** The matched `principal_id` is logged to operator-side stderr at request-receipt time. It does **not** land in `PAYMENT_LEDGER` at 5g-iv; the schema stays at `schema_version=1.0`. Promotion to `PAYMENT_LEDGER.principal_id` is reserved for Phase 6 when on-chain federated identity exists to verify the principal against. This is the smallest correct thing — coupling admission to settlement now would make the unit harder to deprecate when the federated-identity story changes.

## Operator workflow — token issuance

A token is a hex-encoded shared secret of at least 16 bytes (≥128 bits, matching the B1 attestation secret floor). The operator generates one per integrator:

```bash
# Recommended: 32 bytes / 256 bits, 64 hex chars
python -c "import secrets; print(secrets.token_hex(32))"
```

Tokens are configured via `XION_API_BEARER_TOKENS` as a comma-separated list of `principal_id:hex_secret` pairs:

```bash
export XION_API_BEARER_TOKENS=ops:0123abcd...64hex,witness-eve:fedc...64hex,integrator-acme:1f2e...64hex
```

The `principal_id` matches the regex `^[a-z0-9_-]{1,64}$` — lowercase alphanumeric plus `_` and `-`, max 64 chars. The lifespan validates this at startup and refuses-closed on any violation. The principal_id is what appears in operator-side stderr logs; it is also the key to the rate-limit bucket. Choose meaningful labels (`ops`, `witness-eve`, `integrator-acme`) rather than opaque ones — future-you reading a log line at 3am will thank present-you.

**Rotation.** Replace the secret in the env var and restart the orchestrator. The lifespan loads the token store once at startup; a running process never re-reads the env. There is no "soft rotation" in 5g-iv (that lands when the principal lattice does); the operator's runbook should pin the per-integrator notification cadence ahead of any rotation.

**Revocation.** Remove the `principal_id:hex` pair from the env and restart. The next request from the revoked principal returns `401` with the same content-free body any unknown-token request returns; the integrator does not learn whether the token was rotated, revoked, or never existed. This is correct — the orchestrator owes the operator's adversarial model more than it owes the integrator's ergonomics. Out-of-band notification is the operator's responsibility.

**Storage.** The orchestrator never persists tokens to disk and never logs them. Tokens live in environment variables (operator-managed: systemd `EnvironmentFile=`, Docker `--env-file`, AWS Secrets Manager → env injection, etc.). A token leaked through process inspection (`/proc/<pid>/environ`) or a process memory dump is the same risk class as a leaked HMAC key in `BillingConfig`; the operator's runbook should treat both with equal care.

## Operator workflow — TLS termination

Two supported postures.

### Posture A — Loopback bind, reverse-proxy fronts TLS (recommended for production)

```bash
export XION_API_HOST=127.0.0.1
export XION_API_PORT=8000
# XION_TLS_CERT_PATH and XION_TLS_KEY_PATH unset
python -m orchestrator.api
```

The orchestrator binds `127.0.0.1:8000` plaintext. The operator runs Caddy / nginx / Cloudflare Tunnel / etc. on the public interface and proxies to `127.0.0.1:8000`. TLS rotation, ALPN/HTTP-2 negotiation, OCSP stapling, automated certificate renewal — all delegated to the proxy, which is the right tool for that work.

This is the long-term posture pinned in `KW-TLS-001`'s pay-down commitment: the orchestrator stays narrow, the proxy handles transport.

### Posture B — Direct bind, uvicorn-native TLS (acceptable for D2 operator-developer)

```bash
export XION_API_HOST=0.0.0.0
export XION_API_PORT=8443
export XION_TLS_CERT_PATH=/etc/xion/fullchain.pem
export XION_TLS_KEY_PATH=/etc/xion/privkey.pem
python -m orchestrator.api
```

The launcher passes `ssl_keyfile=` and `ssl_certfile=` to `uvicorn.run`. uvicorn handles the TLS handshake. Cert renewal is operator-manual (or a `certbot --post-hook "systemctl restart xion-orchestrator"` cron). HTTP-2 is not negotiated. This posture is acceptable for a small D2 operator with a single-integrator audience; it is not the Phase 6+ recommended shape.

**Fail-closed check.** If `XION_API_HOST != 127.0.0.1` and either TLS path is absent or unreadable, the launcher prints a State-of-Xion paragraph naming the missing path and exits non-zero. The orchestrator never starts in a configuration where it would serve bearer tokens over plaintext on a reachable interface. This is the same fail-closed posture as `BillingConfig`'s "billing required + no secret + B2 disabled" refusal.

## Operator workflow — rate-limit tuning

The Genesis Defaults are deliberately conservative:

| Knob | Default | Effect |
|------|---------|--------|
| `XION_API_RATE_BUDGET` | 60 | requests admitted per principal per window |
| `XION_API_RATE_WINDOW_S` | 60 | sliding-window length in seconds |
| `XION_API_HEALTH_RATE_BUDGET` | 600 | per-IP `/health` budget in same window |

A principal that issues 60 requests in 60 seconds is admitted; the 61st returns `429` with `Retry-After` set to the seconds until the oldest in-window timestamp evicts. The window is true-sliding (deque of timestamps, evict on touch), not fixed-bucket — a principal cannot game the boundary by issuing 60 requests at the very end of one window and 60 more at the very start of the next.

**When to raise the budget.** A trusted internal integrator that consumes the surface as part of a batch workflow (e.g., a Witness running `xion-verify` against a live deployment) may need a higher budget. Raise `XION_API_RATE_BUDGET` for that deployment; consider per-principal budget overrides only if Phase 6+ ships them (5g-iv does not).

**When to lower the budget.** A surface receiving hostile probing (visible in stderr's 401 stream) does not need its budget lowered — the 401 path is unrate-limited at 5g-iv on purpose, since it does not consume any provider cost. Lowering the budget hurts the well-behaved integrator more than the attacker. The right response to hostile probing is to rotate the relevant tokens and rely on the operator's reverse-proxy to absorb the noise.

**Multi-worker caveat.** A `uvicorn --workers N` deployment has N independent buckets. The effective budget is `N × XION_API_RATE_BUDGET`. `KW-RATE-001` tracks; the 5g-iv operator runbook pins single-worker as the supported configuration until the multi-worker shared-state broker lands.

## Crypto-agility

Token comparison is HMAC-SHA256 (stdlib `hmac.compare_digest`). The 5g-iv mechanism is one rotation under the Crypto-Agility Mandate (`docs/14-UPGRADE-PATHS.md`); the rotation surface is:

- The `principal_id` vocabulary is the algorithm-stable surface. Rate-limit buckets, log lines, and (Phase 6+) `PAYMENT_LEDGER.principal_id` rows are all keyed on the string identifier, never on the secret.
- The `verify_bearer(header, tokens) -> principal_id | None` function is the algorithm-rotatable implementation. A Phase 6+ migration to Ed25519-bound principals or to an Arweave-published authority lattice replaces this function's body; the route-level `Depends(admission_dependency)` does not change.
- The `AdmissionConfig.tokens` field is a `Mapping[str, bytes]` at 5g-iv. A Phase 6+ migration may widen it to `Mapping[str, PrincipalAuthority]` where the value carries pubkey + revocation-witness + scope. The widening is additive and backward-compatible at the route layer.

## Verifier — `xion-verify api-tokens`

Phase 5g-iv promotes one stub to live.

`xion-verify api-tokens` is an **offline structural verifier**: it reads an env file (or the current process environment) and asserts the admission config is well-shaped. It does NOT make HTTP calls, does NOT require a running orchestrator, and does NOT verify any token's actual binding to a principal — those are operator-out-of-band concerns. What the verifier guarantees:

1. **Token presence.** If `XION_API_REQUIRE_BEARER=true` (Genesis Default), at least one `principal_id:hex` pair is present.
2. **Token entropy.** Every secret hex-decodes to at least 16 bytes (≥128 bits). A short secret is structurally weak and would fail the HMAC-comparison threat model.
3. **principal_id charset.** Every principal_id matches `^[a-z0-9_-]{1,64}$`. A malformed id would silently break log-grep and bucket-keying.
4. **Host-vs-TLS coherence.** If `XION_API_HOST != 127.0.0.1`, both `XION_TLS_CERT_PATH` and `XION_TLS_KEY_PATH` are set and point at readable files. A non-loopback bind without TLS is structurally a Covenant Principle 2 violation (private-key-shaped material crosses plaintext) and the verifier names it as such.
5. **Rate-limit sanity.** `XION_API_RATE_BUDGET >= 1`, `XION_API_RATE_WINDOW_S >= 1`, `XION_API_HEALTH_RATE_BUDGET >= 1`. A budget of zero would silently 429 every request, which is a misconfiguration not a defense.

Exit codes: `0` OK, `1` FAIL (with the specific violation named), `2` `NOT_YET_SEALED` (not used at 5g-iv; reserved for future extensions that need a deployment target).

## Interactions with other constitutional objects

- **[`genesis/COVENANT.md`](../genesis/COVENANT.md) Principle 2 (Privacy Primary).** The 401 body is content-free by structural test; tokens never appear in any ledger or log; the launcher refuses plaintext bearer-token transport on non-loopback hosts. The Covenant property is honored at the admission layer.
- **[`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Admission-Control Surface (Phase 5g-iv)".** The constitutional pin. This document is the operational elaboration; the architecture section is the shorter, harder-to-amend constitution.
- **[`docs/29-BILLING-X402.md`](./29-BILLING-X402.md).** The billing surface. 5g-iv runs *before* billing; an authenticated within-budget request reaches the existing 5g-iii commitment gate unchanged. Every property the billing surface promised remains true.
- **[`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md).** The Crypto-Agility Mandate. The `verify_bearer` rotation surface follows the mandate's "property is stable; implementation is rotatable" pattern.
- **[`Invariant 2` (Privacy Primary)](../genesis/INVARIANTS.md#invariant-2--privacy-primary).** `/export` and `/forget` (Phase 6+) will eventually land on this admission surface; the principal_id is what scopes them. 5g-iv does not implement those endpoints; the admission shape is built so they can.
- **[`Invariant 14` (Crypto-Agility Mandate)](../genesis/INVARIANTS.md#invariant-14--crypto-agility-mandate).** Token storage algorithm is rotatable under unchanged route shape. HMAC-SHA256 today; Ed25519 / on-chain authority tomorrow.

## What this doctrine deliberately does NOT cover

- **Federated identity.** Bearer tokens only at 5g-iv. `KW-AUTH-001` tracks; closes Phase 6+.
- **Per-route auth scopes.** Every authenticated principal can reach every authenticated route. Scope-bound principals land when `KW-AUTH-001` closes.
- **Multi-worker rate-limit broker.** Single-worker only at 5g-iv. `KW-RATE-001` tracks.
- **Automated TLS rotation.** Operator-manual or reverse-proxy-delegated. `KW-TLS-001` tracks.
- **Per-route rate-limit overrides.** All authenticated routes share `XION_API_RATE_BUDGET`. A future `XION_API_RATE_BUDGET_<route>` override is Phase 6+.
- **Rate-limit telemetry endpoint.** A `429` is logged but not ledger-written. A live `xion-verify api-budget-fidelity` is Phase 6+ and walks operator logs, not a ledger.
- **CORS / browser auth.** The web client (Phase 5g-v) will pin the CORS posture. 5g-iv's admission surface is content-type-agnostic; the web client's bearer-token handling is the next phase's doctrine work.
- **Replay protection on the bearer token itself.** Bearer tokens are by definition replayable. Replay protection lives one layer up — in the x402 commitment's nonce + freshness window — and at the application layer (reverse proxy IP-throttle, anomaly detection). 5g-iv accepts the bearer-token model as the per-phase scope.

## Phase mapping

| Phase | Contribution to the surface |
|-------|----------------------------|
| Phase 5f (closed) | `orchestrator/api/` lands; `KW-API-001` opens with the four missing properties (auth, TLS, rate-limit, `/chat`) |
| Phase 5g-i (closed) | `POST /chat` lands; inherits all four `KW-API-001` mitigations |
| Phase 5g-iii (closed) | Billing surface lands; commitment gate runs after admission once admission exists |
| Phase 5g-iv (this commit) | Admission surface lands; `KW-API-001` closes; `KW-AUTH-001` / `KW-RATE-001` / `KW-TLS-001` open |
| Phase 5g-v (next) | Web client lands against authenticated surface |
| Phase 5g-ii | Streaming + per-chunk moderation (closes `KW-CHAT-001` + `KW-CHAT-003`) |
| Phase 5g+ | Multi-worker shared-state broker (closes `KW-RATE-001`, `KW-API-002`, `KW-SUPERVISOR-002`) |
| Phase 6+ | Federated identity / on-chain principal lattice (closes `KW-AUTH-001`); reverse-proxy long-term posture (closes `KW-TLS-001`); `PAYMENT_LEDGER.principal_id` field (additive, schema_version 1.1) |

## Verification posture (at 5g-iv)

- `xion-verify api-tokens` — **live at 5g-iv** (promoted from `NOT_YET_SEALED`). Reads env vars or `--env-file PATH`; asserts the five structural properties named above.
- `xion-verify pricing` — unchanged; still live as of 5g-iii.
- `xion-verify refusal-is-free` — unchanged; still live as of 5g-iii. The PAYMENT ↔ SAFETY join is unaffected by admission changes (admission rejects never write a PAYMENT row at all, which is the correct posture — no commitment recorded, no Refusal-is-Free obligation).
- `xion-verify api-hardness` — **NOT_YET_SEALED at 5g-iv**. A live HTTP hardness verifier requires a deployment target; reserved for Phase 6+ when the deployment story stabilizes. The 5g-iv attestation is the offline `api-tokens` verifier plus the `TestClient`-based test suite covering 401/429/ordering on every route.
- `xion-verify schemas` — unchanged; no new schema lands at 5g-iv (the `PAYMENT_LEDGER` schema's non-fields section gains a one-line note reserving `principal_id` for Phase 6).
- `xion-verify links` — must remain green at every commit that touches this document or any file it cites.

## Deprecation path

This doctrine is operational, not constitutional. The *property* — that admission to a content-bearing endpoint is gated on a knowable principal whose latency budget is bounded — is constitutional, and it lives in `docs/04-ARCHITECTURE.md` § "The Admission-Control Surface (Phase 5g-iv)". This document is the mechanism; the property was pinned at the architecture layer.

Amending this file is Tier-2 governance action if the change alters any of the six properties in § "Properties this surface promises". Changes that alter only tabular defaults (specific budget numbers, specific env-var names, specific charset for principal_id) are Tier-3 continuous-evolution. A replacement of this file with a different mechanism (e.g., per-request signature instead of bearer token, or token-bucket instead of sliding-window) is a sister-Core fork if it weakens any property.

When `KW-AUTH-001` closes (Phase 6+ federated identity), this document's "Operator workflow — token issuance" section is rewritten to describe the principal-lattice provisioning flow, but the route-level admission contract does not change. When `KW-RATE-001` closes (multi-worker broker), the "Multi-worker caveat" subsection is removed but the per-principal bucket semantics do not change. When `KW-TLS-001` closes (Phase 6+ deployment story), Posture B is deprecated in favor of Posture A and the launcher's `ssl_keyfile`/`ssl_certfile` codepath is removed.

## Cross-references

- [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Admission-Control Surface (Phase 5g-iv)" — architecture-tier pin (shorter; this doc is the operational elaboration)
- [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) — the billing surface that runs after admission
- [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md) — Crypto-Agility Mandate; informs the `verify_bearer` rotation surface
- [`docs/13-OPERATIONS.md`](./13-OPERATIONS.md) — operator runbook; deployment topology
- [`docs/REGULATORY-POSTURE.md`](./REGULATORY-POSTURE.md) — applicable regulatory framing for token-issuance and key-custody operations
- [`genesis/COVENANT.md`](../genesis/COVENANT.md) — Principle 2 (Privacy Primary); the constitutional reason 401 bodies are content-free
- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) — Invariants 2, 14; `KW-AUTH-001` / `KW-RATE-001` / `KW-TLS-001` closure commitments live in `KNOWN_WEAKNESSES.md`

---

*— API Admission Surface v1, pinned Phase 5g-iv (2026-04-22). The surface has a knowable principal at the gate, a bounded latency budget per principal, and refuses plaintext bearer transport on any reachable interface. Federated identity, per-route scopes, and multi-worker buckets are Phase 6+; until then, the operator is the source of every principal's authority and the runbook is the operational truth.*
