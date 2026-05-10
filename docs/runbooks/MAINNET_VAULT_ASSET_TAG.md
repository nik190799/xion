# Mainnet Vault asset tagging — before first withdrawal

## Property

The mainnet `Vault` (`0x64712dFD8441186F3cfF5232C37a019286992bdC`) needs to know which assets are "native to this chain" vs "bridged in" before it will allow withdrawals. Until an asset is tagged via `Vault.tagAsset(address asset, bool nativeAsset)`, calls to `Vault.withdraw(asset, ...)` revert with `UnknownAsset()`.

**Critical clarification.** The Vault accepts **incoming** deposits without any tagging:

- Anyone can `transfer` ETH directly to the Vault (the `receive() external payable {}` accepts it).
- Anyone can `IERC20.transfer(<vault>, amount)` USDC/etc. into it. The Vault holds the tokens.

Tagging is needed **before the first withdrawal call from the Safe**. Until the operator wants to make their first `Vault.withdraw(...)`, this runbook is purely preparatory.

## Pre-built artifacts (already in this branch)

Two single-tx prep files, sequential nonces 1 and 2 (Safe nonce after the 2026-05-10 `deployVault` exec is `1`).

### ETH (NATIVE_ASSET = `address(0)`)

- **File:** [`genesis/MAINNET_VAULT_TAG_ETH_PREP.json`](../../genesis/MAINNET_VAULT_TAG_ETH_PREP.json)
- **Target:** `0x64712dFD8441186F3cfF5232C37a019286992bdC` (the Vault)
- **Function:** `tagAsset(0x0000…0000, true)` — marks ETH as native
- **Nonce:** `1`
- **safeTxHash:** `0x55ab5314f5ce59f5e96804e63fa87801d5de68bb9cf3df5105829f5c643317fc`
- **Call data:** `0x64ab0e6100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001`

### USDC (Base mainnet canonical Circle USDC)

- **File:** [`genesis/MAINNET_VAULT_TAG_USDC_PREP.json`](../../genesis/MAINNET_VAULT_TAG_USDC_PREP.json)
- **Target:** `0x64712dFD8441186F3cfF5232C37a019286992bdC` (the Vault)
- **USDC contract:** `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (verified Circle-issued USDC on Base mainnet)
- **Function:** `tagAsset(0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, true)` — marks USDC as native (Circle issues directly on Base; not a bridged stable)
- **Nonce:** `2`
- **safeTxHash:** `0x4288e90810d285bff9b74adab3ac5aed1200e1aa40937067995471ab4992d3ec`
- **Call data:** `0x64ab0e61000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda029130000000000000000000000000000000000000000000000000000000000000001`

Both verifier-OK against the offline `xion-verify safe-proposal --prep` recompute at commit time.

## Pre-flight (each cosigner runs)

```bash
# ETH prep
xion-verify safe-proposal \
  --prep genesis/MAINNET_VAULT_TAG_ETH_PREP.json \
  --expected-to 0x64712dFD8441186F3cfF5232C37a019286992bdC \
  --expected-call-data 0x64ab0e6100000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001 \
  --expected-value 0
# Expected: safe-proposal: OK

# USDC prep
xion-verify safe-proposal \
  --prep genesis/MAINNET_VAULT_TAG_USDC_PREP.json \
  --expected-to 0x64712dFD8441186F3cfF5232C37a019286992bdC \
  --expected-call-data 0x64ab0e61000000000000000000000000833589fcd6edb6e08f4c7c32d4f71b54bda029130000000000000000000000000000000000000000000000000000000000000001 \
  --expected-value 0
# Expected: safe-proposal: OK
```

Also confirm Safe state hasn't drifted:

```bash
cast call 0x5A91E08D909854b594f07648D23440f4908529b4 'nonce()(uint256)' --rpc-url https://mainnet.base.org
# Expected: 1 (if you've executed nothing else since the deployVault ceremony)
```

If the Safe nonce has moved past 1 (someone executed other operations through the Safe), regenerate both preps with explicit `--nonce <n>` and `--nonce <n+1>` via `xion_ops base-evm safe-prepare`.

## Two ways to execute

### Option A — Two separate ceremonies (simpler, more time)

For each asset:

1. Open <https://app.safe.global/home?safe=base:0x5A91E08D909854b594f07648D23440f4908529b4> on Base mainnet.
2. **Tx Builder → New transaction**:
   - **To**: `0x64712dFD8441186F3cfF5232C37a019286992bdC` (the Vault)
   - **ETH value**: `0`
   - **Data (Hex encoded)**: paste from the prep file's `tx.data` field
3. Verify safeTxHash against the prep, sign, collect 2-of-3, execute.
4. Repeat for the second asset.

### Option B — One batched ceremony (more efficient)

Safe Tx Builder supports adding multiple transactions to a single batch. They execute as one `MultiSendCallOnly` delegatecall:

1. Open Tx Builder, paste the same ABI fragment as before but for `tagAsset(address,bool)`.
2. **Add transaction** with `(address(0), true)`.
3. **Add transaction** again with `(0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913, true)`.
4. **Create batch** → **Send batch**.

Note: this batches into a single SafeTx with a different safeTxHash (because operation = 1 / DELEGATECALL to MultiSendCallOnly). The `xion-verify safe-proposal --prep` flow currently has prep files for the individual calls only; for the batch, the verifier check would need to recompute the batch hash against MultiSendCallOnly. Operators who want batched exec should compare the Safe app's displayed safeTxHash to a manually-computed batch hash, or fall back to Option A.

For most cases, Option A is the conservative answer: two simple SafeTxs whose hashes match committed prep files exactly.

## Cosigner sigs (headless paper-key flow)

Same pattern as `docs/runbooks/SAFE_PROPOSE_DRY_RUN.md` and the deployVault ceremony, now with the `safe-confirm` CLI command:

```bash
# 1. Read paper-owner private key into one-shot env var
read -s PAPER_PK
echo "key length: ${#PAPER_PK}"   # expect: 66

# 2. Sanity-check address
cast wallet address --private-key "$PAPER_PK"
# Must equal one of the Safe owners (paper backups: 0x3143Aae7…, 0x90e099e1…)

# 3. Sign whichever safeTxHash is being confirmed
SIG=$(cast wallet sign --no-hash --private-key "$PAPER_PK" 0x55ab5314f5ce59f5e96804e63fa87801d5de68bb9cf3df5105829f5c643317fc)
# (replace hash with the USDC one for the second tx)

# 4. Submit confirmation
python -m xion_ops.cli base-evm safe-confirm \
  --network base-mainnet \
  --safe-tx-hash 0x55ab5314f5ce59f5e96804e63fa87801d5de68bb9cf3df5105829f5c643317fc \
  --signature "$SIG"

# 5. Cleanup
unset PAPER_PK SIG
history -d $((HISTCMD-1))
```

## Post-execution evidence

After both txs execute, verify on-chain:

```bash
cast call 0x64712dFD8441186F3cfF5232C37a019286992bdC 'assetKnown(address)(bool)' \
  0x0000000000000000000000000000000000000000 \
  --rpc-url https://mainnet.base.org
# Expected: true

cast call 0x64712dFD8441186F3cfF5232C37a019286992bdC 'assetKnown(address)(bool)' \
  0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 \
  --rpc-url https://mainnet.base.org
# Expected: true
```

Then append to `docs/STATE_OF_XION_PREFLIGHT.md` under the existing 2026-05-10 Service-Class Execution section:

> **Vault asset tagging — EXECUTED <date>.** `Vault.tagAsset(address(0), true)` exec tx `0x...` at block `N`; `Vault.tagAsset(USDC, true)` exec tx `0x...` at block `N`. Vault is now operationally complete: `assetKnown(0x0)` and `assetKnown(0x8335…2913)` both return true. Future `Vault.withdraw(...)` from the Warm Safe will succeed for ETH and USDC.

## What this runbook does NOT close

- AR (Arweave) and TAO (Bittensor) — non-EVM, not tagged via this Vault. Separate rail integration.
- `KW-AUDIT-001` (still mitigated-residual until Xion's treasury can fund the audit).
- Any D4 "alive" ceremony.
