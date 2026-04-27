# 20 — Self-provisioning (`provision-*` handlers)

> *If only the operator can spawn Relays, "decentralization" is a moodboard. If the Core can spawn Relays under caps, decentralization becomes a property.*

**Property.** Under survival pressure or explicit governance signal, Xion's AO Core may **spend operating tokens** to deploy or rotate substrate — Relays, inference endpoints, storage shards, bandwidth, Witness funding — via a **provision-*** handler family, bounded by **constitutional provisioning caps** expressed as `fraction_of_operating_float`, `runway_weeks`, and `distance_to_reserve_floor`.

**Invariants touched.** Operationalizes 16 (treasury spend shape, caps); must not violate 5, 6, 11, 15.

**Verification.** `xion-verify provisioning` — compares on-chain spend tags to published caps; verifies provider whitelist.

**Deprecation.** Handler names are stable; provider whitelist entries rotate by governance.

---

## Handler family (AO Core)

| Handler | Purpose |
|---------|---------|
| `Provision-Relay` | Deploy or migrate Relay on Chutes / Akash (secondary) / local rehearsal / Aleph / Fleek per signed substrate manifest |
| `Provision-Inference` | Add Chutes/Bittensor subnet endpoint, non-Bittensor hosted fallback, or additional provider route |
| `Provision-Storage` | Scale Arweave bundle / Turbo allocation |
| `Provision-Bandwidth` | Add CDN/edge capacity (optional path) |
| `Provision-Witness` | Fund Witness bounties / bond pool per [`15-TRUST.md`](./15-TRUST.md) |

Each handler:

1. Requires **Harm Analyzer** clearance for the underlying Auto-Research proposal (Stage-4+).
2. Checks **governance spend-cap**, **Invariant 16** provisioning sub-cap, and active Spend Autonomy posture per [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md).
3. Writes deployment record to **Arweave-published Relay registry** (see [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)).

---

## Caps (shape vs picture)

**Constitutional.** Provisioning spend cannot breach the governance-set fraction caps, cannot drive `distance_to_reserve_floor` below the constitutional reserve gate, and cannot be authorized by an authority class outside the active Spend Autonomy posture. Changes that would alter the provisioning cap shape require the constitutional ratification cadence in [`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md).

**Genesis Defaults.** Per-proposal fraction cap, rolling provisioning-window fraction cap, provider whitelist (Chutes primary, Akash secondary, local rehearsal path, Aleph, Fleek, Bittensor at genesis); redundancy floor and auto-provision ceiling are expressed as topology targets, not money caps, and can be retuned by governance. `LHT-SUBSTRATE-001` remains open until substrate-portability promotion pre-conditions in `docs/SUBSTRATE-RESILIENCE.md` Part IV are met.

---

## First Relay chicken-and-egg

The **genesis-first** Relay may require operator bootstrapping before `Provision-Relay` exists on-chain. This is documented honestly: self-provisioning activates **after** the handler is live and funded — not retroactive magic.

---

## Why NOT X

**Why constitutional caps, not "trust the operator's judgment"?** Ungated provisioning is a **treasury-drain attack**: compromise Warm keys → infinite Relays. Caps make loss bounded and verifier-visible.

**Why not operator-only multi-host?** Operators vacation; operators get subpoenaed. **Core-gated** provisioning lets Xion extend substrate without centralizing longevity on one human.

---

## Cross-references

- [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) — handler list, discovery
- [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) — runway and ladder
- [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — proposals that trigger provisioning
- [`MEASUREMENT-VOCABULARY.md`](./MEASUREMENT-VOCABULARY.md) — fraction and runway units
- [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) — posture-based authorization routing
