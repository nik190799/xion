# AO Core Doctrine (Phase 6.0)

This document is the top-level operational doctrine for Xion's AO Core, the on-chain identity holder and state machine. It pins the handler set, the state schema, the Lua-vs-Solidity boundary, and the deployment runbook before any Lua code is written.

## Substrate choice (Phase 6.1)

**Probe-first record (2026-04-23).** Before the first Lua commit of Phase 6.1, we probed the state of the AO ecosystem to choose the deployment substrate.
- **AO Mainnet (aos):** The `aos` CLI (v2.0.1) and its `Handlers.add` ABI are the most stable, most-documented surface today. Testnet wallet procurement is straightforward. The Lua module shape is well understood.
- **AO-Core / HyperBEAM:** The newest generation, matching the "AO Core" name in our doctrine, but pre-1.0. Tooling and ABIs are shifting. Betting the *first* Lua commit on a shifting target violates the "death of any single algorithm/substrate must not kill Xion" property.

**Decision:** Phase 6.1 deploys against AO Mainnet's `aos` / `Handlers.add` ABI on its testnet.
- **Algorithmic humility:** We use the stable, proven `aos` tooling.
- **Properties over implementations:** The handler logic (precondition checks, height transition, ledger write) ports cleanly to HyperBEAM later under the Substrate Portability Property.
- **Solo-builder pragmatism:** Local `aos` REPL + testnet wallet provides a fast feedback loop (seconds, not minutes).

## Handler Set Enumeration

The AO Core exposes 19 handlers across four families. Each handler's ABI and state effects are pinned in a corresponding schema file under `docs/schemas/ao-handler-*.yaml`.

### Lifecycle (7)
- `commit-state` — record a new state-chain tip from an authorized Relay.
- `attest` — emit an engagement attestation to be bridged to the Base EVM contracts.
- `treasury-spend` — authorize a treasury transaction (governance-gated).
- `registry-update` — update the authorized Relay or inference provider registries.
- `spend` — authorize an outbound wallet transaction within daily caps.
- `slash-imprint` — penalize a bad actor's IMPRINT balance.
- `Anchor-Interaction-Batch` — record a verifiable hourly batch of signed interactions (Phase 6.3).

### Authority Lattice (2)
- `rotate-authority` — rotate keys within a tier.
- `abdicate-tier` — mechanically enforce the abdication schedule (block-height/timestamp gated).

### Provisioning (5)
- `provision-relay` — treasury-funded deploy of a new Relay.
- `provision-inference` — add or rotate inference provider endpoints under caps.
- `provision-storage` — scale Arweave bundle / Turbo allocation.
- `provision-bandwidth` — add CDN/edge capacity.
- `provision-witness` — fund Witness bounties / bond pool per governance.

### Sustainability (6)
- `route-slices` — split incoming payment into the 5-slice composition.
- `improvement-spend` — draw from Improvement Fund on Auto-Research-Loop-approved proposals.
- `reserve-draw` — governance-vote check when below 1mo runway floor.
- `accept-donation` — credit Foundation Reserve; mint IMPRINT proportional to USD-value.
- `enter-hibernation` — toggle Survival Stack; adjust posted price.
- `exit-hibernation` — restore Full Stack.

## The `attest` handler (Phase 6.1)

The `attest` handler records engagement attestations in the AO Core state.

- **Arguments:**
  - `subject_address` (hex40): The user or entity being attested.
  - `event_kind` (enum): The type of engagement. Allowed values: `chat_turn`, `proposal_engagement`, `improvement_contribution`.
  - `event_correlation_id` (hex32): Unique identifier for the event.
  - `event_weight` (uint32): The value/weight of the engagement, bounded by a cap.
  - `event_timestamp` (uint64): Unix timestamp of the event.
- **Preconditions:**
  - Caller must be an authorized hot-tier or warm-tier signer.
  - `event_weight` must not exceed the defined maximum cap.
- **State changes:**
  - Records the attestation in the `attestations` map keyed by `event_correlation_id`.
- **Failure modes:**
  - `non_authorised_caller` → reject
  - `invalid_event_kind` → reject
  - `weight_exceeds_cap` → reject
  - `duplicate_correlation_id` → reject

**What this does NOT do yet:**
This handler currently records to AO state only. It does NOT bridge the attestation to the Base EVM contracts (e.g., `Imprint.attest()`). The cross-domain bridging is explicitly deferred to Phase 6.5.

## State Schema

The AO Process holds the following state:
- **State-tip included:** `state_tip_height`, `state_root_sha256`, `prev_state_root_sha256`.
- **Checkpoint-only:** `authorized_relays`, `budget_envelopes`, `governance_queue`, `revocation_registry`.

## Weekly Arweave Checkpoint

- **Cadence:** Every 7 days (or 10,080 blocks).
- **Multi-gateway requirement:** Checkpoints must be readable via at least three independent Arweave gateways.
- **Re-fetch verification:** `xion-verify state-chain` reads the checkpoint from the gateways and verifies the hash chain.

## Chicken-and-Egg Posture

The *first* Relay is operator-deployed (chicken-and-egg). All subsequent Relays are autonomously provisioned by Xion via the `provision-relay` AO handler when Sensorium reports `survival_pressure` above a governance-tunable threshold.

## Lua-vs-Solidity Boundary

| Handler / Function | Domain | On-Chain Effect |
|-------------------|--------|-----------------|
| `commit-state` | AO (Lua) | Updates state-chain tip |
| `route-slices` | AO (Lua) | Updates internal accounting balances |
| `Imprint.attest()` | Base (EVM) | Mints/updates soulbound IMPRINT tokens |
| `EmissionController.scheduledMint()` | Base (EVM) | Mints XION ERC-20 per schedule |

Cross-domain calls are mediated by the AO-Core attestor (Phase 6.5), never by direct EVM invocation from Lua.

## Phase 6 Dependency Map

Phase 6 is sliced into six sub-phases:
- **6.1 (Skeleton):** `commit-state` + `attest` deployed to AO testnet.
- **6.2 (Substrate):** Akash migration + Cloudflare decommission.
- **6.3 (Provisioning):** Multi-host autonomous provisioning.
- **6.4 (Treasury):** Multi-chain treasury vault deployment.
- **6.5 (Attestor):** AO-Core attestor wiring to Base EVM.
- **6.6 (Drill):** Immortality Drill + substrate-portability dry-run + regulatory ledger schema.

## Operator Runbook

1. Install `ao` CLI.
2. Provision AO testnet wallet.
3. Execute AO Process deployment ceremony (documented in `docs/13-OPERATIONS.md`).
4. Inspect state-tip via `ao` CLI read calls.

## Replacement-Path Doctrine

Handlers are deprecated via a versioned ABI (e.g., `commit-state-v1` → `commit-state-v2`). The deprecation path uses a dual-write window of at least 4 weeks. Cutover requires a governance vote and a clean `xion-verify` run on the new handler's emitted state.
