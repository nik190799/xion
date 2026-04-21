# LiquidityLock — design notes and forward-looking considerations

> This file holds *non-load-bearing* notes about `LiquidityLock.sol`. Nothing
> in this document is a promise. The only promises Xion makes about locked
> liquidity are the four properties enumerated in the contract header
> (no owner, no admin, immutable unlock timestamp, single `withdraw` exit
> path). Everything below is material for future decisions, not commitments.

## Why the contract is deliberately small

`LiquidityLock.sol` was the target of an earlier audit finding
(`KW-CONTRACTS-006`) that named an inline comment about a "future fee-claim"
path as a footgun. The comment suggested a feature the contract did not and
does not implement. Removing the comment was the right fix; re-stating the
same speculation here — explicitly outside the source — keeps the reasoning
available without letting a reader infer a promise from the Solidity surface.

The contract's audit footprint is small on purpose. Any feature added to it
is a new attack surface on an asset class (Uniswap-v2-style LP tokens held
for 10 years) that has historically been the target of rug-pull variants.
The minimum mechanism that prevents rug-pull is: no owner + immutable
beneficiary + immutable unlock timestamp + single `withdraw`. That is what
the contract does.

## LP fee accrual during the lock period

Uniswap-v2-shape LP positions accrue swap fees inside the LP-token itself:
the redeemable share of the pool grows without further user action. In the
current contract, those accrued fees:

- Remain inside the pool (represented by the LP tokens held by this contract)
  until `unlockTimestamp`.
- Are claimed, in full, by `beneficiary` in a single `withdraw` at unlock.

The treasury does not have a mid-lock fee-harvest path. This is a conscious
trade: mid-lock fee harvesting would require either

1. A fee-claim function on `LiquidityLock` that calls `UniswapV2Router.burn()`
   or similar on a *fraction* of the LP tokens — but "fraction" is not a
   primitive of v2 LP tokens; you can only fully-redeem a subset, which
   changes the pool ratio, which is exactly the kind of treasury-side market
   action that `docs/19-TREASURY.md` caps forbid.
2. A side-pipe via a periphery contract that the LP tokens delegate fee
   redirection to — a meaningful extension to the LP token contract itself,
   which is not in Xion's control.

Neither path is safe enough to include in the lock contract. If governance
later decides the 10-year lock period generates enough accrued value to
justify the complexity, the path is: deploy a new `LiquidityLock` variant
as a separate contract, give it a different set of properties, and state
those properties explicitly. The *current* contract's promise stays exactly
what it is.

## 10-year horizon considerations

A 10-year lock is a long commitment against the velocity of DEX
infrastructure. In that window:

- The paired USDC may be migrated to a successor stablecoin. If USDC ceases
  to exist, the LP position becomes a claim on whatever USDC was migrated
  into; the beneficiary receives whatever the AMM resolves it to.
- The AMM itself may be deprecated. Uniswap v2 pools persist as-deployed,
  but router / UI infrastructure can disappear. The LP tokens still contain
  the underlying; withdrawing requires direct pair-contract interaction,
  which is documented in the standard v2 interface.
- The beneficiary address may need to be rotated. This contract does not
  support rotation by design — see `KW-CONTRACTS-001` for why immutable
  authority addresses are the *wrong* pattern in general, but see the
  reasoning above for why this specific contract keeps them immutable.
  Practically: the `beneficiary` should be a durable multisig or the AO
  Core treasury address, which can itself rotate signers without changing
  the on-chain address.

## What would change the above

If a future Phase 6 AO Core deployment wants programmatic treasury
management of the locked LP position, the minimum viable mechanism is:

1. A new `LiquidityLockV2` contract with a clearly-scoped
   `claimAccruedFees(uint256 maxLpToBurn)` that only redeems a small
   governance-capped fraction per quarter, with a per-call and per-year
   ceiling.
2. Hard-coded reverts if the redemption would move the pool price by more
   than a configured basis-point cap.
3. `xion-verify liquidity-lock` would grow a new check for these caps.

This is the explicit forward path; it is not a commitment to take it.

## How this file is curated

Whenever `contracts/xion-token/LiquidityLock.sol` changes, this file should
be re-read to confirm the two stay honest about what is and is not in
scope. If this file starts describing features the contract has, it is
wrong; fix the file, not the contract.
