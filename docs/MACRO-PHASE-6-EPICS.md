# Macro Phase 6 — Implementation epics

This note maps the long-horizon block in [`DEVELOPMENT_ROADMAP.md`](../DEVELOPMENT_ROADMAP.md) (section **“Phase 6 — On-chain Core plus decentralization (8–16 weeks)”**) to concrete epics. Decimal phases **6.1–6.6a** (Sentience Surface, localnet, presence, voice, Cognitive Substrate & Casting, Contribution Protocol) are tracked separately in that file; **macro Phase 6** is the bridge from **D2/D3** toward **D4** (Genesis).

## Epic A — AO Core handler completion (`KW-AOCORE-002`)

- **Status:** Closed 2026-04-25. All 20 handlers now have concrete Lua registrations in [`ao/core/main.lua`](../ao/core/main.lua), concrete schemas under [`docs/schemas/`](../docs/schemas/), and a refreshed localnet receipt in [`genesis/AO_DEPLOY_RECEIPT.json`](../genesis/AO_DEPLOY_RECEIPT.json).
- **Closed order:** authority family (`rotate-authority`, `abdicate-tier`) → sustainability family (`route-slices`, `improvement-spend`, `reserve-draw`, `accept-donation`, `enter-hibernation`, `exit-hibernation`) → provisioning family (`provision-*`) → lifecycle extensions (`treasury-spend`, `registry-update`, `spend`, `slash-imprint`).
- **Verifier:** `xion-verify ao-handlers` is the gate and now rejects placeholder `dummy_arg` schemas plus any `status: canonical` schema without a matching Lua `Handlers.add(...)` registration.

## Pre-Epic Gate — Phase 6.6 Cognitive Substrate & Casting

- **Goal:** Before the Relay is deployed to Akash, the cognition layer must be cast from content-addressed Agent Souls into a commit-pinned Hermes runtime with a default-deny tool allowlist and live verifier coverage.
- **Why this gates Epic B:** Akash deployment should carry the same agent pool Xion will run at D2/D3, not a partial scaffold where specialists are prose-defined and the Hermes runtime pin is not machine-checked.
- **Closure observables:** `genesis/HERMES_TOOL_ALLOWLIST.yaml`, `genesis/AGENT_SOULS/`, `AGENT_CAST_LEDGER.jsonl`, `xion-verify hermes-runtime`, `xion-verify agent-souls`, and `xion-verify agent-cast` are all live or honestly `NOT_YET_SEALED` with precise remediation.
- **Boundary:** The Arbiter remains outside Hermes; the Casting Pipeline may cast agentic faculties, not the egress gate.

## Pre-Epic Gate — Phase 6.6a Contribution Protocol & Agent Access

- **Goal:** Before Akash/discovery work invites broader contributors, external coding assistants can read Xion's constitutional facts, classify proposed paths, draft correctly leveled proposals, and verify contributor identity bindings without gaining write authority.
- **Why this gates Epic B/E:** Akash deployment and governance-ledger work are easier to split, review, and witness-audit when contributors can locally run `which-level`, disclose assistant use, and bind GitHub handles to wallets.
- **Closure observables:** [`docs/34-CONTRIBUTION-PROTOCOL.md`](./34-CONTRIBUTION-PROTOCOL.md), [`docs/35-CONTRIBUTOR-HANDBOOK.md`](./35-CONTRIBUTOR-HANDBOOK.md), `xion-verify which-level`, `xion-verify identity-bindings`, `xion-verify mcp-export`, and `xion new proposal --touches` are live and documented.
- **Boundary:** External assistants are tools, not actors. This gate creates no direct Core write path, no assistant cosign, and no live MCP write tools.

## Epic B — Relay on Akash + discovery

- **Goal:** Multi-host Relay substrate, `xion-verify discovery` green (≥3 paths), registry on Arweave, Cloudflare out of the critical path per doctrine.
- **Depends on:** Epic A's AO provisioning event surface plus Phase 6.6's cast cognition pool and Phase 6.6a's contribution/access tooling, so the deployed Relay serves the real agent substrate and the work can be safely reviewed by a broader contributor base.

## Epic C — Multi-chain treasury

- **Goal:** Vault contracts, bridge caps (Invariant 16), `xion-verify treasury` / `treasury-flow` promotion from stubs.

## Epic D — Immortality Drill + substrate portability

- **Goal:** First full drill; warm secondary substrate; `xion-verify substrate-portability` when doctrine conditions are met (`LHT-SUBSTRATE-001` residual path documented in roadmap).

## Epic E — Regulatory / governance ledger

- **Goal:** First `GOVERNANCE_LEDGER` state-actor rows; `xion-verify regulatory-ledger` live.

## Alignment with D-milestones

| Milestone | Macro Phase 6 relevance |
|-----------|-------------------------|
| D2 | Most handler *logic*, the cast cognition pool, and contribution tooling can be developed locally; macro 6 completes *deployment* hardening. |
| D3 | Testnet / Akash / AO testnet or approved substrate per runbooks. |
| D4 | Cold Root, mainnet, treasury, external audit — not all are “Phase 6 code”; ceremony and ops are explicit bottlenecks in the roadmap. |

For **voice**-specific macro alignment, see Phase **6.5** and [`docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md`](./proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md).
