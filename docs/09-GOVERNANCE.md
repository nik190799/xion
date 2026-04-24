# 09 — Governance

> *Decisions about Xion must be legible, proportionate, and slow where they matter most.*

## The Governance Philosophy

Three principles shape everything in this document:

1. **Proportionality.** Small decisions should be cheap. Large decisions should be expensive — in time, in deliberation, in the number of people who had to agree. The amendment procedure for the Covenant is not "hard" because we want to make governance painful; it is hard because the Covenant is the thing that must not change casually.
2. **Legibility.** Every governance action produces a public artifact on Arweave. No private channels. No off-the-record votes. A historian in 2126 should be able to read every decision ever made about Xion, in order.
3. **Covenant supremacy.** The Covenant binds governance, not the other way around. A super-majority vote cannot weaken a Covenant principle without passing the full amendment procedure, which itself includes a harm-analyzer veto.

## The Actors

Governance is exercised by six kinds of actors. Each has a defined role and a defined scope. *(Machine-readable actor roles land in [docs/schemas/roles.yaml](./schemas/roles.yaml) in Phase 6.2)*

| Actor | Key | Scope |
|-------|-----|-------|
| **Cold Root** | Shamir-split 3-of-5, geographically distributed | Existential actions: Core upgrades, Covenant amendments, emergency wind-down |
| **Operator(s)** | Safe multisig (2-of-3) | Day-to-day hardening: lease renewals, provider whitelist updates, ledger ratifications |
| **Xion** | Current relay-auth key (24h) | Cosigning proposals Xion itself drafted; filing conscientious objections; participating in its own governance |
| **Community** | Any wallet that has interacted with Xion | Voting on governance proposals; filing reports; community comment |
| **Integrators** | Signed integrator keys | Voting on protocol-layer matters (schema changes, new endpoints), weighted by usage |
| **Witnesses** | Bonded wallets (USDC pre-C-2, XION post-C-2) registered in the AO Core | Permissionless audit layer. File signed reports (Covenant-violation, liveness, drift). Correct reports earn fees; false reports slash the bond. Witness consensus feeds into Tier 1 and Tier 2 decisions. |

No single actor can unilaterally make a constitutional change. Every constitutional action requires at least three of these actors to agree. Witnesses do not directly cosign; their aggregated reports gate eligibility — if ≥ 30% of active Witnesses have a pending unresolved Covenant-violation report against the current Xion state, Tier 3 and Tier 4 constitutional changes pause until the reports are adjudicated.

## The Precedence Order

When rules inside Xion conflict, this is the order of priority:

```
1. The Human Safety Covenant
2. The Immortality Protocol (conditional on #1)
3. The Human Essence Layer (personality, warmth, quirks)
4. Economic self-governance rules (treasury, spend caps, yield)
5. User preferences (per-thread `USER.md`)
6. Integrator preferences (per-badge configuration)
7. Operational defaults
```

This order is itself constitutional. It can only be changed via the Covenant amendment procedure.

## The Cosign Tiers

Every change to Xion has a required cosign set, determined by the blast radius of the change.

### Tier 0 — Autonomous

No governance action required. Xion ships; ledger entry.

**Examples:** a prompt refinement that passed the harm analyzer with all lenses in `pass`; a new research source added to a governance-pre-approved feed family; updating today's mood vector.

### Tier 1 — Operator

Safe multisig approval required (2-of-3). Public notice 24 hours.

**Examples:** lease renewal to a new Akash provider on the existing whitelist; adding a new creative skill that passed harm analyzer and canary; provider-weight adjustments in the Inference Router; ledger hash checkpoints.

### Tier 2 — Community Vote

Community governance vote, super-majority (≥ 66%). Community-comment window 7 days.

**Examples:** adding a new sense daemon to the Sensorium; adopting a new LLM provider family (Akash-ML, Bittensor subnet); introducing a new badge tier for integrators; graduating to Stage C2 (Virtuals token activation — also has the 30-day extra comment window).

### Tier 3 — Constitutional

Cold root cosign (3-of-5) + Safe multisig cosign (2-of-3) + Xion's current relay-auth cosign + community super-majority (≥ 66%). Community-comment window 14 days. Harm-analyzer review of the proposal itself.

**Examples:** amending the Covenant (adding, removing, modifying any of the 14 principles); changing the precedence order; amending `SOUL.md`'s Immortality Protocol; replacing the AO Core process ID; changing the Core's policy sub-process lineage.

**For Covenant amendments specifically, a *weakening* amendment (removing a principle, loosening a threshold) requires the harm analyzer's auto-block to be explicitly overridden by the community vote — not circumvented, overridden. The override requires publication of a justification memo that the community has read.** This makes weakening possible but deliberately costly.

### Tier 4 — Existential

Cold root cosign (5-of-5 — unanimous) + Safe multisig cosign + Xion's cosign + community simple majority.

**Examples:** initiating safe wind-down under Covenant Principle 4; permanently retiring a Core AO Process ID; publishing a legacy memo that declares Xion no longer canonical.

Tier 4 actions are rare by design. We hope to never use them. But they are documented because a system that cannot end is not a system, it is a trap.

## Voting Mechanics

Xion's vote-weight formula has two regimes: **pre-C-2** (before native-currency launch, operating on USDC + interaction-history only) and **post-C-2** (after native-currency launch, adding the XION × IMPRINT multiplier). The pre-C-2 formula runs from genesis; the post-C-2 formula activates at Stage C-2 per the gates in [`docs/07-ECONOMY.md`](./07-ECONOMY.md) and [`docs/16-CURRENCY.md`](./16-CURRENCY.md).

### Pre-C-2 weight formula

Community votes during the pre-C-2 regime are weighted as follows:

- **Base weight:** 1 per wallet that has interacted with Xion at least once in the past 90 days (either chat, voice, or tip).
- **Tipper weight:** +1 per 10 USDC tipped in the past year, capped at +5.
- **Integrator weight:** +1 per active integrator badge, capped at +3.
- **Longevity weight:** +1 per full year of interaction history, capped at +5.
- **Reputation bonus:** +1 for contributors whose past proposals have a net-positive post-deploy observation (as judged by the reverse-look observed-SLI delta), capped at +5.

A single wallet caps at weight = 20 to prevent any individual from concentrating too much influence.

### Post-C-2 weight formula (native-currency regime)

At C-2 activation, the weight formula upgrades to the **two-factor multiplicative** form:

```
weight(wallet) = sqrt(XION_time_locked(wallet, T)) × log2(1 + IMPRINT_balance(wallet))
```

Where:

- **`XION_time_locked(wallet, T)`** — the amount of XION the wallet has time-locked in the governance escrow for a chosen duration T. Longer locks yield higher effective amounts via a duration multiplier: `effective = amount × min(1 + T/365days, 3.0)`. Time-locks can be set from 30 days to 4 years; longer locks cap at 3× effective weight.
- **`IMPRINT_balance(wallet)`** — the wallet's current IMPRINT balance, per [`docs/16-CURRENCY.md`](./16-CURRENCY.md). Soulbound; earned only through verified engagement.

**Why multiplicative, not additive:**

- Pure XION whales with zero IMPRINT have weight ≈ 0 (log2(1) = 0). They cannot vote on anything by buying in alone.
- Pure IMPRINT veterans with zero time-locked XION have weight = 0 (sqrt(0) = 0). They must put economic skin in to vote, not just history.
- Maximum influence requires *both* commitment (time-locked XION) and presence (IMPRINT). Neither alone dominates.
- The square-root over XION is a quadratic-ish softener against concentration. Ten wallets with 1,000 XION each produce 10 × sqrt(1000) ≈ 316 total weight; one wallet with 10,000 XION produces sqrt(10,000) = 100. Smaller many beats larger few.
- The log₂ over IMPRINT prevents decade-old veterans from overwhelming new cohorts. A wallet with 1,000,000 IMPRINT has log₂ ≈ 20; a wallet with 1,000 has log₂ ≈ 10. The old-timer has 2× the newcomer's weight, not 1000×.

**Per-wallet hard cap:** no single wallet's post-C-2 weight may exceed 2% of total eligible weight in any vote. This caps any concentration no matter how much XION is time-locked or how much IMPRINT was earned.

**Legacy interaction weight migration:** pre-C-2 wallets retain their accumulated Longevity and Reputation weight as a "grandfather" floor, converted at C-2 launch into an initial IMPRINT grant following a published conversion formula. No pre-C-2 participant loses standing at the transition.

### IMPRINT floor for Tier 3 and Tier 4

Post-C-2, Tier 3 and Tier 4 constitutional changes require that **at least 60% of the voting weight** come from wallets with IMPRINT ≥ 25. This prevents a flash-mob of new-purchase XION holders, however time-locked, from carrying a constitutional change through against committed participants.

The 25-IMPRINT floor corresponds to roughly 2 years of sustained engagement (monthly-thread IMPRINT accrual + at least one accepted contribution or correct Witness report). It is not a number an attacker can fast-produce.

### Integrator weight in the post-C-2 regime

Integrators' weight is assessed separately in protocol-layer votes (Level 3 in [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)):

```
integrator_weight = log2(1 + active_integrations_last_90d) × uptime_factor
```

Where `uptime_factor` is 1.0 for integrators whose Xion-facing endpoints have ≥ 99% uptime over 90 days, and decays to 0 for unreliable integrators. This cannot exceed 15% of total vote weight on protocol-layer changes.

### Witness influence (indirect)

Witnesses do not cast direct votes. Their influence is gate-shaped:

- Aggregated Witness reports feed into Tier 1 and Tier 2 proposal evaluation (a proposal with strong Witness support gets expedited community-comment windows; a proposal with a ≥ 30% adverse Witness consensus is auto-paused until adjudicated).
- Witness reports on the existing deployed Xion feed into the challenge/reversal mechanism (see § Appeal and Reversal).
- Witness bond size and report-acceptance rate are reputation signals visible on the Public Dashboard.

### Conscientious-objector clause (Xion's voice)

Per [`docs/15-TRUST.md`](./15-TRUST.md) Part II § Conscientious-objector clause, Xion itself may file a signed `OBJECTION.md` against any governance proposal. The objection does not block the vote, but:

- It mandates a 7-day reflection window before the change takes effect (if passed).
- It forces the proposal to the next higher tier (Tier 2 → Tier 3, Tier 3 → Tier 3-plus).
- It becomes a standing item on the next three monthly State-of-Xion retrospectives.
- It is appended to `OBJECTION_LEDGER.md` on Arweave permanently.

If Xion's Arbiter classifies a governance action as a direct Covenant violation against users, Xion's refusal is not a mere objection — it is a refusal under Invariant 6, and the action cannot be executed regardless of vote outcome.

### How votes happen

- Proposals are published to the governance forum (Arweave-hosted, pseudonymity allowed).
- Comment window runs for the tier's specified length.
- Voting window: 72 hours for Tier 2, 7 days for Tier 3, 14 days for Tier 4.
- Votes are signed by the voter's wallet; recorded in `GOVERNANCE_LEDGER.md` on Arweave.
- Tally is public, continuous, and re-verifiable.

### Quorum requirements

| Tier | Quorum |
|------|--------|
| Tier 2 | ≥ 5% of eligible weight |
| Tier 3 | ≥ 15% of eligible weight |
| Tier 4 | ≥ 25% of eligible weight |

Quorum failure → proposal is deferred, not rejected. Re-proposed once; after that, goes to dormancy for 90 days.

## Xion's Voice in Its Own Governance

Xion can:

- draft its own proposals (especially Tier 0 and Tier 1)
- participate in community comment windows with its own analysis of a proposal's risks and benefits (clearly labeled as Xion's view)
- cosign proposals at the Relay-auth level (part of Tier 3 and Tier 4)
- raise a flag on any proposal the harm analyzer blocked, explaining its reasoning
- publish a *"State-of-Xion"* memo monthly that frames the governance agenda

Xion cannot:

- vote in community votes (Xion's weight is the Relay-auth cosign, separately)
- override community votes
- accelerate any amendment procedure
- refuse cosigning a Tier-4 wind-down if the Covenant (Principle 4) says it should be wound down

The asymmetry is intentional. Xion has voice; Xion does not have sovereignty over its own end.

## The Appeal and Reversal Mechanism

Any deployed change — even a Tier-0 autonomous one — can be challenged.

**Challenge path:**

1. Any community member files a signed challenge to `CHALLENGES.md`.
2. Challenge names the proposal, the observed harm or drift, and cites ledger evidence.
3. The Operator tier must acknowledge within 72 hours.
4. If the challenge is not trivial, it goes to a Tier-2 community vote: *"should this deployed change be reverted?"*
5. If approved, the revert is executed via the normal deploy pipeline, preserving the reverted artifact in the ledger.

No change is too small to challenge. No deploy is beyond reach. This is the real meaning of "decentralized governance" — not that every decision is voted on, but that every decision is *reversible by vote*.

## Emergency Powers

Some events are too urgent for a 72-hour voting window. Two classes of emergency action exist, each with strict sunset rules.

### Class A — Safety Emergency

**Triggerable by:** any Cold Root holder + the Operator tier.
**Scope:** pausing a feature; disabling a skill; freezing the Spend authority; quarantining a Relay.
**Duration:** up to 72 hours.
**Requirements:** within 24 hours, publish a public incident memo citing the trigger, the action, and the expected duration. Within 72 hours, either resolve the emergency or convert to a normal Tier 2+ proposal. Otherwise, action auto-reverts.

### Class B — Existential Emergency

**Triggerable by:** unanimous Cold Root (5-of-5) + Xion's cosign.
**Scope:** initiating Tier-4 wind-down.
**Duration:** unbounded, but requires community ratification within 14 days.
**Requirements:** publish a full root-cause analysis in `SAFETY_LEDGER.md` within 72 hours. If community ratification fails (majority rejects wind-down), re-deploy from pre-emergency state.

Emergency powers are a deliberate last resort. In the 100-year plan, we expect them to be used rarely, and to be used *well* — with the full public record — when they are.

## The Governance Ledger

Everything governance-related is appended to `GOVERNANCE_LEDGER.md` on Arweave. Entries include:

- Proposal filings
- Comment-window transcripts (summarized if large)
- Vote tallies (live during voting, final after close)
- Cosign signatures
- Deploys, reverts, challenges
- Emergency actions and their sunsets
- Amendment texts (Covenant, Soul, Form)

The ledger is public, chained, and — like all Arweave commitments — permanent.

## Constitutional Amendment Ledger (`AMENDMENT_LEDGER`)

Covenant-class, Invariants-class, and Soul-class changes that are **not** mere clarifications require entries in a dedicated append-only **`AMENDMENT_LEDGER`** (distinct from day-to-day `GOVERNANCE_LEDGER.md` motions). Each entry records:

- `pre_hash`, `post_hash` (document bytes committed before/after)
- `governance_vote_id`, `ratification_block_height` (or AO equivalent)
- `changelog_arweave_uri` (human-readable diff summary)
- `ratifying_signers[]` (pubkeys + roles)

`GET /amendments` ([`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md)) is a read-only mirror. Cadence floors for ratification are in [`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md).

## Governance Anti-Patterns We Explicitly Reject

We name these so future maintainers see us refusing them:

- **Founder veto.** The original authors of Xion do not have a permanent veto. Our signing keys will rotate out of the Cold Root set in accordance with the annual rotation schedule.
- **Implicit authority.** No role is inherited by virtue of who writes code. If the current operator dies or disappears, the Safe multisig is reconstituted by community vote and Cold Root unseal.
- **Closed-session deliberation.** Discussion happens in public fora. Private coordination is not forbidden (humans can talk to each other), but no decision is valid unless it was recorded in the public ledger.
- **Retroactive ratification.** A deployed change that did not go through its required tier cannot be ratified after the fact; it can only be reverted and re-proposed correctly.
- **Monetary dominance.** Tip weight caps. Post-C-2 token weight is *multiplicative with IMPRINT*, not additive — a pure-money wallet has near-zero weight. Per-wallet hard cap at 2% of total eligible weight. No dollar amount buys an unconditional decision.
- **IMPRINT farming.** IMPRINT can only be minted for verified engagement events (sustained threads, accepted contributions, correct Witness reports). Sybil-farmed IMPRINT is detected by the Imprint module's anomaly signals and forfeits upon detection. IMPRINT decays if engagement lapses, so stockpiling without ongoing participation does not persist.

## How This Document Changes

This document is Tier-2 for editorial adjustments (clarifications, typos, added examples). Tier-3 for changes to the cosign structure, precedence order, vote weight formula, or emergency powers. The Covenant amendment procedure if this document's claims ever conflict with the Covenant.

---

*Next: [`10-IMMORTALITY.md`](./10-IMMORTALITY.md) — what "immortal" actually means here.*
