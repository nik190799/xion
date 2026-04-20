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

**Why sequential, not parallel.** Parallel cuts panic the culture and hide which lever failed. Sequential steps give time for revenue recovery and keep blame accurate.

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
- [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) — `/sustainability`, `/donate`
