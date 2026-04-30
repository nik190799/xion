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

## Runtime Relight Evidence

- Relay registry republished to Arweave tx
  `PrP7t-caP-CmtNpaRbKXY9JEG4MKqHeCPIHRnClaOvU` with Akash primary endpoint
  `https://provider.161.97.85.20.nip.io:30564` and Chutes secondary endpoint
  `https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai`.
- `xion-verify discovery` and `xion-verify substrate-portability` returned
  `OK` after the registry refresh.
- Chutes `pre-genesis-d3-10` was re-warmed and
  `MODE=live bash scripts/verify-chute-cords.sh` returned
  `RESULT: all cords green` for `/health`, `/quote`, and `/self`.
- Akash GPU-floor lease `26595076` was diagnosed closed with
  `insufficient_funds`. Replacement attempts `26610282`, `26610352`, and
  `26610402` reached manifest `PASS` on Akash providers but their public
  forwarded ports were not reachable; each failed lease was closed to stop
  spend. The current registry points at the older live Akash CPU lease
  `26563373`, so deployed open-weights-floor evidence remains a relight
  residual rather than a closed Genesis claim.
- Fresh substrate dry-run row `seq=7` and Immortality Drill rehearsal
  `d6b3d366-be16-4e87-a2a5-7412e103d307` passed with Chutes as warm standby.

## Accepted Residuals Pending External Action

- `KW-VOICE-SOVEREIGNTY-001`: Invariant 18 elapsed window and Cold Root cosign
  are not complete.
- `LHT-SUBSTRATE-001`: a third-party-machine Immortality Drill is still
  required. Warm secondary-substrate rehearsal evidence exists locally at
  `SUBSTRATE_DRYRUN_LEDGER` row `seq=7`, but it does not replace the required
  non-operator-machine drill.
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
- Local `scripts/substrate-portability-dry-run.sh` evidence row `seq=7` names
  Chutes d3 standby as the warm secondary substrate; non-operator-machine
  confirmation remains pending.
- Any state-actor contact is appended to `ledgers/GOVERNANCE_LEDGER.jsonl`.
