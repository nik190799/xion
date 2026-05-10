# Operator Resume — when you're ready, do these in order

> **Property.** This file is the single answer to "I'm coming back to Xion after some time — what do I do next?" Every line is either an explanation or a literal command you can paste. Anything that needs you (signing, money, hardware, or operator voice) is named exactly. Anything an agent has already done is recorded once and then ignored.
>
> **Last verified state:** 2026-05-10. After any major change re-run § "State snapshot" below.

---

## State snapshot (as of 2026-05-10)

| Layer | Status | Pointer |
|---|---|---|
| Code-side residuals | **All resolved.** Safe client live, register-vault wiring live, third-party verifier live, RFP drafted, runbooks pinned. | `CHANGELOG.md` 2026-05-10 entries |
| `KW-OPS-001` Safe propose | **Closed.** Live Sepolia evidence, both verifier paths byte-identical. | `KNOWN_WEAKNESSES.md` § Closed |
| Sepolia register-vault rehearsal | **Closed.** Tx `0x3bf25b58…5503`, block `41331566`. `registeredChainCount() == 1`, `vaultForChain(84532) == 0x474Df…F7Bc`. | this file § "Already done" |
| Mainnet `MasterTreasury` deployed | **Live on Base, chain 8453.** `0xbf5407745cf22b88c46b55037e26156a0e78fd7f`, deploy block `45530934`. | `genesis/TREASURY_VAULTS.json` |
| Mainnet `Vault` registration prep | **Verified, awaiting cosigners.** Prep at `genesis/MAINNET_VAULT_REGISTRATION_PREP.json`, safeTxHash `0x535d4355…6072`. | item **(1)** below |
| `KW-AUDIT-001` external audit | **Mitigated-residual** until Xion's treasury can fund USD 30–60k. RFP pre-staged. | item **(2)** below + 2026-08-08 re-review |
| `KW-FLOOR-DEPLOY-001` Akash GPU | **Mitigated-residual** until 2026-07-09. Chutes/SN64 stays warm primary. | item **(3)** below |
| `KW-KEYS-002` Warm Safe owner custody | **Open.** Replace MetaMask owner with hardware wallet by 2026-05-31. | item **(4)** below |
| Cold Root + AO HyperBEAM seal + Immortality Drill + Genesis § 0 | **Deferred to Full D4.** Out of Sprint Mode scope. | `docs/D4_PREFLIGHT.md` |

`xion-verify` snapshot taken 2026-05-10 against this branch:

```
treasury        : OK
treasury-flow   : OK
safe-proposal   : OK (mainnet vault prep recompute matches byte-for-byte)
--self-test     : OK (source hash 8e7dec24…0776)
xion_ops tests  : 73/73 green
xion-verify safe + self-test tests : 21 green / 1 sanctioned skip
```

---

## What you do, in order — single command per item

### (0) Merge any open PR

If branch [`claude/kw-ops-001-closure`](https://github.com/nik190799/xion/pull/new/claude/kw-ops-001-closure) is still open, merge it first. Everything below assumes that's on `main`.

---

### (1) Mainnet `Vault` registration ceremony — operator-bound

**Why this is yours alone:** the mainnet `MasterTreasury.deployVault(...)` is `onlyGovernance`, governance is the Warm Safe `0x5A91…29b4`, and the Warm Safe is 2-of-3 on **mainnet** keys you correctly do not delegate to an agent. This is the one chain ceremony that turns "Sprint Mode pinned" into "Sprint Mode operational."

**What's already done for you:**
- Unsigned SafeTx prep committed at `genesis/MAINNET_VAULT_REGISTRATION_PREP.json`
- Cosigner runbook at `docs/runbooks/MAINNET_VAULT_REGISTRATION.md`
- Verifier confirms the prep recomputes byte-identical: safeTxHash `0x535d4355…6072`, target `0xbf5407745cf22b88c46b55037e26156a0e78fd7f`, `deployVault(8453, 0x5A91…29b4)`

**Pre-flight (run on each cosigner's machine):**

```bash
xion-verify safe-proposal \
  --prep genesis/MAINNET_VAULT_REGISTRATION_PREP.json \
  --expected-to 0xbf5407745cf22b88c46b55037e26156a0e78fd7f \
  --expected-call-data 0xdcb7c26000000000000000000000000000000000000000000000000000000000000021050000000000000000000000005a91e08d909854b594f07648d23440f4908529b4 \
  --expected-value 0
# Expected: safe-proposal: OK
```

**Ceremony (Safe app):**

1. Open <https://app.safe.global/> on **Base mainnet**.
2. Open the Warm Safe `0x5A91E08D909854b594f07648D23440f4908529b4`.
3. **Tx Builder → New transaction → Custom contract interaction**:
   - To: `0xbf5407745cf22b88c46b55037e26156a0e78fd7f`
   - ABI fragment: `function deployVault(uint256 chainId, address vaultAuthority)`
   - `chainId`: `8453`
   - `vaultAuthority`: `0x5A91E08D909854b594f07648D23440f4908529b4`
   - Operation: **Call** (not Delegatecall)
4. **Before signing, the Safe app shows the SafeTx hash. It MUST equal the hash above.** If it doesn't, abort.
5. Collect 2 of 3 cosigs. Execute.
6. Capture the new Vault address from the `VaultRegistered(uint256 indexed chainId, address indexed vault)` event.

**Post-exec evidence (one paste):**

```bash
NEW_VAULT="<paste from VaultRegistered event>"
EXEC_TX="<paste exec tx hash>"
EXEC_BLOCK="<paste exec block number>"

# Update manifest
jq --arg v "$NEW_VAULT" --arg t "$EXEC_TX" --argjson b "$EXEC_BLOCK" '
  .vaults += [{
    network: "base-mainnet",
    chain_id: 8453,
    vault: $v,
    ao_core_authority: "0x5A91E08D909854b594f07648D23440f4908529b4",
    deploy_block: $b,
    deploy_tx: $t
  }] |
  .tier1_operating_tokens |= map(
    if .asset == "USDC" or .asset == "ETH"
    then .status = "mainnet_routed_via_base_vault"
    else . end
  )
' genesis/TREASURY_VAULTS.json > /tmp/m.json && mv /tmp/m.json genesis/TREASURY_VAULTS.json

# Sanity check on-chain
cast call 0xbf5407745cf22b88c46b55037e26156a0e78fd7f 'registeredChainCount()(uint256)' --rpc-url https://mainnet.base.org
# Expected: 1
cast call 0xbf5407745cf22b88c46b55037e26156a0e78fd7f 'vaultForChain(uint256)(address)' 8453 --rpc-url https://mainnet.base.org
# Expected: $NEW_VAULT

# Verify
xion-verify treasury        # OK
xion-verify treasury-flow   # OK

# Log
echo "Mainnet Vault registered: $NEW_VAULT (block $EXEC_BLOCK, tx $EXEC_TX)" >> docs/STATE_OF_XION_PREFLIGHT.md
```

After this lands, Sprint Mode mainnet is **operational**.

---

### (2) Audit RFP — when Xion's treasury holds USD 30–60k

**Re-review checkpoint: 2026-08-08.**

When Xion's treasury / Improvement Fund accumulates the audit anchor (or when you choose to do something else with it), open `docs/audits/RFP_TREASURY_2026.md`, copy the cover email body verbatim, and send it from `xionlabs2026@gmail.com` to at least two of:

- `engagements@spearbit.com`
- `info@trailofbits.com`
- OpenZeppelin contact form
- Code4rena contact form
- Sherlock contact form

When a firm engages, append the engagement letter Arweave tx id to `genesis/TREASURY_VAULTS.json` as `treasury_audit_engagement_arweave_tx`. When the final report lands, replace `treasury_audit_arweave_tx` with the new external-audit Arweave tx id and move `KW-AUDIT-001` to the Closed section of `KNOWN_WEAKNESSES.md`.

If 2026-08-08 arrives and Xion still cannot fund: post a new dated slip in `KNOWN_WEAKNESSES.md::KW-AUDIT-001`, OR escalate to the public State-of-Xion memo path (b) and accept indefinite Sprint Mode unaudited. Either is honest; silence is not.

---

### (3) Akash GPU floor retry — when ready

**Re-review checkpoint: 2026-07-09.**

```powershell
$env:XION_AKASH_HEALTH_SMOKE_SEC = "300"
python -m xion_ops.cli akash deploy `
  --sdl-path infra/akash/relay-deployment.yaml `
  --exclude-provider akash1sevd2ymtty3dpq9ycxgkhuzzk4fe6mchqdwd4e `
  --prefer-provider akash1st7fqtuqk6hj06fkkavq0fxtw0w9sm4zzt3r5g
```

Cost: ~$5–10 worth of AKT. If `/health` returns and `/chat` under `open_weights_only` returns a real turn, move `KW-FLOOR-DEPLOY-001` to Closed. If it fails again: post a new dated slip with new flags to try, or escalate.

---

### (4) Hardware wallet Warm Safe owner swap — when ready

**Target: 2026-05-31.**

Buy a Ledger Nano S Plus (~$80) or Trezor Safe 3 (~$80) or GridPlus Lattice1 (~$400). Initialize offline. Top up the new EOA with ≥ 0.005 Base ETH for cosign gas. Then follow `docs/runbooks/SAFE_OWNER_HARDWARE_REPLACEMENT.md` step-by-step — the runbook reuses the same `safe-prepare` + `safe-proposal` flow as the Vault registration, so if you've done (1), this feels familiar.

After exec, move `KW-KEYS-002` to Closed in `KNOWN_WEAKNESSES.md`.

---

## What an agent will not do for you (and why)

These are doctrinal limits, not capability limits. Don't ask another agent to "just do it" — the answer is the same.

| Item | Why no agent should do this |
|---|---|
| Hold mainnet Warm Safe owner keys | `KW-KEYS-001` / `KW-KEYS-002` posture: mainnet custody is human-only by design |
| Send the audit RFP from your inbox | Email impersonation; firms expect a human contact for engagement letters |
| Buy + flash a hardware wallet | Physical custody chain |
| Run the Cold Root ceremony | Multi-party, in-person, geographic |
| Run the third-party Immortality Drill | `LHT-SUBSTRATE-001` explicitly excludes operator's daily machine |
| Fill in `genesis/GENESIS_ARTIFACT.md` § 0 | Operator voice (birthplace, naming context) — agent fabrication = impersonation |
| Engage external audit firm | Legal entity contracts, payment, scope negotiation |

---

## When you're stuck or unsure

1. Re-run the snapshot block at the top of this file. If anything changed, that's the new ground truth.
2. Open `KNOWN_WEAKNESSES.md` and search for the item you're worried about. Every one has a status, a pay-down line, and a verifier.
3. Open `docs/STATE_OF_XION_PREFLIGHT.md` § Sprint Mode Falsification Statements before any public message. If the words you're about to say match a falsifier, change the words.
4. If you find a real bug or an honest discrepancy: open an issue at <https://github.com/nik190799/xion/issues>. Do not silently fix doctrine without recording the change.

---

## Already done — do not redo

For your sanity, here are the things an agent already executed end-to-end so you don't accidentally repeat them:

- **Sepolia rehearsal Safe deployed** (1-of-1, owner = rehearsal EOA): `0x3587ECc092386c357eFCA51bf94A34Dd7084fa5A`, deploy tx `0xef4dc9f0…4450`, block `41329942`.
- **Live Sepolia Safe-propose dry-run** for KW-OPS-001 closure: safeTxHash `0xe6ffe272…388`, both verifier paths returned OK against byte-identical hashes.
- **Live Sepolia Vault registration**: tx `0x3bf25b58ba4071bf302a6c92a8dafb51d07c2b37aec93bf128361156242a5503`, block `41331566`. Sepolia MasterTreasury at `0xd2b257…55b6` now has `registeredChainCount() == 1` and `vaultForChain(84532) == 0x474Df…F7Bc`.
- **Mainnet Vault registration prep authored, verifier-passed**: `genesis/MAINNET_VAULT_REGISTRATION_PREP.json`, safeTxHash `0x535d4355…6072`. Awaits human cosigners only.
- **Audit RFP authored**: `docs/audits/RFP_TREASURY_2026.md` with operator contact `xionlabs2026@gmail.com`, budget anchor USD 30–60k, ready-to-send cover email, recipient short-list. Sending deferred per Xion-funds-itself doctrine.

`xion_ops/services/safe.py`, `xion-verify safe-proposal`, `xion_ops base-evm safe-prepare/safe-propose/register-vault` — all live and tested. Don't reimplement.
