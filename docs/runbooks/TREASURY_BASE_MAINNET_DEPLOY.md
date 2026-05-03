# Treasury — Base mainnet deploy and verification

This runbook is for **operator execution after** Base Sepolia rehearsal (`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`), verifier gates, and an explicit **Full D4** or **Sprint Mode** posture recorded in `docs/OPERATOR_TRACK_D4.md` and `KNOWN_WEAKNESSES.md`.

## Preconditions

1. **No Sepolia EOA habits on mainnet** — use Cold Root / hardware-wallet flows per `docs/13-OPERATIONS.md` and `docs/D4_PREFLIGHT.md`. Do not reuse testnet private keys as production governance.
2. **Forge CI green** — `.github/workflows/foundry.yml` on the commit you deploy.
3. **`KW-AUDIT-001` closed or Sprint-accepted** — external audit for deployable bytecode, or documented unaudited acceptance with Sepolia soak + coverage evidence (`docs/audits/treasury-2026-report.CORRECTION.md`).
4. **Bytecode / manifest honest** — `genesis/TREASURY_VAULTS.json` pins and `xion-verify treasury` green for the revision you broadcast.

## `KW-AUDIT-002` / correction pairing (manifest)

Before broadcasting Base mainnet (or re-pinning after deploy):

- **`treasury_audit_arweave_tx`** and **`treasury_audit_correction_arweave_tx`** must be populated per `genesis/TREASURY_VAULTS.json` schema; `xion-verify treasury` fails if a correction is required but the paired field is empty.
- Publish the correction narrative beside the original internal review per `docs/audits/treasury-2026-report.CORRECTION.md` and record the Arweave tx id in the manifest.

## Scripted gates (operator workflow)

From repo root (bash; WSL on Windows is fine):

```bash
bash scripts/verify-mainnet-deploy-gates.sh
# or: python scripts/verify_mainnet_deploy_gates.py
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

Per `DEVELOPMENT_ROADMAP.md` Phase 7: clone the **same tagged commit** (or release tag) the operator broadcast from onto a **non-operator** machine, install `xion-verify` (`pip install -e ./xion-verify[dev]`), export read-only RPCs if needed (`BASE_MAINNET_RPC`, `BASE_SEPOLIA_RPC` for rehearsal cross-check), and run:

```bash
xion-verify --self-test
bash scripts/verify-mainnet-deploy-gates.sh
```

Optional Sepolia soak cross-check on the third-party host:

```bash
TREASURY_SOAK_PROBES=1 bash scripts/verify-mainnet-deploy-gates.sh
```

Record commit hash, verifier transcript, and any `WARN` lines from `treasury-flow` / `akash-deploy-discipline` in your State-of-Xion / Phase 7 memo.
