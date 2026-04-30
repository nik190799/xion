# State of Xion — Preflight Memo Draft

## Status

Draft. This memo is not a Genesis memo and must not be treated as signed until
Cold Root and Witness evidence exist.

## Phase 6 Macro Status

- Epic A: closed.
- Epic B: closed.
- Epic C: code-completable treasury depth is in progress; external audit,
  testnet redeploy, and mainnet deploy remain one-way doors.
- Epic D: code-completable scope closed; third-party-machine drill remains an
  operator action under `LHT-SUBSTRATE-001`.
- Epic E: governance-ledger writer, intake route, runbook, and verifier
  safety-link mode are code-complete; no real state-actor row exists as of this
  draft.

## Accepted Residuals Pending External Action

- `KW-VOICE-SOVEREIGNTY-001`: Invariant 18 elapsed window and Cold Root cosign
  are not complete.
- `LHT-SUBSTRATE-001`: a third-party-machine Immortality Drill and warm
  secondary-substrate evidence are still required.
- `KW-AUDIT-001`: treasury contract audit has a scope document but no external
  auditor report yet.
- `KW-BRIDGE-001`: deterministic AO checkpoint evidence is live; full
  trust-minimized AO light-client maturity remains post-Genesis hardening.

## Preflight Commands

```bash
xion-verify --self-test
xion-verify schemas
xion-verify discovery --no-cloudflare
xion-verify treasury
xion-verify treasury-flow
xion-verify bridge-attest --backend=lightclient
xion-verify regulatory-ledger
xion-verify pre-genesis
```

## Operator Sign-Off Checklist

- Invariant 18 amendment row is `ratified`.
- Treasury audit report is committed under `docs/audits/` and anchored.
- Base Sepolia redeploy addresses are pinned in `genesis/TREASURY_VAULTS.json`.
- Mainnet treasury addresses are pinned after Cold Root deploy.
- `scripts/immortality-drill-third-party.sh` evidence row is appended.
- `scripts/substrate-portability-dry-run.sh` evidence row names a non-operator
  warm secondary substrate.
- Any state-actor contact is appended to `ledgers/GOVERNANCE_LEDGER.jsonl`.
