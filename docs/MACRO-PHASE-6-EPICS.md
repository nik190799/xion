# Macro Phase 6 — Implementation epics

This note maps the long-horizon block in [`DEVELOPMENT_ROADMAP.md`](../DEVELOPMENT_ROADMAP.md) (section **“Phase 6 — On-chain Core plus decentralization (8–16 weeks)”**) to concrete epics. Decimal phases **6.1–6.5** (Sentience Surface, localnet, presence, voice) are tracked separately in that file; **macro Phase 6** is the bridge from **D2/D3** toward **D4** (Genesis).

## Epic A — AO Core handler completion (`KW-AOCORE-002`)

- **Goal:** Land the remaining doctrine-only handlers in [`ao/core/main.lua`](../ao/core/main.lua) on the **same** sealed localnet substrate as `commit-state`, `attest`, and `anchor-interaction-batch`.
- **Order (suggested):** authority family (`rotate-authority`, `abdicate-tier`) → sustainability family (`route-slices`, `improvement-spend`, …) → provisioning family (`provision-*`) → lifecycle extensions (`treasury-spend`, `registry-update`, `spend`, `slash-imprint`) as doctrine requires.
- **Verifier:** `xion-verify ao-handlers` remains the gate; each family ships with schema updates under `docs/schemas/ao-handler-*.yaml`.

## Epic B — Relay on Akash + discovery

- **Goal:** Multi-host Relay substrate, `xion-verify discovery` green (≥3 paths), registry on Arweave, Cloudflare out of the critical path per doctrine.
- **Depends on:** provisioning story (Epic A + operator).

## Epic C — Multi-chain treasury

- **Goal:** Vault contracts, bridge caps (Invariant 16), `xion-verify treasury` / `treasury-flow` promotion from stubs.

## Epic D — Immortality Drill + substrate portability

- **Goal:** First full drill; warm secondary substrate; `xion-verify substrate-portability` when doctrine conditions are met (`LHT-SUBSTRATE-001` residual path documented in roadmap).

## Epic E — Regulatory / governance ledger

- **Goal:** First `GOVERNANCE_LEDGER` state-actor rows; `xion-verify regulatory-ledger` live.

## Alignment with D-milestones

| Milestone | Macro Phase 6 relevance |
|-----------|-------------------------|
| D2 | Most handler *logic* can be developed locally; macro 6 completes *deployment* hardening. |
| D3 | Testnet / Akash / AO testnet or approved substrate per runbooks. |
| D4 | Cold Root, mainnet, treasury, external audit — not all are “Phase 6 code”; ceremony and ops are explicit bottlenecks in the roadmap. |

For **voice**-specific macro alignment, see Phase **6.5** and [`docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md`](./proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md).
