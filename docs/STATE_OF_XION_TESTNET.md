# State of Xion Testnet - 2026-05-03

## 2026-05-06 update (Akash GPU closure pass)

- Automated GPU deploy retries (`relay-deployment.yaml`) were rolled back; see
  [`genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json`](../genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json)
  and **`docs/runbooks/POST_FUNDING_DEPLOY.md`** § *Operator log — GPU lease retries*.
- **`KW-FLOOR-DEPLOY-001`** remains **open**; **`KW` / `LHT-SUBSTRATE-001` /
  Immortality Drill** docs updated for the honesty gate (no third-party drill
  claim until the floor closes).
- The committed Akash URL in `ledgers/RELAY_REGISTRY.json` may be **stale or
  unreachable** after lease closure — `xion-verify discovery` still checks
  **structure + payload hash**, not live HTTP.

## Status

This is a D3 testnet-deployed status note. It is not a Genesis memo, not a
mainnet announcement, and not a claim that Xion is alive in the constitutional
D4 sense.

## What Is Reachable Today

- Akash registry primary endpoint: `https://provider.161.97.85.20.nip.io:30564`
  returned `ok` through `xion_ops akash health-smoke`.
- Registry row: `ledgers/RELAY_REGISTRY.json` carries
  `instance_class="cpu-only"` and `image_tag="pre-genesis-akash-wall120"` for
  the Akash row.
- Registry Arweave tx: `5yCnBKyrlGQrf4KJCmCTJexGVxNBB6F2N4GDqcSPIbw`.
- `xion-verify discovery` returns `OK`.
- `xion-verify substrate-portability` returns `OK`.
- `xion-verify pre-genesis` returns `OK` with accepted residuals for missing
  Docker, partial vital-sign domains, and no shadow relay on port `8001`.
- Chutes remains the warm secondary registry row at
  `https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai`.

## What Was Attempted

`xion_ops` added a provider allowlist plus pre-accept provider ingress checks to
stop blindly accepting the cheapest broken Akash bid. The D3 relight path also
adds a CPU-only SDL at `infra/akash/relay-deployment-cpu-only.yaml`.

Fresh Akash deploy attempts on 2026-05-03:

- `dseq=26654856`: strict preferred provider
  `akash1x2g8wfa429fukudgkclaag00d00z4rn846j7wq` did not bid; deployment was
  closed before lease acceptance.
- `dseq=26654863`: strict preferred provider
  `akash1rja3y2ctj3tzmesvh0zfhzzx95rfjw405hwt8d` did not bid; deployment was
  closed before lease acceptance.
- `dseq=26654870`: adaptive provider
  `akash16yr3wxt97ae045a06kr3ycde9srcgpg8syjxxm` passed the pre-accept provider
  probe, but the actual forwarded Relay endpoint timed out after manifest; the
  deployment was closed by `AkashService.deploy_relay()`.

The registry therefore republishes the still-reachable older Akash CPU endpoint,
not a fresh GPU floor.

## What Is Still Blocked

- Base Sepolia `MasterTreasury` redeploy and rotation rehearsal are now unblocked, as the required `.env` variables and signer material have been provided. The deployment command is queued for execution.
- `KW-FLOOR-DEPLOY-001` remains open. The CPU-only Akash row is a D3 registry
  relight bridge, not proof of a deployed open-weights floor.
- D4 remains blocked by external audit, Cold Root custody, AO mainnet seal,
  Genesis Artifact finalization, and the third-party Immortality Drill.

## Sepolia treasury next actions

1. `python -m xion_ops.cli base-evm prepare-sepolia-env` then add signer material to `.env` (`PRIVATE_KEY` or `XION_DEPLOYER_PRIVATE_KEY`; see [.env.example](../.env.example) treasury block).
2. `python -m xion_ops.cli base-evm preflight-treasury --network base-sepolia` (fail fast if env incomplete).
3. Run rehearsal end-to-end: [`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`](runbooks/TREASURY_SEPOLIA_DEPLOY.md) (`deploy-treasury` → `pin-deployment` only if addresses change) → soak → `xion-verify supply` / treasury family). `genesis/TREASURY_VAULTS.json` already pins a live Base Sepolia deployment; redeploy only when source/manifest policy requires it.
4. During soak: `bash scripts/treasury-soak-probes.sh` or `TREASURY_SOAK_PROBES=1 bash scripts/verify-mainnet-deploy-gates.sh`.
5. Scripted verifier bundle for operators: [`scripts/verify-mainnet-deploy-gates.sh`](../scripts/verify-mainnet-deploy-gates.sh).
6. Record whether the operator intends **full D4** vs **Sprint Mode** residuals in [`docs/OPERATOR_TRACK_D4.md`](OPERATOR_TRACK_D4.md). Track Phase 7 externals in [`docs/PHASE_7_PREFLIGHT_STATUS.md`](PHASE_7_PREFLIGHT_STATUS.md).
7. Base mainnet (post gates + posture): [`docs/runbooks/TREASURY_BASE_MAINNET_DEPLOY.md`](runbooks/TREASURY_BASE_MAINNET_DEPLOY.md).

Pull requests touching `contracts/**` execute Foundry **`forge build` / `forge test`** in [`.github/workflows/foundry.yml`](../.github/workflows/foundry.yml).

## Verification Commands

```bash
xion-verify akash-deploy-discipline
xion-verify discovery
xion-verify substrate-portability
xion-verify pre-genesis
```

`xion-verify all --allow-not-yet-sealed` returns OK on this operator
workstation when invoked with `XION_API_REQUIRE_BEARER=false` exported into
the verifier's process environment (the verifier does not auto-load `.env`;
the orchestrator's lifespan does, but the verifier is intentionally
explicit about its config sources — see the `--env-file` option on
`xion-verify api-tokens`).

Two operator residuals were resolved before this run:

1. `genesis/HERMES_TOOL_ALLOWLIST.yaml` (and twelve other LF-anchored
   files) had drifted to CRLF in the local working tree on this Windows
   checkout. The git index already held the sealed LF bytes; the working
   tree was renormalized in place by rewriting `\r\n` to `\n`. Post-fix
   sha256 matches the Genesis Artifact pin
   `08a944b41994e7cb2da7f6acc84c4138f5275f7aee505ee171b1cf3b9c4c1c9b`
   exactly. No commit was required (the bytes are already canonical in
   `HEAD`). `.gitattributes` already pins `genesis/* text eol=lf`; this
   was a one-time editor-side regression on a pre-existing checkout.
2. `XION_API_REQUIRE_BEARER=false` is present in the operator's local
   `.env` (matches `.env.example`), but `xion-verify` runs outside the
   FastAPI lifespan and does not load `.env` implicitly. Operators
   running `xion-verify all` must export the flag (or use
   `xion-verify api-tokens --env-file .env` for the single subcommand).
   This is a documentation gap, not a doctrine gap; the verifier's
   default of `require_bearer=True` is fail-closed by design.

`NOT_YET_SEALED` rows in the `all` summary are honest residuals (no
BILLING_LEDGER yet, no SHADOW_LEDGER yet, no AO state-tip pinned, no
sealed AO mainnet identity, etc.) and not bugs.

The D3 deploy blockers are unblocked and queued for operator approval.
