# contracts/xion-token/

Solidity contracts for the **XION** fungible currency, deployed on Base at Stage C-2.

This directory contains three contracts:

| Contract | Purpose |
|----------|---------|
| `XionToken.sol` | The ERC-20 contract. Fixed cap 420B. Schedule-enforced minting via authorized minter. Burnable (holder only). |
| `EmissionController.sol` | The schedule enforcer. Holds the only mint authority against `XionToken`. Enforces era boundaries, per-era caps, no-acceleration, no-emergency-mint. |
| `LiquidityLock.sol` | The 10-year liquidity lock for the fair-launch bonding curve pool. |

## Deployment order

1. Deploy `XionToken.sol` with cap and foundation-multisig as initial owner.
2. Deploy `EmissionController.sol`, pointing at the `XionToken` address and the schedule constants.
3. `XionToken.setMinter(emissionController)` — transfer mint authority.
4. `XionToken.renounceOwnership()` — no owner, no admin, only the EmissionController can mint, and it only follows the schedule.
5. Deploy `LiquidityLock.sol` with the Virtuals bonding-curve LP token address and 10-year unlock timestamp.
6. Fund the bonding curve with the 168B fair-launch allocation.
7. Transfer the resulting LP tokens to the `LiquidityLock` contract.

After step 5, the lock is irrevocable.

## Invariant mapping

These contracts implement the following Genesis-Locked Invariants:

- **Invariant 8** (Total supply ≤ 420B forever) — `XionToken.MAX_SUPPLY` constant, `_mint` checks cap.
- **Invariant 9** (Emission schedule not accelerable) — `EmissionController` has no `advance` function; `pause` / `slow` / `retire` only.
- **Invariant 13** (Treasury cannot price-impact) — enforced at the AO Core Treasury-Spend handler level, not in this contract. `XionToken` is indifferent to transfer destination.

The IMPRINT soulbound token (Invariant 10) is in a separate directory: `../imprint/`.

## Verification

- Source code is published and verified on Base block explorer.
- Reproducible-build digest is committed to Arweave; `xion-verify supply` confirms the on-chain contract bytecode matches.
- Deploy script and constructor arguments are published to `CONTRACTS_LEDGER.md` on Arweave.
