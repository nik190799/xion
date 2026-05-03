# Treasury — Base Sepolia deploy, pin, soak, verify

This runbook restores the **Sepolia treasury path** blocked when no deploy signer is present in `.env`. It aligns with Sprint Mode mitigation “24–48h Base Sepolia soak before mainnet” (`DEVELOPMENT_ROADMAP.md`) and with `KW-AUDIT-001` / `KW-AUDIT-002` honesty around audit records.

## Prerequisites

1. **Foundry** (`forge`, `cast`) on `PATH`. On Windows, `xion-ops` falls back to WSL if forge is missing on the native shell; install via [Foundry Book](https://book.getfoundry.sh/getting-started/installation).
2. **Funded Sepolia/Base deployer EOA** (small ETH on Base Sepolia for gas).
3. **Secrets only in `.env`** (never commit). Repo root `.env` is gitignored.

## Required environment variables

| Variable | Purpose |
|----------|---------|
| `PRIVATE_KEY` or `XION_DEPLOYER_PRIVATE_KEY` | Deployer hex key (omit `0x` or include it — match your Foundry habit). Not for mainnet genesis; use hardware flow on mainnet. |
| `BASE_SEPOLIA_RPC` or `XION_BASE_SEPOLIA_RPC` | Optional; defaults to public Base Sepolia RPCs if unset. |

Treasury constructor env (wired into Forge script):

| Variable | Purpose |
|----------|---------|
| `XION_TREASURY_GOVERNANCE` | `governance` address on `MasterTreasury`. |
| `XION_AO_CORE_AUTHORITY` | AO-aligned operational authority slot. Testnet rehearsal often uses distinct addresses later; documenting chosen addresses is mandatory. |
| `XION_BRIDGE_CAP_BPS` | e.g. `1000` for 10 %. |

Bootstrap non-secret template into `.env` (overwrites blanks for these three keys):

```bash
python -m xion_ops.cli base-evm prepare-sepolia-env
```

Then add `PRIVATE_KEY` or `XION_DEPLOYER_PRIVATE_KEY` manually.

Install Solidity deps once ( **`contracts/lib/`** is gitignored — CI reinstalls each run):

```bash
cd contracts
forge install OpenZeppelin/openzeppelin-contracts@v5.5.0 --no-commit
forge install foundry-rs/forge-std@v1.9.7 --no-commit
```

## Deploy MasterTreasury to Base Sepolia

Default network is **`base-sepolia`** (CLI prevents accidental `--network base` without an explicit flip).

```bash
python -m xion_ops.cli base-evm deploy-treasury --network base-sepolia
```

Inspect JSON: `ok` must be **`true`** and `master_treasury` populated from `broadcast/.../84532/run-latest.json`.

### Pin genesis manifest

Replace placeholders with broadcast output fields:

```bash
python -m xion_ops.cli base-evm pin-deployment \
  --address <MasterTreasury> \
  --tx <deploy_tx_hash> \
  --block <block_number>
```

`genesis/TREASURY_VAULTS.json` is updated via `pin_treasury_deployment` (addresses + residual text normalization).

Optional **rotation rehearsal** (sends governance-gated txs; consumes gas):

```bash
python -m xion_ops.cli base-evm rotation-rehearsal \
  --network base-sepolia \
  --master-treasury <MasterTreasury>
```

## Soak window

After pin: run Relay / operator traffic if applicable, monitor `cast call` probes for selectors that must exist on **`MasterTreasury`** for the pinned source revision (examples: `governance()`, `aoCoreAuthority()`, `registeredChainCount()`). Minimum **24–48 hours** soak before Sprint Mode-style mainnet is doctrine-honest.

## Verifiers

From repo root (install `pip install -e xion-verify[dev]` and orchestrator extras as in CI):

```bash
xion-verify treasury
xion-verify treasury-flow   # requires testnet posture in manifest
xion-verify supply          # compares on-chain bytecode/manifest pins (needs RPC/env perVerifier)
```

Discovery / substrate portability for D3 honesty:

```bash
xion-verify discovery
xion-verify substrate-portability
```

Composite pre-genesis drill:

```bash
xion-verify pre-genesis --allow-not-yet-sealed   # CI convenience only; tighten before ceremony
bash scripts/verify-mainnet-deploy-gates.sh       # scripted bundle (loads `.env` if present via shell export step)
```

## Audit record honesty

Any citation of treasury audit artifacts must pair **original Arweave tx** with **correction tx** (`treasury_audit_correction_arweave_tx`) per `docs/audits/treasury-2026-report.CORRECTION.md`. `xion-verify treasury` enforces the pair when `treasury_audit_arweave_tx` is set.
