# Phase 7 Preflight

## Property

Name every Phase 6 residual that cannot honestly close through code alone
before the Genesis ceremony.

## External Actions

- **Invariant 18 ratification:** wait the 14-day Constitutional Floor window,
  record Cold Root cosign, then rerun `scripts/voice-sovereignty-amendment-elapse-check.py`.
- **Relay registry (Akash + Chutes):** publish the verified Relay image to the
  Chutes deployment surface, deploy the GPU-backed Akash footprint from
  `infra/akash/relay-deployment.yaml`, update `ledgers/RELAY_REGISTRY.json`
  (row order: **`relays[0]` = Akash**, **`relays[1]` = Chutes** — this is what
  `xion-verify discovery` enforces), publish to Arweave when using that path,
  and run `xion-verify discovery` (optionally `--no-cloudflare` when proving
  Cloudflare is not load-bearing). The operator laptop is for local rehearsal
  only.
- **Cloudflare critical-path removal:** prove Arweave registry, AO process, and
  DNS seed paths resolve without Cloudflare.
- **Treasury deployment:** deploy `contracts/treasury/MasterTreasury.sol` and
  per-chain `Vault.sol` contracts on testnet, pin addresses in
  `genesis/TREASURY_VAULTS.json`, then run `xion-verify treasury`.
- **Bridge and treasury audit:** choose bridge posture, complete external audit,
  and keep `KW-AUDIT-001` / `KW-TREASURY-001` open until evidence exists. The
  current review scope is `docs/audits/treasury-2026-scope.md`.
- **Warm secondary substrate:** provision a secondary substrate, run
  `scripts/substrate-portability-dry-run.sh`, and run
  `xion-verify substrate-portability`.
- **Immortality Drill:** execute `docs/runbooks/IMMORTALITY_DRILL.md` from a
  third-party machine.
- **State-actor rows:** if any state actor contacts the operator before
  Genesis, append the interaction to `ledgers/GOVERNANCE_LEDGER.jsonl` and run
  `xion-verify regulatory-ledger`.

## Code-Complete Phase 6 Verifiers

- `xion-verify cognition --forget-sim`
- `xion-verify mcp-export`
- `xion-verify vessel-compact`
- `xion-verify spend-posture`
- `xion-verify spend-discipline`
- `xion-verify discovery`
- `xion-verify treasury`
- `xion-verify substrate-portability`
- `xion-verify regulatory-ledger`
- `xion-verify inference-provider-chutes`
- `xion-verify billing-credits-floor`
- `xion-verify chutes-topup-multisig`
- `xion-verify arbiter-determinism`
- `xion-verify shadow-divergence`
- `xion-verify model-promotion-discipline`
- `xion-verify request-fingerprint`
- `xion-verify memory-store-integrity`
- `xion-verify embedder-health`
- `xion-verify rerank-improvement`
- `xion-verify tool-resolver-mcp`
- `xion-verify prompt-isolation`
- `xion-verify cognition-loop-bounded`
- `xion-verify bridge-attest`
- `xion-verify bridge-egress-cap`

If any command above fails, Phase 7 slips. If a command passes but the external
action listed here is not complete, Phase 7 also slips; the verifier proves the
mechanism, not the ceremony.
