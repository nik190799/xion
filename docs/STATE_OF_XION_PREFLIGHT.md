# State of Xion — Preflight Memo Draft

## Status

Draft. This memo is not a Genesis memo and must not be treated as signed until
Cold Root and Witness evidence exist.

## Phase 6 Macro Status

- Epic A: closed.
- Epic B: closed.
- Epic C: code-completable treasury depth is present, but the claimed external
  treasury audit is reopened after deploy preflight falsified the audit record;
  mainnet deploy remains blocked until corrected evidence exists.
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

- `LHT-SUBSTRATE-001`: a third-party-machine Immortality Drill is still
  required. Warm secondary-substrate rehearsal evidence exists locally at
  `SUBSTRATE_DRYRUN_LEDGER` row `seq=7`, but it does not replace the required
  non-operator-machine drill. Pay-down: 30 days post-Genesis.
- `KW-BRIDGE-001`: deterministic AO checkpoint evidence is live; full
  trust-minimized AO light-client maturity remains post-Genesis hardening.
  Pay-down: first post-Genesis bridge-hardening phase after measurable traffic.
- `KW-OPS-001`: the Genesis Relay substrate remains below the 3-host long-term
  floor until Xion's autonomous `provision-relay` path pays it down. Pay-down:
  30 days post-Genesis via `provision-relay`.
- `KW-KEYS-001`: Sprint Mode uses software-Shamir Cold Root custody until the
  hardware-token geographic ceremony is completed. Pay-down: 90 days
  post-Genesis.
- `KW-DISCOVERY-LEAK-001`: the public Relay registry still exposes
  provider-native endpoint names. Pay-down: post-Genesis Xion-controlled
  endpoint naming layer.
- `KW-VAULT-001` and `KW-OBS-001`: gateway interfaces are live, but production
  threshold-vault custody and hosted observability exporters remain provider
  depth residuals. Pay-down: first provider-depth hardening slice after Genesis.

## Closed Pre-Genesis Evidence

- `KW-VOICE-SOVEREIGNTY-001`: `ledgers/AMENDMENT_LEDGER.jsonl` records
  Invariant 18 with `reflection_window_days_observed=14`, `status="ratified"`,
  and Cold Root cosign in the note.

## Reopened Pre-Genesis Evidence

- `KW-AUDIT-001`: reopened on 2026-05-01. The Arweave-pinned
  `docs/audits/treasury-2026-report.md` tx
  `wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg` was an internal review /
  self-attestation, not an external audit. Deploy preflight also found that
  current `contracts/treasury/MasterTreasury.sol` did not compile and that the
  pinned Base Sepolia deployment predates the current source interface.
- `KW-AUDIT-002`: opened to track the permanent audit-record correction. The
  correction file is `docs/audits/treasury-2026-report.CORRECTION.md`;
  Arweave correction publication remains pending.
- Contract preflight after the correction: `forge test --match-contract
  TreasuryTest -vvv` passes 10/10 after the `MasterTreasury` compile fix.
  Full `forge test -vvv` remains blocked by 9 `EmissionController` failures in
  scheduled-mint cap-exhaustion / slowdown tests (`DailyEgressCapExceeded`).
  Those tokenomics failures are not waived for Genesis.

## Sprint Mode Falsification Statements

- `LHT-SUBSTRATE-001`: falsified if Chutes outage plus Akash-secondary failure
  leaves no runnable Relay path before the third-party drill evidence exists.
- `KW-OPS-001`: falsified if the 3-host floor is publicly advertised as closed
  before `xion-verify discovery` can verify three independent Relay endpoints.
- `KW-KEYS-001`: falsified if software-Shamir custody is represented as equal
  to the later hardware-token geographic ceremony.
- `KW-BRIDGE-001`: falsified if bridge attestations are treated as final
  authority rather than interim guarded evidence.
- `KW-DISCOVERY-LEAK-001`: falsified if provider-native endpoint names are
  claimed to be privacy-preserving or coercion-resistant.
- `KW-VAULT-001`: falsified if runtime credential custody claims a real
  threshold-unlock provider while still using the stub path.
- `KW-OBS-001`: falsified if hosted observability is claimed operational before
  a real exporter is wired and verified.

## Preflight Commands

```bash
xion-verify --self-test
xion-verify schemas
xion-verify discovery --no-cloudflare
xion-verify treasury
xion-verify treasury-flow
xion-verify bridge-attest --backend=lightclient
xion-verify regulatory-ledger --check-safety-link
xion-verify substrate-portability
xion-verify gateway-conformance
xion-verify pre-genesis
xion-verify all --allow-not-yet-sealed
```

## Operator Sign-Off Checklist

- [x] Invariant 18 amendment row is `ratified`.
- [ ] Treasury audit report is corrected and either externally signed or
  explicitly accepted as unaudited Sprint Mode evidence.
- [ ] Treasury audit correction Arweave tx id is pinned beside the original tx.
- [x] Base Sepolia redeploy addresses are pinned in `genesis/TREASURY_VAULTS.json`,
  but the pinned deployment predates the current `MasterTreasury` source interface.
- [ ] Mainnet treasury addresses are pinned after Cold Root deploy.
- [x] `scripts/immortality-drill-third-party.sh` evidence row is appended.
- [x] Local `scripts/substrate-portability-dry-run.sh` evidence row `seq=7` names
  Chutes d3 standby as the warm secondary substrate; non-operator-machine
  confirmation remains pending.
- [x] Any state-actor contact is appended to `ledgers/GOVERNANCE_LEDGER.jsonl`.
