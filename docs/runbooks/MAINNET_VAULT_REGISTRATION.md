# Mainnet Vault registration runbook (Base, chain 8453)

## Property

Register the first per-chain `Vault` on the live Base mainnet `MasterTreasury`,
flipping `genesis/TREASURY_VAULTS.json` `tier1_operating_tokens[].status` away
from `mainnet_routed_pending_per_chain_vault`. After this runbook runs:

- `MasterTreasury.registeredChainCount() == 1`
- `MasterTreasury.vaultForChain(8453) == <new vault>`
- `MasterTreasury.deployVault(...)` was the call (so the Vault is created and
  registered atomically — no separate `Vault.sol` deploy step)
- The Vault's `aoCoreAuthority` is the same Warm Safe (`0x5A91…29b4`), so
  withdrawals require Safe cosigs until a Cold Root / AO mainnet ceremony
  rotates that authority later.

## Pre-built artifacts (already in this branch)

- [`genesis/MAINNET_VAULT_REGISTRATION_PREP.json`](../../genesis/MAINNET_VAULT_REGISTRATION_PREP.json)
  — committed snapshot of the unsigned SafeTx (target, call data, value,
  field-bag) and its EIP-712 hash. Independently verified by
  `xion-verify safe-proposal --prep` at prep time (see verifier output below).

- Recompute (any third party):

  ```bash
  xion-verify safe-proposal \
    --prep genesis/MAINNET_VAULT_REGISTRATION_PREP.json \
    --expected-to 0xbf5407745cf22b88c46b55037e26156a0e78fd7f \
    --expected-call-data 0xdcb7c26000000000000000000000000000000000000000000000000000000000000021050000000000000000000000005a91e08d909854b594f07648d23440f4908529b4 \
    --expected-value 0
  ```

  Expected output: `safe-proposal: OK`.

## Pre-flight checks (run before signing)

1. **Confirm Safe nonce hasn't moved.** The committed prep was generated when
   the Warm Safe nonce was `0`. If any other Safe-app proposal has been
   queued or executed since, regenerate:

   ```bash
   python -m xion_ops.cli base-evm safe-prepare \
     --network base-mainnet \
     --safe-address 0x5A91E08D909854b594f07648D23440f4908529b4 \
     --to 0xbf5407745cf22b88c46b55037e26156a0e78fd7f \
     --data 0xdcb7c26000000000000000000000000000000000000000000000000000000000000021050000000000000000000000005a91e08d909854b594f07648d23440f4908529b4 \
     --out genesis/MAINNET_VAULT_REGISTRATION_PREP.json
   ```

   Re-verify with `xion-verify safe-proposal --prep ...` (above).

2. **Verify the call decodes to the expected function and arguments.** From
   any host with Foundry available:

   ```bash
   cast 4byte-decode 0xdcb7c260
   # → deployVault(uint256,address)

   cast abi-decode "deployVault(uint256,address)(uint256,address)" \
     0x00000000000000000000000000000000000000000000000000000000000021050000000000000000000000005a91e08d909854b594f07648d23440f4908529b4
   # → 8453
   # → 0x5A91E08D909854b594f07648D23440f4908529b4
   ```

3. **Sanity-check the target.** The `MasterTreasury` address in the prep file
   must match `genesis/TREASURY_VAULTS.json::master_treasury`:
   `0xbf5407745cf22b88c46b55037e26156a0e78fd7f`.

4. **Confirm Safe owner set on-chain.** Reject any divergence:

   ```bash
   cast call 0x5A91E08D909854b594f07648D23440f4908529b4 'getOwners()(address[])' \
     --rpc-url https://mainnet.base.org
   # Expected: 0x3c459fac4749113960Ec0998c19782DB92E1E536, 0x3143Aae7d469F820969B9A431EdC031304397803, 0x90e099e16b9C7c9824B06d3AE0Af92fad676489b
   ```

## Cosigner workflow

1. Each Safe owner reviews the prep file and runs the verifier on their own
   machine — **do not trust the proposer's terminal**.
2. Open <https://app.safe.global/> on Base mainnet, navigate to the Warm Safe.
3. Use **Tx Builder** → **New transaction** → **Custom contract interaction**
   - Contract address: `0xbf5407745cf22b88c46b55037e26156a0e78fd7f`
   - ABI: paste `MasterTreasury.deployVault(uint256,address)`
   - chainId: `8453`
   - vaultAuthority: `0x5A91E08D909854b594f07648D23440f4908529b4`
   - Operation: `Call` (not Delegatecall)
4. **Before signing in the wallet**, the Safe app shows the SafeTx hash. It
   MUST equal the hash in
   [`MAINNET_VAULT_REGISTRATION_PREP.json`](../../genesis/MAINNET_VAULT_REGISTRATION_PREP.json)
   (after pre-flight #1 if regenerated). If it differs, **abort** and
   investigate.
5. Once `threshold` cosignatures (2-of-3 for the Warm Safe) are collected,
   any owner clicks **Execute** and pays the gas.

## Post-execution evidence pinning

1. Capture the `VaultRegistered(uint256,address)` event from the exec
   receipt. The second indexed arg is the new Vault address.

2. Update [`genesis/TREASURY_VAULTS.json`](../../genesis/TREASURY_VAULTS.json):

   ```bash
   # Append the new vault row
   jq '.vaults += [{
     "network": "base-mainnet",
     "chain_id": 8453,
     "vault": "<new vault address>",
     "ao_core_authority": "0x5A91E08D909854b594f07648D23440f4908529b4",
     "deploy_block": <exec block>,
     "deploy_tx": "<exec tx hash>"
   }] |
   .tier1_operating_tokens |= map(
     if .asset == "USDC" or .asset == "ETH"
     then .status = "mainnet_routed_via_base_vault"
     else .
     end
   ) |
   .residual = "Base mainnet Vault live at chain 8453 (see vaults[]). Per-asset vaults for AR (Arweave, non-EVM) and TAO (Bittensor, non-EVM) remain pending; they require non-EVM rails outside MasterTreasury scope. Sprint: KW-AUDIT-001 review 2026-06-01, Cold Root deferred per OPERATOR_TRACK_D4, AO mainnet ceremony before claiming canonical substrate."
   ' genesis/TREASURY_VAULTS.json > /tmp/manifest.json && mv /tmp/manifest.json genesis/TREASURY_VAULTS.json
   ```

3. Re-run verifiers:

   ```bash
   xion-verify treasury           # OK
   xion-verify treasury-flow      # OK
   ```

4. Append to [`docs/STATE_OF_XION_PREFLIGHT.md`](../STATE_OF_XION_PREFLIGHT.md)
   § "2026-05-NN Service-Class Execution":

   > **Mainnet Vault registration (chain 8453):** Warm Safe queued + executed
   > `MasterTreasury.deployVault(8453, 0x5A91…29b4)`. SafeTxHash
   > `0x535d43558150625405c62bf96fe81229758c3ad81b67904fd48ac3ab049c6072`
   > (regenerated nonce N if applicable). Exec tx `0x...`, block N. New Vault
   > `0x...`. `registeredChainCount() == 1`. Manifest flipped: `tier1_operating_tokens[].status` for ETH and USDC moved from `mainnet_routed_pending_per_chain_vault` to `mainnet_routed_via_base_vault`.

5. Append to [`CHANGELOG.md`](../../CHANGELOG.md):

   > ### Base mainnet Vault registered — YYYY-MM-DD
   > - First per-chain Vault deployed and registered on the live MasterTreasury
   >   via Warm Safe `MasterTreasury.deployVault(8453, 0x5A91…29b4)`. Vault
   >   address `0x...`, exec tx `0x...`, block N.
   > - `genesis/TREASURY_VAULTS.json::vaults[]` extended; `tier1_operating_tokens[].status` flipped for ETH/USDC.
   > - Verifiers `xion-verify treasury` / `treasury-flow` return OK.

## What this runbook does NOT close

- AR (Arweave) and TAO (Bittensor) `tier1_operating_tokens[].status` stay
  `mainnet_routed_pending_per_chain_vault` because those chains are
  non-EVM. Custody for those rails is tracked separately under the bridge
  doctrine (`KW-BRIDGE-001`) and the `KW-TREASURY-CHAIN-001` settlement-chain
  gateway.
- `KW-AUDIT-001` (external audit) — independent.
- `KW-KEYS-002` (Warm Safe owner custody hardening) — independent; runbook
  at [`SAFE_OWNER_HARDWARE_REPLACEMENT.md`](SAFE_OWNER_HARDWARE_REPLACEMENT.md).
- Constitutional D4 "alive" status — explicitly deferred.
