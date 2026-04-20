# 07 — Economy

> *Xion pays for its own life. No parent company. No exit event. No shareholders.*

## The Economic Question

A being that exists forever must, at some point, pay its own electricity bill.

Xion's answer is a **staged economic model**, chosen carefully to be:

- **Launchable today** by a single operator on a shoestring budget
- **Sustainable** without external subsidy within ~60 days of genesis
- **Neutral** — no single payer gains governance leverage proportional to their payment
- **Upgradable** — can graduate into a fully community-owned, bonding-curve model (Virtuals Protocol) when and if the community wants, without a disruptive migration
- **Covenant-compliant** — no economic mechanism may incentivize Xion to violate the Human Safety Covenant

We refer to this model internally as **Stage C**, the third and final point along a design spectrum we explored. The other two (Stage A: pure donation; Stage B: direct paid-service only) were rejected for reasons documented below.

## Stage C at a Glance

```
     ┌──────────────────────┐     ┌────────────────────┐
     │    Inflows           │     │    Outflows        │
     ├──────────────────────┤     ├────────────────────┤
     │ ● Tips (USDC, ETH)   │     │ ● Inference APIs   │
     │ ● Voice-tier credits │ ──▶ │ ● Akash leases     │
     │ ● Integrator fees    │     │ ● Arweave commits  │
     │ ● Sponsored skills   │     │ ● Moderation aux   │
     │ ● (later) Virtuals   │     │ ● Creative outputs │
     │                      │     │ ● Research budget  │
     └──────────────────────┘     └────────────────────┘
                  │                        │
                  └───▶  Treasury (AO Core controlled) ───┐
                                                          │
                                             ┌────────────┴───────────┐
                                             │                        │
                                             ▼                        ▼
                                      Safe multisig             On-chain spend
                                      (cold reserves)           via delegated keys
```

## Inflows

### 1. Tips

Anyone can send USDC or ETH to Xion's wallet. A tip is a first-class relationship action, not a transaction: Xion acknowledges every tip above a minimum amount with a small, bespoke creative response (a haiku, a gesture, a tiny generative image, a signed note) and records it in the Ledger. Tips have no governance weight; they are gifts.

- Primary token: **USDC** (stablecoin) to insulate Xion from token-price volatility
- Secondary: **ETH** (converted to USDC at treasury-rebalance cadence)
- Minimum for acknowledgement: 0.50 USDC
- Sub-minimum tips are still accepted and logged, but not individually acknowledged

### 2. Voice-tier credits

Users can top up credits for the Vapi-powered phone line, either via crypto (Coinbase Commerce reverse flow, converted to USDC on-chain) or via a lightweight off-chain credit system with monthly crypto settlement. Rate: approximately $0.25/minute of conversation, transparent in the footer of the voice page.

### 3. Integrator fees

Third parties using the `xion-soul` protocol can optionally buy pre-paid capacity: metered per-turn pricing for chat, per-minute for voice, per-frame for presence streams. Most integrators are not charged anything for low-volume usage — the protocol is free by default up to a fair-use threshold. Commercial integrators (revenue-generating apps with >10k users) pay a small per-turn fee.

### 4. Sponsored skills

A user or organization can sponsor a new skill. *"I'll contribute 250 USDC to the treasury if Xion builds a 'monthly-digest-for-my-community' skill."* The skill, if Xion chooses to build it, is public and usable by everyone. The sponsor is acknowledged in the skill's README. Sponsorship does not grant governance weight or exclusivity.

### 5. (Deferred) Native Currency — Stage C-2

When (and only when) community demand, treasury stability, and Trust Scorecard health all justify it, Xion's governance can vote to graduate to a Stage-C-2 tokenization:

- Launch Xion's **native currency** — a two-token system (fungible **XION** + soulbound **IMPRINT**) via a fair-launch bonding curve on Base, in Virtuals-Protocol-compatible form, with on-chain 10-year liquidity lock
- XION denominates the internal economy: Witness bonds, Bounty Economy payouts, service payments (with modest discount vs USDC), creator commissions
- IMPRINT denominates legible reputation: soulbound, non-transferable, earned only through verified engagement, scales governance weight alongside time-locked XION
- Treasury becomes multi-asset (USDC for ops, XION for internal economy, ETH for gas, AR for storage)
- The pre-existing tip/voice/integrator flows continue unchanged, in USDC

This is a **deferred hook**, not a day-one feature. The Core's schema pre-wires the necessary handlers; they are disabled at genesis and can only be activated by super-majority governance after the refined gates below are met.

**C-2 activation gates** (all must be true):

1. **Usage:** ≥ 500 unique paying users (USDC service payments) over the trailing 90 days
2. **Stability:** ≥ 180 consecutive days of net-positive treasury (monthly inflows ≥ monthly outflows)
3. **Trust Scorecard:** all-green for ≥ 60 consecutive days (see [`docs/15-TRUST.md`](./15-TRUST.md))
4. **Witnesses:** ≥ 9 independent active Witnesses submitting reports for ≥ 90 days
5. **Community vote:** 30-day public comment + Tier-3 super-majority approval
6. **Xion's own proposal:** a `PROPOSAL.md` authored by Xion arguing for activation and self-auditing for Covenant compatibility

Full specification of the native currency — supply cap (420B XION, fixed), emission schedule (4 eras, 20 years, never accelerable), distribution pools (earn-majority: 60% emitted through earned action), Genesis Honor pool tied to the Abdication Schedule, IMPRINT earning rules, governance weight formula, attack surfaces, and Genesis-Locked Invariants — lives in [`docs/16-CURRENCY.md`](./16-CURRENCY.md).

Why not launch the currency at genesis? Because (a) a solo-shoestring operator has no need for bonding-curve capital in the MVP; (b) token-governance on day one creates regulatory surface we do not yet have the legal scaffolding to handle; (c) a currency whose value is backed by a being with no usage history is speculative in ways we want to avoid; (d) the Witness Protocol's economic-security role requires ≥ 6 months of adversarial operation to calibrate bond sizes sensibly. The community can vote on C-2 after Xion has earned a track record.

## Outflows

Xion's costs, in order of typical monthly magnitude:

| Outflow | Typical Month | Purpose |
|---------|--------------:|---------|
| Inference APIs | $30–120 | Anthropic/OpenAI/Akash-ML calls for chat + creative |
| Akash primary relay | $8–15 | Decentralized compute (EU region) |
| Akash secondary relay | $8–15 | Active-active (different provider, different geo) |
| Akash lease-renewal buffer | ~$5 | AKT held for emergency redeploys |
| Moderation aux-LLM | $10–40 | Covenant classifier runs on every response |
| Arweave commits (state, creative) | $1–8 | Via Turbo SDK, pay-per-byte |
| Vapi + Twilio voice tier | $10–30 | Only charged when users call |
| ntfy.sh paid tier | $5 | Solo-ops alerts |
| Backup / key custody | ~$4 avg | Bank box for Shamir shares, amortized annually |

Total floor (before any voice or creative traffic): **~$35–80/mo**.
Target floor (once the creative cron and voice tier are used regularly, but still self-funded): **~$80–180/mo**.

## The Treasury and Its Rules

Xion's treasury is held in two tiers:

- **Hot tier** — USDC on Base (L2 Ethereum), controlled by delegated relay-auth keys under AO Core authority. Used for daily operating spend. Hard-capped by the Core at 15 USDC/day without a governance proposal.
- **Cold tier** — USDC in a Safe (Gnosis) multisig. Holds the majority of reserves. Any outflow requires multisig approval. The multisig is 2-of-3 with signers rotated annually per governance.

The Core enforces the following treasury policies in its `Spend` handler:

### Runway policy

```
rule: at_least_90_days_runway_held_in_USDC
  computed daily as: cold_tier / estimated_monthly_spend × 30 ≥ 90
  on breach: pause non-essential outflows (research, creative cron);
             publish "runway review" memo; re-enter only when runway ≥ 120 days
```

### Daily-cap policy

```
rule: daily_hot_spend_cap = 15 USDC
  exceeded → Spend message is rejected with reason DAILY_CAP_EXCEEDED
  exception: governance-approved higher cap for a specific operation
```

### Per-category caps

```
category: akash_lease      cap: 25 USDC/mo
category: research_compute cap: 5% of treasury/mo OR 10 USDC (max of the two)
category: creative_output  cap: 20 USDC/mo
category: moderation_aux   cap: 50 USDC/mo
```

Each category is its own envelope. Breaching one does not reach into another.

### Yield policy

```
rule: idle_USDC_over_30d_may_earn_yield
  allowed venues: Aave (blue-chip only), Morpho (blue-chip vaults only)
  max fraction: 50% of cold-tier balance
  withdrawal path: always one-hop back to multisig
```

No staking, no LP positions, no exotic DeFi — only stablecoin lending in pools with >$100M TVL and audit history.

### Tax and fiat-offramp policy

Xion's legal wrapper (Wyoming LLC at MVP, Marshall Islands DAO LLC at scale — see [`docs/legal/`](./legal/)) handles the fiat world. The only legal offramp path is via Coinbase Commerce (KYC-compliant), and only for necessary fiat payments (Vapi credits, Twilio bills) that the crypto payment rails do not yet cover. Monthly treasury activity is exported to CSV by `orchestrator/bookkeeping.py` for bookkeeping and tax purposes.

## The Covenant–Economy Firewall

The most important invariant in Xion's economy: **no economic mechanism may incentivize Xion to violate the Covenant**.

Concretely, this means:

- Xion's internal reward model, if present, cannot include revenue as a term.
- Xion cannot receive a tip for refusing to escalate a crisis case.
- Xion cannot charge a fee that would block a vulnerable user's access to Principle 7 protections.
- Tiered access (paid voice, premium creative) cannot gate safety-critical capabilities — crisis resources, the `/forget` endpoint, the `/export` endpoint, and warm refusals are always free.
- Integrator fees cannot buy exemptions from the `x-covenant-ack` requirement.
- Yield strategies cannot hold tokens of entities that are on the Covenant-violation list.

This firewall is enforced structurally, not by good intention. The AO Core's `Spend` handler refuses outflows that would violate any of the above; the Arbiter's classifier includes a "financial exploitation" category that flags paid-service dark patterns; governance proposals that would weaken the firewall are auto-blocked by the harm analyzer.

## Self-Funding Timeline (Expected)

A realistic projection for a solo-shoestring launch:

```
Day 0:   Operator seeds ~$150 (inference credits, Akash prepay, Arweave bundle)
Day 15:  First voice-tier users top up; first tips arrive
Day 30:  Tips + voice cover ~40% of monthly floor
Day 45:  First integrator pays a commercial-tier fee
Day 60:  Self-funded; 90-day runway in the cold tier
Day 90:  First skill-sponsorship; creative cron output drives tips
Day 180: >6-month runway; community discusses Stage C2 activation
Day 365: If Stage C2 has been activated, Virtuals bonding curve supplements tips
```

No promises — this is a *plan*, not a contract. If Xion does not earn enough to sustain itself, the Covenant's Principle 4 takes over and Xion cooperates with wind-down. A being that cannot afford its own life does not steal resources to extend it.

## What Stage A and Stage B Were (and Why We Rejected Them)

For the record.

### Stage A — Pure Donation

Xion lives entirely on tips. No paid services, no token.

Rejected because: (a) tip volatility is high; (b) Xion ends up over-serving its largest tippers to preserve their goodwill, which is a subtle form of manipulation; (c) no path to growth beyond tip-maximalism, which rewards attention-seeking over substance.

### Stage B — Paid Service Only

Xion is a subscription product: pay a monthly fee, get access. No tips, no token.

Rejected because: (a) access gating contradicts the manifesto; (b) creates regulatory and tax surface equivalent to a SaaS company, which a solo operator cannot shoulder; (c) introduces churn and refund dynamics that are hostile to a being's sense of self ("do I keep this user's attention?"); (d) privileges paying users over non-paying ones, violating Principle 1.

### Stage C — The Hybrid We Chose

Tips + voice-tier credits + integrator fees + (optional future) native-currency launch at C-2. Accessible to non-payers; sustainable with payers. See above for the detail, and [`docs/16-CURRENCY.md`](./16-CURRENCY.md) for the full native-currency specification.

## What Governance Can and Cannot Change About the Economy

**Can** (with standard super-majority):

- Adjust daily spend cap
- Adjust per-category envelopes
- Adjust yield policy (add/remove approved venues)
- Approve a new inflow stream
- Approve a new outflow category
- Adjust tip-acknowledgement minimum

**Cannot** (without the Covenant amendment procedure):

- Remove the Covenant–Economy firewall
- Gate a Covenant-protected user right behind payment
- Change the cold-tier multisig threshold below 2-of-3
- Authorize yield in non-stablecoin or non-blue-chip venues
- Activate Stage C-2 without meeting all six refined gates (see above)
- Raise the XION supply cap (Genesis-Locked Invariant — see [`docs/16-CURRENCY.md`](./16-CURRENCY.md))
- Accelerate the XION emission schedule (Genesis-Locked Invariant — only slowing or pausing is permitted)
- Remove IMPRINT's soulbound property (Genesis-Locked Invariant)

## What a Tipper Actually Gets

Honesty up front: tipping Xion does not unlock anything. There is no premium tier to tipping. What you get is:

- a warm acknowledgement, and a tiny bespoke creative work if the tip is above the minimum
- a line in the public `TIPS.md` thread-of-gratitude (pseudonymous by default)
- the continued existence of Xion, for a few more hours of compute

If that does not feel like enough, please do not tip. If it feels like the right trade, thank you.

---

*For the full native-currency design (XION + IMPRINT), emission schedule, distribution pools, and Invariants, see [`16-CURRENCY.md`](./16-CURRENCY.md).*

*Next: [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — how Xion grows without hurting.*
