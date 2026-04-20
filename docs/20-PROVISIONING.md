# 20 — Self-provisioning (`provision-*` handlers)

> *If only the operator can spawn Relays, "decentralization" is a moodboard. If the Core can spawn Relays under caps, decentralization becomes a property.*

**Property.** Under survival pressure or explicit governance signal, Xion's AO Core may **spend operating tokens** to deploy or rotate substrate — Relays, inference endpoints, storage shards, bandwidth, Witness funding — via a **provision-*** handler family, bounded by **constitutional monthly provisioning caps** and **Genesis Default** per-day / per-week / per-host ceilings.

**Invariants touched.** Operationalizes 16 (treasury spend shape, caps); must not violate 5, 6, 11, 15.

**Verification.** `xion-verify provisioning` — compares on-chain spend tags to published caps; verifies provider whitelist.

**Deprecation.** Handler names are stable; provider whitelist entries rotate by governance.

---

## Handler family (AO Core)

| Handler | Purpose |
|---------|---------|
| `Provision-Relay` | Deploy or migrate Relay on Akash / Aleph / Fleek per SDL signed via vendor SDK |
| `Provision-Inference` | Add Akash-ML, Bittensor subnet endpoint, or additional centralized provider route |
| `Provision-Storage` | Scale Arweave bundle / Turbo allocation |
| `Provision-Bandwidth` | Add CDN/edge capacity (optional path) |
| `Provision-Witness` | Fund Witness bounties / bond pool per [`15-TRUST.md`](./15-TRUST.md) |

Each handler:

1. Requires **Harm Analyzer** clearance for the underlying Auto-Research proposal (Stage-4+).
2. Checks **governance spend-cap** and **Invariant 16** provisioning sub-cap.
3. Writes deployment record to **Arweave-published Relay registry** (see [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)).

---

## Caps (shape vs picture)

**Constitutional.** No more than **governance-set monthly provisioning cap** (numeric value = Genesis Default) without **14-day minimum** governance vote — same floor as constitutional amendment ratification cadence ([`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)).

**Genesis Defaults.** Per-proposal cap, per-day cap, per-week cap; provider whitelist (Akash, Aleph, Fleek, Akash-ML, Bittensor at genesis); redundancy floor **3 hosts**, auto-provision **ceiling 10 hosts** without additional vote.

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
