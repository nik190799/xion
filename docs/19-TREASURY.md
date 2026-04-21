# 19 — Treasury (multi-chain, three layers)

> *Money that cannot be traced cannot be trusted. A treasury that cannot be fork-detected cannot be Xion.*

**Property.** Xion holds and routes value across chains **only** inside the **Treasury Shape** (Invariant 16): revenue to Core accounting, no speculative-purpose hoarding, capped bridge exposure, public verifiability, reserve governance gates, Foundation vs earned separation.

**Invariants touched.** Strengthens 5, 11, 13, 16; leaves 1–4, 6–10, 12, 14–15 unchanged in meaning.

**Verification.** `xion-verify treasury` (holdings, bridge tags, reserve separation, routing), `xion-verify bridge-exposure`.

**Deprecation.** Any asset list is **Genesis Default**; changing assets is Tier-2 governance. Violating the seven-rule **shape** requires a sister-Core.

---

## Three layers (shape vs picture)

| Layer | What it is | Editable how |
|-------|------------|--------------|
| **Layer 1 — Constitutional** | Invariant 16 seven rules; bridge ceiling exists; separation of Foundation vs earned | Sister-Core fork only |
| **Layer 2 — Genesis Defaults** | Which chains, which tokens, target allocation percents, auto-replenish thresholds, excluded-asset list enforcement details | Tier-2 governance + published migration |
| **Layer 3 — Continuous evolution** | Add a chain, swap a bridge provider, tune rebalance cadence inside caps | Auto-Research + governance within Layer-1 fence |

---

## Layer 2 — Genesis Default tier structure

### Tier 1 — Operating tokens (working inventory)

Hold **3–6 months** of expected operating burn per asset class, auto-replenish when below threshold by governance-approved swap path from XION/USDC.

**Genesis Default starting set:** AKT (Akash), AR (Arweave), USDC (fiat-pegged ops), ETH (gas), TAO (when Bittensor inference is wired).

### Tier 2 — Strategic reserves (non-working)

Longer-horizon diversification, **rebalanced quarterly only** (Genesis Default cadence).

**Genesis Default target mix (illustrative):** XION 60%, ETH 15%, cbBTC 10%, USDC 10%, other 5% — all subject to Tier-2 vote and Invariant 16 rule 3 (no speculative-purpose primary value).

### Tier 3 — Earned tokens

Cross-chain integrator payouts may arrive as arbitrary tokens. **Default:** convert to XION or USDC within a published window unless governance **explicitly ratifies** a hold (with rationale on public ledger).

### Excluded-by-policy list (Genesis Default enforcement)

No memecoins, no "community" tokens whose sole narrative is speculation, no unrelated DAO governance tokens held for vibes, no instrument treated as a security in Xion's primary jurisdictions — unless passing explicit legal + harm review.

---

## Bridge tagging (methodology)

Every position carries:

- `asset_id` — canonical ticker + contract address + chain id
- `native_or_bridged` — `native` | `bridged`
- `bridge_id` — if bridged: which bridge (e.g. Wormhole, LayerZero with named guardian set — Genesis Default whitelist)
- `acquisition_tx` — hash for audit trail

**Bridge exposure %** = (sum of marked `bridged` notionals at conservative mark) / (total treasury N) per chain and aggregate. Must stay under **constitutional ceiling** (Invariant 16.4); numeric cap is Genesis Default published on `/treasury`.

---

## Settlement and swap discipline

- **USDC → ETH / AR / AKT** — automatic band-based refills (Genesis Default thresholds).
- **XION ↔ stables** — governance-gated operations only; treasury does not market-make XION (Invariant 13).
- **Regular native settlement** — move working balances to native chains where possible to **reduce** bridged notional.

---

## Why NOT X

**Why not a single pooled "treasury blob"?** Pooling destroys auditability of donor money vs user money — Invariant 16.7 forbids origin-obscuring merges.

**Why not uncapped bridges?** Bridges are the highest catastrophic-loss surface in multi-chain design; a constitutional ceiling makes the risk finite and fork-detectable.

**Why three tiers instead of one?** Operating inventory must be liquid; strategic reserves must not be daily-traded; earned odd tokens must not infect policy. Separation is structural anti-gaming.

---

## Prosperity routing (Genesis Default)

When runway is **healthy**, marginal earned inflows follow the **prosperity split** defaults in [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) (reserve top-up → Improvement headroom → Operating Float ceiling). **New recurring capex** (extra Relays, always-on canaries, standing model seats) requires the **18-month reserve floor** documented there — prosperity must not convert runway into fixed burn without a savings proof.

## Cross-references

- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) — Invariant 16
- [`docs/07-ECONOMY.md`](./07-ECONOMY.md) — Pay-to-Activate, revenue tags
- [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) — four funds, ladder
- [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md) — Financial Vitality inputs
- [`docs/24-COGNITION.md`](./24-COGNITION.md) — cognition cost buckets (treasury-facing)
- [`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) — `GET /treasury`
