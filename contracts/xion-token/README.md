# contracts/xion-token/

Solidity contracts for the **XION** fungible currency, deployed on Base at Stage C-2.

This directory contains three contracts:

| Contract | Purpose |
|----------|---------|
| `XionToken.sol` | The ERC-20 contract. Fixed cap 420B. Schedule-enforced minting via authorized minter. Burnable (holder only). |
| `EmissionController.sol` | The schedule enforcer. Holds the only mint authority against `XionToken`. Enforces era boundaries, per-era caps, no-acceleration, no-emergency-mint. Rotation-lattice gated (KW-CONTRACTS-001). |
| `LiquidityLock.sol` | The 10-year liquidity lock for the fair-launch bonding curve pool. |

Forward-looking notes that are not part of the contract surface live in [`LIQUIDITY_LOCK_NOTES.md`](./LIQUIDITY_LOCK_NOTES.md).

## Deployment order

The `contracts/script/Deploy.s.sol` script automates steps 1, 2, 5, and the
constitutional GENESIS_SPLIT post-deploy verification. Steps 3, 4, 6, 7 are
ceremony transactions and are deliberately NOT in the script — they require
the foundation multisig and are run manually after visual verification of the
deployed addresses.

1. **Deploy `XionToken.sol`** with the foundation multisig as initial owner.
2. **Deploy `EmissionController.sol`**, pointing at the `XionToken` address and passing the AO-Core operational authority and the governance address.
3. **`XionToken.setMinter(emissionController)`** — transfer mint authority. Run from the foundation multisig.
4. **`XionToken.renounceOwnership()`** — no owner, no admin, only the EmissionController can mint, and only on-schedule.
5. **Deploy `LiquidityLock.sol`** with the DEX pair's LP-token address and the 10-year unlock timestamp.
6. **Emit genesis** via `EmissionController.emitGenesis(recipients)`. Only the fair-launch slot is non-zero; the on-chain `GENESIS_SPLIT(i)` constants are pinned to docs/16-CURRENCY.md (KW-CONTRACTS-002).
7. **Seed the bonding curve** with the 84B fair-launch allocation and transfer the resulting LP tokens to `LiquidityLock`.
8. **Emit genesis for IMPRINT** is not required — IMPRINT starts at 0 balance for all wallets and only grows via attested engagement.

After step 4, `XionToken` has no owner. After step 7, the LP tokens are irrevocably locked for 10 years.

## Running the deploy script

`contracts/script/Deploy.s.sol` wires `XionToken`, `EmissionController`, `Imprint`, and `LiquidityLock` in a single Forge script. It does NOT call `setMinter`, `renounceOwnership`, or `emitGenesis` — those require the foundation multisig and ceremony gating.

### Required environment variables

| Variable | Meaning |
|----------|---------|
| `PRIVATE_KEY` | Hex private key for the deployer EOA. For testnets only; on mainnet use a hardware-wallet-backed signer flow (`--ledger` / `--trezor`). |
| `FOUNDATION_MULTISIG` | Address that will own `XionToken` until ownership is renounced at step 4. MUST be a multisig on mainnet. |
| `AO_CORE_AUTHORITY` | Operational authority for `EmissionController.scheduledMint` / `emitGenesis` and for `Imprint.attest` / `slash`. Rotatable on a 7-day timelock by governance. |
| `GOVERNANCE` | Constitutional authority. Can rotate `AO_CORE_AUTHORITY` (7 d) and itself (30 d), call `slowEra` / `pauseMinting` / `retirePool`. MUST be the Cold-Root multisig on mainnet. |
| `LP_TOKEN` | Address of the DEX LP token that will be locked. On testnet, this can be a placeholder; the lock contract only calls `transfer` and `balanceOf`. |
| `LP_BENEFICIARY` | Address that can call `withdraw()` after `UNLOCK_TIMESTAMP`. Must be non-zero; should be a durable multisig that can rotate its own signers without changing its address. |
| `UNLOCK_TIMESTAMP` | Unix seconds (integer). Must be in the future at deploy time. Production value is 10 years after genesis. |

### Invocation — Base Sepolia smoke deploy

```powershell
$env:PRIVATE_KEY          = "0x..."
$env:FOUNDATION_MULTISIG  = "0x..."
$env:AO_CORE_AUTHORITY    = "0x..."
$env:GOVERNANCE           = "0x..."
$env:LP_TOKEN             = "0x..."
$env:LP_BENEFICIARY       = "0x..."
$env:UNLOCK_TIMESTAMP     = "1920000000"  # 2030-ish; pick a future timestamp
$env:RPC_URL              = "https://sepolia.base.org"

forge script script/Deploy.s.sol:Deploy `
  --rpc-url $env:RPC_URL `
  --broadcast `
  --verify `
  --etherscan-api-key $env:ETHERSCAN_KEY
```

The script prints four deployed addresses at the end. Record them — together with the governance / authority values and the `UNLOCK_TIMESTAMP` — in `CHANGELOG.md` under a new "Testnet deployment" heading, with the network name and block number.

### What the script does NOT do (by design)

- **Does not** call `setMinter` — this is a foundation-multisig action (step 3 above). To unblock a single-key testnet smoke test, uncomment the `if (vm.addr(pk) == foundationMultisig) xion.setMinter(...)` block in `Deploy.s.sol`. Do not deploy this modified script to mainnet.
- **Does not** call `renounceOwnership` — same reasoning.
- **Does not** call `emitGenesis` — this is a ceremony transaction run only after the C-2 activation gates have passed and the deployed addresses have been publicly reviewed.
- **Does not** set up the rotation lattice's pending states — rotation proposals are submitted from the `governance` multisig after deployment.

### Constitutional verification baked into the script

At the end of deployment, the script queries the on-chain `EmissionController.GENESIS_SPLIT(i)` for `i = 0..6` and fails hard unless:
- the sum equals `GENESIS_ALLOC` (84,000,000,000 XION),
- index 0 (FAIR_LAUNCH) equals `GENESIS_ALLOC`,
- indices 1..6 are all zero.

This matches the split committed in [`docs/16-CURRENCY.md`](../../docs/16-CURRENCY.md) "Genesis emission split" subsection and mirrored in [`docs/schemas/genesis-split.yaml`](../../docs/schemas/genesis-split.yaml), whose `source_sha256` must match the doctrine file byte-for-byte. `xion-verify schemas` enforces that match pre-deploy; the script enforces the on-chain-vs-doctrine match post-deploy.

If any of these checks fail, the deployment transaction does NOT revert (the contracts are already deployed by then), but the script exits with a non-zero status and a legible error. You must re-deploy a new `EmissionController` — the failing one is constitutionally unusable.

## Invariant mapping

These contracts implement the following Genesis-Locked Invariants:

- **Invariant 8** (Total supply ≤ 420B forever) — `XionToken.MAX_SUPPLY` constant, `mint` checks `totalMinted + amount <= MAX_SUPPLY`.
- **Invariant 9** (Emission schedule not accelerable) — `EmissionController` has no `advance` function; `slowEra` cannot raise a slowdown, `pauseMinting` / `retirePool` only reduce.
- **Invariant 13** (Treasury cannot price-impact) — enforced at the AO Core Treasury-Spend handler level, not in this contract. `XionToken` is indifferent to transfer destination.

The IMPRINT soulbound token (Invariant 10) is in a separate directory: `../imprint/`.

## Test suite

- `forge test` runs the full suite (112+ tests, all green at Phase 3 seal).
- `forge coverage` reports ≥95% line and ≥90% branch coverage — the roadmap-specified mainnet prerequisite.
- Each rotation / era / cap / CEI / overflow behavior named in `KNOWN_WEAKNESSES.md` under `KW-CONTRACTS-001..007` has an explicit named test.

## Verification

- Source code is published and verified on the Base block explorer.
- Reproducible-build digest is committed to Arweave; `xion-verify supply` (promoted from NOT_YET_SEALED after mainnet deploy) confirms the on-chain contract bytecode matches.
- Deploy script and constructor arguments are published to `CONTRACTS_LEDGER.md` on Arweave.
- `xion-verify schemas` runs in CI on every commit and guarantees `docs/schemas/genesis-split.yaml` and the other canonical schemas stay byte-exact-pinned to their doctrine files.
