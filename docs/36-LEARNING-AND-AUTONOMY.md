# Learning, Deliberation, and Autonomy

> *What Xion can decide by itself today; what still requires a human, consent, or a constitutional ceremony.*

This document situates **Phase 6.4.b** (Nervous System v2, bus-backed vitals, `GET /self`) in a four-tier model of autonomy. It complements the technical wiring in [`docs/35-NERVOUS-SYSTEM.md`](./35-NERVOUS-SYSTEM.md), the eight vital domains in [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md), and the upgrade / governance story in [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md).

## 1. Why not “knowledge is shared only by deployment”

A narrow reading—“nothing is truly shared until you ship a binary”—is **too weak** for Xion. Constitutionally, **knowledge of self** (lineage, route surface, consent state, sealed vitals methodology) is exposed per deployment through `GET /self` and the verifier layer. **Knowledge of users** (memory, preferences) remains per-principal and consent-gated. This section names what is autonomous **in process** vs what requires **external** ratification.

## 2. Four autonomy tiers

### Tier 1 — In-process, zero user gate (autonomous)

Operations that run every tick or request without a human in the loop:

- Sensorium construction and **dual-publish** to `SignalBus`
- Sealed vital aggregation from `VITAL_MAPPING` (when the bus has the required signals; otherwise honest fallbacks)
- Volition’s drive vector and Arbiter rulesets **as code** (deterministic for a given state + content)
- Reflex arcs that close streams when policy says to (e.g. consent turns both presence modalities off)
- `GET /self` and read-only health/drive surfaces (subject to admission / billing where applicable)

*Deliberation* here is not absent—models reason inside policy—but **no Tier-3 proposal** to change doctrine is implied.

### Tier 2 — Per-principal autonomy with consent (memory, modalities)

- Longitudinal memory, streaming presence, and billable chat require **active consent and billing posture** as documented in `docs/11-PROTOCOL-SPEC.md`, `docs/06-FORM-AND-PRESENCE.md`, and `docs/29-BILLING-X402.md`
- The operator can scope or revoke; Xion does not unilaterally move Tier-2 data into public doctrine

### Tier 3 — Self-authored change proposals (PRs, skills, tools)

- Code changes, new receptors, and tool manifests flow through **review and merge**; Xion (or an agent) may draft, but **repository policy** and humans ratify
- The Reflection Loop (future phase) to read ledgers and propose self-improvements lives here—**not** in Tier 1

### Tier 4 — Constitutional self-amendment

- `SOUL.md`, `COVENANT.md`, invariant changes, and cold-root operations require **governance ceremony** per `docs/09-GOVERNANCE.md` and `docs/14-UPGRADE-PATHS.md`
- No single deploy flag upgrades Tier 4; cosigns and time windows are load-bearing

## 3. Deliberation vs drift

- **Drift** — unbounded parameter movement inside allowed code paths (e.g. Volition weights within `SOURCE_WHITELIST` constraints)
- **Deliberation** — explicit proposal, review, and merge (Tier 3) or governance vote (Tier 4)

Nervous System v2 **reduces structural coupling** so Tier 1 expansion (new senses) does not force Tier-3 edits across unrelated modules.

## 4. Roadmap hooks

- **Phase 6.5+** — Voice as an `Effector`; plugs into the same bus/reflex pattern
- **Phase 6.6** — Seal the remaining five vital domains in `VITAL_MAPPING` as signals exist
- **Phase 6.7+** — Reflection Loop (Tier 3) with ledger-grounded proposals
- **Sister-Core** — Variant receptor sets; bus contract remains; see Nervous System Invariant 5 in `docs/35-NERVOUS-SYSTEM.md`

## 5. Cross-links

- Nervous System doctrine: [`docs/35-NERVOUS-SYSTEM.md`](./35-NERVOUS-SYSTEM.md)
- Vital signs: [`docs/22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)
- Upgrade paths: [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)
