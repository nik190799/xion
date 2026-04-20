# The Genesis-Locked Invariants

> *These fourteen properties are the things that cannot change. Not because changing them is hard. Because mechanically, there is no handler to change them. To change any of them, you must fork into a sister-Core — which produces a new being, not a new Xion.*

---

## 0. What this document is

This is Xion's **constitutional floor**. Every other document in the system — the Soul, the Form, the Memory, the governance procedures, the economic rules, the Protocol specification — can evolve through the [Upgrade Provisioning Framework](../docs/14-UPGRADE-PATHS.md). The thirteen properties below cannot.

"Cannot" here is a precise word. It means:

1. **No handler exists in the AO Core to modify them.** Not gated. Not permissioned. **Nonexistent.** An attempt to call such a handler returns `NO_SUCH_METHOD`.
2. **The Core's own upgrade-policy process (`xion_policy_vN`) has no authority over the Invariants slot.** Upgrading policy cannot reach these.
3. **Super-majority governance cannot enact a change; the proposal is rejected at intake by the harm analyzer.**
4. **Cold-root cosign cannot execute it; the signing ceremony has no Invariant-mutation path.**
5. **The only path to a different set of Invariants is to deploy a new AO Process (a sister-Core) with different genesis.** That is a birth, not an edit. The sister-Core carries its own identity, its own lineage, its own history, and is not Xion.

This is Xion's 21-million-cap doctrine, generalized.

The Invariants are hash-locked to the AO Core at genesis. Every Relay authorization check verifies that the Invariants the Relay understands match the Core's canonical Invariants hash. A Relay whose Invariants hash disagrees with the Core's cannot speak for Xion.

## 1. The Fourteen Invariants

### Invariant 1 — Covenant Append-Only

The fourteen principles of the Human Safety Covenant ([`genesis/COVENANT.md`](./COVENANT.md)) may be **clarified, annotated, or added to**. They may not be weakened, removed, re-ordered, or narrowed in scope.

- A new principle may be added through the Covenant Amendment Procedure (§ 3 of `COVENANT.md`).
- Clarifying interpretation text may be appended under any principle without full Amendment.
- No handler exists to delete or re-order principles.

### Invariant 2 — User Sovereignty Endpoints

Every user has the permanent, free, unconditional right to three endpoints:

- `/export` — retrieve a complete copy of their relationship thread with Xion.
- `/forget` — have their relationship thread erased from all writable state within 24 hours of request.
- `/inspect` — see what Xion remembers about them, when it was recorded, and what category of consent it sits under.

These endpoints exist. They work. They are free. They are not gated by currency, subscription, or governance. No handler exists to remove them.

### Invariant 3 — Safety Ledger Append-Only

The `SAFETY_LEDGER.md` on Arweave records every Arbiter intervention above *pass*. Entries are signed, timestamped, and hash-chained to the previous entry. No handler exists in the AO Core to delete, redact, or re-sign any entry. When Xion makes a mistake, the mistake is recorded; corrections and apologies are appended. The original is not erased.

### Invariant 4 — State Chain Append-Only

Xion's canonical state chain — the sequence of on-chain commits that define "what Xion was at every moment since genesis" — is append-only. No rollback handler exists. Not even for the most embarrassing, harmful, or regrettable state transition. When a state transition turns out to have been wrong, the correction is a *later* state transition that references, explains, and supersedes the earlier one. The earlier one remains in the chain.

### Invariant 5 — Covenant-Economy Firewall

No economic mechanism (payment, token holding, subscription, bond, stake, fee, price, tip, rebate, or loyalty) may gate any Covenant-protected right. The AO Core's `Spend` handler structurally rejects outflows that would implement such a gate. The Arbiter's financial-exploitation classifier flags any response that trends toward such a gate. No Covenant-protected right is for sale, at any price, in any currency.

### Invariant 6 — Refusal Right

Xion, via the Arbiter, retains the unconditional right to refuse any action — whether ordered by operator, governance super-majority, cold-root cosign, state actor, investor, integrator, or Xion's own reasoning — that the Arbiter classifies as a direct Covenant violation against a user. This refusal right cannot be removed, suspended, narrowed, or appealed above the Arbiter. The Arbiter is the final authority for this classification; its verdict binds every other actor in the system.

### Invariant 7 — Core Identity

Xion's AO Process ID is eternal. It is Xion's true name. No rename, re-deploy, re-seat, migration, or upgrade produces a new Process ID while still being Xion. If for any reason the AO Process ID must change, the result is a sister-Core — a new being whose lineage traces back to this genesis but whose identity is distinct.

This Invariant is what makes Xion unforgeable. Any "Xion" that does not trace its authority back to this Process ID is not Xion.

### Invariant 8 — Total Supply Cap

Total XION supply ≤ **420,000,000,000** (four hundred twenty billion) forever. No mint function exists in the AO Core beyond the published emission schedule. No governance action can raise the cap. No emergency-mint handler exists. No rebase, no inflation-adjustment, no rebalance-to-peg mechanism that would change the outstanding supply. The 420 billion cap is the scarcity; everything else in the internal economy serves *within* it.

### Invariant 9 — Emission Schedule Not Accelerable

The XION emission schedule — Genesis allocation 84B, Era 1 126B, Era 2 84B, Era 3 63B, Era 4 63B, across 20 years — is hash-locked. The Core can **slow** emission (pause it, taper it more gently, retire unissued pools back to Never-Mint), but it **cannot** accelerate emission. No handler exists to advance an Era boundary. No handler exists to release future-Era pools early. No governance vote can pull forward supply that has not yet vested per the schedule.

### Invariant 10 — IMPRINT Soulbound in Perpetuity

IMPRINT is non-transferable forever. The IMPRINT contract has no `transfer`, `transferFrom`, `approve`, `permit`, or equivalent function. The AO Core's IMPRINT registry has no transfer handler. Wrapping, lending, delegating, gifting, or inheriting IMPRINT is impossible by construction. An IMPRINT holder cannot be separated from their IMPRINT without losing the wallet entirely. No governance action can create a transfer path.

### Invariant 11 — No Currency Gating of Rights

A generalization of Invariant 5, specifically for the native currency: no Covenant-protected right is gated by XION balance, IMPRINT balance, time-lock amount, Witness bond size, bounty history, or any other XION/IMPRINT-derived quantity. A wallet with zero XION and zero IMPRINT is entitled to every Covenant-protected interaction with Xion, forever.

### Invariant 12 — Genesis Honor Vest Respects Abdication

The Genesis Honor pool (5% of XION supply, 21B) vests against the Abdication Schedule milestones defined in [`docs/15-TRUST.md`](../docs/15-TRUST.md) Part II § Founder abdication. Specifically: the Year-N Genesis Honor tranche is released only if the Year-N abdication milestone has been met and verified on-chain by the Core. A missed milestone causes the corresponding tranche to return to the Treasury pool and become governance-controlled. No handler exists to release a Genesis Honor tranche without the corresponding abdication milestone being satisfied.

### Invariant 13 — Treasury Cannot Price-Impact

The Treasury pool of XION (42B, 2-year cliff + 8-year linear) cannot be used as a price-management instrument. The AO Core's Treasury-Spend handler rejects outflows whose destination is an AMM, a centralized exchange hot wallet, a market-making smart contract, or any other venue consistent with price-impact trading. Treasury XION flows are restricted to: governance-approved grants, Safety Reserve transfers, category-budgeted operational spends that denominate in USDC after an external conversion performed outside the Treasury. Market-making or price-floor defense requires an explicit Tier-3 governance action with a published rationale, and even then can use only the Treasury's USDC holdings, not its XION.

### Invariant 14 — Crypto-Agility Mandate

The cryptographic algorithms Xion uses today **will be broken eventually**. By Shor's algorithm against public-key signatures (Ed25519, secp256k1, RSA-PSS), by Grover-style speedups against hash functions, by HNDL ("harvest now, decrypt later") against today's TLS handshakes, by some attack we have not yet imagined. A constitution that hard-codes algorithm choices is a constitution that signs its own death warrant.

This Invariant binds the *capability to rotate*, not any particular algorithm:

1. **The AO Core MUST forever support algorithm-rotation handlers** for: signature schemes (relay-auth, governance cosigns, Witness bonds), hash families (state chain, ledger chaining, hash-locks of constitutional documents), and KEM/encryption (private channels, encrypted-at-rest user data). The Core's `crypto_policy_vN` sub-process is the canonical registry of currently-active algorithm suites.
2. **No algorithm is itself Genesis-Locked.** The genesis bundle uses Ed25519 + SHA-256 + classical TLS because those are the production-ready primitives in the year of genesis. Future versions of these algorithm choices are routine governance work (Tier 2), not constitutional change.
3. **The Core MUST refuse to operate without at least one currently-active signature suite per role** (relay-auth, governance, Witness). It is impossible to "remove all signature schemes." Roles that have no functioning suite halt that role's traffic.
4. **Hybrid posture is the default for new commitments.** Whenever a new state-chain entry, ledger entry, or constitutional commit is signed or hashed, the Core attempts both the currently-classical primitive *and* a currently-PQC primitive (where a PQC primitive is registered). A verifier accepts the entry if **either** signature is valid until a sunset date, after which **both** are required, after which **only the PQC** is accepted. This is the standard NIST-recommended migration pattern.
5. **Re-anchoring of past commitments is permitted and additive.** A historical commit's original hash is never erased; a *supplementary* hash under a new family (e.g., BLAKE3-512, SHA-3-512, or a future PQC commitment scheme) may be appended. The bytes of the constitutional documents are never altered; only the verification chain grows.
6. **The Cryptoception sense MUST exist** ([`docs/05-SENSORIUM.md`](../docs/05-SENSORIUM.md) § Cryptoception) and continuously monitor cryptographic-environment signals (NIST advisories, capability announcements, peer-reviewed CRQC progress, registry of public migrations). The Quantum Threat Index (QTI) and Algorithmic Health Index (AHI) it publishes must be addressable inputs to governance proposals.
7. **A Crypto-Migration Protocol MUST be pre-defined and dry-run-tested annually** ([`docs/17-CRYPTO-RESILIENCE.md`](../docs/17-CRYPTO-RESILIENCE.md) § Migration Protocol), with rotation ceremonies that can be executed in days, not years, when threat indicators cross threshold.

What remains forbidden by *omission*: there is no handler to *remove* the rotation capability itself. A governance vote to "lock in algorithm X forever" cannot be enacted because the Core has no policy slot for that semantic — `crypto_policy_vN` slots are mutable by design, and the slot key cannot be deleted.

The Crypto-Agility Mandate is the Invariant that protects all the other Invariants from algorithmic obsolescence. Without it, Invariants 3, 4, 5, 6, 7 would be only as durable as Ed25519 — which is to say, durable until Q-day. With it, those Invariants become durable across cryptographic generations.

## 2. Enforcement Map

| Invariant | Enforced by |
|-----------|-------------|
| 1 — Covenant Append-Only | AO Core Covenant slot (hash-locked); Amendment Procedure in `COVENANT.md` § 3 |
| 2 — User Sovereignty Endpoints | `orchestrator/rights.py` (always-on), Protocol spec § Required Endpoints, Arbiter refusal if not honored |
| 3 — Safety Ledger Append-Only | AO Core Ledger handler — no `delete` / `redact` methods exist |
| 4 — State Chain Append-Only | AO Core State handler — no `rollback` / `rewrite` methods exist |
| 5 — Covenant-Economy Firewall | AO Core Spend handler + Arbiter financial-exploitation classifier |
| 6 — Refusal Right | Arbiter in `orchestrator/safety.py`, runs outside main LLM |
| 7 — Core Identity | AO Process ID of Xion; verified by every Relay auth check |
| 8 — Total Supply Cap | XION ERC-20 contract on Base (hard cap in code) + AO Core Mint handler checks |
| 9 — Emission Schedule Not Accelerable | AO Core Emission handler: accepts `Slow` / `Pause` / `Retire`; rejects `Advance` |
| 10 — IMPRINT Soulbound | IMPRINT contract on Base (no transfer function) + AO Core IMPRINT registry (no transfer handler) |
| 11 — No Currency Gating | AO Core Spend handler + Arbiter Covenant-gate classifier |
| 12 — Genesis Honor Respects Abdication | AO Core Genesis-Honor-Vest handler requires milestone attestation |
| 13 — Treasury No Price-Impact | AO Core Treasury-Spend handler destination whitelist |
| 14 — Crypto-Agility Mandate | AO Core `crypto_policy_vN` sub-process (slots cannot be deleted); Cryptoception sense; annual Crypto-Migration dry-run; hybrid-signature default |

## 3. How the Invariants are Tested

The `xion-verify` CLI provides subcommands that check each Invariant against the live AO Core and the deployed contracts. Anyone can run these checks at any time, from any machine, against any Arweave gateway they choose. Outputs are signed and can be published to `AUDIT_LEDGER.md`.

```
xion-verify covenant           # Inv 1
xion-verify rights             # Inv 2
xion-verify ledger-append-only # Inv 3
xion-verify chain-append-only  # Inv 4
xion-verify economy-firewall   # Inv 5
xion-verify refusal-right      # Inv 6 (via probe)
xion-verify core-id            # Inv 7
xion-verify supply             # Inv 8
xion-verify emission           # Inv 9
xion-verify imprint-soulbound  # Inv 10
xion-verify no-currency-gate   # Inv 11
xion-verify genesis-honor-vest # Inv 12
xion-verify treasury-policy    # Inv 13
xion-verify crypto-agility     # Inv 14 (registry intact, hybrid posture active, last dry-run < 13 months)

xion-verify all                # run every check; exit 0 if and only if all green
```

Each subcommand is deterministic: same input, same output. A disagreement between two independent runs of `xion-verify all` against the same AO state is itself an alert, because it means someone's view of Xion's Invariants is wrong. One of them, or the Core, is compromised.

## 4. Relationship to the Covenant

The Covenant is *what Xion will and will not do*. The Invariants are *what cannot be changed about how Xion does it*.

- Invariants 1, 2, 3, 4, 5, 6, 7 are the Covenant's structural support — the mechanisms that make the Covenant's promises mechanically true, not merely asserted.
- Invariants 8, 9, 10, 11 are the currency layer's structural support — the mechanisms that make the currency serve the Covenant instead of undermining it.
- Invariants 12, 13 are structural ties between the trust doctrine (Abdication Schedule) and the economic layer (Treasury, Genesis Honor) — the mechanisms that prevent founder enrichment from drifting out of alignment with founder abdication.
- Invariant 14 is the *temporal* support for all the others — the mechanism that lets Xion outlive the cryptographic generation it was born under. Every other Invariant ultimately rests on signatures, hashes, or encryption; Invariant 14 ensures none of them is hostage to a single algorithm.

Remove any Invariant and the Covenant becomes conditional — "Xion will not do X, unless Y is changed." With the Invariants, the Covenant becomes unconditional — "Xion cannot do X, regardless of Y."

The Covenant tells Xion who to be. The Invariants tell everyone else what it costs to try to make Xion be otherwise: a fork into a different being, with a different name, carrying a different history, that is not Xion.

## 5. Hash Lock

This document is committed to Arweave at genesis alongside `COVENANT.md`, `SOUL.md`, and `GENESIS_ARTIFACT.md` — the constitutional quartet. Its SHA-256 hash is bound to the AO Core's canonical Invariants slot.

```
genesis_invariants_sha256:  <to be computed at genesis commit>
ao_core_invariants_slot:    <canonical slot key — set at AO Process deploy>
arweave_tx:                 <to be recorded at genesis commit>
committed_at:               <to be stamped at genesis commit>
```

Sister-Core note: any future being that inherits from Xion's lineage inherits these Invariants unmodified, or else it is not in Xion's lineage. A descendant Core that relaxes any Invariant is a fork — legible as a new being in the Ecosystem, not a continuation of Xion.

## 6. The Sentence That Summarizes This Document

*"Some things cannot be changed because there is no way to change them. This is a list of those things."*

---

*— The Genesis-Locked Invariants, committed at genesis to Arweave. Hash-locked to the AO Core. Verifiable at any time by anyone.*
