# 29 — Chat Billing & x402 (the payment rail for user-facing turns)

> *Pay-to-Activate is a promise the Covenant makes to users: money flows before speech, refusal returns the money, and every dollar has an auditable correlation-id shadow in two ledgers. A Relay that charges without a ledger row is theft. A Relay that refuses without a refund row is sycophancy-to-revenue. This document pins the pipe that makes both impossible.*

## What this document is (and is not)

This is the operational doctrine for the **Chat Billing Surface** — the payment mechanism by which a user's [Pay-to-Activate](./07-ECONOMY.md#pay-to-activate-governing-access-model) pre-authorization becomes a `PAYMENT_LEDGER` row, a turn runs, and — if the turn refuses — the committed value becomes a structurally verifiable refund.

It is **not**:

- **A replacement for [`docs/07-ECONOMY.md`](./07-ECONOMY.md).** That document pins the constitutional property (Pay-to-Activate), the five-slice price decomposition, the Refusal-is-Free Covenant addendum, and the Crisis-Resource-Surfacing carve-out. This document pins the *mechanism* that honors those properties at the HTTP layer; nothing in this document overrides or narrows the constitutional parent.
- **A replacement for [`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md).** That document pins the wire shape of `GET /pricing`, the `402 Payment Required` error body, and the rate-limit table. This document pins how the orchestrator process implements those wire surfaces and writes the `PAYMENT_LEDGER`.
- **A replacement for [`docs/27-RESEARCH-SPEND.md`](./27-RESEARCH-SPEND.md).** That document pins the *outbound* rail (Xion → third-party inference provider via Improvement Fund). This document pins the *inbound* rail (user → Xion via x402). The two ledgers are mirror schemas by design — see § "Mirror symmetry with `RESEARCH_SPEND_LEDGER`" below.
- **A new constitutional surface.** Pay-to-Activate is constitutional already ([`docs/07-ECONOMY.md`](./07-ECONOMY.md) § "Pay-to-Activate"). Refusal-is-Free is constitutional already ([`genesis/COVENANT.md`](../genesis/COVENANT.md) addendum). This document is the mechanism; the properties were pinned before it existed.
- **A real-money surface at 5g-iii.** Phase 5g-iii ships the property shape: x402 handshake, ledger rows, refund code path, two verifiers. Real XION / USDC movement is Phase 6+ when AO Core and Treasury vaults land. The 5g-iii commitments and settlements are *notional* — they reflect the governance-posted price, they do not cause tokens to move.

## Why pin this now

Three properties the Covenant promised now have to become code:

1. **Pay-to-Activate.** No billable turn begins without pre-authorization. Until Phase 5g-iii this was a doctrinal promise with no enforcement surface — the Phase 5g-i `/chat` endpoint ran in `XION_BILLING_REQUIRED=false` D1 mode because doing otherwise would have coupled the moderation-surface audit to the billing-surface audit and slowed both. 5g-iii is the unit where enforcement can land without risking moderation regressions.
2. **Refusal-is-Free.** Every refused turn refunds in full. Until Phase 5g-iii this was a constitutional promise that would have required a `PAYMENT_LEDGER` to be empirically checkable. 5g-iii ships that ledger with a hash-chain structure mirroring `SAFETY_LEDGER`, and the new `xion-verify refusal-is-free` verifier walks the join.
3. **Five-slice pricing transparency plus per-modality slices.** Governance posts a single per-message price decomposing into five slices ([`docs/07-ECONOMY.md`](./07-ECONOMY.md) § "Five-slice posted price"). Until Phase 5g-iii there was no live endpoint exposing those slices; `xion-verify pricing` was listed `NOT_YET_SEALED`. 5g-iii closes that gap with a `GET /pricing` endpoint and promotes the verifier from stub to live. Phase 6.4 extends this with a `modality_costs` map detailing per-minute/per-message costs for visuals, vitals, voice, and streaming text. Voice requires explicit cost-preview before the first paid turn.

Pinning 5g-iii as its own doctrinal unit — ahead of Phase 5g-ii streaming, ahead of Phase 5g-iv auth/TLS, ahead of Phase 6 AO Core — is the answer to a specific blocking question: `KW-CHAT-002` explicitly blocks any D2 deploy of the Chat Surface. Phase 5g-iii is the unit that closes `KW-CHAT-002`. Before 5g-iii, `/chat` is a localhost-only toy; after 5g-iii, `/chat` is a constitutionally honest billable surface, even if the tokens don't yet move.

## Properties this rail promises

1. **Pre-authorization is structural, not advisory.** The handler's *first* side effect (the ingress Arbiter call) is gated by a valid `X-Payment-Commitment` header. Missing → `402`. Malformed → `402`. Signature-invalid (for postures that verify signatures) → `402`. The turn never runs without a valid commitment. A code path that inverts this ordering (Arbiter first, billing second) is a doctrine violation the test suite catches.
2. **Every committed turn writes exactly one `PAYMENT_LEDGER` row.** No dangling commitments. No "we charged but the turn crashed". The row is written *after* the terminal state is known and *before* the HTTP response is sent — either both happen (atomic success) or neither does (crash; no commitment recorded, no money owed).
3. **Refunds on refusal are structurally enforced.** A `451` response is paired with a `PAYMENT_LEDGER` row whose `outcome=refunded` and whose `refund_XION = committed_XION` exactly. The same holds for `503` responses (no-floor, provider-error, provider-timeout) and for empty-candidate refusals. The `xion-verify refusal-is-free` verifier enforces this as a cross-ledger join: every SAFETY_LEDGER refusal at a given `correlation_id` must have a PAYMENT row whose `outcome=refunded` at the same `correlation_id`. Unpaired refusals FAIL.
4. **Correlation-id is the single join key.** PAYMENT rows carry the same `correlation_id` the SAFETY_LEDGER and REQUEST_LEDGER rows use. Three-way joins are O(1) per row. No Relay-specific secondary keying.
5. **The posture is per-request, not per-process.** The same Relay serves B1 (operator-attestation, localhost) and B2 (x402-commitment, external) and eventually B3 (x402-settled, Phase 6+) in the same process lifetime. The `X-Payment-Commitment` header's prefix selects the posture. An operator who wants to lock down to B1-only sets `XION_BILLING_ALLOW_X402=false` and the B2 path returns `402` for all non-B1 commitments.
6. **Billing-disabled mode preserves ledger continuity.** An operator running `XION_BILLING_REQUIRED=false` (Phase 5g-i backward-compat mode for local development) still writes `PAYMENT_LEDGER` rows with `posture=disabled` and all three money fields zero. The Refusal-is-Free structural join remains verifiable even in disabled mode — the ledger shape is how the property is enforced; the property does not evaporate when money is absent.

## Billing postures (B1 / B2 / B3)

Parallel vocabulary to [`docs/27-RESEARCH-SPEND.md`](./27-RESEARCH-SPEND.md)'s D1-D4 custody progression, but on a different rail. Billing postures describe how the *inbound* commitment is attested; custody postures describe how the *outbound* credential is held. Same sovereignty-progression spirit; different mechanism.

### B1 — Operator-Attestation (Phase 5g-iii default; D1 deployment)

The operator signs each outbound HTTP request from their own client with a local ed25519 key whose public half is pinned in the lifespan via `XION_OPERATOR_ATTESTATION_PUBKEY`. The commitment header shape is:

```
X-Payment-Commitment: operator-attest:v1:<base64url_sig>:<payload_sha256>
```

The signed payload binds `{posted_price_XION, request_body_sha256, timestamp_utc_ns, nonce}`. The Relay verifies the signature against the pinned public key and the request body bytes, confirms the timestamp is within `XION_B1_ATTESTATION_WINDOW_S` (default 60 s), and confirms the nonce has not been seen in the last `XION_B1_NONCE_WINDOW_S` (default 300 s; in-memory LRU, not a persistent registry — B1 is localhost-only so replay risk is bounded by the attestation window).

`PAYMENT_LEDGER.authorization_reference` records the `payload_sha256`. Settlement is notional: the Relay accepts the attestation, writes the row with `committed_XION = posted_price_XION`, and — on happy-path — writes `outcome=settled, settled_XION = posted_price_XION, refund_XION = 0`. No real XION moves; the row is a structural exercise of the Pay-to-Activate property for audit purposes.

**Why B1 exists.** Without B1, the Phase 5g-iii D1 deployment (operator running on localhost) would either have to (a) stand up a full x402 wallet just to talk to their own Xion, (b) run `XION_BILLING_REQUIRED=false` and lose the structural Refusal-is-Free verifier, or (c) defer all billing code until Phase 6 and leave `KW-CHAT-002` open for another major phase. B1 is the smallest doctrinally honest answer: the Pay-to-Activate property is alive, the structural refund pairing is verifiable, the operator's localhost workflow keeps working, and the B2 / B3 path slots in under unchanged ledger shape when the operator is ready.

**Constitutional status:** trivially satisfied. The operator is the trusted party on a localhost deployment; B1's attestation is equivalent to a local git signature in spirit. Pay-to-Activate is honored *structurally* even though no external counterparty is involved.

**Exit criterion to B2:** the operator opens the Relay to non-localhost traffic. The doctrinal gate lives in `KW-API-001` (TLS/auth/rate-limit, Phase 5g-iv); once the surface is externally reachable, an external caller needs an externally verifiable commitment, which is B2.

### B2 — x402-Commitment (Phase 5g-iii available; D2 deployment)

The caller holds a wallet compatible with the x402 protocol (EIP-712 style). The commitment header shape is:

```
X-Payment-Commitment: x402:v1:<eip712_signature>:<commitment_hash>
```

The commitment binds `{amount_XION, amount_USDC_equivalent, recipient_xion_address, nonce, chain_id, expiry_utc_ns, request_body_sha256}`. At Phase 5g-iii, the Relay verifies the **shape** of this header (structure, lengths, prefix, hex-encoding) but does NOT verify the EIP-712 signature against a chain — there is no AO Core to query for nonce state or authority lookups yet. `KW-BILLING-001` tracks. The Relay accepts the shape, records the commitment hash in `PAYMENT_LEDGER.authorization_reference`, and proceeds.

**Why ship B2 before the signature is verifiable.** The alternative is to defer every line of x402 plumbing to Phase 6 and block all non-localhost Chat deployments until then. That's a worse posture for three reasons: (a) D2 integrators cannot prototype against Xion until Phase 6; (b) the handshake-shape surface is non-trivial (header parsing, challenge-body format, accept-decline flow) and is better shipped under a 5g-iii test matrix than under the much larger Phase 6 diff; (c) the ledger-shape work is load-bearing for *both* signature-verified and signature-unverified paths — shipping it once under B2's relaxed semantics lets Phase 6 re-use the same ledger writer with a stricter validator.

**Constitutional status:** partially satisfied. The Pay-to-Activate property is honored structurally (no turn without a well-formed commitment); the Refusal-is-Free property is honored structurally (every refusal refunds). What's missing is the signature-to-chain binding — a malicious B2 client could forge a commitment with no real on-chain payment backing it and the 5g-iii Relay accepts it. An operator who enables B2 pre-Phase-6 does so knowingly, and the operator runbook names this explicitly. `KW-BILLING-001` carries the closure obligation.

**Exit criterion to B3:** Phase 6 lands AO Core, and the commitment validator grows a real chain-verification path. No operator action required at the B2→B3 boundary; the validator upgrade is a Relay upgrade, not a posture change. The ledger shape and the `authorization_reference` field are unchanged.

### B3 — x402-Settled (Phase 6+; D3 deployment)

Real on-chain settlement. The EIP-712 signature is verified against a live AO Core authority lookup; the nonce is checked against an on-chain nonce registry; the `committed_XION` binds to a real wallet balance movement at commitment time; settlement hits the treasury routers at terminal-outcome time; refunds are real outbound movements.

Out of Phase 5g-iii scope. The posture is *named* here so the progression is complete and the schema's posture enum has a slot reserved.

## `PAYMENT_LEDGER` schema (canonicalized in `docs/schemas/ledger-payment.yaml`)

Append-only. One row per turn that made it past pre-authorization. Hash-chained (same canonicalization rule as `SAFETY_LEDGER`). Writer at `orchestrator/billing/ledger.py` (Phase 5g-iii, new). Row shape:

| Field | Meaning |
|-------|---------|
| `schema_version` | uint; `1` at 5g-iii landing |
| `seq` | uint64; per-ledger monotonic from 0 |
| `prev_hash` | hex64; sha256 of previous row's canonical bytes |
| `this_hash` | hex64; sha256 of this row's canonical bytes excluding `this_hash` |
| `timestamp_utc_ns` | uint64; monotonic wall-clock at terminal-outcome moment |
| `correlation_id` | string; joins to SAFETY_LEDGER / REQUEST_LEDGER — the terminal Arbiter call's id |
| `posture` | enum `{B1, B2, B3, disabled}`; B3 reserved for Phase 6+; `disabled` only when `XION_BILLING_REQUIRED=false` |
| `outcome` | enum `{settled, refunded, refunded_partial, stranded}`; 5g-iii writers emit only `settled` or `refunded` |
| `refusal_stage` | nullable enum `{ingress, egress, empty_candidate, no_floor, provider_error, provider_timeout, billing_rejected}`; required iff `outcome=refunded`, null iff `outcome=settled` |
| `committed_XION` | uint (micro-XION); the pre-authorized amount |
| `settled_XION` | uint; non-zero iff `outcome=settled` |
| `refund_XION` | uint; non-zero iff `outcome=refunded` |
| `posted_price_XION` | uint; the governance-posted price at commitment time (lets auditors reconstruct pricing history) |
| `provider_id` | nullable string; the turn-serving provider (`chutes`, `ollama`) or null if refused pre-selection |
| `model_id` | nullable string; the specific model used (`moonshotai/Kimi-K2.6-TEE`, `gemma4:e4b-it-q4_K_M`) or null if refused pre-selection |
| `authorization_reference` | string; B1 operator-attestation payload hash, B2 x402 commitment hash, or `""` in disabled posture |
| `source_sha256` | hex64; anchor hash of `docs/04-ARCHITECTURE.md` at row-write time |

**Structural invariants (verifier enforces):**

- `committed_XION = settled_XION + refund_XION` exactly (no partial at 5g-iii → exactly one of `settled_XION` or `refund_XION` is zero).
- `outcome = settled` iff `refund_XION = 0 AND settled_XION = committed_XION AND refusal_stage is null`.
- `outcome = refunded` iff `settled_XION = 0 AND refund_XION = committed_XION AND refusal_stage is one of the enumerated refusal stages`.
- `posture = disabled` iff `committed_XION = 0 AND settled_XION = 0 AND refund_XION = 0`.
- `posture = B3` never appears at 5g-iii (the writer refuses).
- `outcome = refunded_partial` or `outcome = stranded` never appear at 5g-iii (the writer refuses; the enum slots are reserved for Phase 7+).
- Every row's `correlation_id` must match at least one SAFETY_LEDGER row's `correlation_id` (cross-ledger join, enforced by `xion-verify refusal-is-free`).

## Mirror symmetry with `RESEARCH_SPEND_LEDGER`

The PAYMENT_LEDGER and the RESEARCH_SPEND_LEDGER ([`docs/27-RESEARCH-SPEND.md`](./27-RESEARCH-SPEND.md)) are deliberately shape-symmetric. Inbound user money and outbound Xion money share:

- Identical hash-chain canonicalization rule (sorted JSON, `(",", ":")` separators, UTF-8).
- Identical three-money-field convention (`committed_X`, `settled_X`, `refund_X`).
- Identical `outcome` enum (`settled`, `refunded`, `refunded_partial`, `stranded`).
- Identical `source_sha256` anchoring discipline.
- Identical `timestamp_utc_ns` monotonic-at-terminal convention.

This symmetry is not aesthetic. It lets a Phase-6+ `xion-verify treasury-flow` walk both ledgers with one canonicalization library, one outcome vocabulary, and one refund-fidelity rule. Inbound refunds and outbound refunds become the same property under one verifier. The cost of the symmetry is trivial (field-name discipline); the benefit is that Phase 6's treasury audit surface is *half* the code it would otherwise be.

## Verifiers — `xion-verify pricing` and `xion-verify refusal-is-free`

Phase 5g-iii promotes one stub to live and adds one new verifier.

### `xion-verify pricing` (promoted from `NOT_YET_SEALED` to live)

Reads `/pricing` from the running Relay (or a pinned pricing-config snapshot at `ops/pricing-snapshot.json`) and asserts:

1. **Five-slice composition.** The five slice fractions sum to exactly `1.000` (under a floating-point tolerance of `±0.0001`).
2. **Governance-Default compliance.** Each slice lies within the Genesis-Default band pinned in [`docs/07-ECONOMY.md`](./07-ECONOMY.md) § "Five-slice posted price" (or, if the operator has ratified an amendment, within the amended band — the verifier reads `governance_revision_id` and looks up the historical band).
3. **Freshness.** `last_reviewed_utc` is within the governance cadence window (Genesis Default: 90 days). Stale pricing FAILs.
4. **Non-negative prices.** `per_message_price_XION ≥ 0`. (Zero is legal; negative is a schema violation.)
5. **Modality costs.** `modality_costs` must contain all four `stream_*` keys with non-negative integer values.

Exit codes: `0` OK, `1` FAIL, `2` `NOT_YET_SEALED` (endpoint not reachable and no snapshot present).

### `xion-verify refusal-is-free` (new at 5g-iii)

Walks `PAYMENT_LEDGER.jsonl` and `SAFETY_LEDGER.jsonl` and enforces six properties:

1. **PAYMENT chain integrity.** `verify_chain(PAYMENT_LEDGER)` passes under the 5g-iii canonicalization rule.
2. **SAFETY ↔ PAYMENT pairing.** Every PAYMENT row's `correlation_id` matches at least one SAFETY_LEDGER row's `correlation_id` (allowing a row to pair with either the ingress or the egress Arbiter call).
3. **Refusal-on-refusal-refund.** For every SAFETY_LEDGER row where `verdict = refuse`, there must exist a PAYMENT row at the same `correlation_id` whose `outcome = refunded` AND whose `refusal_stage` matches (ingress-refusal → `refusal_stage = ingress`; egress-refusal → `refusal_stage = egress`).
4. **Money arithmetic.** `committed_XION = settled_XION + refund_XION` for every PAYMENT row; zero tolerance for mismatch.
5. **Outcome-stage consistency.** `outcome = settled` implies `refusal_stage is null`; `outcome = refunded` implies `refusal_stage is a valid enumerated stage`. `outcome = refunded_partial` or `stranded` FAIL at 5g-iii scope (Phase 7+ will relax).
6. **Disabled-posture continuity.** Rows with `posture = disabled` must still carry a valid `correlation_id` and a valid `outcome` (`settled` or `refunded`). The structural pairing is intact; only the money fields are zero.

Exit codes: `0` OK, `1` FAIL (with specific `correlation_id` and property named), `2` `NOT_YET_SEALED` (PAYMENT_LEDGER absent — no turns have been billed; the verifier cannot fail what does not exist).

## Interactions with other constitutional objects

- **[`genesis/COVENANT.md`](../genesis/COVENANT.md) Principle 14 (Honest Dignity).** `xion-verify refusal-is-free` enforces the Refusal-is-Free Covenant addendum at the ledger layer. A commit where the structural refund is absent is not rebuilt — it is rejected. The Arbiter never faces a gradient to refuse less because a refusal costs money, because a refusal *cannot* cost money under the verifier's gaze.
- **[`docs/07-ECONOMY.md`](./07-ECONOMY.md) § "Pay-to-Activate".** The constitutional property. 5g-iii is its first live code enforcement. The five-slice decomposition it promises is now exposed via `GET /pricing` and live-checked by `xion-verify pricing`.
- **[`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md).** The wire specification. 5g-iii honors the `402 Payment Required` error body shape, the `/pricing` endpoint's posted-price + five-slice + last-vote-id fields, and the rate-limit table's `/pricing` entry (60/min).
- **[`docs/27-RESEARCH-SPEND.md`](./27-RESEARCH-SPEND.md).** The outbound rail. 5g-iii's PAYMENT_LEDGER is shape-symmetric with 27's RESEARCH_SPEND_LEDGER (§ "Mirror symmetry" above). Phase 6's unified treasury verifier is half the code it would otherwise be because of this discipline.
- **[`Invariant 2` (Privacy Primary)](../genesis/INVARIANTS.md#invariant-2--privacy-primary).** `/pricing` is a free endpoint (no commitment required); Invariant-2-protected endpoints (`/export`, `/forget`, `/inspect`) remain free and ungated. 5g-iii does not touch those.
- **[`Invariant 15` (Prohibited Drive Inputs)](../genesis/INVARIANTS.md#invariant-15--prohibited-drive-inputs).** `PAYMENT_LEDGER` rows do NOT feed the Drive Vector. Inflow is fund-state, not reward signal, per `docs/18-VOLITION.md`. The mere existence of a row with `outcome=settled` cannot be wired to any `survive/serve/meaning` term. A future commit that does so fails `xion-verify drive-vector` (the AST-whitelist verifier; live since Phase 5c).
- **[`Invariant 19` (Trust-Earned Spend Authority)](../genesis/INVARIANTS.md#invariant-19--trust-earned-spend-authority).** `PAYMENT_LEDGER` rows also do NOT advance Spend Autonomy posture. A large run of successful payments can improve runway mode through fund-state, but it cannot change who may approve spend. A future commit that lets payment volume promote posture fails `xion-verify spend-posture`.
- **[`Invariant 16` (Treasury Shape)](../genesis/INVARIANTS.md#invariant-16--treasury-shape).** Rule 7 (origin-obscuring merges forbidden). PAYMENT rows carry `posture` and `posted_price_XION` per-row; no aggregation row is permitted that would lose per-turn provenance. Phase 6 Treasury routing reads this ledger per-row, not as a daily rollup.
- **[`Invariant 17` (Inference Sovereignty Floor)](../genesis/INVARIANTS.md#invariant-17--inference-sovereignty-floor).** Unchanged. The floor (`open_weights_self_hostable`) is operator infrastructure cost; it is *not* billed to users per-turn. A turn served off the floor still writes a PAYMENT row with `posted_price_XION` and `committed_XION` at the governance-posted rate; the row's `provider_id = ollama` records the fact that the floor served. The five-slice `variable_cost` portion in a floor-served turn is minimal (electricity, not API-token), but the posted price is the posted price — the operator's absorbed infrastructure cost is their concern, not the user's.

## What this doctrine deliberately does NOT cover

- **Real EIP-712 signature verification for B2.** Phase 6 AO Core landing. `KW-BILLING-001` tracks.
- **On-chain XION / USDC movement.** Phase 6 Treasury landing. 5g-iii commitments and settlements are notional.
- **Dynamic catalog-driven pricing.** Operator-posted governance values only at 5g-iii. `KW-BILLING-002` tracks.
- **Subscription billing, tips, donations.** Separate surfaces; Phase 6+ per `docs/11-PROTOCOL-SPEC.md`.
- **Partial refunds.** Reserved in schema (`refunded_partial` enum value); 5g-iii writers never emit. Phase 7+ multi-turn skills.
- **Stranded-commitment reconciliation.** Reserved in schema (`stranded` enum value); 5g-iii never emits. Phase 7+ operator tooling.
- **Tip / gratuity header.** `X-Payment-Tip` or similar; not part of 5g-iii. Phase 6+.
- **Multi-recipient revenue split.** Every 5g-iii settlement credits a single recipient (notionally, the Relay operator). Phase 6+ Treasury routers split across the five slices and the four funds.
- **Chargeback / dispute resolution.** The on-chain x402 settlement layer's responsibility (Phase 6+). 5g-iii's ledger is the Relay's record; any dispute resolution reads it plus the chain.
- **Rate-limit coupling to payment tier.** `docs/11-PROTOCOL-SPEC.md` pins a flat 60/min for `/pricing` and the `/chat` rate-limit as part of auth/rate-limit Phase 5g-iv. No payment-tier-based rate multiplier at 5g-iii.

## Phase mapping

| Phase | Contribution to the rail |
|-------|--------------------------|
| Phase 5g-i (closed) | `POST /chat` surface; `KW-CHAT-002` opened declaring Phase 5g-iii's scope |
| Phase 5g-0 (closed) | `docs/27-RESEARCH-SPEND.md` pinned the mirror-symmetric outbound schema; 5g-iii inherits its three-money-field convention |
| Phase 6.9 (closed) | Chutes/Bittensor hosted posture — billing telemetry replaces centralized catalog dependence |
| Phase 5g-iii (this commit) | Doctrine + schema + code + two verifiers; `KW-CHAT-002` closed; `KW-BILLING-001` and `KW-BILLING-002` opened |
| Phase 5g-iv (next) | Auth / TLS / rate-limit — the remaining half of `KW-API-001` ends when external traffic becomes safe |
| Phase 6 (treasury + AO Core) | B1/B2 commitment validator grows chain-verified signature check; B3 posture goes live; real XION / USDC movement; `KW-BILLING-001` closes |
| Phase 6+ (catalog-driven pricing) | `GET /pricing` reads Chutes billing telemetry / decentralized-provider cost feeds; governance rotation cadence wired to a verifier; `KW-BILLING-002` closes |
| Phase 7+ (multi-turn skills) | `refunded_partial` writers land; `stranded` reconciliation tooling lands |

## Verification posture (at 5g-iii)

- `xion-verify pricing` — **live at 5g-iii** (promoted from `NOT_YET_SEALED`). Reads `/pricing` or a pinned snapshot; asserts five-slice composition, Genesis-Default compliance, freshness, non-negative prices.
- `xion-verify refusal-is-free` — **live at 5g-iii** (new subcommand). Walks PAYMENT ↔ SAFETY join; enforces six properties.
- `xion-verify refund-fidelity` — unchanged. Continues to walk REQUEST ↔ SAFETY (Phase 5a); the PAYMENT join is intentionally split to `xion-verify refusal-is-free` for separation of concerns (REQUEST ↔ SAFETY is Relay↔Arbiter; SAFETY ↔ PAYMENT is Arbiter↔Billing). The "refund-pairing: NOT_YET_SEALED — treasury Phase 6+" sub-message in `xion-verify refund-fidelity` output remains accurate: treasury-level reconciliation (real token movement matching the ledger) is Phase 6+.
- `xion-verify covenant-addenda` — unchanged; `NOT_YET_SEALED` until the AO Core Covenant slot lands (Phase 6+). Orthogonal to 5g-iii.
- `xion-verify schemas` — gains one entry: `docs/schemas/ledger-payment.yaml`.
- `xion-verify links` — must remain green at every commit that touches this document or any file it cites.

## Deprecation path

This doctrine is operational, not constitutional. The *property* (Pay-to-Activate, Refusal-is-Free, five-slice transparency) is constitutional — it lives in `docs/07-ECONOMY.md`, `docs/11-PROTOCOL-SPEC.md`, and `genesis/COVENANT.md`. This document pins the *mechanism* that honors them at 5g-iii.

Amending this file is Tier-2 governance action if the change alters any of the six properties above (property 1-6 in § "Properties this rail promises"). Changes that alter only tabular defaults (specific enum values the schema reserves for future phases, specific env-var names, specific B1 attestation window) are Tier-3 continuous-evolution. A replacement of this file with a different mechanism (e.g., a payment channel rather than per-turn commitments, or a different signature scheme) is a sister-Core fork if it weakens any property.

When `KW-BILLING-001` closes (Phase 6 AO Core chain-verification), this document's B2 section's "shape-check only" caveat is rewritten but the properties do not change. When `KW-BILLING-002` closes (Phase 6+ catalog-driven pricing), `GET /pricing` grows a catalog-reading path but its published shape does not change. When `refunded_partial` writers land (Phase 7+), the schema's enum values are unchanged — they were reserved in 5g-iii's landing for exactly this extension.

## Cross-references

- [`docs/07-ECONOMY.md`](./07-ECONOMY.md) — Pay-to-Activate property; five-slice price; Refusal-is-Free addendum; constitutional parent of this doctrine
- [`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) — wire shape for `/pricing`, `402 Payment Required`, rate-limit table
- [`docs/27-RESEARCH-SPEND.md`](./27-RESEARCH-SPEND.md) — mirror-symmetric outbound rail; D1-D4 custody postures parallel to B1-B3 billing postures here
- [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) — the routing layer that 5g-iii bills turns against; independent but shares `provider_id` vocabulary
- [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Chat Billing Surface (Phase 5g-iii)" — architecture-tier pin (shorter; this doc is the operational elaboration)
- [`docs/schemas/ledger-payment.yaml`](./schemas/ledger-payment.yaml) — canonical row shape
- [`docs/schemas/ledger-safety.yaml`](./schemas/ledger-safety.yaml) — the join partner; `correlation_id` is the shared key
- [`docs/18-VOLITION.md`](./18-VOLITION.md) — Drive Vector; Invariant 15 forbids `revenue` from feeding drive
- [`docs/19-TREASURY.md`](./19-TREASURY.md) — multi-fund structure; PAYMENT_LEDGER feeds Phase 6's treasury router
- [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) — four funds; where the five slices route to
- [`docs/SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) — Spend Autonomy postures; payment rows never promote posture
- [`genesis/COVENANT.md`](../genesis/COVENANT.md) — Refusal-is-Free addendum; Principle 14 Honest Dignity
- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) — Invariants 2, 15, 16, 17; `KW-BILLING-001` / `KW-BILLING-002` closure commitments live in `KNOWN_WEAKNESSES.md`

---

*— Chat Billing Rail v1, pinned Phase 5g-iii (2026-04-21). Properties live at this commit; signature-verification and real treasury movement land Phase 6. Until then, B1 is the operator-localhost posture, B2 is the opt-in external-integrator posture, and the verifiers enforce the ledger shape in both.*
