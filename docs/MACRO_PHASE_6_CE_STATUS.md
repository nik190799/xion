# Macro Phase 6 — Epic C and Epic E closure status

This note **does not mint constitutional truth**; it links repo evidence for **`DEVELOPMENT_ROADMAP.md`** “next engineering focus” items: **Macro Phase 6 Epic C (multi-chain treasury)** and **Macro Phase 6 Epic E (regulatory / governance ledger)**.

## Epic C — Treasury (multi-chain posture)

**Code anchors**

- Solidity: [`contracts/treasury/MasterTreasury.sol`](../contracts/treasury/MasterTreasury.sol), [`contracts/treasury/Vault.sol`](../contracts/treasury/Vault.sol), deploy script [`contracts/treasury/script/Deploy.s.sol`](../contracts/treasury/script/Deploy.s.sol).
- Manifest pins: [`genesis/TREASURY_VAULTS.json`](../genesis/TREASURY_VAULTS.json).
- Operator automation: [`xion_ops/services/base_evm.py`](../xion_ops/services/base_evm.py) (`deploy-treasury`, `pin-deployment`, `rotation-rehearsal`).
- Verifiers: `xion-verify treasury`, `xion-verify treasury-flow` (manifest must be populated for `treasury-flow`).

**Operational next steps**

1. Keep Sepolia bytecode aligned with pinned source (**soak → pin → verifier**) using [`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`](runbooks/TREASURY_SEPOLIA_DEPLOY.md).
2. Maintain honest audit posture: **`KW-AUDIT-001`** (external audit or explicit Sprint residue) and **`KW-AUDIT-002`** correction pairing on Arweave / manifest (`treasury_audit_correction_arweave_tx`).
3. Base mainnet only after **Forge CI green** (`.github/workflows/foundry.yml`) and verifier bundle in `scripts/verify-mainnet-deploy-gates.sh`.

## Epic E — Governance / regulatory intake

**Code anchors**

- Ledger writer: [`orchestrator/governance/ledger.py`](../orchestrator/governance/ledger.py).
- HTTP intake: [`docs/runbooks/STATE_ACTOR_INTAKE.md`](runbooks/STATE_ACTOR_INTAKE.md) and orchestrator `/governance/state-actor`.
- Safety join: `xion-verify regulatory-ledger --check-safety-link`.

**Residuals**

Operational evidence (witness memos, rate limits, AO mirror) stays tracked via **`KNOWN_WEAKNESSES.md`** until Tier-3 ceremony items close.
