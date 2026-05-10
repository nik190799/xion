# Safe propose dry-run runbook (Base Sepolia)

## Property

Produce live evidence on Base Sepolia that
[`xion_ops.services.safe`](../../xion_ops/services/safe.py) builds a SafeTx,
that [`BaseEvmService.safe_propose_tx`](../../xion_ops/services/base_evm.py)
posts it to the Safe Transaction Service, and that
[`xion-verify safe-proposal`](../../xion-verify/src/xion_verify/commands/safe_proposal.py)
recomputes the EIP-712 hash and proves byte-identity against both the
proposer's prep payload and the queued service entry. This is the closure
evidence required by `KW-OPS-001`'s pay-down line:

> "Closure requires a real Safe Transaction Service client behind
> `BaseEvmService.safe_propose_tx()`, offline tests for payload construction,
> and live dry-run evidence against Base Sepolia."

The offline-tests evidence already exists at
[`xion_ops/tests/test_safe_client_mocked.py`](../../xion_ops/tests/test_safe_client_mocked.py)
and [`xion-verify/tests/test_safe_proposal.py`](../../xion-verify/tests/test_safe_proposal.py).
This runbook produces the missing live-Sepolia row.

## Pre-requisites

1. A Base Sepolia 2-of-N or 1-of-N **rehearsal Safe** that you control. If
   you do not yet have one, deploy via <https://app.safe.global/> on
   `base-sepolia.safe.global` with a single owner = your Sepolia EOA. The
   test Safe does not need to mirror the mainnet 2-of-3 — it only needs to
   accept proposals from a known owner.
2. Foundry installed (`cast --version` works on PATH; on Windows the
   xion_ops fallback uses WSL).
3. The proposer EOA has a small Sepolia balance (≥ 0.001 ETH for nothing
   more than gas budgeting; we never **execute** in this dry-run).
4. `XION_DEPLOYER_PRIVATE_KEY` (or `PRIVATE_KEY`) exported in the shell —
   used only by `cast wallet sign` below, not by the propose POST.

## Steps

### 1. Build the SafeTx and write the prep payload

Pick any read-only-ish target the Safe is allowed to call. The cleanest
choice is the rehearsal Sepolia `MasterTreasury`'s `registerVault(uint256,address)`
with bogus arguments — the proposal will queue but never reach a threshold,
so nothing executes.

```bash
SEPOLIA_SAFE="0x<your-sepolia-rehearsal-safe>"
SEPOLIA_MASTER_TREASURY="$(jq -r '.master_treasury' genesis/TREASURY_VAULTS.json)"
DUMMY_VAULT="0x000000000000000000000000000000000000bEEF"

python -m xion_ops.cli base-evm register-vault \
  --network base-sepolia \
  --master-treasury "$SEPOLIA_MASTER_TREASURY" \
  --chain-id 1337 \
  --vault-address "$DUMMY_VAULT" \
  --safe-address "$SEPOLIA_SAFE" \
  --out /tmp/safe_prep.json
```

> **Note**: `register-vault --network base-sepolia` normally takes the
> direct-broadcast EOA path. To exercise the Safe path on Sepolia for this
> dry-run, **skip** `register-vault` and call `safe-prepare` directly:

```bash
python -m xion_ops.cli base-evm safe-prepare \
  --network base-sepolia \
  --safe-address "$SEPOLIA_SAFE" \
  --to "$SEPOLIA_MASTER_TREASURY" \
  --data 0xc7ce67a000000000000000000000000000000000000000000000000000000000000005390000000000000000000000000000000000000000000000000000000000000bEEF \
  --out /tmp/safe_prep.json
```

(The 4-byte selector `0xc7ce67a0` is the keccak prefix of
`registerVault(uint256,address)`; the next 32 bytes encode `1337` and the
final 32 bytes are the dummy vault left-padded.)

The output JSON contains `safe_tx_hash`, `chain_id`, `safe_address`, `nonce`,
and the `tx` field bag. Save it.

### 2. Verify the prep payload offline

```bash
xion-verify safe-proposal \
  --prep /tmp/safe_prep.json \
  --expected-to "$SEPOLIA_MASTER_TREASURY" \
  --expected-call-data 0xc7ce67a0... \
  --expected-value 0
```

Expected: `safe-proposal: OK`. This proves the recomputed hash equals the
hash the prep file claimed.

### 3. Sign the safeTxHash with a Safe owner

```bash
HASH="$(jq -r .safe_tx_hash /tmp/safe_prep.json)"
SIG="$(cast wallet sign --private-key "$XION_DEPLOYER_PRIVATE_KEY" "$HASH")"
echo "signature: $SIG"
```

(`cast wallet sign` of a 32-byte hex string applies the Ethereum signed
message prefix internally; for a Safe v1.4.1 proposer signature, you want
the **raw EIP-712 signature**. Use `cast wallet sign --no-hash` over the
already-final hash, or sign through the Safe app and copy the signature
from the network panel.)

### 4. Submit the proposal to the Safe Transaction Service

```bash
TO="$(jq -r .tx.to /tmp/safe_prep.json)"
DATA="$(jq -r .tx.data /tmp/safe_prep.json)"
SENDER="0x<safe-owner-address>"

python -m xion_ops.cli base-evm safe-propose \
  --network base-sepolia \
  --safe-address "$SEPOLIA_SAFE" \
  --to "$TO" \
  --data "$DATA" \
  --sender "$SENDER" \
  --signature "$SIG"
```

Expected output: a JSON `DeploymentResult` with `ok=true`,
`id=0x...safeTxHash`, and a `service_response` echoing the Safe service's
record of the proposal.

### 5. Verify the queued proposal independently

```bash
xion-verify safe-proposal \
  --safe-address "$SEPOLIA_SAFE" \
  --network base-sepolia \
  --safe-tx-hash "$HASH" \
  --expected-to "$SEPOLIA_MASTER_TREASURY" \
  --expected-call-data "$DATA"
```

Expected: `safe-proposal: OK`. This proves the **service's** view of the
proposal still matches the original payload — the third-party check that
makes this verifier load-bearing.

### 6. Reject the proposal in the Safe app

Open <https://app.safe.global/> on Base Sepolia, find the queued tx by
nonce, and **reject** it. The dry-run is closeout-of-band; do not let it
collect cosigs and execute.

## Evidence to record

Append to `docs/STATE_OF_XION_PREFLIGHT.md` § "2026-05 Service-Class
Execution":

> **Safe propose dry-run (Sepolia, KW-OPS-001 closure):** `safe-prepare`
> produced `safe_tx_hash=0x...`; `safe-propose` queued tx; `xion-verify
> safe-proposal --prep` and `--safe-tx-hash` both returned **OK**;
> proposal subsequently rejected in the Safe app. Date: YYYY-MM-DD.

Then move `KW-OPS-001` to **Closed** in `KNOWN_WEAKNESSES.md` with the same
date and a link back to this runbook.

## What this does not close

- `KW-KEYS-002`: Warm Safe owner custody (replace MetaMask owner with a
  hardware wallet owner) is independent.
- `KW-AUDIT-001`: external audit of bytecode is independent.
- Mainnet `MasterTreasury.registerVault` is a separate ceremony tracked
  under [`docs/PHASE_7_PREFLIGHT_STATUS.md`](../PHASE_7_PREFLIGHT_STATUS.md).
