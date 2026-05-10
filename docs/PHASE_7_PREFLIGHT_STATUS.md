# Phase 7 preflight — status ledger (operator-maintained)

**Purpose:** Track each **external** obligation in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md). Verifiers prove mechanisms; this table records ceremony and infrastructure reality.

**Last reviewed:** 2026-05-10 (Safe propose client wired in `xion_ops`; `xion-verify safe-proposal` live; mainnet `MasterTreasury.deployVault(8453, Warm Safe)` prep payload committed at `genesis/MAINNET_VAULT_REGISTRATION_PREP.json` and verifier-passed; audit RFP drafted; hardware-wallet swap runbook drafted; `KW-FLOOR-DEPLOY-001` placed in dated residue to 2026-07-09). Next: operator Sepolia A5 dry-run (closes `KW-OPS-001`), audit RFP send, hardware-wallet swap, mainnet Vault cosign + exec.

| External action | Status | Notes / residual |
|-----------------|--------|------------------|
| Invariant 18 ratification — 14-day window, Cold Root cosign, `voice-sovereignty-amendment-elapse-check.py` | Closed | Amendment row is `ratified` with Cold Root cosign. |
| Chutes Relay + `ledgers/RELAY_REGISTRY.json` + `xion-verify discovery` | Partial | See [STATE_OF_XION_TESTNET.md](STATE_OF_XION_TESTNET.md); Akash GPU floor in dated residue to 2026-07-09 (`KW-FLOOR-DEPLOY-001`); Chutes/Bittensor SN64 warm primary; verifier **OK** on latest pinned registry. |
| Cloudflare removal from critical path (`discovery --no-cloudflare`) | Closed (gate) | `scripts/verify_mainnet_deploy_gates.py` runs `discovery --no-cloudflare` in the default bundle. |
| Treasury testnet deploy + pin + `xion-verify treasury` | Partial | **2026-05-03** redeploy + pin: `master_treasury` **`0xd2b257200cc12b4e44d65063c0d63d25989455b6`**, tx **`0xe8932fde35a88a70bff67d6d3af5495e48680c08c1bdd1220633725ab9f59deb`**, block **`41040532`**. Verifiers **OK**. Soak: `treasury_soak_probes.py` JSON-RPC or `cast`. |
| Treasury mainnet deploy + per-chain Vault registration + `xion-verify treasury` | Mainnet pin partial — Vault registration prep ready, awaiting cosigners | `MasterTreasury` mainnet at `0xbf5407745cf22b88c46b55037e26156a0e78fd7f` (block 45530934). Vault prep at [`genesis/MAINNET_VAULT_REGISTRATION_PREP.json`](../genesis/MAINNET_VAULT_REGISTRATION_PREP.json), runbook [`docs/runbooks/MAINNET_VAULT_REGISTRATION.md`](runbooks/MAINNET_VAULT_REGISTRATION.md), independently verified by `xion-verify safe-proposal --prep`. Cosigner threshold (2-of-3) and exec are operator-side. |
| Safe transaction proposal client (`KW-OPS-001`) | Code-complete; closure pending Sepolia dry-run | `xion_ops/services/safe.py` + `BaseEvmService.safe_propose_tx` wired; offline tests + verifier (`xion-verify safe-proposal`) live; runbook [`docs/runbooks/SAFE_PROPOSE_DRY_RUN.md`](runbooks/SAFE_PROPOSE_DRY_RUN.md) names the operator-side step that produces the closure evidence row. |
| Warm Safe owner custody (`KW-KEYS-002`) | Open | Replace MetaMask owner with hardware wallet by **2026-05-31** per [`docs/runbooks/SAFE_OWNER_HARDWARE_REPLACEMENT.md`](runbooks/SAFE_OWNER_HARDWARE_REPLACEMENT.md). |
| Bridge / treasury external audit (`KW-AUDIT-001`) | Open | RFP drafted at [`docs/audits/RFP_TREASURY_2026.md`](audits/RFP_TREASURY_2026.md); operator sends to short-listed firms by **2026-05-15**. Engagement target **2026-06-01**, final report target **2026-08-01**. |
| Warm secondary substrate + `xion-verify substrate-portability` | Operator-dependent | Re-run after relay/substrate changes; gate bundle **OK** on latest dry-run ledger. |
| Third-party Immortality Drill | Open | `LHT-SUBSTRATE-001` / D4 preflight. **Schedule target:** non-operator-machine run per `docs/runbooks/IMMORTALITY_DRILL.md` by **2026-07-01** (slip documented in `docs/STATE_OF_XION_PREFLIGHT.md`) or new slip in `KNOWN_WEAKNESSES.md`. |
| State-actor rows + `xion-verify regulatory-ledger` | Operator-dependent | [STATE_ACTOR_INTAKE.md](runbooks/STATE_ACTOR_INTAKE.md). |

**Code-complete Phase 6 verifier list** lives in [PHASE_7_PREFLIGHT.md](PHASE_7_PREFLIGHT.md); treat any FAIL as a Phase 7 slip until fixed or honestly deferred with dates in `KNOWN_WEAKNESSES.md`.

**Mainnet checklist:** [TREASURY_BASE_MAINNET_DEPLOY.md](runbooks/TREASURY_BASE_MAINNET_DEPLOY.md), [TREASURY_SEPOLIA_DEPLOY.md](runbooks/TREASURY_SEPOLIA_DEPLOY.md), [D4_PREFLIGHT.md](D4_PREFLIGHT.md).
