# Non-EVM rail Vaults — design memo for AR and TAO

**Status:** design only. No code lands from this file. Operator reviews open questions before any implementation begins.

**Why this exists:** The 2026-05-12 vault asset tagging armed ETH + USDC withdrawals from the Base mainnet [`Vault`](../../contracts/treasury/Vault.sol) at `0x64712dFD…2bdC`. AR (Arweave) and TAO (Bittensor) are listed in [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json) `tier1_operating_tokens` as `mainnet_routed_pending_per_chain_vault`. They cannot be tagged on the Base Vault — they're not EVM tokens. They need their own custody rail.

This memo proposes what those rails should look like, names what's deferred, and lists the open decisions the operator owns.

## Recap: what the Base Vault gives us

From [`contracts/treasury/Vault.sol`](../../contracts/treasury/Vault.sol) (60 lines, audit-pending):

- `aoCoreAuthority` — single immutable address that can act on the Vault.
- `tagAsset(address, bool nativeAsset)` — operator declares an asset known + native-or-bridged. `onlyAuthority`.
- `withdraw(address asset, address payable to, uint256 amount)` — withdraws to `to`. `onlyAuthority`. Reverts if asset is not tagged.
- `balanceOf(address asset)` — pure view, no auth.
- `receive() external payable {}` — anyone can deposit ETH; ERC-20 deposits use the token's own `transfer`.

From [`contracts/treasury/MasterTreasury.sol`](../../contracts/treasury/MasterTreasury.sol):

- `vaultForChain[chainId]` mapping with `deployVault(chainId, vaultAuthority)` and `registerVault(chainId, vault)`.
- `bridgeExposureCapBps`, `DAILY_BRIDGE_EGRESS_CAP`, `requestReplenish` — bridge-discipline accounting.
- 7-day `AUTHORITY_ROTATION_DELAY` for rotating the authority on file.
- Both register methods are `onlyGovernance` (Warm Safe on mainnet, EOA on Sepolia).

The Base Vault is **operationally**: a single-tenant treasury contract whose authority is a multisig (Warm Safe 2-of-3) that whitelists assets and signs withdrawals.

The non-EVM analog has to reproduce three properties, ideally without contract changes during the audit-deferred window:

1. **Threshold custody** — no single key can withdraw.
2. **Asset whitelist** — only declared rails/assets are spendable.
3. **Verifiable manifest** — `xion-verify treasury` can confirm shape from outside.

## AR rail (Arweave)

### Current state

- AR is held in a single hot Arweave JWK referenced via `XION_REGISTRY_WALLET_JWK_PATH` (see [`xion_ops/services/arweave.py:60`](../../xion_ops/services/arweave.py)).
- Balance: ~17.189 AR (per `docs/STATE_OF_XION_PREFLIGHT.md` 2026-05-03 funding snapshot).
- Use: signs Arweave transactions to publish the relay registry, treasury audit report, ledger anchors, and genesis bundle (`publish_relay_registry`, `publish_treasury_audit_arweave.py`, etc.).
- [`genesis/CREDENTIALS.md`](../../genesis/CREDENTIALS.md) line 35 lists "scoped Arweave wallet" as one of the encrypted credential vault entries under a 2-of-3 threshold scheme. **But:** [`KW-VAULT-001`](../../KNOWN_WEAKNESSES.md) marks the orchestrator vault unlock as `mitigated-residual` — runtime still reads the JWK from env at boot.

### Sprint-Mode target (no AO mainnet seal yet, no contract change)

Arweave is a permanent-storage chain, not a smart-contract chain. The only on-chain "vault" abstraction is via AO processes (Lua handlers on Arweave-anchored state). AO mainnet seal is deferred per `docs/D4_PREFLIGHT.md`, so any AO-process Vault we build today runs against legacynet — not Genesis-aligned, can't claim mainnet custody.

The honest Sprint shape:

- **Custody:** Keep a single Arweave JWK as the operational signer (publishing must work today). Move it under a real threshold-unlock per `KW-VAULT-001` — that's already the named pay-down. The "Arweave Vault" is the JWK + the threshold-unlock policy, not an on-chain construct.
- **Asset whitelist:** Trivial — AR is the only asset on the rail. No tag step needed beyond a manifest declaration.
- **Verifiable manifest:** A new `non_evm_vaults` block in `TREASURY_VAULTS.json` pins the AR wallet address. `xion-verify treasury` queries the Arweave gateway for the live balance and confirms it matches the declared shape.
- **Withdraw discipline:** Operator policy, not contract-enforced. A new runbook `docs/runbooks/AR_VAULT_WITHDRAW.md` documents the threshold cosig flow for transferring AR out of the operational wallet (e.g., refunding the operator, rotating to a fresh wallet). Each withdraw appends an evidence row to `STATE_OF_XION_PREFLIGHT`.

### Post-AO-seal target (Full D4)

When AO mainnet seal lands, the AR Vault becomes an AO process holding an Arweave wallet share, with handlers for `deposit`, `withdraw`, `rotateAuthority`, and a Base-side attestor that asserts the AO process is the canonical custodian. Out of scope for Sprint.

## TAO rail (Bittensor)

### Current state

- TAO is needed to replenish Chutes inference credits — per `docs/26-INFERENCE-POLICY.md:83`, Chutes accounts expose a Bittensor SS58 `payment_address`; treasury TAO is the load-bearing asset for refilling.
- [`genesis/CREDENTIALS.md`](../../genesis/CREDENTIALS.md) line 35 lists "TAO top-up signer metadata" as a vault entry. No specific custody address yet pinned in repo.
- Current balance: unknown / not yet funded (TAO is referenced as a needed asset but the wallet is not in `xion_ops balances` per the 2026-05-03 snapshot).
- "At S1 this requires operator multisig co-sign; S3+ auto-top-up inside a cap is named but not enabled" — the doctrine already names a multisig as the S1 target.

### Sprint-Mode target

Bittensor is Substrate-based. Substrate runtimes have native multisig via `pallet-multisig` (Polkadot's `as_multi` flow), so we get threshold custody **without writing a contract**. This is the cleanest non-EVM analog to the Base Warm Safe.

- **Custody:** A 2-of-3 Bittensor multisig SS58. Three coldkeys held by the operator (mirroring the Base Safe owner set: one MetaMask-equivalent — likely Polkadot.js or Subkey — and two paper backups). The multisig SS58 is computed deterministically from the three signatory addresses + the threshold value (`subkey inspect` or `pallet-multisig` derivation).
- **Asset whitelist:** Trivial — TAO is the only Tier-1 asset on the rail.
- **Verifiable manifest:** Same `non_evm_vaults` block declares the Bittensor multisig SS58. `xion-verify treasury` queries a Bittensor RPC endpoint (`wss://entrypoint-finney.opentensor.ai:443` or equivalent) for the multisig balance.
- **Top-up flow:** TAO transfer from multisig SS58 to Chutes `payment_address` requires 2-of-3 cosig via `as_multi`. The first cosigner initiates, the second cosigner approves, the call dispatches. Each top-up appends an evidence row to `STATE_OF_XION_PREFLIGHT` with the Bittensor block + extrinsic hash.

### Subtleties specific to Bittensor

- **Coldkey vs hotkey.** In Bittensor, "coldkey" holds funds; "hotkey" is for validator/miner operations. We only care about coldkeys for treasury — Xion is not running a Bittensor validator. The 2-of-3 should be coldkeys.
- **Subnet 64 staking is not part of this Vault.** SN64 staking would use a separate hotkey delegation; if/when Xion decides to stake into SN64 (out of scope), the staked TAO is custodied differently. The Vault holds liquid TAO only.
- **Tao denomination.** TAO has 9 decimals (rao = 10⁻⁹ TAO). Manifest target should pin both representations to avoid the kind of decimals error that bit Base early-on.

## Cross-rail manifest schema

Proposed addition to `genesis/TREASURY_VAULTS.json` (additive, non-breaking — the existing `vaults` array stays as-is for EVM rails):

```json
{
  "non_evm_vaults": [
    {
      "rail": "arweave",
      "custody_model": "threshold_unlocked_jwk",
      "address": "<Arweave address derived from JWK>",
      "asset": "AR",
      "decimals": 12,
      "gateway": "https://arweave.net",
      "verifier_balance_query": "/wallet/{address}/balance",
      "evidence": "docs/runbooks/AR_VAULT_WITHDRAW.md; xion_ops/services/arweave.py:balance_ar"
    },
    {
      "rail": "bittensor",
      "custody_model": "pallet_multisig_2_of_3_coldkeys",
      "address": "<Bittensor multisig SS58>",
      "signatories": [
        "<coldkey A SS58>",
        "<coldkey B SS58>",
        "<coldkey C SS58>"
      ],
      "threshold": 2,
      "asset": "TAO",
      "decimals": 9,
      "rpc": "wss://entrypoint-finney.opentensor.ai:443",
      "evidence": "docs/runbooks/TAO_VAULT_TOPUP.md"
    }
  ]
}
```

This is **manifest-only authority** — no `MasterTreasury` change is required. `xion-verify treasury` gets a `non_evm_vaults` branch that:

1. For each entry, validates the schema shape.
2. Queries the declared `gateway`/`rpc` for the address balance.
3. For `bittensor`, additionally validates that the published multisig SS58 derives correctly from the listed signatories + threshold (deterministic check, no RPC required).

## Why not register non-EVM Vaults in the Base `MasterTreasury` (yet)

That route requires adding a method like `registerNonEvmVault(bytes32 chainHash, string memory chainName, bytes memory attestation)` to the contract — i.e., a deploy of new bytecode. That:

- Invalidates today's mainnet `MasterTreasury` (`0xbf54…fd7f`, block 45530934).
- Requires audit re-pass; `KW-AUDIT-001` is `mitigated-residual` until **2026-08-08** budget re-review.
- Would extend the Warm Safe nonce window during a redeploy ceremony, which is operator-time expensive.

For Sprint Mode, **manifest authority** + `xion-verify treasury` enforcement is honest custody discipline without touching contracts. After the 2026-08-08 audit decision and any contract revision, a cross-rail registry on Base mainnet can be added if it pays for itself.

## Runbook outlines (drafts only — to be written when operator greenlights)

### `docs/runbooks/AR_VAULT_DEPLOY.md` (sketch)

1. Generate fresh Arweave JWK on hardware-isolated workstation (not on cloud).
2. Encrypt under 2-of-3 threshold per `genesis/CREDENTIALS.md` shard layout.
3. Single AR transfer from old wallet to new wallet (sign with current operational JWK).
4. Update `TREASURY_VAULTS.non_evm_vaults[].arweave.address` to new wallet.
5. Run `xion-verify treasury` — confirm the new wallet shows expected balance.
6. Append evidence row to `STATE_OF_XION_PREFLIGHT`.

### `docs/runbooks/TAO_VAULT_DEPLOY.md` (sketch)

1. Generate 3 Bittensor coldkeys on hardware-isolated workstation (`btcli wallet new_coldkey` or Subkey). Store mnemonics analogous to Base Safe paper backups.
2. Compute multisig SS58: `subkey inspect <derivation>` with the three SS58s + threshold = 2.
3. Fund the multisig by transferring TAO from the operator coldkey via Polkadot.js Apps or `btcli`.
4. Register multisig SS58 in `TREASURY_VAULTS.non_evm_vaults[].bittensor`.
5. Run `xion-verify treasury` — confirm multisig SS58 derives correctly and shows expected balance.
6. Append evidence row to `STATE_OF_XION_PREFLIGHT`.

### `docs/runbooks/TAO_VAULT_TOPUP.md` (sketch)

1. Operator A initiates `as_multi(threshold=2, other_signatories=[B, C], maybe_timepoint=None, call=balances.transfer(chutes_payment_address, amount))`.
2. Operator A waits for inclusion, records the `timepoint` (block + extrinsic index).
3. Operator B calls `as_multi(threshold=2, other_signatories=[A, C], maybe_timepoint=Some(timepoint), call=…)` — dispatches the transfer.
4. Record block, extrinsic hash, new Chutes balance in `STATE_OF_XION_PREFLIGHT`.

## Open questions the operator owns

These are real forks — each changes the design:

1. **AR custody target:** Stay at single hot JWK + threshold-unlock (Sprint, lowest risk), or build the AO process Vault now against legacynet (more constitutional but Genesis-misaligned)? *Recommended: Sprint shape now, AO process post-AO-seal.*

2. **TAO multisig timing:** Build the 2-of-3 Bittensor multisig **before** the Base Safe hardware-wallet swap (KW-KEYS-002, deadline 2026-05-31) or **after**? Building before means the new HW wallet won't be in the Bittensor signer set; building after delays TAO custody by weeks. *Recommended: after — the hardware-wallet generation discipline is identical and parallel work risks key-management mistakes.*

3. **Manifest-only vs contract-registered:** Confirm the design uses manifest-only authority for non-EVM rails (Option B) and defers a `MasterTreasury.registerNonEvmVault` method until post-2026-08-08 audit decision. *Recommended: confirm Option B.*

4. **Verifier scope:** Should `xion-verify treasury` block on live RPC liveness for Bittensor (could fail in transient network conditions and make `xion-verify all` flaky), or should it stay manifest-shape-only with a separate `xion-verify treasury --check-non-evm-liveness` flag? *Recommended: manifest-only by default, opt-in liveness via flag — same pattern as `discovery --no-cloudflare`.*

5. **TAO funding source:** TAO isn't currently in any Xion wallet. Where does the initial TAO balance come from — operator personal funds (would violate Self-Provisioning doctrine), bridged USDC → TAO via a CEX (introduces a centralized step), or wait for Chutes-side revenue (passive)? This is a strategy question, not a design one, but the rail can't function without funding.

## What this memo does NOT do

- It does not write contract code. No `.sol` files touched.
- It does not edit `TREASURY_VAULTS.json`. The schema is proposed; landing it requires operator review.
- It does not commit to the AR custody being a JWK forever — only that it stays a JWK through Sprint Mode.
- It does not address staking, validator operations, or AO process Vaults. Those are out-of-scope.
- It does not close `KW-VAULT-001` (orchestrator credential vault stub) — that work runs in parallel and is the more general pay-down.

## Verification (when this lands)

If/when the operator approves the design and the work is implemented:

- `xion-verify treasury` with the new `non_evm_vaults` branch returns `OK` for both AR and TAO rails.
- `xion-verify treasury-flow` returns `OK`.
- A dry-run AR transfer (small amount, self-to-self) confirms the threshold-unlock flow.
- A dry-run TAO transfer on a Bittensor testnet (if available) or a small mainnet self-to-self confirms the `as_multi` flow.
- New rows in `STATE_OF_XION_PREFLIGHT` for each deploy.

## Cross-references

- [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json) — manifest target
- [`contracts/treasury/Vault.sol`](../../contracts/treasury/Vault.sol), [`contracts/treasury/MasterTreasury.sol`](../../contracts/treasury/MasterTreasury.sol) — EVM analog
- [`genesis/CREDENTIALS.md`](../../genesis/CREDENTIALS.md) — credential-vault threshold model
- [`docs/26-INFERENCE-POLICY.md`](../26-INFERENCE-POLICY.md) — TAO + Chutes payment flow
- [`xion_ops/services/arweave.py`](../../xion_ops/services/arweave.py) — current AR signer
- [`docs/runbooks/MAINNET_VAULT_ASSET_TAG.md`](../runbooks/MAINNET_VAULT_ASSET_TAG.md) — Base ceremony to mirror
- [`KNOWN_WEAKNESSES.md`](../../KNOWN_WEAKNESSES.md): `KW-VAULT-001`, `KW-AUDIT-001`, `KW-KEYS-002`
