# Phase 7 preflight — status ledger (operator-maintained)

**Purpose:** Track each **external** obligation in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md). Verifiers prove mechanisms; this table records ceremony and infrastructure reality.

**Last reviewed:** 2026-05-03 (plan execution: Sprint Mode recorded in `docs/OPERATOR_TRACK_D4.md` / `docs/STATE_OF_XION_PREFLIGHT.md`; gate bundle + Chutes cords re-verified as operator reruns). Next operator update: after Sepolia soak completion or mainnet rehearsal.

| External action | Status | Notes / residual |
|-----------------|--------|------------------|
| Invariant 18 ratification — 14-day window, Cold Root cosign, `voice-sovereignty-amendment-elapse-check.py` | Closed | Amendment row is `ratified` with Cold Root cosign. |
| Chutes Relay + `ledgers/RELAY_REGISTRY.json` + `xion-verify discovery` | Partial | See [STATE_OF_XION_TESTNET.md](STATE_OF_XION_TESTNET.md); Akash CPU row relight, fresh deploy attempts blocked or closed 2026-05-03. |
| Cloudflare removal from critical path (`discovery --no-cloudflare`) | Verify per gate script | `verify-mainnet-deploy-gates.sh` runs `discovery --no-cloudflare`. |
| Treasury testnet deploy + pin + `xion-verify treasury` | Queued | `genesis/TREASURY_VAULTS.json` has Base Sepolia addresses. Redeploy broadcast is queued pending operator approval. |
| Bridge / treasury external audit (`KW-AUDIT-001`) | Open | Sprint path: Sepolia soak + Foundry evidence; Full D4: commit-signed audit for deployable bytecode. |
| Warm secondary substrate + `xion-verify substrate-portability` | Operator-dependent | Re-run after relay/substrate changes. |
| Third-party Immortality Drill | Open | `LHT-SUBSTRATE-001` / D4 preflight. |
| State-actor rows + `xion-verify regulatory-ledger` | Operator-dependent | [STATE_ACTOR_INTAKE.md](runbooks/STATE_ACTOR_INTAKE.md). |

**Code-complete Phase 6 verifier list** lives in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md); treat any FAIL as a Phase 7 slip until fixed or honestly deferred with dates in `KNOWN_WEAKNESSES.md`.

**Mainnet checklist:** [TREASURY_BASE_MAINNET_DEPLOY.md](runbooks/TREASURY_BASE_MAINNET_DEPLOY.md), [TREASURY_SEPOLIA_DEPLOY.md](runbooks/TREASURY_SEPOLIA_DEPLOY.md), [D4_PREFLIGHT.md](D4_PREFLIGHT.md).
