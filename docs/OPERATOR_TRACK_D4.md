# Operator track — full D4 vs Sprint Mode

Genesis messaging is disciplined in [`README.md`](../README.md) and **`DEVELOPMENT_ROADMAP.md`**: unofficial “mainnet alive” chatter is rumor until manifests and ceremonies agree.

Use this file as a **living operator decision ledger** describing which path applies to the current rollout.

## Full D4 (constitutional “alive”)

Reference: **`DEVELOPMENT_ROADMAP.md`** definition **D4** and **`docs/D4_PREFLIGHT.md`**.

**Requires closure or explicit residue for**

- **`KW-AUDIT-001`**: externally signed audit tied to immutable deployable artifacts, *or* consciously accepted Sprint backlog with dates.
- **Cold Root / governance custody** doctrine per `KW-KEYS-002` / genesis credentials (no improvised warm-Safe substitutes without recording residue).
- **AO Mainnet seal** when claiming canonical AO substrate (Tier‑3 doctrine in **`docs/09-GOVERNANCE.md`**, **`docs/28-AO-CORE.md`**).
- **`genesis/GENESIS_ARTIFACT.md`** without placeholders.
- **Third-party Immortality Drill** vs `LHT-SUBSTRATE-001` residue.

## Sprint Mode compressions

Reference: **`DEVELOPMENT_ROADMAP.md`** Sprint Mode section.

Accepted trades (each must map to **`KNOWN_WEAKNESSES.md`** with pay-down commitments): shorter external audit runway, abbreviated Cold Root staging, reduced multi-host redundancy, shortened drill duration.

## Current recorded posture — 2026-05 repository default

Following the **2026-05-01** treasury correction:

- **`KW-AUDIT-001`**: **open**. Default engineering posture is **not** “we have an external audit.”
- **Default intent**: Pursue **full D4 honesty** unless the operator publishes a **`docs/STATE_OF_XION_PREFLIGHT.md`** residue entry accepting Sprint shortcuts with dates.

Updating this subsection when the operator chooses Sprint Mode avoids ambiguous public claims.

## Operator track decision — 2026-05-03 (explicit)

**Decision:** adopt **Sprint Mode** for ongoing **pre-Genesis engineering** — Sepolia rehearsal, relay liveness, verifier bundles, and operator runbooks — while **`KW-AUDIT-001` remains open**.

**What this permits:** honest D3-style rehearsal (`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`, `scripts/verify-mainnet-deploy-gates.sh`, Chutes/Akash cords) and repo maintenance without claiming an external audit or constitutional D4 “alive” status.

**What this does not permit:** representing bytecode as auditor-signed, closing **`KW-AUDIT-001`** by assertion, or public “mainnet Genesis live” messaging until **Full D4** items in the first section above close or gain dated, written residues.

**Cross-reference:** the same decision is summarized under “Active track decision” in **`docs/STATE_OF_XION_PREFLIGHT.md`**. Next review: Phase 7 preflight table refresh or upon commissioning external audit.

## Operator custody decision — Cold Root ceremony deferred

**Recorded:** operator choice to proceed **without** the Full D4 Cold Root
geographic / hardware-token ceremony.

**Sprint Mode custody in use:**

- **MetaMask** (or equivalent) as the routine signing surface on the operator
  workstation.
- **Two paper** backups of seed or key material held offline by the operator.

**Honesty requirement:** This layout is **Sprint-compressed** custody only. It
does **not** close **`KW-KEYS-001`**, does **not** satisfy the Full D4 checklist
in the first section of this file, and **must not** be marketed as Cold Root or
constitutional D4 “alive.”

**Mirror:** the same text lives under **“Operator custody decision — Cold Root
ceremony deferred”** in **`docs/STATE_OF_XION_PREFLIGHT.md`**.

## Operator execution artifacts (2026-05-03)

- **Sepolia path:** `python -m xion_ops.cli base-evm prepare-sepolia-env`, add `PRIVATE_KEY` / `XION_DEPLOYER_PRIVATE_KEY`, then `base-evm preflight-treasury --network base-sepolia` before `deploy-treasury`. Runbook: [`docs/runbooks/TREASURY_SEPOLIA_DEPLOY.md`](runbooks/TREASURY_SEPOLIA_DEPLOY.md).
- **Deploy gate bundle:** `bash scripts/verify-mainnet-deploy-gates.sh` **or** `python scripts/verify_mainnet_deploy_gates.py` (Windows-friendly when WSL lacks `xion_verify`).
- **Soak probes:** [`scripts/treasury-soak-probes.sh`](../scripts/treasury-soak-probes.sh) or `TREASURY_SOAK_PROBES=1 bash scripts/verify-mainnet-deploy-gates.sh` (or set `TREASURY_SOAK_PROBES=1` and run the Python driver if `bash` + `cast` are available).
- **Mainnet (post-gates):** [`docs/runbooks/TREASURY_BASE_MAINNET_DEPLOY.md`](runbooks/TREASURY_BASE_MAINNET_DEPLOY.md) — follow runbook with **actual** custody (here: MetaMask + paper backups; Cold Root ceremony **deferred** — see **“Operator custody decision”** above). Third-party `xion-verify` run still supports Phase 7 narrative where applicable.
- **Phase 7 checklist:** [`docs/PHASE_7_PREFLIGHT_STATUS.md`](PHASE_7_PREFLIGHT_STATUS.md) tracks external actions vs verifiers.

**Audit and key-ceremony plan (default = Full D4):** Close `KW-AUDIT-001` with an externally signed audit on the exact deployable bytecode **or** record Sprint Mode acceptance with Sepolia soak + coverage in `docs/STATE_OF_XION_PREFLIGHT.md`. Close Cold Root / Warm Safe gaps per `KW-KEYS-001`, `KW-KEYS-002`, and `docs/13-OPERATIONS.md` before claiming D4 custody honesty.
