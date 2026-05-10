# Replace MetaMask Safe owner with hardware wallet (KW-KEYS-002 pay-down)

## Property

The Base mainnet Warm Safe at `0x5A91E08D909854b594f07648D23440f4908529b4`
is a real 2-of-3 multisig (Safe v1.4.1+L2) but `KNOWN_WEAKNESSES.md::KW-KEYS-002`
records that owner custody is not yet hardened: two owner seeds are paper-backups
and one owner is a MetaMask software wallet. The pay-down commitment is to
replace the MetaMask owner with a hardware-wallet owner by **2026-05-31**.

After this runbook runs:

- The MetaMask EOA is **no longer** in the Safe's owner set.
- A hardware-wallet EOA (Ledger / Trezor / GridPlus) **is** in the owner set.
- `getOwners()` returns the same length (3) and same threshold (2-of-3); only
  the membership changed.
- `KW-KEYS-002` moves from **`open`** to **`closed`** with an evidence row in
  [`docs/STATE_OF_XION_PREFLIGHT.md`](../STATE_OF_XION_PREFLIGHT.md).

## Recommended hardware

Pick one. All three are widely available, support EIP-712 typed-data signing
(required for Safe v1.4.1), and can be air-gapped during the swap:

| Device | Why | Approx price |
|---|---|---|
| **Ledger Nano S Plus** | Cheapest hardened option; Safe app integration via Ledger Live + Safe app's Ledger connector | ~$80 |
| **Trezor Safe 3** | Open-source firmware; matches the project's "structural trust" doctrine | ~$80 |
| **GridPlus Lattice1** | Air-gapped + per-tx physical confirmation screen; meaningfully better against host malware | ~$400 |

For the Sprint Mode posture, **Ledger Nano S Plus** or **Trezor Safe 3** are
sufficient; GridPlus is the right answer if the operator anticipates a
later upgrade to the Cold Root posture and wants the device to survive into
that ceremony.

## Pre-flight

1. Receive the device sealed; verify tamper-evident packaging.
2. Initialize **offline**, away from any computer you've used for crypto.
3. Generate a fresh seed phrase; record on the device's own paper card. Do
   **not** type the seed into any computer.
4. Derive the new EOA address on the standard Ethereum derivation path
   (`m/44'/60'/0'/0/0`). Record the address; it is what becomes the new Safe
   owner.
5. Send a tiny test transaction (a few cents of ETH) from a hot wallet to the
   new hardware EOA to confirm derivation and signing work end-to-end. Sign
   the tx through the hardware device.
6. Top up the new EOA with **≥ 0.005 Base ETH** so the new owner can pay gas
   for cosigning future Safe transactions.

## Determine which owner to replace

The MetaMask owner is whichever of the three current owners corresponds to the
operator's MetaMask account. Confirm via either:

```bash
# From your daily machine, with MetaMask connected to Base mainnet:
# In MetaMask, select the account currently used for Safe signing.
# Compare the address against the live owner set:
cast call 0x5A91E08D909854b594f07648D23440f4908529b4 'getOwners()(address[])' \
  --rpc-url https://mainnet.base.org
```

The matching address is the `oldOwner` in the swap call. The other two owners
are the paper-backup seeds.

## Build the SafeTx

Safe `swapOwner(prevOwner, oldOwner, newOwner)` takes:

- `prevOwner`: the address that **points to** `oldOwner` in the Safe's
  internal linked list. The Safe owner list is implemented as a singly-linked
  list with sentinel `0x0000000000000000000000000000000000000001`. To compute
  `prevOwner`:
  - Get the array order from `getOwners()` above.
  - If `oldOwner` is at index 0 → `prevOwner = 0x0000000000000000000000000000000000000001` (sentinel).
  - Otherwise `prevOwner = owners[index_of_oldOwner - 1]`.
- `oldOwner`: the MetaMask EOA you are replacing.
- `newOwner`: the hardware-wallet EOA from pre-flight.

Build and prep:

```bash
SAFE="0x5A91E08D909854b594f07648D23440f4908529b4"
PREV="<computed-prev-owner>"           # 0x...0001 or owners[i-1]
OLD="<MetaMask EOA>"                    # to remove
NEW="<hardware-wallet EOA>"             # to add

# 1. Encode the call
CALL_DATA="$(wsl -- bash -lc "export PATH=\"\$HOME/.foundry/bin:\$PATH\"; \
  cast calldata 'swapOwner(address,address,address)' '$PREV' '$OLD' '$NEW'")"

# 2. Generate prep payload (the Safe is calling itself — self-administration)
python -m xion_ops.cli base-evm safe-prepare \
  --network base-mainnet \
  --safe-address "$SAFE" \
  --to "$SAFE" \
  --data "$CALL_DATA" \
  --value 0 \
  --operation 0 \
  --out genesis/SAFE_OWNER_SWAP_PREP.json

# 3. Independently verify
xion-verify safe-proposal \
  --prep genesis/SAFE_OWNER_SWAP_PREP.json \
  --expected-to "$SAFE" \
  --expected-call-data "$CALL_DATA" \
  --expected-value 0
```

Expected output: `safe-proposal: OK`. Note `--to` here is the **Safe itself**
because owner swaps are self-administration — the Safe calls its own
`swapOwner` method.

## Cosigner workflow

Same as [`MAINNET_VAULT_REGISTRATION.md`](MAINNET_VAULT_REGISTRATION.md) §
Cosigner workflow, with two differences:

1. The target contract is the Safe itself (`0x5A91…29b4`), not the
   `MasterTreasury`.
2. The MetaMask owner being replaced **must not sign their own removal in a
   way that locks them out before the swap executes**. Specifically: collect
   exactly the `threshold - 1 = 1` cosigs from the **paper-backup owners**
   first, then have the MetaMask owner sign last and execute. Once exec lands,
   the MetaMask key is no longer authoritative.

   If you want a belt-and-suspenders approach, sign with both paper-backup
   owners (giving you the full 2 cosigs without MetaMask) and have any owner
   execute. That way the MetaMask key is not used at all in its own swap-out.

## Post-execution evidence pinning

1. Capture the swap exec tx hash and block number.
2. Verify the new owner set:

   ```bash
   cast call 0x5A91E08D909854b594f07648D23440f4908529b4 'getOwners()(address[])' \
     --rpc-url https://mainnet.base.org
   # Expected: hardware-wallet EOA replaces the MetaMask EOA; threshold unchanged
   cast call 0x5A91E08D909854b594f07648D23440f4908529b4 'getThreshold()(uint256)' \
     --rpc-url https://mainnet.base.org
   # Expected: 2
   ```

3. Append to [`docs/STATE_OF_XION_PREFLIGHT.md`](../STATE_OF_XION_PREFLIGHT.md)
   § "Operator custody decision":

   > **Hardware-wallet Safe owner swap (KW-KEYS-002 closure):**
   > MetaMask owner `0x...` replaced by hardware-wallet owner `0x...` via Safe
   > self-admin tx `0x...`, block N. Hardware vendor: Ledger Nano S Plus /
   > Trezor Safe 3 / GridPlus Lattice1. Safe owner set is now: paper backup A
   > (`0x...`), paper backup B (`0x...`), hardware wallet (`0x...`).

4. Update [`KNOWN_WEAKNESSES.md::KW-KEYS-002`](../../KNOWN_WEAKNESSES.md):
   move **Status** from `open` to `closed`, add closure date and evidence
   pointer.

5. Append to [`CHANGELOG.md`](../../CHANGELOG.md):

   > ### Warm Safe owner custody hardened — YYYY-MM-DD
   > - MetaMask Safe owner replaced by hardware wallet via Safe self-admin
   >   `swapOwner(prev, old, new)` from the Warm Safe at `0x5A91…29b4`. Exec
   >   tx `0x...`, block N.
   > - `KW-KEYS-002` moved from `open` to `closed`. Two owner slots remain
   >   paper-backup; their off-site geographic distribution remains the
   >   subject of a future Cold Root ceremony.

## What this runbook does NOT close

- `KW-KEYS-001` (Cold Root posture) — Sprint Mode software-Shamir custody is
  still in use; full Cold Root requires geographic shard distribution and
  in-person ceremony. Deferred to Full D4.
- The remaining two paper-backup owners are still single-location paper.
  They could be moved off-site separately as part of an operator follow-up;
  not blocking for KW-KEYS-002 closure.
- AO Core mainnet authority — independent.

## Operator action checklist

- [ ] Buy the hardware wallet device.
- [ ] Initialize device offline; generate fresh seed; record on device paper card.
- [ ] Top up the hardware-wallet EOA with ≥ 0.005 Base ETH for gas.
- [ ] Identify which of the three current Safe owners is the MetaMask EOA.
- [ ] Build the swapOwner prep file via the commands in § "Build the SafeTx".
- [ ] Independently verify with `xion-verify safe-proposal`.
- [ ] Cosign + execute through `app.safe.global` per § "Cosigner workflow".
- [ ] Pin evidence per § "Post-execution evidence pinning".
- [ ] Verify `xion-verify funding-balances` still passes after the swap (the
      new owner inherits the funding-target requirement).
