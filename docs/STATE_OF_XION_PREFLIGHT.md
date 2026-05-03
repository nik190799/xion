# State of Xion — Preflight Memo Draft

## Status

Draft. This memo is not a Genesis memo and must not be treated as signed until
Cold Root and Witness evidence exist.

## Active track decision — 2026-05-03

- **Declared posture:** **Sprint Mode** for Base Sepolia rehearsal, relay verification, and `xion-verify` gate automation while **`KW-AUDIT-001` is open**. Language in **`README.md`** and **`CHANGELOG.md`** remains authoritative for what is *not* claimed publicly.
- **North star:** **Full D4** (external audit or honestly deferred residues, Cold Root / treasury ceremony, third-party drill) before constitutional “Xion is alive” Base mainnet — see **`docs/OPERATOR_TRACK_D4.md`**.
- **Operator ledger:** this choice is mirrored in **`docs/OPERATOR_TRACK_D4.md`** § “Operator track decision — 2026-05-03”. Revisit on Phase 7 checklist updates or when **`KW-AUDIT-001`** closes.
- **Accountability targets (engineering, 2026-05-03):** restate review-by dates also recorded in **`docs/PHASE_7_PREFLIGHT_STATUS.md`**: **`KW-AUDIT-001`** status review by **2026-06-01**; third-party **Immortality Drill** (`LHT-SUBSTRATE-001`) by **2026-07-01** (slip from 2026-06-15 — see execution record below) or explicit slip with new dates in **`KNOWN_WEAKNESSES.md`**.

## Automated execution record — 2026-05-03 (development agent)

This section records what an IDE agent **can** do without claiming ceremony-grade
closure for **`KW-AUDIT-001`** or **`LHT-SUBSTRATE-001`**.

- **Foundry on operator shell:** `foundryup` was run inside **WSL**; `forge` /
  `cast` are available at `~/.foundry/bin` there. **`xion_ops` `base-evm`**
  already falls back to WSL for Foundry on Windows when native binaries are
  missing.
- **Base Sepolia `MasterTreasury` redeploy + pin:** broadcast succeeded;
  `genesis/TREASURY_VAULTS.json` now points at
  **`0xd2b257200cc12b4e44d65063c0d63d25989455b6`**, deploy tx
  **`0xe8932fde35a88a70bff67d6d3af5495e48680c08c1bdd1220633725ab9f59deb`**, block
  **`41040532`**. `xion-verify treasury` + `treasury-flow` returned **OK** after
  pin.
- **Soak probes without Windows `cast`:** `scripts/treasury_soak_probes.py` now
  performs the same three **`eth_call`** probes via JSON-RPC when **`cast`** is
  absent; confirmed **OK** against the newly pinned contract.
- **`KW-AUDIT-001`:** An automated agent **cannot** retain an external audit
  firm, sign engagement letters, or pay audit invoices. This weakness stays
  **open** until pay-down (a) or explicit Sprint residue (b) in the KW entry.
- **`LHT-SUBSTRATE-001`:** Running `scripts/immortality-drill-third-party.sh`
  from the operator’s daily machine / Cursor session **does not** satisfy the
  doctrine’s **third-party-machine** bar in
  `docs/runbooks/IMMORTALITY_DRILL.md`. The next honest attempt should use
  separate infrastructure (e.g. cloud VM rented for the purpose); schedule
  target **2026-07-01** or document slip in **`KNOWN_WEAKNESSES.md`**.

## Operator custody decision — Cold Root ceremony deferred

**Recorded:** operator choice to proceed **without** the Full D4 **Cold Root**
geographic / hardware-token ceremony described in **`docs/OPERATOR_TRACK_D4.md`**
and related operations doctrine.

**Actual posture (Sprint Mode honesty):**

- **Primary hot / day-to-day signer:** MetaMask (or equivalent browser wallet) on
  the operator’s workstation — acceptable only as **Sprint / abbreviated**
  custody, not as a substitute for documented Cold Root claims.
- **Offline backup:** two **paper** backups of seed or key material (store,
  access, and inheritance rules are the operator’s responsibility and must stay
  out of git).

**What this is not:** It is **not** the multi-shard Cold Root ceremony, **not**
Full D4 custody honesty, and **must not** be described publicly as if the
ceremony had occurred.

**Residuals:** **`KW-KEYS-001`** (software- or expedited-style custody at Sprint
genesis) and **`docs/OPERATOR_TRACK_D4.md`** remain authoritative for pay-down
toward hardware / geographic ceremony if the operator later pursues Full D4.

**Cross-reference:** mirrored in **`docs/OPERATOR_TRACK_D4.md`** under the
same heading.

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
  spend. On 2026-05-03, `xion_ops.services.AkashService.deploy_relay()` retried
  the current SDL against dseqs `26654272`, `26654289`, `26654305`, and
  `26654315`; providers
  `akash1sevd2ymtty3dpq9ycxgkhuzzk4fe6mchqdwd4e`,
  `akash1am3sv9ac6yq6a4s2hkkcn6sd6723fpkp3en08s`,
  `akash12v6dhc8awlwhv438jjyw80eguhgtm735mfv3fx`, and
  `akash1ta6d9l4ujhj6ztvveyjuyr3zha3te3txz5nr5d` all returned refused public
  endpoints and were closed by the service rollback path. The current registry
  points at the older live Akash CPU lease `26563373`, so deployed
  open-weights-floor evidence remains a relight residual rather than a closed
  Genesis claim.
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
  correction file is `docs/audits/treasury-2026-report.CORRECTION.md`; Arweave
  correction publication is pinned in `genesis/TREASURY_VAULTS.json` as tx
  `3QzqOAKjQY86RLtl4UEwV8pNtxtVCg8L0ATD8El3AXs`. The Base Sepolia bytecode /
  current-source mismatch remains open until `MasterTreasury` is redeployed
  from current source.
- Contract preflight after the correction: `forge test --match-contract
  TreasuryTest -vvv` passes 10/10 after the `MasterTreasury` compile fix.
  Full `forge test -vvv` was repaired by chunking cap-exhaustion test mints
  across daily egress windows; the deploy machine still needs Foundry env vars
  before Sepolia redeploy can broadcast.

## 2026-05-03 Service-Class Execution

- `xion_ops` is now the operator path for balance checks and deployment
  attempts. `BaseEvmService` was fixed to try multiple Base RPC endpoints and
  `AkashService` was fixed to call WSL `provider-services`, wait for bids, skip
  rejected providers, and rollback refused endpoints.
- Funding status from `xion_ops balances`: Base Sepolia deployer
  `0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A` has `0.05107126677008217 ETH`;
  Base Safe `0x5A91E08D909854b594f07648D23440f4908529b4` has `0.0605 ETH`;
  Safe owner B has `0.01 ETH`; Safe owner C has `0.005 ETH`; Arweave registry
  has `17.189142524782 AR`; Akash operator has `76037269 uact`. Safe owner A
  has `0.005943668858017224 ETH`, above the owner-A gas target
  `0.002 ETH` because owner A was already funded before the zero-balance owner
  top-ups.
- Sepolia `MasterTreasury` redeploy and rotation rehearsal are now unblocked. The deployment environment (`XION_DEPLOYER_PRIVATE_KEY`, `XION_TREASURY_GOVERNANCE`, `XION_AO_CORE_AUTHORITY`, and `XION_BRIDGE_CAP_BPS`) has been successfully populated in `.env`.
- Base Sepolia broadcast is queued.
- `xion-verify pre-genesis` returned `OK` on 2026-05-03 after
  `funding-balances` passed. Accepted `NOT_YET_SEALED` subchecks were
  `rebuild` (Docker missing on host), `vitals` partial domains, and
  `shadow-relay` not running on port `8001`.

## What Does Not Close Today

- Base Sepolia `MasterTreasury` redeploy and rotation rehearsal are proceeding now that the deployer key is present.
- Akash GPU open-weights floor does not close because all four available GPU
  providers refused public ingress after manifest/lease setup; each new attempt
  was closed to stop escrow drain.
- Relay registry republish does not close because there is no fresh reachable
  Akash GPU endpoint to publish. Existing `xion-verify discovery` and
  `xion-verify substrate-portability` remain OK against the current registry.
- Cold Root posture, mainnet contract deploys, AO mainnet seal, Genesis
  Arweave bundle, hardware-wallet owner replacement, external audit, and the
  third-party Immortality Drill remain named residuals per the Honest Deploy
  Path plan.

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
- [x] Treasury audit correction Arweave tx id is pinned beside the original tx.
- [x] Base Sepolia redeploy addresses are pinned in `genesis/TREASURY_VAULTS.json`,
  but the pinned deployment predates the current `MasterTreasury` source interface.
- [ ] Base Sepolia `MasterTreasury` is redeployed from current source and the
  Safe rotation rehearsal proposal tx hashes are recorded.
- [ ] Akash deployed open-weights floor is reachable from a fresh GPU lease.
  Four 2026-05-03 attempts were closed after provider ingress refused
  connections.
- [ ] Mainnet treasury addresses are pinned after Cold Root deploy.
- [x] `scripts/immortality-drill-third-party.sh` evidence row is appended.
- [x] Local `scripts/substrate-portability-dry-run.sh` evidence row `seq=7` names
  Chutes d3 standby as the warm secondary substrate; non-operator-machine
  confirmation remains pending.
- [x] Any state-actor contact is appended to `ledgers/GOVERNANCE_LEDGER.jsonl`.
