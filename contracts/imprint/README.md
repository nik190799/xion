# contracts/imprint/

Solidity contracts for **IMPRINT**, Xion's soulbound reputation token.

IMPRINT is **non-transferable in perpetuity** (Genesis-Locked Invariant 10). It is earned through verified engagement events attested by the AO Core and decays if engagement lapses. It is used as a multiplier in the post-C-2 governance weight formula:

```
weight(wallet) = sqrt(XION_time_locked(wallet, T)) × log2(1 + IMPRINT_balance(wallet))
```

See [`docs/09-GOVERNANCE.md`](../../docs/09-GOVERNANCE.md) and [`docs/16-CURRENCY.md`](../../docs/16-CURRENCY.md) for the full role.

## Contracts

| Contract | Purpose |
|----------|---------|
| `Imprint.sol` | The soulbound reputation contract. ERC-5192-spirit (non-transferable); balance-based (not tokenId-based) for gas efficiency and fungibility-of-reputation; implements the decay function and the Core-attested mint path. |

## Why not vanilla ERC-5192 NFTs?

ERC-5192 was designed for soulbound *NFTs* with a `locked(uint256 tokenId)` signal per token. Xion's reputation is **quantitative and fungible** (a wallet has "42 IMPRINT", not "5 specific soulbound achievements"). Enforcing non-transferability on a balance is equivalent to enforcing it per-tokenId and cheaper in gas. We implement the *spirit* of ERC-5192 — non-transferability enforced at the protocol level, legibly signaled, with no escape hatches — without inheriting its NFT-shaped overhead.

If a future Ecosystem participant wants IMPRINT-as-NFT badges (e.g., "Completed 100 relationship threads"), those can live as a separate, complementary ERC-5192 contract. The base IMPRINT reputation stays balance-based.

## Invariant mapping

- **Invariant 10** (IMPRINT soulbound in perpetuity) — `Imprint.sol` has no `transfer`, `transferFrom`, `approve`, `permit`, or `delegate` functions. The non-transferability is by *omission*, not by boolean flag that could be flipped.
- **Invariant 11** (No currency gating of rights) — enforced at the orchestrator / AO Core level, not in this contract. The contract itself is indifferent to which rights the balance is used for.

## Earning path

IMPRINT is minted only by the registered **EngagementAttestor** address, which is the AO Core's relay-auth key. The AO Core attests an engagement event (e.g., a user completed a sustained relationship thread, an accepted contribution was ratified, a correct Witness report was adjudicated) and the Attestor mints the corresponding IMPRINT amount. There is no user-initiated mint. There is no purchase path. There is no admin override.

The earning rules and amounts live in the AO Core's `engagement_policy_vN` sub-process, not in this contract. The contract enforces *non-transferability and decay*; the Core enforces *what earns how much*.

## Decay

IMPRINT decays at a slow rate (~2% per 30 days) if the wallet has no IMPRINT-earning activity in the period. This rewards sustained presence over one-time accumulation. Decay is computed lazily at read-time (no gas burn for inactive wallets). A wallet that resumes activity after a long absence still has a baseline decayed amount; it does not go to zero unless many months pass.

## Anti-farm features

- Rate limits per wallet per Attestor call (enforced off-chain by the Core, signaled on-chain via the `mintReason` tag).
- Forfeit path: the Attestor can `slash(wallet, amount, reason)` if the Core's anomaly detector confirms Sybil behavior. Slashed IMPRINT is permanently burned; it does not redistribute.
- No batch-transfer, no merge, no split, no delegation. Every wallet's IMPRINT is that wallet's own.
