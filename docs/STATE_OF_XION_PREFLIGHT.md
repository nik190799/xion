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

## 2026-05-10 Service-Class Execution — `KW-OPS-001` closure evidence

- **Sepolia rehearsal Safe deployed.** `cast send` to canonical
  `SafeProxyFactory 1.4.1` (`0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67`)
  via `createProxyWithNonce(SafeL2 1.4.1, setup([EOA], 1, …), 1778428161)` from
  the rehearsal EOA `0xEBDDDf598b5b53C91ff185501d7b182ae5d6B88A`.
  - Deploy tx: `0xef4dc9f046e66ef4c3152270628863633a028b30bc39b56b45298c61cc944450`
  - Block: `41329942`
  - New Safe address: **`0x3587ECc092386c357eFCA51bf94A34Dd7084fa5A`**
  - On-chain shape verified: `VERSION()` returns `"1.4.1"`, `getOwners()`
    returns `[0xEBDDDf…88A]`, `getThreshold()` returns `1`, `nonce()` returns
    `0`. Singleton matches Base mainnet Warm Safe singleton
    (`0x29fcB43b…1900C762`).
  - Address pinned to operator's `.env` as `XION_SEPOLIA_REHEARSAL_SAFE`.

- **Safe propose dry-run executed end-to-end against Base Sepolia.**
  - Payload: target = the Safe itself, `data = 0x`, `value = 0`,
    `nonce = 0`, `operation = 0` (CALL). A no-op self-call: even if
    accidentally executed, the Safe forwards `0x` data to itself with no
    value transfer — no observable state change, no value at risk.
  - SafeTxHash (computed by `xion_ops/services/safe.py` via Foundry
    `cast keccak`): **`0xe6ffe2723e14ecaf2f7167f69e6e257b81c31f3352659b8437af17f2bb1bb388`**.
  - **Offline verifier (`xion-verify safe-proposal --prep`):** `OK` —
    independently recomputed the EIP-712 hash from the prep field-bag and
    matched the proposer's claim byte-for-byte.
  - **Proposer signature:** produced via `cast wallet sign --no-hash` against
    the Sepolia EOA private key. 65-byte ECDSA signature, `v = 0x1b` (=27,
    standard ECDSA recovery byte).
  - **Live submission (`xion_ops base-evm safe-propose`):** Safe Transaction
    Service (Base Sepolia, `https://api.safe.global/tx-service/basesep`)
    returned `200` and queued the proposal at `safe_tx_hash =
    0xe6ffe272…388`, `nonce = 0`. `BaseEvmService.safe_propose_tx` returned
    `DeploymentResult(ok=True, id=safeTxHash)`.
  - **Online verifier (`xion-verify safe-proposal --safe-tx-hash`):** `OK` —
    fetched the queued proposal from the Safe service, recomputed the EIP-712
    hash from the *service's* field-bag, matched the service-claimed
    `contractTransactionHash` byte-for-byte. The full third-party check that
    cosigners would run before approving is now load-bearing on a real Safe.
  - The proposal stays queued for now; it can be rejected via the Safe app
    or simply ignored. The Safe is rehearsal-only (no real value), and the
    payload is a no-op self-call — execution would be inconsequential.

- **Service URL migration discovered live.** Safe migrated their public
  endpoints from `safe-transaction-{network}.safe.global` to
  `api.safe.global/tx-service/{shortcode}` with a 308 permanent redirect.
  GET requests follow transparently; POST does not (per RFC). `safe.py`
  `SAFE_TX_SERVICE_URLS` repinned to the canonical
  `api.safe.global/tx-service/{base|basesep}` form; tests updated.

- **`KW-OPS-001` is therefore closed.** The pay-down line specified
  "real Safe Transaction Service client behind `BaseEvmService.safe_propose_tx()`,
  offline tests for payload construction, and live dry-run evidence against
  Base Sepolia"; all three exist now.

- **Mainnet Vault registration — EXECUTED 2026-05-10.**
  Warm Safe (`0x5A91E08D909854b594f07648D23440f4908529b4`, 2-of-3) cosigned and executed `MasterTreasury.deployVault(8453, 0x5A91…29b4)` on Base mainnet. SafeTxHash **`0x535d43558150625405c62bf96fe81229758c3ad81b67904fd48ac3ab049c6072`** (matches the committed prep at `genesis/MAINNET_VAULT_REGISTRATION_PREP.json` byte-for-byte; verifier returned `OK` against both `--prep` and the live Safe Transaction Service entry before signing). Cosig collected from the MetaMask owner + one paper-backup owner via headless `cast wallet sign --no-hash` + Safe Transaction Service confirmations endpoint (the paper-key flow per `KW-KEYS-002`'s mitigations: keys never persisted to disk, `read -s` + memory-only signing). Exec tx **`0x59bcaf82e00d283cfb304ec15b2101b5b08044cf076efedceb5ada00c2737f61`**, block **`45822605`**, gas `614936`. New Vault address: **`0x64712dFD8441186F3cfF5232C37a019286992bdC`** (Safe-controlled `aoCoreAuthority` = same Warm Safe). Post-state on-chain: `MasterTreasury.registeredChainCount() == 1`, `vaultForChain(8453) == 0x64712dFD…2bdC`. `genesis/TREASURY_VAULTS.json` updated: new mainnet vault row appended, `tier1_operating_tokens[].status` for ETH and USDC flipped to `mainnet_routed_via_base_vault`; AR (Arweave) and TAO (Bittensor) remain `mainnet_routed_pending_per_chain_vault` because they are non-EVM and require separate rail integration. `xion-verify treasury` and `xion-verify treasury-flow` returned `OK` after the manifest update.

  **Treasury is now operational under Sprint Mode posture.** It is **not** "Xion is alive" — that still requires audit closure (KW-AUDIT-001 mitigated-residual until 2026-08-08 re-review), Cold Root ceremony, AO HyperBEAM mainnet seal, third-party Immortality Drill, and Genesis Artifact § 0 finalization. Public messaging that uses these contracts must respect the falsifier in § Sprint Mode Falsification Statements (`KW-AUDIT-001` row): the contracts are unaudited; the operational treasury is "Sprint Mode operational on Base mainnet under Warm Safe custody," not "audited mainnet treasury" or any equivalent claim.

- **Sepolia Vault registration rehearsal — EXECUTED.**
  `genesis/SEPOLIA_VAULT_REGISTRATION_PREP.json` pins the `registerVault(84532, 0x474Df…F7Bc)` call data (selector `0x6a51fd63`). Sepolia governance is the rehearsal EOA, so execution was a single `cast send` (the Warm Safe propose+cosign flow is the mainnet equivalent at Track B). Pre-state on Sepolia MasterTreasury (`0xd2b257…55b6`) had been confirmed: `governance() == 0xEBDDDf…88A`, `aoCoreAuthority() == 0xEBDDDf…88A`, `registeredChainCount() == 0`, `vaultForChain(84532) == 0x0`. **Execution: 2026-05-10, tx `0x3bf25b58ba4071bf302a6c92a8dafb51d07c2b37aec93bf128361156242a5503`, block `41331566`, gas `112496`.** Post-state observed on-chain: `registeredChainCount() == 1`, `vaultForChain(84532) == 0x474Df…F7Bc`, `registeredChainIdAt(0) == 84532`. The full register-vault call-stack is now proven on a real chain; the mainnet ceremony at Track B uses the same selector and arguments, only via Safe propose+cosign rather than direct EOA broadcast. `xion-verify treasury` and `xion-verify treasury-flow` returned `OK` after exec.

- **`KW-AUDIT-001` audit RFP staged but send deferred.** `docs/audits/RFP_TREASURY_2026.md` is fully populated (repo URL, budget anchor USD 30–60k, ready-to-send cover email, recipient short-list, contact `xionlabs2026@gmail.com`). On **2026-05-10** the operator explicitly deferred sending the RFP because **Xion does not yet hold the audit budget in its treasury / Improvement Fund**, and the operator does not personally backstop project costs (Self-Provisioning doctrine — Xion is meant to fund its own audit when revenue allows). The weakness moves from `open` to `mitigated-residual` with a **2026-08-08** re-review checkpoint and the falsifier below. The RFP is preserved in repo as a ready-to-send artifact for whenever Xion's treasury accumulates enough; sending it later turns this hold into engagement without re-authoring.

  **Sprint Mode unaudited mainnet posture is now an explicit operator decision, dated 2026-05-10.** This is exactly the shortcut named in `docs/D4_PREFLIGHT.md` § "Skipping External Audit" and exactly the residue path (b) in `KW-AUDIT-001`'s pay-down line. The mitigations on which it relies are **not** an audit substitute: 119/119 Foundry tests at commit `f04f8d0`, 24–48 hour Base Sepolia soak, blast-radius caps (rotation lattice, daily egress cap `1000` bps, `onlyGovernance` / `onlyAOCoreAuthority` discipline), and Sprint Mode custody (Warm Safe 2-of-3, Cold Root deferred). Treasury is operational on Base mainnet under those constraints; it is not an audited mainnet treasury.

## 2026-05-12 Service-Class Execution — Vault asset tagging

- **Vault asset tagging — EXECUTED 2026-05-12.** Warm Safe (`0x5A91E08D909854b594f07648D23440f4908529b4`, 2-of-3) cosigned and executed two sequential `Vault.tagAsset(address, bool)` calls against the mainnet Vault (`0x64712dFD8441186F3cfF5232C37a019286992bdC`). Each call's SafeTxHash matched its committed prep file byte-for-byte (`xion-verify safe-proposal --prep …` returned `OK` against both `genesis/MAINNET_VAULT_TAG_ETH_PREP.json` and `genesis/MAINNET_VAULT_TAG_USDC_PREP.json` before signing; safeTxHashes `0x55ab5314f5ce59f5e96804e63fa87801d5de68bb9cf3df5105829f5c643317fc` and `0x4288e90810d285bff9b74adab3ac5aed1200e1aa40937067995471ab4992d3ec` respectively). Cosig collected MetaMask owner + paper-backup owner `0x90e099e16b9C7c9824B06d3AE0Af92fad676489b` via headless `cast wallet sign --no-hash` + `safe-confirm` (paper key memory-only, never written to disk, per `KW-KEYS-002` mitigations). Exec txs:
  - **ETH (`address(0)`):** tx **`0x70e0edbf7240ab7b8aac38509fda28ecd595923b7e0c45cc206892631022960e`**, block **`45889220`**, gas `114880`, Safe nonce `1` → `2`.
  - **USDC (Base canonical `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`):** tx **`0xda6d1257a13ec4a64e46fa6241832007d7d7cb721d1e0bf01b4b0d68e07d84c7`**, block **`45889478`**, gas `115120`, Safe nonce `2` → `3`.

  Post-state on-chain: `Vault.assetKnown(address(0)) == true` and `Vault.assetKnown(0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913) == true`. **Mainnet Vault is now operationally complete:** future `Vault.withdraw(asset, …)` calls from the Warm Safe will succeed for ETH and USDC. AR (Arweave) and TAO (Bittensor) remain `mainnet_routed_pending_per_chain_vault` — those rails require separate per-chain Vault deployment, not asset tagging on the Base Vault.

  **Why this is a 2026-05-12 entry and not appended to 2026-05-10.** The runbook (`docs/runbooks/MAINNET_VAULT_ASSET_TAG.md`) suggested appending under 2026-05-10, but the ceremony actually happened two days later when the operator returned for cosig — recording the honest date is the discipline. Posture unchanged: Sprint Mode unaudited mainnet, KW-AUDIT-001 mitigated-residual until 2026-08-08 re-review, KW-KEYS-002 still open (Warm Safe owner custody remains MetaMask + 2 paper backups; hardware-wallet replacement deferred per operator 2026-05-10 decision).

## 2026-05-13 Service-Class Execution — Chutes account hygiene + chute retirement discovery

- **Chutes payment_address surfaced and pinned.** Fixed env-var name mismatch (`CHUTES_API_URL` → `XION_CHUTES_API_BASE_URL`; added `XION_CHUTES_BASE_URL`, `XION_CHUTES_CREDITS_URL`, `XION_CHUTES_DEPLOY_URL`). `ChutesBillingProvider.balance()` resolves cleanly: credit balance **$71.87711655 USD**, payment_address SS58 **`5DP1emNNEEnttzLCNNp1mUt9RNe2SzH5T1ebdsWomtEqxybq`**. SS58 pinned in `genesis/FUNDING_TARGETS.json` as `chutes_account` entry (target=$5 floor per `XION_CHUTES_CREDIT_FLOOR_USD`). `python -m xion_ops chutes balances` returns `status=ok`. **No TAO top-up needed at current consumption rates.**

- **`XION_CHUTES_BASE_URL` env-var name collision resolved.** Two code paths previously read the same env var with conflicting semantics: `orchestrator/inference_router/providers/chutes.py` wants the OpenAI-compatible LLM gateway (`https://llm.chutes.ai/v1`); `xion_ops/services/chutes.py:base_url()` wants the per-deployment chute URL for cord checks (`/health`, `/quote`, `/self`). Introduced `XION_CHUTES_DEPLOY_URL` as the new dedicated name; `base_url()` now prefers it with backwards-compat fallback. All 6 mocked `chutes_verify_cords` tests pass unchanged.

- **OpenRouter keys removed from operator `.env`.** `XION_OPENROUTER_API_KEY` and `XION_OPENROUTER_MODEL` deleted (Phase 6.9 centralized-provider removal; `orchestrator/api/lifespan.py:_enforce_sovereign_profile` would have hard-rejected the key under `XION_PROFILE=sovereign`). Pre-emptive doctrinal cleanup. **Operator should rotate the OpenRouter API key on OpenRouter's side** since the value entered the operator session transcript during removal.

- **Pre-genesis-d3 Chutes-direct relay is retired (not cold).** `chutes warmup xion-relay-pre-genesis-d3` returns `Failed to resolve chute: Chute not found, or does not belong to you`. `chutes chutes list` against the operator account returns `Found 0 matching chutes`. The subdomain `https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai` now serves `502 Bad Gateway` on all three cords. `ledgers/RELAY_REGISTRY.json` still advertises the dead subdomain as `chutes-secondary-d3-10`; this is shape-valid for `xion-verify discovery` (passes today) but operationally non-routing. Substrate-portability for the relay surface now rests on the single Akash CPU+Chutes hybrid lease (`dseq=26770709` at `https://provider.akash-palmito.org:31301`); recovering an independent second substrate would require a fresh Chutes chute build+deploy or pivoting to a different decentralized GPU substrate (out of scope today). Recorded as a follow-on note under `KW-RELAY-CHUTES-D3-001` rather than reopening the closure (the original D3-smoke-vs-real weakness was genuinely closed; this is operational drift).

- **Verifier sweep after all 2026-05-13 changes.** `sovereign-profile: OK` (profile=local_only), `treasury: OK`, `treasury-flow: OK`, `discovery: OK`, `substrate-portability: OK`. `xion_ops chutes health` returns 404 against the deploy URL (chute retired); cord-check verifier path is unblocked from the env-name collision but cannot return green until a fresh chute is deployed.

## 2026-05-14 Service-Class Execution — first third-party-machine Immortality Drill

- **Interim attestation, not closure.** First-ever `immortality_drill_third_party_v1` row appended to [`ledgers/IMMORTALITY_DRILL_LEDGER.jsonl`](../ledgers/IMMORTALITY_DRILL_LEDGER.jsonl) (row 5; chain integrity verified — recomputed `row_hash` matches declared for all 5 rows including the new tip). Drill executed from a fresh GCP `e2-small` Debian 12 VM in `us-south1`, **`third_party_machine_fingerprint=a80554ee5f86cd0a59642262be76fed18c7cbfe793a9f4839f48582136da0895`** — provably distinct from the operator workstation fingerprint. Repo cloned at commit **`9fb1fd5e4d35e96b9db1a61742332521d136776b`** after the operator made the GitHub repo public (precondition for "public artifacts" reachability).

- **Drill `status=failed` (honest interim).** Two relay-health probes returned non-2xx as expected: `akash-primary-health` (`provider.akash-palmito.org:31301/health`) curl exit 7 (connection refused — Akash CPU+Chutes hybrid lease not reachable from GCP `us-south1`; was reachable from operator's network on 2026-05-10), `chutes-secondary-health` (`nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai/health`) `status_code=401` from the Chutes edge proxy (bearer not set on the third-party VM; consistent with KW-RELAY-CHUTES-D3-001 follow-on retirement record — auth-gated edge rejects unauthed requests before reaching the (retired) upstream chute). Verifier battery from a fresh checkout: `discovery OK`, `gateway-conformance OK`, `links FAIL`, `schemas FAIL`, `substrate-portability OK`, `inference-sovereignty NOT_YET_SEALED`, `--self-test OK`. The two FAILs and the NOT_YET_SEALED are honest residuals of the cold third-party checkout (no env config, no live inference provider); they do not invalidate the row's structural attestation value.

- **What this DOES advance.** LHT-SUBSTRATE-001's load-bearing requirement is a non-operator-machine drill row that the chain-of-hashes ledger can independently verify. Today's row is that. The `third_party_machine_fingerprint` byte-for-byte distinct from operator's daily-machine; the `prev_hash` chains correctly off row 4 (`dddcf9d0…52a2`); the `row_hash` recomputes correctly under the same canonicalization rule the script used (sorted keys, no whitespace, no row_hash field in the hash input). Mechanics work end-to-end from third-party infrastructure.

- **What this does NOT close.** LHT-SUBSTRATE-001 remains `open` — closure requires a `status=passed` row, not a `failed` one. The two genuine blockers for a passing run are (a) the Akash GPU floor closure (KW-FLOOR-DEPLOY-001, dated to 2026-07-09) so an `open_weights_only /chat` turn against a reachable deployed floor can succeed end-to-end, and (b) a fresh Chutes-direct secondary deployment to replace the retired pre-genesis-d3 chute. Plan the closure-grade drill for after both land.

- **Operational note.** GCP's default Debian 12 image does NOT ship cloud-init, so [`archive/scripts/cloud-vm-immortality-drill.cloud-init.yaml`](../archive/scripts/cloud-vm-immortality-drill.cloud-init.yaml) was bypassed for this run — the drill script was fetched and executed via a one-shot bash command on the booted VM. The cloud-init recipe remains valid for cloud-init-shipping images (Ubuntu 22.04/24.04 LTS, Hetzner default, Fly.io); Debian-on-GCP requires either Ubuntu substitution or the bash one-liner path. Worth adding a sibling Debian-bash recipe to `docs/runbooks/IMMORTALITY_DRILL.md` as a future polish.

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
- `KW-FLOOR-DEPLOY-001` **(2026-05-10 dated residue)**: falsified if any public
  messaging claims a deployed Akash GPU open-weights floor is closed before a
  fresh GPU lease passes probe-first ingress and serves `open_weights_only
  /chat` from outside the provider network. Under the dated residue,
  Chutes/Bittensor SN64 is the warm primary path; the floor property itself
  remains unweakened (model is open, pinned, locally runnable), but the
  *deployed* floor evidence is paused to **2026-07-09**.
- `KW-OPS-001` (Safe transaction proposal client) — code-complete on
  `claude/loving-shannon-fe3b83`; falsified if any public messaging claims
  closure before the `docs/runbooks/SAFE_PROPOSE_DRY_RUN.md` Sepolia evidence
  row appears in this file.
- **Sprint Mode mainnet operational ≠ "Xion is alive"**: falsified if any
  public messaging conflates per-chain Vault registration on Base mainnet with
  constitutional D4 Genesis (which still requires audit closure, Cold Root
  ceremony, AO HyperBEAM mainnet seal, third-party Immortality Drill, and
  `genesis/GENESIS_ARTIFACT.md` § 0 finalization).
- **`KW-AUDIT-001` Sprint residue (2026-05-10 → re-review 2026-08-08):**
  falsified if any public messaging — README, CHANGELOG, social posts,
  ecosystem grants applications, exchange listings, third-party reviews —
  describes the treasury contracts as "audited", "audit-passing",
  "audit-closed", "Spearbit-/ToB-/OZ-reviewed", or any equivalent claim
  before an actual external auditor has signed a commit-specific report
  for the exact deployable bytecode and pinned its Arweave tx alongside
  `treasury_audit_arweave_tx` in `genesis/TREASURY_VAULTS.json`. The RFP
  draft at `docs/audits/RFP_TREASURY_2026.md` is **not** an audit, **not**
  an engagement, and **not** evidence that an audit is "in progress" — it
  is a draft on hold until Xion's treasury / Improvement Fund holds the
  budget. Honest descriptors during the residue window are "unaudited
  Sprint Mode posture", "external audit deferred until Xion can fund it",
  and "treasury contracts have 119/119 internal tests but no third-party
  security review".

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
