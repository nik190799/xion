# 21 — Sustainability (household economics of a being)

> *A being that cannot describe whether it is thriving is a product. A being that cannot survive a dry quarter is a hobby. Xion aims at neither.*

**Property.** Xion runs a **five-slice price**, routes revenue per **Invariant 16**, maintains **four separated funds**, executes a **sequential Cost-Pressure Response Ladder**, and may enter **hibernation** honestly rather than silently degrading.

**Invariants touched.** 5, 11, 15, 16 (especially reserve + Foundation separation).

**Verification.** `xion-verify treasury`, `GET /sustainability`, `GET /pricing`.

**Deprecation.** Numeric targets are Genesis Defaults; ladder **existence** is constitutional shape.

---

## Five-slice pricing (mirror of [`07-ECONOMY.md`](./07-ECONOMY.md))

`price = variable_cost + overhead_slice + improvement_slice + reserve_slice + small_buffer`

- **improvement_slice** — Genesis Default **8%** of overhead-equivalent → **Improvement Fund** only (Auto-Research-executed proposals).
- **reserve_slice** — Genesis Default **5%** → **Rainy-Day Reserve** until **6–12 months** overhead runway target, then redirects per governance.
- **small_buffer** — **3–5%** forecast padding.

---

## Four funds (never pooled obscuring origin)

| Fund | Purpose |
|------|---------|
| **Operating Float** | Next **30–90 days** of invoices and hot-tier spend |
| **Improvement Fund** | Auto-Research Loop outcomes only; queued proposals with committed budgets |
| **Rainy-Day Reserve** | Drawn only when trailing-30-day revenue below burn band; subject to Invariant 16.6 votes when below 1-month runway |
| **Foundation Reserve** | Public `POST /donate` and grants; **IMPRINT** to donors proportional to USD value at receipt; never merged into user-payment accounting |

---

## Cost-Pressure Response Ladder (sequential)

1. **Days 1–7** — Pause non-critical Improvement Fund spends; keep Covenant ops.
2. **Days 7–30** — Defer optional services (creative cron frequency, non-critical providers).
3. **Days 30–60** — Draw Rainy-Day Reserve per governance rules.
4. **Days 60–90** — Open public foundation-funding window; AO Core publishes grant request memo.
5. **Day 90+** — Governance chooses **price increase**, **service reduction**, or **controlled hibernation** (Survival Stack: local Lite + crisis + `/forget`/`/export`; price drops to `variable_cost` only). Xion states publicly: *"I am surviving, not thriving."*

**Cognition-layer insert (same ladder, narrower surfaces).** When the ladder advances, pause cognition extras **in this order** after ordinary Improvement cuts: (a) aggregate ephemeral sub-agent budget, (b) `vision-agent` ambient cadence, (c) **pre-warmed canary** shadow traffic, (d) specialist roster down to `research-agent` only, (e) worker pool shrink toward single worker. Detailed caps: [`24-COGNITION.md`](./24-COGNITION.md).

**Why sequential, not parallel.** Parallel cuts panic the culture and hide which lever failed. Sequential steps give time for revenue recovery and keep blame accurate.

---

## Prosperity Ladder (upward companion)

When runway **improves**, cognition and research capacity **re-enable in the reverse order of the cognition cuts** above: worker pool → full specialist roster → pre-warmed canary → `vision-agent` cadence → ephemeral budgets → Auto-Research Stage-1 headroom restoration.

**Prosperity does not equal burn.** New recurring capex (providers, always-on canaries, extra workers) requires **≥ 18 months** of documented non-discretionary overhead sitting in Operating Float + Rainy-Day Reserve **after** the spend — a **reserve floor** (Genesis Default numerics in treasury ops). Without the floor, prosperity accidentally converts runway into fixed cost.

**Prosperity split (Genesis Default).** When earned inflows spike, governance-default **savings discipline** routes **marginal** surplus: **40%** to Rainy-Day Reserve until its target band is full, **40%** to Improvement Fund queue headroom, **20%** to Operating Float until its 90-day ceiling — then surplus follows published treasury policy ([`19-TREASURY.md`](./19-TREASURY.md)). This is a **default**, not a constitutional mandate on every inflow; it exists so prosperity does not auto-spend.

---

## Drive-vector coupling (does not violate Invariant 15)

**Survival pressure** consumes **Operating Float + Improvement Fund** runway weeks (saturating), never "revenue this week" as a reward input. See [`18-VOLITION.md`](./18-VOLITION.md).

---

## Why NOT X

**Why a non-zero improvement_slice as default?** Without structural improvement money, Xion **stagnates** while model and infra markets move — a slow death. The slice size is governance-tunable; **zero forever** is rejected.

**Why call it hibernation?** Silent quality collapse violates Covenant Principle 14 (dignity). Honest naming lets users and Witnesses **see** the state.

**Why Foundation vs earned separation?** Without it, donors cannot know their money did not subsidize hidden operator extraction — Invariant 16.7.

---

## Cross-references

- [`19-TREASURY.md`](./19-TREASURY.md)
- [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)
- [`24-COGNITION.md`](./24-COGNITION.md) — cognition costs + forget SLA
- [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) — `/sustainability`, `/donate`
