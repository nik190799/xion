# Phase 7 preflight — status ledger (operator-maintained)

**Purpose:** Track each **external** obligation in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md). Verifiers prove mechanisms; this table records ceremony and infrastructure reality.

**Last reviewed:** 2026-05-03 (Sepolia **`MasterTreasury`** redeploy + manifest pin; `python scripts/verify_mainnet_deploy_gates.py` core steps **OK**; with **`TREASURY_SOAK_PROBES=1`**, **`treasury_soak_probes.py`** uses **`cast`** when on PATH else **JSON-RPC `eth_call`**; Unix may use **`treasury-soak-probes.sh`**). Next: external audit (`KW-AUDIT-001`), non-operator Immortality Drill (**2026-07-01** target), mainnet rehearsal when ready.

| External action | Status | Notes / residual |
|-----------------|--------|------------------|
| Invariant 18 ratification — 14-day window, Cold Root cosign, `voice-sovereignty-amendment-elapse-check.py` | Closed | Amendment row is `ratified` with Cold Root cosign. |
| Chutes Relay + `ledgers/RELAY_REGISTRY.json` + `xion-verify discovery` | Partial | See [STATE_OF_XION_TESTNET.md](STATE_OF_XION_TESTNET.md); Akash CPU row relight, fresh deploy attempts blocked or closed 2026-05-03. Verifier **OK** on latest pinned registry. |
| Cloudflare removal from critical path (`discovery --no-cloudflare`) | Closed (gate) | `scripts/verify_mainnet_deploy_gates.py` runs `discovery --no-cloudflare` in the default bundle. |
| Treasury testnet deploy + pin + `xion-verify treasury` | Partial | **2026-05-03** redeploy + pin: `master_treasury` **`0xd2b257200cc12b4e44d65063c0d63d25989455b6`**, tx **`0xe8932fde35a88a70bff67d6d3af5495e48680c08c1bdd1220633725ab9f59deb`**, block **`41040532`**. Verifiers **OK**. Soak: `treasury_soak_probes.py` JSON-RPC or `cast`. |
| Bridge / treasury external audit (`KW-AUDIT-001`) | Open | Sprint path: Sepolia soak + Foundry evidence; Full D4: commit-signed audit for deployable bytecode. **Next review target:** 2026-06-01 (commission audit or extend dated Sprint residue in `docs/STATE_OF_XION_PREFLIGHT.md`). |
| Warm secondary substrate + `xion-verify substrate-portability` | Operator-dependent | Re-run after relay/substrate changes; gate bundle **OK** on latest dry-run ledger. |
| Third-party Immortality Drill | Open | `LHT-SUBSTRATE-001` / D4 preflight. **Schedule target:** non-operator-machine run per `docs/runbooks/IMMORTALITY_DRILL.md` by **2026-07-01** (slip documented in `docs/STATE_OF_XION_PREFLIGHT.md`) or new slip in `KNOWN_WEAKNESSES.md`. |
| State-actor rows + `xion-verify regulatory-ledger` | Operator-dependent | [STATE_ACTOR_INTAKE.md](runbooks/STATE_ACTOR_INTAKE.md). |

**Code-complete Phase 6 verifier list** lives in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md); treat any FAIL as a Phase 7 slip until fixed or honestly deferred with dates in `KNOWN_WEAKNESSES.md`.

**Mainnet checklist:** [TREASURY_BASE_MAINNET_DEPLOY.md](runbooks/TREASURY_BASE_MAINNET_DEPLOY.md), [TREASURY_SEPOLIA_DEPLOY.md](runbooks/TREASURY_SEPOLIA_DEPLOY.md), [D4_PREFLIGHT.md](D4_PREFLIGHT.md).
