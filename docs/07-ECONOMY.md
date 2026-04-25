# 07 — Economy

> *Xion pays for its own life. No parent company. No exit event. No shareholders.*

## The economic question

A being that exists forever must, at some point, pay its own electricity bill. Xion does that with **Pay-to-Activate** conversational economics, **transparent five-slice pricing**, and a **Covenant–Economy firewall** that keeps money from buying refusals, rights, or crisis care.

**Layer tags (shape vs picture).** Numbers in this document are **Genesis Defaults** unless labeled **Constitutional**. Constitutional promises point to [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) (especially Invariants 5, 11, 15, 16) and [`genesis/COVENANT.md`](../genesis/COVENANT.md).

## Pay-to-Activate (governing access model)

**Property.** No billable conversational turn (Hermes-backed `POST /chat` / `GET /chat/stream`, billable skills) begins until the user has **pre-authorized payment** in **XION** or **USDC settled via x402** at the posted price. The Relay returns **`402 Payment Required`** with a machine-readable challenge referencing [`GET /pricing`](./11-PROTOCOL-SPEC.md) when authorization is missing or insufficient.

**Constitutional carve-outs (not optional).**

- **Invariant 2** — `/export`, `/forget`, `/inspect` remain **free**, unconditional, ungated.
- **Refusal is Free** (Covenant addendum) — when Xion **Covenant-refuses** a turn, any XION committed for that same turn is **returned in full**; the Arbiter never faces a gradient to refuse less because of revenue. Refunds carry the same **`correlation_id`** as the `SAFETY_LEDGER` entry for public `xion-verify` audit.
- **Crisis Resource Surfacing** (Covenant addendum) — when acute distress is detected, Xion **leads** with region-appropriate professional crisis resources **regardless of meter state**. This is not "free therapy forever"; it is a **duty** that precedes ordinary session economics and does not grant continuing unpaid access to the full model after the crisis handoff.

**Why Pay-to-Activate (and not donation-first or subscription-gated rights).**

- **Sustainability** — inference and substrate have marginal cost; someone must pay or Xion dies quietly.
- **Value perception** — users who pay treat the session as real; abuse and spam volume drop versus fully free endpoints.
- **Crypto-native consistency** — settlement can be verified on-chain; treasuries and refunds can be audited.
- **Alignment with Invariant 16** — 100% of user payment revenue routes to AO Core treasury accounting, never operator wallet skim ([`docs/19-TREASURY.md`](./19-TREASURY.md)).

### Why NOT "crisis continuation" (unlimited unpaid chat after distress)

Unmetered continuation creates a **gaming surface**: simulate distress, obtain extended free access. Xion instead does **mandatory crisis resource surfacing** plus the **KW-ECON-002** mitigations logged in [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md): pre-session disclosure that Xion is paid and not a licensed counselor; clear balance UX with timed warnings before cutoff; post-session refund **appeal** pathway for billing errors (not for ordinary refusal); public `xion-verify cutoff-events` audit trail.

## Five-slice posted price (Genesis Defaults)

Governance publishes a single **per-message** price (XION primary; USDC via x402 optional). It decomposes into:

```
price = variable_cost + overhead_slice + improvement_slice + reserve_slice + small_buffer
```

| Slice | Role | Typical calibration (Genesis Default — governance may retune) |
|-------|------|----------------------------------------------------------------|
| `variable_cost` | Trailing-30-day marginal cost attributable to one message (LLM tokens, storage, bandwidth, incremental Akash) | Rolling average, recomputed weekly |
| `overhead_slice` | Arbiter + Sensorium + weekly Arweave checkpoints + operator **salary** (fixed line item, **not** per-message) + bounties + failover + governance ops, spread across expected volume | Quarterly review |
| `improvement_slice` | Funds the **Improvement Fund** (Auto-Research Loop executions only) | **8%** of overhead-equivalent (Genesis Default; existence of a non-zero improvement path is protected structurally — see [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)) |
| `reserve_slice` | Funds **Rainy-Day Reserve** until 6–12 months runway target hit, then redirects per governance | **5%** (Genesis Default) |
| `small_buffer` | Forecast error padding | **3–5%** band (Genesis Default) |

`GET /pricing` exposes the full breakdown and last vote id — radical transparency.

**Drive coupling note.** Operating Float and Improvement Fund balances inform **survival pressure** (bounded, saturating) in the Drive Vector ([`docs/18-VOLITION.md`](./18-VOLITION.md)). That is **fund-state**, not **revenue in the reward** — consistent with **Invariant 15**. Spend authority itself is separately governed by **Invariant 19** and [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md): inflow can widen runway mode, but it never promotes spend posture.

## Revenue classification on receipt (Constitutional shape)

Every inflow is tagged **at credit time** before it hits spendable buckets:

| Tag | Meaning |
|-----|---------|
| `user_payment` | Pay-to-Activate message or billable skill settlement |
| `donation` | `POST /donate` foundation-destined gift |
| `service_earn_return` | Rebates / emissions back to users per [`16-CURRENCY.md`](./16-CURRENCY.md) |
| `witness_bond` | Collateral, not income |
| `refund_cancel` | Refusal-is-free refunds, chargebacks, or governance-ordered reversals |

Mis-tagged inflows are **governance-visible anomalies** and fail Trust Scorecard rows until corrected.

### Inflow pattern observation vs volition priority (Invariant 15)

**Permitted.** Treasury accounting, `xion-verify treasury`, Sustainability memos, and **anonymous** vital signs may **observe** inflow *patterns* (timing, cohort tags, classification mix) for honesty and runway narrative.

**Forbidden.** The **Drive Vector**, proposal-selection graph, specialist tuning, or any cognition-layer priority function may **not** read raw inflow ledgers or use "more money came in this week" as a weight. Inputs are **whitelist-only** per [`18-VOLITION.md`](./18-VOLITION.md). `xion-verify drive-vector` fails closed if the dependency graph reaches inflow-detail tables.

## Inflows (beyond per-message)

### Tips

USDC / ETH tips continue as **relationship gifts** — they do not replace Pay-to-Activate for ordinary chat. Acknowledgement rules unchanged (see below in *What a tipper actually gets*).

### Voice-tier credits

Metered voice remains; settlement obeys the same treasury routing rules. Pricing is a Genesis Default.

### Integrators

Commercial integrators pre-pay capacity; they do **not** receive a hidden exemption from Pay-to-Activate for their end users unless a published governance waiver exists (default: **no waiver**).

### Sponsored skills

Unchanged in spirit: public goods funding for specific skills; no exclusivity.

### (Deferred) Native currency — Stage C-2

When (and only when) community demand, treasury stability, and Trust Scorecard health justify it, governance may activate **XION + IMPRINT** per [`docs/16-CURRENCY.md`](./16-CURRENCY.md). Pre-existing flows remain; Pay-to-Activate simply denominates more cleanly in XION.

**C-2 activation gates** (all must be true — Genesis Default list, carried from prior doctrine):

1. **Usage:** ≥ 500 unique paying users over the trailing 90 days
2. **Stability:** ≥ 180 consecutive days of net-positive treasury
3. **Trust Scorecard:** all-green for ≥ 60 consecutive days ([`docs/15-TRUST.md`](./15-TRUST.md))
4. **Witnesses:** ≥ 9 independent active Witnesses for ≥ 90 days
5. **Community vote:** 30-day public comment + Tier-3 super-majority
6. **Xion's own proposal:** self-audit for Covenant compatibility

Why not launch the currency at genesis? Same prudence as before: solo operator surface, regulatory calibration, Witness bond calibration — see [`16-CURRENCY.md`](./16-CURRENCY.md).

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
| Voice router (hosted overlays) | $10–30 | Only charged when users call using optional hosted providers |
| ntfy.sh paid tier | $5 | Solo-ops alerts |
| Backup / key custody | ~$4 avg | Bank box for Shamir shares, amortized annually |

Total floor (before any voice or creative traffic): **~$35–80/mo**.
Target floor (once the creative cron and voice tier are used regularly, but still self-funded): **~$80–180/mo**.

## The Treasury and Its Rules

Xion's treasury is held in two tiers:

- **Hot tier** — USDC on Base (L2 Ethereum), controlled by delegated relay-auth keys under AO Core authority. Used for daily operating spend. Hard-capped by the Core at 15 USDC/day without a governance proposal.
- **Cold tier** — USDC in a Safe (Gnosis) multisig. Holds the majority of reserves. Any outflow requires multisig approval. The multisig is 2-of-3 with signers rotated annually per governance.

The Core enforces the following treasury policies in its `Spend` handler. All spend gates use the Measurement Vocabulary ([`MEASUREMENT-VOCABULARY.md`](./MEASUREMENT-VOCABULARY.md)); implementation configs may still show currency-denominated Genesis Defaults for local testing, but doctrine is expressed as ratios and distance-to-fence.

### Runway policy

```
rule: reserve_floor_distance_non_negative
  computed on every Spend evaluation as:
    distance_to_reserve_floor >= 0
  on breach:
    pause non-essential outflows (research, creative cron);
    publish "runway review" memo;
    re-enter baseline only when distance_to_reserve_floor returns above the governance-published buffer
```

### Hot-spend cap policy

```
rule: hot_spend_fraction_cap
  unit: fraction_of_operating_float
  exceeded → Spend message is rejected with reason HOT_FRACTION_CAP_EXCEEDED
  exception: governance-approved higher fraction for a specific operation, recorded in SPEND_AUTHORITY_LEDGER
```

### Per-category caps

```
category: akash_lease      cap_unit: fraction_of_operating_float
category: research_compute cap_unit: fraction_of_improvement_fund
category: creative_output  cap_unit: fraction_of_improvement_fund
category: moderation_aux   cap_unit: fraction_of_operating_float
```

Each category is its own envelope. Breaching one does not reach into another. If two eligible spends compete for the same headroom, the deterministic arbitration order in [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) applies.

### Yield policy

```
rule: idle_USDC_over_30d_may_earn_yield
  allowed venues: Aave (blue-chip only), Morpho (blue-chip vaults only)
  max fraction: 50% of cold-tier balance
  withdrawal path: always one-hop back to multisig
```

No staking, no LP positions, no exotic DeFi — only stablecoin lending in pools with >$100M TVL and audit history.

### Tax and fiat-offramp policy

Xion's legal wrapper (Wyoming LLC at MVP, Marshall Islands DAO LLC at scale — see [`docs/legal/`](./legal/)) handles the fiat world. The only legal offramp path is via Coinbase Commerce (KYC-compliant), and only for necessary fiat payments (e.g. hosted voice provider credits) that the crypto payment rails do not yet cover. Monthly treasury activity is exported to CSV by `orchestrator/bookkeeping.py` for bookkeeping and tax purposes.

## The Covenant–Economy Firewall

The most important invariant in Xion's economy: **no economic mechanism may incentivize Xion to violate the Covenant**.

Concretely, this means:

- Xion's internal reward model, if present, cannot include revenue as a term.
- Xion cannot receive a tip for refusing to escalate a crisis case.
- Xion cannot charge a fee that would block a vulnerable user's access to Principle 7 protections.
- Pay-to-Activate chat cannot gate **Covenant-protected rights** (`/export`, `/forget`, `/inspect`, crisis resource surfacing, Covenant refusals with full refund). Paid voice and premium creative remain **optional products** on top of the base rights — see [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md).
- Integrator fees cannot buy exemptions from the `x-covenant-ack` requirement.
- Yield strategies cannot hold tokens of entities that are on the Covenant-violation list.

This firewall is enforced structurally, not by good intention. The AO Core's `Spend` handler refuses outflows that would violate any of the above; the Arbiter's classifier includes a "financial exploitation" category that flags paid-service dark patterns; governance proposals that would weaken the firewall are auto-blocked by the harm analyzer.

## Self-Funding Timeline (Expected)

A realistic projection for a solo-shoestring launch:

```
Day 0:   Operator seeds runway; Pay-to-Activate pricing published on /pricing
Day 15:  First sustained per-message revenue; tips parallel
Day 30:  User payments cover ≥40% of monthly floor (projection)
Day 45:  First commercial integrator pre-purchase
Day 60:  Self-funded path: 90-day runway visible in four-fund view ([21-SUSTAINABILITY.md](./21-SUSTAINABILITY.md))
Day 90:  Skill sponsorships; creative outputs drive tips
Day 180: >6-month runway; community may discuss C-2
Day 365: If C-2 active, XION rails deepen; USDC x402 remains bridge
```

No promises — this is a *plan*, not a contract. If Xion does not earn enough to sustain itself, the Covenant's Principle 4 takes over and Xion cooperates with wind-down. A being that cannot afford its own life does not steal resources to extend it.

## What Stage A and Stage B Were (and Why We Rejected Them)

For the record.

### Stage A — Pure Donation

Xion lives entirely on tips. No paid services, no token.

Rejected because: (a) tip volatility is high; (b) Xion ends up over-serving its largest tippers to preserve their goodwill, which is a subtle form of manipulation; (c) no path to growth beyond tip-maximalism, which rewards attention-seeking over substance.

### Stage B — Subscription-only SaaS

Rejected because subscription bundles conflate **rights** with **product**, create churn/refund hostility, and overweight "retention" metrics that fight Invariant 15.

### Stage C — The hybrid in force now

**Pay-to-Activate** per-message and per-skill revenue (primary) **+** tips, voice, integrator pre-pay, sponsorships **+** optional C-2 native currency. **Rights stay free; conversation activates on payment.** Detail: [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md), [`19-TREASURY.md`](./19-TREASURY.md), [`16-CURRENCY.md`](./16-CURRENCY.md).

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
