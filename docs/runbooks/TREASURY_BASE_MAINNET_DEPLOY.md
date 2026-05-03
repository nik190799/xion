# Treasury — Base mainnet deploy and verification

This runbook is for **operator execution after** Base Sepolia rehearsal (`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`), verifier gates, and an explicit **Full D4** or **Sprint Mode** posture recorded in `docs/OPERATOR_TRACK_D4.md` and `KNOWN_WEAKNESSES.md`.

## Preconditions

1. **No Sepolia EOA habits on mainnet** — use Cold Root / hardware-wallet flows per `docs/13-OPERATIONS.md` and `docs/D4_PREFLIGHT.md`. Do not reuse testnet private keys as production governance.
2. **Forge CI green** — `.github/workflows/foundry.yml` on the commit you deploy.
3. **`KW-AUDIT-001` closed or Sprint-accepted** — external audit for deployable bytecode, or documented unaudited acceptance with Sepolia soak + coverage evidence (`docs/audits/treasury-2026-report.CORRECTION.md`).
4. **Bytecode / manifest honest** — `genesis/TREASURY_VAULTS.json` pins and `xion-verify treasury` green for the revision you broadcast.

## Scripted gates (operator workflow)

From repo root (bash; WSL on Windows is fine):

```bash
bash scripts/verify-mainnet-deploy-gates.sh
```

Optional **during soak** on Sepolia (or spot-check after mainnet pin):

```bash
TREASURY_SOAK_PROBES=1 bash scripts/verify-mainnet-deploy-gates.sh
```

## Broadcast

1. Set `BASE_MAINNET_RPC` (or `XION_BASE_MAINNET_RPC` if your tooling reads it), constructor env (`XION_TREASURY_GOVERNANCE`, `XION_AO_CORE_AUTHORITY`, `XION_BRIDGE_CAP_BPS`), and signer material per your hardware / multisig process — **not** necessarily `PRIVATE_KEY` in `.env` if you use a ledger; adapt `forge` invocation accordingly.
2. Deploy with explicit **`--network base`** or **`base-mainnet`** only when intentionally targeting chain id 8453:

```bash
python -m xion_ops.cli base-evm preflight-treasury --network base-mainnet
python -m xion_ops.cli base-evm deploy-treasury --network base-mainnet
```

3. Pin manifests, publish correction/audit citations as required, and re-run `xion-verify treasury` / `xion-verify supply` with mainnet RPC env.

## Third-party verification

Per `DEVELOPMENT_ROADMAP.md` Phase 7: clone the tagged commit on a **non-operator** machine, install `xion-verify`, export read-only RPCs if needed, and run:

```bash
xion-verify --self-test
bash scripts/verify-mainnet-deploy-gates.sh
```

Record hashes, commit, and verifier transcript in your State-of-Xion memo.
