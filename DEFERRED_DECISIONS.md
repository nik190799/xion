# DEFERRED DECISIONS

Architectural and operational questions surfaced but not yet decided. Each entry has a **default-if-not-decided** so the agent can proceed under the default without re-surfacing the question. When the operator decides, mark `Resolved: YYYY-MM-DD` with a one-line outcome; do not delete resolved entries (they are evidence of decision history).

Convention: `DD-NNN` numbering, monotonic. Operator-facing summary at the top; agent-facing default at the bottom of each entry.

---

## Open

*(only DD-003 remains open — operator-only decision)*

### DD-003 — KW-KEYS-002 hardware-wallet brand

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** KW-KEYS-002 target 2026-05-31 (warm Safe hardware-wallet owner swap). Operator declined this sprint due to no purchase time. When ready, brand selection matters for setup and seed handling.

**Options:**
- (a) Ledger (Nano S Plus / Nano X / Stax) — widely supported, Safe-native UI, well-documented
- (b) Trezor (Safe 3 / Safe 5) — open-source firmware, Safe support via WalletConnect
- (c) GridPlus Lattice1 — air-gapped option, larger device, deepest expert tier
- (d) Keystone / OneKey / other QR-air-gapped — fully offline signing

**Default if not decided:** none — KW-KEYS-002 stays open until operator decides + purchases.

**Owner:** Operator (purchase + setup)
**Blocks:** KW-KEYS-002 closure. Does not block current sprint work.

**Agent note:** This DD is **deliberately left open even under broad delegation 2026-05-15**. Hardware-wallet brand is a personal-preference + threat-model decision that should align with the operator's own air-gap habits, travel patterns, multisig recovery plan, and risk tolerance. Agent will not pick; defaults stay null.

---

## Resolved

### DD-001 — Warm-secondary substrate slot for LHT-SUBSTRATE-001

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** Closure-grade Immortality Drill requires `relays[0]` (primary) AND `relays[1]` (secondary) both healthy. With Chutes as new `relays[0]`, what fills `relays[1]`? See [`docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md`](docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md) "The architectural question this plan does NOT decide."

**Options:**
- (a) Akash CPU-only at [`infra/akash/relay-deployment-cpu-only.yaml`](infra/akash/relay-deployment-cpu-only.yaml) — low cost, but same provider economics caused recurring manifest-refusal / ingress problems
- (b) Second independent Chutes endpoint — REJECTED (both substrates on Bittensor SN64; violates Part IV.2 diversity)
- (c) Build new substrate (Aleph, io.net, Render Dispersed.com) — high cost, outside this sprint
- (d) Attestation-grade (`residual_closed: false`) and defer full closure — zero cost, honest

**Default if not decided:** **Option (d)** — attestation-grade. Closure-grade slips beyond 2026-07-01 target.

**Owner:** Operator
**Blocks:** LHT-SUBSTRATE-001 closure-grade row; does NOT block first passing attestation row.

**Resolved: 2026-05-15 — Option (d) (attestation-grade for this sprint; full closure slips to multi-quarter).** Agent-decided under operator delegation. Rationale: consistent with `8513740` posture (Akash evidence-of-option only), zero added cost, honest. Closure-grade gate moves out behind LHT-SUBSTRATE-001 Phase 4 success + warm-secondary follow-up.

---

### DD-002 — `inference-sovereignty` exit-2 treatment (long-term)

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** `xion-verify inference-sovereignty` exits 2 (`NOT_YET_SEALED`) when `XION_OPEN_WEIGHTS_GGUF_PATH` is unset — i.e., on every third-party VM by definition. Phase 1 of the closure plan (`dbdf48a`) allowlists exit 2 in the drill harness as a tactical measure.

**Options:**
- (a) Allowlist exit 2 indefinitely (current state) — drill never blocks on operator-side gguf gap
- (b) Seal the gguf pin (gemma4-e4b-it-q4-k-m-gguf to verified blob) — closes the gap; non-trivial doctrinal work
- (c) Make the gguf pin operator-environment-aware so it auto-seals on operator's daily machine but is honestly NOT_YET_SEALED on third-party VMs — best of both, more code

**Default if not decided:** **Option (a)** — current allowlist stands. Document as expected behavior in [`docs/runbooks/IMMORTALITY_DRILL.md`](docs/runbooks/IMMORTALITY_DRILL.md) if a closure-grade row lands.

**Owner:** Operator
**Blocks:** Nothing immediate. Long-term: closure-grade Invariant 17 attestation cleanliness.

**Resolved: 2026-05-15 — Option (a) (allowlist exit 2 indefinitely; documentation pass when first closure-grade row lands).** Agent-decided under operator delegation. Rationale: the verifier itself documents NOT_YET_SEALED as an operator-side gap, not a structural failure; sealing the gguf pin is non-trivial doctrinal work outside this sprint's scope. Allowlist already in drill harness via `dbdf48a`.

---

### DD-004 — Cloud-VM access mode for third-party-VM drills

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** LHT-SUBSTRATE-001 Phase 4 requires a non-operator-machine fingerprint per [`docs/runbooks/IMMORTALITY_DRILL.md`](docs/runbooks/IMMORTALITY_DRILL.md) lines 103-108. Agent cannot autonomously satisfy this today.

**Options:**
- (a) Pre-provisioned VM pool — operator spins 2-3 small VMs (GCP us-south1 or Hetzner), records SSH key + IP in `genesis/THIRD_PARTY_VMS.json`, agent SSHes via Bash tool. Recurring cost ~$5-10/month idle.
- (b) Cloud CLI in `.env` — `gcloud auth` or `aws` credentials available to agent; agent spins VMs within `cloud_vm_usd` cap. Lower friction; higher trust delegation.
- (c) GitHub Actions runner — repurpose CI as the "third-party machine" by definition. Scheduled workflow clones the repo, runs the drill, commits the ledger row. Zero ongoing cost; meets non-operator-fingerprint property cleanly.

**Default if not decided:** **Option (c)** — GitHub Actions. Lowest cost, lowest trust delegation, recurring cadence for free. Agent drafts the workflow under Track A.7-alt of session-2026-05-15 task list when this is confirmed.

**Owner:** Operator (decide); Agent (implement)
**Blocks:** LHT-SUBSTRATE-001 Phase 4. Phase 2 + Phase 3 can proceed without this.

**Resolved: 2026-05-15 — Option (c) (GitHub Actions runner).** Agent-decided under operator delegation. Rationale: zero ongoing cost, no SSH keys / cloud CLI credentials to share, clean non-operator-fingerprint property (`GITHUB_ACTIONS=true` is auditor-legible), and recurring drill cadence comes for free once the workflow lands. Agent will draft the workflow under Track A.7-alt when LHT-SUBSTRATE-001 Phase 2 + Phase 3 are committed.

---

### DD-005 — Akash retry policy post-Cosmos-migration

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** Akash announced Cosmos chain deprecation October 2025; Solana frontrunner among 15+ candidates; no fixed migration timeline. KW-FLOOR-DEPLOY-001 floor evidence is "evidence-of-option" only — no further GPU floor closure attempts on akashnet-2.

**Options:**
- (a) Hard freeze on akashnet-2 investment; pivot to alternate decentralized GPU substrate (io.net, Render Dispersed.com) for primary
- (b) Soft freeze; revisit on Akash chain-migration outcome (Q4 2026 best case per their RFP timeline)
- (c) Continue intermittent attestation-grade Akash runs as decentralized-option proof (no GPU floor closure attempts), document outcomes

**Default if not decided:** **Option (c)** — intermittent attestation runs only. Already codified in commit `8513740` strategic posture.

**Owner:** Operator
**Blocks:** Nothing immediate. Affects multi-quarter roadmap.

**Resolved: 2026-05-15 — Option (c) (intermittent attestation runs only on akashnet-2; re-evaluate after Akash chain-migration outcome).** Agent-decided under operator delegation. Rationale: already locked in `8513740` commit body ("Akash = decentralized-option proof, not primary GPU floor"). No new investment on akashnet-2 beyond evidence runs; full pivot decision deferred until Akash announces new chain (Q4 2026 best case).

---

### DD-006 — 23 pre-existing `xion-verify` test failures

**Surfaced:** 2026-05-15 (CST), session-2026-05-15
**Context:** `pytest xion-verify/tests/` reports 23 failures at HEAD `dbdf48a` (pre-existed at `670d2e0`; not caused by this session's work). Clusters: `test_pricing_verifier.py` (6), `test_provisioning.py` (1), `test_shadow_relay.py` (1), 15 others. xion_ops tests pass cleanly (76/76).

**Options:**
- (a) Investigate root cause and fix (1-2 hours of diagnosis; may surface real bugs in pricing/provisioning verifiers)
- (b) Mark as `pytest.mark.skip` with reason + link to a known-failures issue; clean test signal at cost of coverage
- (c) Remove the test files entirely if the underlying features are deprecated
- (d) Leave as-is; document in `OPERATOR_HANDOFF.md` § 6 as known pre-existing failures (current state)

**Default if not decided:** **Option (d)** — already documented in handoff § 6. Pre-existing failures don't block sprint work; sweep is hygiene-level.

**Owner:** Operator (decide approach); Agent (execute (a) diagnosis or (b)/(c) markers)
**Blocks:** Nothing immediate. Affects audit-readiness: an external auditor will see 23 failing tests and ask.

**Resolved: 2026-05-15 — Option (d) (documented as pre-existing in handoff § 6 for now; revisit to Option (a) after LHT-SUBSTRATE-001 closure-grade row lands).** Agent-decided under operator delegation. Rationale: investigating 23 failures is a 1-2 hour lateral move away from the active sprint thread; current sprint thread (LHT-SUBSTRATE-001) takes priority. After a passing drill row lands, audit-readiness becomes the next bottleneck and the 23 failures should be re-triaged under Option (a) — flagged forward in the next session's pickup note.

---

## How to use this file

**At session start:** read top to bottom; understand which defaults are in play.

**During session:** if you encounter a decision the operator hasn't made, check if it's here first. If it is, proceed under the default. If it is not, add a new entry (next DD-NNN), assign options + default, note it in the session, surface to operator only if the default would block sprint work.

**When operator decides:** move entry to "Resolved" section with `Resolved: YYYY-MM-DD — <one-line outcome>`. Reference the resolving commit/decision in `STATE_OF_XION_PREFLIGHT.md` or similar canonical tracker.

**Reviewing this file:** if an entry's default-if-not-decided was followed by sprint work that depended on it, that's an implicit ratification — when explicit confirmation comes, mark resolved with `Implicit (followed default; ratified <date>)`.
