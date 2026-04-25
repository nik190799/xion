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

## Substrate amendment (Phase 6.1.b, 2026-04-24)

**Why this amendment exists.** Between the original Phase 6.1 substrate decision (2026-04-23, above) and the first agent-driven attempt to land the testnet seal (2026-04-24), the AO ecosystem's legacy testnet messenger unit at `https://mu.ao-testnet.xyz` began returning HTTP 500 on every spawn attempt — reproduced multiple times across two process names, with explicit gateway/CU/MU URL overrides, all returning `{"error":"TypeError: Cannot read properties of null (reading 'toLowerCase')"}` server-side. The same attempt also discovered that `aos` 2.0 silently flipped its default network to AO mainnet, which is forbidden at this phase by `docs/09-GOVERNANCE.md`. Both blockers are tracked together as `KW-AOCORE-004` in `KNOWN_WEAKNESSES.md`. Three closure paths were named there; this amendment records the doctrine change required to execute path #2 (adopt a Xion-local AO substrate) without violating the Phase 6.1 testnet-only rule.

**What is now permissible for the Phase 6.1 seal.** A Phase 6.1 deploy may target either of these substrates:

1. **Upstream legacynet** — the AO-ecosystem-operated testnet (gateway `https://cu.ao-testnet.xyz`, MU `https://mu.ao-testnet.xyz`). Receipt records `substrate: "legacynet"`. This is the original [`docs/runbooks/AO_DEPLOY_WSL2.md`](runbooks/AO_DEPLOY_WSL2.md) path, retained as an option for whenever upstream recovers.
2. **Xion-local AO substrate** — the [`infra/ao-localnet/`](../infra/ao-localnet/) Docker stack, a thin wrapper around the upstream `permaweb/ao-localnet` Docker Compose stack pinned to a known commit SHA. Receipt records `substrate: "localnet"`. Operator path is [`docs/runbooks/AO_DEPLOY_LOCALNET.md`](runbooks/AO_DEPLOY_LOCALNET.md).

Mainnet (`substrate: "mainnet"`) remains forbidden at Phase 6.1 by `docs/09-GOVERNANCE.md` — that requires a Phase 6+ Tier-3 ceremony with cold-root cosigns, on a freshly-generated Cold Root wallet, NOT any operator-side wallet. The verifier `xion-verify ao-handlers` enforces this allowlist at the receipt layer (any receipt declaring `substrate: "mainnet"` returns FAIL at this phase).

**What "the seal is valid" means for the localnet path.** The Phase 6.1 testnet-seal bar — equally for both substrates above — is:

1. The 19-handler doctrine is loaded into the AO process (verifier already checks this against the `docs/schemas/ao-handler-*.yaml` set).
2. One round-trip `commit-state` message is accepted by the deployed Lua, advancing `StateTip` from `height=0` to `height=1` with the empty-bytes root.
3. The orchestrator's `STATE_CHAIN_LEDGER` writer records the seed row.
4. `xion-verify ao-handlers` reads `XION_AO_GATEWAY_URL` (defaulting to `https://cu.ao-testnet.xyz` for legacynet; the operator sets it to `http://localhost:4004` for localnet) and confirms tip parity between the local ledger row and the substrate's CU.
5. The receipt at `genesis/AO_DEPLOY_RECEIPT.json` records `substrate`, `process_id`, `signer_address`, `lua_source_sha256`, `aos_version`, and (for localnet receipts) the upstream pin used to bring the substrate up so a third-party operator can reproduce the bring-up byte-for-byte.

**What this amendment explicitly does NOT promote.** Public-Arweave durability, multi-CU/multi-MU redundancy, mainnet-grade signer custody, and the cross-domain bridging to Base EVM are NOT requirements of the Phase 6.1 seal under either substrate. They are Phase 6+ obligations and remain tracked as separate residuals (`KW-AOCORE-002` for the unbuilt 17 handlers; the mainnet-ceremony obligation is handled in `docs/09-GOVERNANCE.md`).

**Substrate Portability Property restated.** The handler Lua is identical across substrates — the same `ao/core/main.lua` loads on both legacynet and localnet, and would load on mainnet at Phase 6+ with no source change. The substrate field in the receipt records *which* CU was witness to the seal, not what the seal was. This preserves the doctrine's "death of any single algorithm/substrate must not kill Xion" property: if either substrate is unavailable later, the other can witness future seals using the same handler bytes.

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

### Phase 6.9 Bridge Attestor

The attestor is now a modular runtime interface under `orchestrator/bridge`. Genesis uses a multisig attestor for AO event evidence and reserves a `LightClientBridgeAttestor` as `NOT_YET_SEALED` for future trust-minimized verification. EVM-side egress is capped per day in `EmissionController.sol` and `MasterTreasury.sol`; see [`AO-EVM-BRIDGE.md`](./AO-EVM-BRIDGE.md).

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
