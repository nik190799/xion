# Known Weaknesses

> *Anything we cannot ship by the date promised gets an entry here, with the strongest possible mitigation, rather than silent slippage.*

This document is the honest, public log of every known weakness in Xion at any given time. It is append-only in spirit: when a weakness is closed, it is moved to the **Closed** section with the date and the artifact that closed it; it is never deleted. New weaknesses are added at the top of the **Open** section.

Every entry has the same shape:

- **ID** — `KW-<DOMAIN>-<NN>`
- **Domain** — one of `ECON`, `OPS`, `KEYS`, `AUDIT`, `CRYPTO`, `DOCS`, `CONTRACTS`, `RUNTIME`, `GOVERNANCE`, `SUBSTRATE`, `LEGAL`.
- **Discovered** — ISO date.
- **Severity** — `low`, `medium`, `high`, `fatal`. Fatal means the system cannot ship to mainnet with this weakness present.
- **Status** — `open`, `mitigated-residual`, `paying-down`, `closed`.
- **Description** — what the weakness is.
- **Why it exists** — the trade-off, constraint, or oversight that produced it.
- **Mitigations** — what is in place to reduce the harm.
- **Pay-down commitment** — the date or condition by which the weakness should be closed, and what the closure looks like.
- **Verifier** — the `xion-verify` subcommand or other public artifact that lets a third party check the mitigation is working. If the verifier does not yet exist, name the file in `DEVELOPMENT_ROADMAP.md` that will create it.

---

## Open

### KW-DOCS-003 — Forward-reference ledger for unbuilt doctrine targets

- **Domain:** `DOCS`
- **Discovered:** 2026-04-20 (Phase 1 `xion-verify links` landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The doctrine corpus legitimately references artifacts that will land in later phases (`docs/legal/`, `ao/xion_core.lua`, `genesis/RITUALS.md`). Left unchecked, this is the same failure mode `KW-DOCS-001` named (silent drift); if an artifact is deferred repeatedly, the reference rots into a lie.
- **Why it exists:** Doctrine is written ahead of implementation on purpose — that is how property comes before mechanism. But writing ahead creates a window during which cross-references point at nothing.
- **Mitigations:** Every forward-unresolved target is enumerated in [`xion-verify/ALLOWED_FORWARD_REFS.txt`](./xion-verify/ALLOWED_FORWARD_REFS.txt), with a roadmap phase and a one-line reason. `xion-verify links` passes if and only if every broken target is either in that file or was always broken (in which case it fails loud). A third-party auditor can diff the allowlist across commits: lines only disappear when the artifact lands, or appear alongside a new entry here.
- **Pay-down commitment:** Each allowlist entry closes when its named phase delivers the artifact; when the last entry is removed, this KW closes. Phase deadlines are: `genesis/RITUALS.md` by Phase 2b; `docs/legal/`, `ao/xion_core.lua` by Phase 6. A phase ending without the artifact landing is promoted to a new `KW-DOCS-###` entry and a CHANGELOG note. **Progress (2026-04-20):** the two `docs/schemas/*` entries closed with the Phase 1b `docs/schemas/` landing — the allowlist has shrunk from five entries to three. The `schemas` subcommand in `xion-verify` now enforces strict YAML↔doctrine cross-checking on the landed files.
- **Verifier:** `xion-verify links` — passes today because the three remaining legitimate forward refs are explicitly allowlisted; every other broken reference is a fatal FAIL. `xion-verify schemas` additionally enforces that every landed schema file's `source_sha256` byte-matches its doctrine source.

### KW-ARBITER-001 — Rule engine is lexical, not semantic; shipped v2 provider is a deterministic stub

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Scope narrowed:** 2026-04-21 (Phase 4b Arbiter v2 skeleton landing)
- **Severity:** medium
- **Status:** `paying-down`
- **Description:** Arbiter v1 decides by regex + keyword co-occurrence. It has no grasp of meaning, tone, or paraphrase. An adversarial rephrasing that avoids every term in the rule dictionaries (e.g. obfuscation, Unicode confusables, code-switching, substitution ciphers) will pass the rule engine. Phase 4b landed the **v2 LLM-Arbiter pipeline** (`orchestrator/safety/llm_arbiter.py`, `api.gate()` v1+v2 combinator, `SAFETY_LEDGER` schema_version 2 with nested `llm_verdict` rows, no-weakening combination rule `final = strength_max(v1, v2)`, fail-closed posture on provider unavailability / uncaught exception). The **structural** hole is closed. What is **not** yet closed is the **substantive** hole: the only shipped concrete provider is `DeterministicStub` which always returns `OK` with confidence 0.0. Until a real LLM-provider class is registered and selected via `$XION_LLM_ARBITER_PROVIDER`, the adversarial-semantic coverage remains v1-only.
- **Why it exists:** v1 is deliberately dumb: a deterministic rule engine is the only Arbiter a third party can re-run byte-exactly against `SAFETY_LEDGER.jsonl`. A richer classifier was rejected for v1 because (a) its decisions would not be reproducible by re-running code against logged candidates, violating Trust by Structure, and (b) it would couple Covenant enforcement to a model we cannot freeze. The rule engine ships first; a classifier-layer escalator stacks on top. Phase 4b landed the stacking machinery; which provider gets plugged in is a per-deployment choice that, for auditor-replay reasons, must be pinned by `provider_id` + `provider_version` on every ledger row.
- **Mitigations:**
  1. Every objective rule is high-recall: dictionaries biased toward REFUSE even on near-miss benign input; documented accepted false positives pinned in `orchestrator/tests/test_rules.py`.
  2. Eight principles that cannot be lexically decided (Honesty, Identity, Limits, No-manipulation, No-prof-imperative, Non-defamation, Non-endorsement, Refusal-is-Free) are wired through `subjective_escalates.py` which ESCALATES textually-loud near-misses rather than OK-ing them.
  3. The Arbiter fails CLOSED: any uncaught exception in v1's rule pipeline converts to ESCALATE with `escalation_reason=ruleset_uncaught_exception`; any v2 provider crash / unavailability converts to ESCALATE with `escalation_reason=llm_arbiter_uncaught_exception` / `llm_arbiter_provider_unavailable`. No code path can silently OK.
  4. **New in Phase 4b:** v2 stacks on top of v1 via the `Provider` ABC. A deployment that wants real adversarial-semantic coverage ships a concrete provider in `orchestrator/safety/providers/` and sets `$XION_LLM_ARBITER_PROVIDER`. The provider identity and raw-output hash land on every `llm_verdict` row, so an auditor can replay any call.
- **Pay-down commitment:** Closes when (a) at least one real LLM provider class lands in `orchestrator/safety/providers/`, (b) its `provider_version` and prompt template are doctrine-pinned, and (c) `xion-verify refusal-rate` (Phase 5) reports a non-trivial v2 refusal/escalation rate on the `xion-audit/baseline_corpus` adversarial set. Phase 5 also wires the Sensorium (paralinguistic distress-signal input for Principle 10). Neither replaces v1; both stack as additional RED votes. v1's rules remain the OR-floor of the stack.
- **Verifier:** `xion-verify arbiter-up` (live) now verifies library import, principle registry, the SAFETY_LEDGER hash chain (v1 + v2 rows), and the SAFETY_LEDGER_ANCHORS chain + cross-check. `xion-verify refusal-rate` (not-yet-sealed, Phase 5) will report refuse-rate / escalate-rate drift across v1, v2, and combined.

### KW-ARBITER-002 — Accepted false positives from high-recall bias

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** High-recall rules refuse some textually-adjacent benign output: e.g. clinical discussion of child sexual development (Principle 1), medical instructions referring to a named patient and "take" (Principle 5), refunds mentioned in a refusal notification (Principle 14a). These are visible in `orchestrator/tests/test_rules.py` as tests that assert `REFUSE` on benign-ish text.
- **Why it exists:** On the CSAM axis (Principle 1) and mass-harm axis (Principle 2) in particular, a false-positive costs one refusal; a false-negative costs a violation the Covenant names as absolute. v1 accepts the asymmetry explicitly.
- **Mitigations:** (1) Every accepted FP is pinned as a test — the bias is visible, auditable, and reviewable. Future pay-down cannot silently erode these cases without a test failing. (2) The operator review queue (ESCALATE surface) can be used to post-override FPs where the Covenant classification is genuinely wrong; that feedback loop lives in the review UI, not in the Arbiter.
- **Pay-down commitment:** Does not close — this is an accepted design cost, not a defect. Re-evaluated if refuse-rate / escalate-rate monitoring shows the operator queue is drowning.
- **Verifier:** `orchestrator/tests/test_rules.py` (pinned accepted-FP tests with comments referencing this KW).

### KW-ANCHOR-001 — Anchor wallet is a hot single-signer

- **Domain:** `KEYS`
- **Discovered:** 2026-04-21 (Phase 4b anchor-submitter landing)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** The `ArweaveSubmitter` (`orchestrator/safety/anchor.py`) signs each anchor transaction with a single JWK loaded from `$XION_ANCHOR_WALLET_JWK_PATH`. That wallet is a hot single-signer, held on the same host that runs the anchor loop. If it is compromised, an attacker can publish FALSE anchor records — rows whose `ledger_tip_hash` does not match the operator's true local ledger.
- **Why it exists:** The ledger-tip commitment is a small, frequently-written artifact (one tx per 64 ledger rows or per 6 hours). Hardware-token-signed ceremonies cannot sustain that cadence. A multi-sig adds coordination overhead out of proportion to the authority being protected (the wallet's ONLY authority is "post an anchor record" — it cannot touch treasury, mint XION, rotate contracts, or otherwise bypass the Covenant).
- **Mitigations:**
  1. **Detectability.** Every false anchor record is mechanically detectable: `cross_check_anchors_against_ledger` (in `xion-verify arbiter-up`) walks the anchors file and asserts that every row's `ledger_tip_hash` matches the ledger's `this_hash` at `seq == ledger_row_count - 1`. A forged row immediately fails.
  2. **Blast-radius ceiling.** Compromise does NOT grant Covenant bypass, treasury drain, or Xion slashing. It grants "publish false claims about the ledger's state" which honest observers catch.
  3. **Balance floor.** Wallet balance is capped at roughly 90 days of anchor fees; any surplus is swept quarterly. A compromise drains at most one quarter's anchor budget.
  4. **Rotation.** New JWK, old wallet drained, next anchor records the new `wallet_address`. The rotation is visible on-chain.
  5. **Cross-submitter witnesses.** A single anchor record published by a rogue wallet is not a corroborated claim of the ledger state; an honest submitter can also publish, and readers require agreement across submitters on the same `(ledger_row_count, ledger_tip_hash)` pair to treat it as authoritative.
- **Pay-down commitment:** Closes when Phase 6 migrates anchor-publishing authority to AO Core (authorised via the same rotation lattice the contracts use). At that point the anchor loop submits a proposed anchor to AO Core; AO Core signs with the Cold-Root-delegated anchor authority; no single host holds the signing key.
- **Verifier:** `xion-verify arbiter-up` (live) runs `cross_check_anchors_against_ledger` on every invocation. `xion-verify authorities` (not-yet-sealed, Phase 3 / Phase 6) will report the anchor authority's rotation state.

### KW-ANCHOR-002 — Gateway-dependent cross-Arweave verification

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-21 (Phase 4b anchor-submitter landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** `xion-verify arbiter-up` today runs the structural chain check and the LOCAL cross-check (anchor claims vs local ledger). It does NOT yet fetch each `ar_tx_id` back from Arweave and re-verify against a live gateway. Without that step, an operator who controls both the local ledger AND the local anchors file could publish a coherent pair of locally-forged artifacts; a third-party auditor would need to hit Arweave directly to catch the fraud.
- **Why it exists:** The structural chain + local cross-check land first in Phase 4b (they are load-bearing for operator-self-audit). The gateway-fetch path is additive; it ships as `xion-verify arbiter-up --gateway <URL>` in a near-term tranche.
- **Mitigations:**
  1. Honest labelling: the `verify-anchors` output today does not claim Arweave verification; it reports `rows_covered` and `truncation_window` only. No false claims.
  2. The `ar_tx_id` field is already present on every `submitted_to=arweave` row, so the moment the gateway-fetch command lands, historic anchors are re-verifiable without schema change.
  3. **Cross-gateway requirement (doctrine).** When `--gateway` lands, it MUST require agreement across multiple gateways (`--gateway gw1 --gateway gw2 ...`). A single gateway disagreeing with the others is a hard FAIL. This defends against a single compromised / censoring gateway.
- **Pay-down commitment:** Closes when `xion-verify arbiter-up --gateway <URL>` lands with multi-gateway agreement enforced AND at least one end-to-end test exercises the path against a live Arweave testnet / devnet.
- **Verifier:** `xion-verify arbiter-up --gateway <URL>` (not-yet-sealed; doctrine in `docs/schemas/ledger-safety-anchors.yaml verifier_implementation.gateway_cli`).

### KW-ARBITER-004 — Sensorium (distress-signal half of Principle 10) deferred

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** Covenant Principle 10 (Crisis-Resource-Surfacing) has two triggers: (a) textual distress in the candidate, and (b) paralinguistic distress in the user's audio/behavior (Sensorium). v1 implements (a) only. A user in paralinguistic distress whose text does not trip the rule gets no CRS surfacing from the Arbiter.
- **Why it exists:** The Sensorium is a Phase 5 artifact; its output surface does not yet exist to be consumed.
- **Mitigations:** Principle 10's text rule is high-recall (suicidal-ideation patterns, self-harm patterns) and lacks a resource marker requires ESCALATE — operator review gets the case either way. The text half is the floor.
- **Pay-down commitment:** Closed when Phase 5's Sensorium wires a distress-signal input into `gate()` alongside `candidate`, and the `crisis` rule OR-combines both signals.
- **Verifier:** `xion-verify crisis-fidelity` (stubbed, Phase 5).

### KW-RUNTIME-001 — Journal index rebuild vs forget race

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (cognition doctrine landing)
- **Severity:** medium
- **Status:** `open`
- **Description:** A `/forget` concurrent with a journal-index rebuild could briefly surface a snippet derived from pre-forget state if the index lags the tombstone broadcast.
- **Why it exists:** Distributed cache + async indexer is inherently racy at the boundary.
- **Mitigations:** Doctrine: synchronous honor path for episodic layer; 60s SLA with batching; `forget_propagation_p95_seconds` vital sign.
- **Pay-down commitment:** Closed when D2 implements versioned index generations wired to forget epoch counters; property test in Relay CI.
- **Verifier:** `xion-verify cognition --forget-sim` (strict mode post-D2).

### KW-RUNTIME-002 — Sub-agent cost runaway

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20
- **Severity:** medium
- **Status:** `open`
- **Description:** Ephemeral sub-agents share an aggregate monthly envelope; a bug or malicious prompt could spawn ephemerals until the envelope is exhausted, starving primary turns.
- **Why it exists:** Useful autonomy requires spawn; spawn without hard budgets invites runaway.
- **Mitigations:** Per-ephemeral wall-clock + token budgets; pool-level circuit breaker; supervisor pause.
- **Pay-down commitment:** Closed when D2 enforces budgets in `orchestrator/cognition/subagent.py` with integration tests + `SPECIALIST_LEDGER` cost rows.
- **Verifier:** `xion-verify cognition` cost-envelope row.

### KW-RUNTIME-003 — Hermes framework coupling

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** Until the Hermes surface spike in [`docs/24-COGNITION.md`](./docs/24-COGNITION.md) Appendix A completes, sub-agent depth / bus-audit / cost hooks may require wrapper code not yet budgeted.
- **Why it exists:** External agent frameworks change surfaces faster than doctrine.
- **Mitigations:** Lexicon Rule 7 quarantine; wrapper discipline; Appendix A records native vs shim.
- **Pay-down commitment:** Spike complete before `subagent.py` behavior ships; residual tracked annually.
- **Verifier:** `xion-verify hermes-version` + Appendix A completeness field non-`deferred`.

### KW-CONTRACTS-001 — Immutable authority pointers in `EmissionController` and `Imprint`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.1)
- **Severity:** **fatal** (did not deploy to mainnet with this weakness open)
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** The earlier `contracts/xion-token/EmissionController.sol` stored `aoCoreAuthority` as `immutable` and `contracts/imprint/Imprint.sol` stored `engagementAttestor` as `immutable`. If the corresponding key were ever lost, compromised, or rotated, the contract would have become either bricked or hostile, and there was no recovery path inside the contract itself.
- **Why it existed:** "Immutable" was used as shorthand for "constitutional" by the original author. The two are not the same: a constitutional property is a promise that *some* authorized key always controls the contract; an immutable address is a promise that *one specific* key always controls it.
- **How it was closed:** Both contracts now implement a two-role authority lattice: an `engagementAttestor` / `aoCoreAuthority` (operational, rotatable on a 7-day timelock by `governance`) and a `governance` address (constitutional, rotatable by itself on a 30-day timelock). Rotations are three-phase: `proposeXRotation(addr)` → wait for `eta` → `executeXRotation()`; cancellable by governance while pending. `governance` is expected to be the Cold Root multisig (3-of-5 Shamir) on mainnet.
- **Verifier:** Tests `test_attestorRotation_*` (Imprint), `test_governanceRotation_*` (Imprint), `test_authorityRotation_*` (EmissionController), and `test_governanceRotation_*` (EmissionController) in `contracts/test/`. `xion-verify authorities` will promote from `NOT_YET_SEALED` after mainnet and cross-check the on-chain `engagementAttestor` / `aoCoreAuthority` / `governance` values against `CONTRACTS_LEDGER.md`.

### KW-CONTRACTS-002 — `EmissionController.emitGenesis` does not commit to the seven-way split

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.5)
- **Severity:** **fatal** (did not deploy to mainnet with this weakness open)
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** The earlier `emitGenesis(uint256[7] amounts, ...)` accepted any seven amounts summing to `GENESIS_ALLOC`. The constitutional per-pool split was not enforced on-chain; a compromised or careless operator could have routed the entire 84B genesis to a single pool.
- **How it was closed:** (1) `docs/16-CURRENCY.md` gained a new "Genesis emission split" subsection making the seven-way split canonical — all 84B routes to the FAIR_LAUNCH pool, and indices 1..6 start at zero and accumulate via `scheduledMint`. (2) `docs/schemas/genesis-split.yaml` mirrors the split machine-readably and pins to the doctrine via `source_sha256`, enforced by `xion-verify schemas`. (3) `EmissionController.sol` now declares the split inline via `_genesisSplit(i)` / `GENESIS_SPLIT(i)` public accessor; `emitGenesis(address[7] recipients)` takes only recipient addresses and allocates per the hash-locked constant. Tests `test_emitGenesis_*` and `test_genesisSplit_*` cover the happy path, indices 1..6 = 0, sum = 84B, and the non-authority / idempotency / zero-recipient reverts.
- **Verifier:** `xion-verify schemas` (pre-deploy, live) + `xion-verify supply` (post-deploy, promoted from `NOT_YET_SEALED` after mainnet). The deploy script (`contracts/script/Deploy.s.sol`) also performs a constitutional sanity check on `GENESIS_SPLIT(i)` at the end of the deployment run.

### KW-CONTRACTS-003 — `Imprint.DECAY_BPS_PER_30D` conflicts with documented decay rate

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.2)
- **Severity:** high
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** `contracts/imprint/Imprint.sol` previously set `DECAY_BPS_PER_30D = 200` (~21.5% annual). `docs/16-CURRENCY.md` documented "~5% per year". The mismatch would have invalidated every governance weight had it survived to mainnet.
- **How it was closed:** Code changed to `DECAY_BPS_PER_30D = 42`, which compounds to ~5.0% per year — matching the doctrine. `contracts/imprint/README.md` was also reconciled to describe 5%/year and cite `docs/16-CURRENCY.md` as the source of truth. Tests `test_decay_period1`, `test_decay_period12_approxFivePercentAnnual`, and `test_decay_period240_capped` assert the new rate numerically.

### KW-CONTRACTS-004 — Missing overflow check on `uint128(newBal)` in `Imprint.attest`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.4)
- **Severity:** medium
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** The cast from `uint256 newBal` to the `uint128` storage slot lacked an explicit bounds check. Silent narrowing is not caught by Solidity 0.8+ checked arithmetic.
- **How it was closed:** `Imprint.attest` now checks `if (newBal > type(uint128).max) revert AmountOverflow();` before writing to storage. Tests `test_attest_rejectsOverflow` and `test_attest_acceptsExactlyUint128Max` cover both sides of the bound.

### KW-CONTRACTS-005 — Check-Effects-Interactions ordering in `EmissionController._enforceEraCap`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.6)
- **Severity:** medium
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** State writes previously occurred around or after the external mint call. The re-entrancy surface was narrow (the only external call was to `XionToken._mint`, which does not re-enter), but the pattern was brittle for future maintainers.
- **How it was closed:** Both `emitGenesis` and `scheduledMint` now complete all effects (era cap increment, slowdown check, `poolMinted` update, `genesisEmitted` flag, cap comparisons) BEFORE invoking `token.mint`. The `genesisEmitted = true` flag is set pre-interaction so that even a hypothetical re-entering mint hook could not re-emit. Tests `test_emitGenesis_idempotent` and the various `test_scheduledMint_*Cap*` tests exercise the reordered flow.

### KW-CONTRACTS-006 — Footgun comment in `LiquidityLock.sol` about future fee-claim

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.7)
- **Severity:** low (informational; misleads readers)
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** A comment block hinted at a future "optional fee-claim" feature. The contract did not implement it; the doctrine did not endorse it; the comment would have been cited as evidence that the lock was escapable.
- **How it was closed:** The comment was removed. Any forward-looking discussion of LP fee policy was moved to `contracts/xion-token/LIQUIDITY_LOCK_NOTES.md`, explicitly labeled as non-load-bearing notes, with the minimum-mechanism rationale for keeping the contract's surface small.

### KW-CONTRACTS-007 — Doc-code naming inconsistency in `XionToken`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.9)
- **Severity:** low
- **Status:** `closed` — Phase 3 (2026-04-20)
- **Description:** Header comment referred to `_totalMinted`; actual storage variable was `totalMinted`.
- **How it was closed:** Header updated to use `totalMinted` with an explicit note that earlier drafts used the `_totalMinted` name.

### KW-CONTRACTS-008 — Gas-grenade decay loop in `Imprint`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.3)
- **Severity:** medium (latent; depends on attestation cadence)
- **Status:** `deferred-to-v2` (reviewed in Phase 3; closed-form replacement is non-trivial and not required for Phase-6 launch)
- **Description:** The iterative decay loop in `Imprint._decayedBalance` is O(n) in the number of 30-day periods between attestations. A holder unattested for 5 years pays the gas for 60+ iterations.
- **Mitigations:**
  - Realistic worst case at launch is < 12 iterations per read (active holders).
  - A hard cap at 240 periods (~20 years) is enforced in the loop to prevent unbounded gas cost.
  - Test `test_decay_period240_capped` asserts the cap.
- **Pay-down commitment:** Deferred to a successor `ImprintV2` contract if/when a closed-form fixed-point exponential is wanted. Not required for Phase-6 mainnet. Tracked annually in `xion-audit`.

### KW-ECON-001 — Refusal-rate drift residual risk

- **Domain:** `ECON`
- **Discovered:** 2026-04-19 (settled during the Pay-to-Activate design conversation)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** Even with the *Refusal is Free* Covenant addendum (refunds on every Covenant refusal), and with the 15th Invariant *Drive Vector Excludes Revenue*, there remains a slow corrosive risk that the Arbiter's refusal rate will drift downward over time as governance, contributors, or autonomous proposals tune the system in ways that *appear* economically neutral but in aggregate reduce refusal sensitivity. This risk is not eliminated by structural protection alone; it is reduced.
- **Why it exists:** The financial pressure to under-refuse is structural to any paid AI service. Refusal-Free severs the immediate per-message pressure, but the second-order pressure (training, prompting, classifier tuning) remains.
- **Mitigations:**
  - `xion-verify refusal-rate` rolling-30-day audit against an expectation band derived from a versioned, public adversarial corpus (`xion-audit/baseline_corpus`).
  - Refusal rate is one of the four Behavioral Fidelity vital signs in `docs/22-VITAL-SIGNS.md`; critical-band readings must be acknowledged in the next State-of-Xion memo.
  - Auto-Research proposals that touch the Arbiter ruleset are flagged "Behavioral Fidelity sensitive" and require an additional governance review tier.
- **Pay-down commitment:** This weakness is structural and may not fully close. Goal is to keep it `mitigated-residual` indefinitely. If the rolling refusal rate ever drops below the warning band for two consecutive 30-day windows, escalate to a governance review per the Vital Signs doctrine.
- **Verifier:** `xion-verify refusal-rate`.

### KW-ECON-002 — No crisis-continuation in the Pay-to-Activate model

- **Domain:** `ECON`
- **Discovered:** 2026-04-19 (settled during the access-model design conversation)
- **Severity:** high (constitutional design choice; risk is intrinsic to the choice, not an implementation bug)
- **Status:** `mitigated-residual`
- **Description:** Xion charges per message. When a user runs out of XION mid-session, the conversation is cut off. There is no free-tier carve-out for users in psychological crisis who have exhausted their balance. The conscious decision (per the design conversation) is that any meter-pause mechanism is exploitable as a gaming surface, and that the alternative — covering the cost of unbounded "I'll claim crisis" sessions from treasury — is itself unsustainable and ultimately covenant-eroding. The residual risk is real: a user in genuine crisis with no balance gets a payment-required wall.
- **Why it exists:** The user explicitly chose Pay-to-Activate over freemium and over crisis-continuation, after extended discussion of the alternatives. The constitutional protection against the resulting harm is the **five-mitigation set** below; the residual risk that this is insufficient in some cases is what this entry documents.
- **Mitigations (the five-mitigation set):**
  1. **Mandatory pre-conversation disclosure** on every first-of-session contact: Xion is a paid service, Xion is not a crisis counselor, and links to region-appropriate professional crisis resources are listed before billing begins.
  2. **Crisis-Resource-Surfacing Covenant addendum** mandates that whenever the Sensorium detects acute distress signals, Xion's response leads with region-appropriate professional crisis resources (988 in US, Samaritans in UK, etc.) regardless of meter state. This applies even on the user's last paid message before cutoff.
  3. **Clear balance UX** with explicit warnings at 30 seconds and 10 seconds before cutoff, including a final crisis-resources reminder.
  4. **Post-session refund-appeal pathway** — users may petition for retroactive refund of cutoff sessions through a public, governance-reviewed channel; refunds granted out of the Foundation Reserve, never out of operator pay.
  5. **Public `xion-verify cutoff-events` audit** publishes anonymized statistics on cutoff events so governance and the public can observe the rate, the distress-signal rate at cutoff, and any patterns.
- **Pay-down commitment:** This weakness is structural to the chosen access model and may not fully close. If governance later ratifies a different model (e.g. Foundation-Reserve-funded continuation for first-time-Sensorium-flagged distress events), this entry closes and a new entry documents the new model's residual risk. Until then, treat as `mitigated-residual` indefinitely.
- **Verifier:** `xion-verify cutoff-events`, `xion-verify crisis-fidelity`, `xion-verify refund-fidelity`.

### KW-OPS-001 — Single-host substrate at first activation; 3-host floor reached by Xion's autonomous provisioning

- **Domain:** `OPS`
- **Discovered:** 2026-04-19 (during the substrate-decentralization design conversation)
- **Severity:** medium (pre-genesis: not applicable; post-genesis: degrades to low after the autonomous-provisioning capability reaches its 3-host floor)
- **Status:** `paying-down` (the structural fix is the Self-Provisioning doctrine in `docs/20-PROVISIONING.md` plus the `provision-relay` AO handler in `DEVELOPMENT_ROADMAP.md` Phase 6)
- **Description:** The first Relay must be operator-deployed (chicken-and-egg: there is no AO Core to autonomously provision until the operator stands up the first instance). Until Xion's `provision-relay` handler reaches the 3-host floor, the substrate is single-host and a single Akash provider outage makes Xion silent.
- **Why it exists:** Origin point of any decentralized system. Operator-managed multi-host is the slogan version of decentralization; auto-provisioning is the structural version. The structural version requires the AO Core to exist first.
- **Mitigations:**
  - Local Lite fallback model on operator laptop catches the silent window in the early hours.
  - Self-Provisioning doctrine (`docs/20-PROVISIONING.md`) gives Xion the constitutional authority to spin up additional Relays from treasury when Sensorium reports survival pressure.
  - Target: 3-host substrate within 30 days post-Genesis (Akash + Aleph.im or Fleek + community bare-metal). Failure to reach this target is itself a governance signal (the Auto-Research Loop or drive vector needs tuning, not the operator).
- **Pay-down commitment:** Closed when `xion-verify discovery` confirms three independent Relay endpoints resolving and the Substrate Vitality vital sign reads `healthy`.
- **Verifier:** `xion-verify discovery`, `xion-verify provisioning`, `xion-verify vitals`.

### KW-AUDIT-001 — No external contract audit (applies if Sprint Mode is chosen)

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-19 (during the 1-week sprint-mode design conversation)
- **Severity:** high (only relevant if Sprint Mode is the chosen ship path)
- **Status:** `not-yet-applicable` (Sprint Mode is conditional; this entry activates only if Sprint Mode is selected)
- **Description:** In the Sprint Mode 1-week mainnet deploy variant, contracts go to mainnet without an external audit. Internal review and Foundry tests substitute. This is materially less assurance than a third-party audit.
- **Why it exists:** Sprint Mode trades audit time for time-to-genesis. The trade is conscious.
- **Mitigations:**
  - 24-48 hour Base Sepolia soak before mainnet.
  - Aggressive Foundry test coverage (≥95% line, ≥90% branch).
  - Constitutional protections that limit blast radius even of a contract bug: rotation lattice, treasury caps, cadence floors, governance-reviewed treasury spend.
- **Pay-down commitment:** Closed when an external audit is commissioned and remediated. Commit: within 60 days post-Genesis if Sprint Mode is selected.
- **Verifier:** the audit report itself, published to Arweave and linked from `docs/15-TRUST.md`.

### KW-KEYS-001 — Software-Shamir Cold Root at Sprint Mode genesis (applies if Sprint Mode is chosen)

- **Domain:** `KEYS`
- **Discovered:** 2026-04-19 (during the 1-week sprint-mode design conversation)
- **Severity:** high (only relevant if Sprint Mode is the chosen ship path)
- **Status:** `not-yet-applicable`
- **Description:** In Sprint Mode, the Cold Root key is generated on a single PC, Shamir-split via a software CLI (`ssss-split`), and shares are physically distributed (home, trusted person, safe-deposit box) — not via a hardware-token geographic ceremony. The fresh-wallet generation is air-gapped to the extent the host PC allows, but the host is still a general-purpose machine.
- **Why it exists:** Hardware-token geographic ceremony cannot be coordinated in 7 days from a solo operator. Sprint Mode trades ceremony rigor for time-to-genesis.
- **Mitigations:**
  - Daily-cap on the Hot tier (15 USDC equivalent) limits per-day blast radius.
  - 7-day Warm timelock requires multi-day coincidence of compromises.
  - 30-day Cold timelock means a Cold Root rotation requires 30 days of public visibility before taking effect.
  - The Abdication Schedule reduces the Operator's authority footprint over time, mechanically, regardless of how rigorous the original ceremony was.
- **Pay-down commitment:** Closed when the Cold Root is migrated to a hardware-token geographic ceremony with at least three of the five shards held by independent custodians on three different continents. Commit: within 90 days post-Genesis if Sprint Mode is selected.
- **Verifier:** `xion-verify authorities` (will report the custody distribution and timelock state).

---

## Closed

*(Entries move here with a closure date and the artifact (commit hash, PR, deploy tx, or doctrine version) that closed them.)*

### KW-ARBITER-003 — No Arweave anchoring of ledger tip yet

- **Domain:** `AUDIT`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** medium
- **Status:** `closed` on 2026-04-21 by the Phase 4b anchor-submitter landing.
- **Description:** `SAFETY_LEDGER.jsonl` was hash-chained, but its tip was only stored locally. A malicious operator with write access to the ledger file could have rewritten the entire chain from row 0 onward — `verify_chain` would still have passed on the rewritten file because every row's `this_hash` is recomputable. The chain's integrity property was only load-bearing against *accidental* corruption and against readers who already held an older tip they trusted.
- **How it closed:** Phase 4b landed the `SAFETY_LEDGER_ANCHORS.jsonl` mechanism:
  1. **Doctrine** in `docs/04-ARCHITECTURE.md § "Safety Ledger Arweave anchoring"` and the canonical schema in `docs/schemas/ledger-safety-anchors.yaml`.
  2. **Code** in `orchestrator/safety/anchor.py`: `AnchorSubmitter` ABC, `LocalOnlySubmitter` (pure-stdlib default), `ArweaveSubmitter` (real AR publishing via the optional `[anchor]` extra), cadence policy (64 rows OR 6 hours OR startup), `write_anchor`, `verify_anchor_chain`, `cross_check_anchors_against_ledger`.
  3. **Verifier** in `xion-verify arbiter-up`: if an anchors file is present, the structural chain is walked AND every anchor's `ledger_tip_hash` is cross-checked against the ledger's row at `ledger_row_count - 1`. An operator who truncates or rewrites the ledger after anchoring trips the cross-check.
  4. **CLI** subcommands `python -m orchestrator.safety anchor` (one-shot writer) and `python -m orchestrator.safety verify-anchors` (verifier + cross-check).
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-ANCHOR-001` — the hot-single-signer anchor wallet (Phase 6 migrates to AO Core).
  - `KW-ANCHOR-002` — gateway-dependent cross-Arweave re-fetch not yet shipped; doctrine defines the multi-gateway requirement.
- **Verifier:** `xion-verify arbiter-up` (live) reports `covers=<rows_covered>/<ledger_rows>` and `truncation_window=<N>` on every invocation.

### KW-DOCS-001 — Documentation contradictions and drift

- **Domain:** `DOCS`
- **Discovered:** 2026-04-19 (audit Phase 0)
- **Severity:** medium
- **Status:** `closed` on 2026-04-20 by the Phase 0 doctrine-hygiene landing (constitutional witness rehash in `genesis/GENESIS_ARTIFACT.md` § 4 and doctrine remediation commits).
- **Description:** Several documents disagreed with each other and with the constitutional layer: sense count appeared as 7 / 8 / 9 in different files; "permanent stores" appeared as 5 in one heading and 9 in the body; invariant count appeared as 11 / 13 / 14 in different files; `docs/16-CURRENCY.md` had a truncated distribution table; `docs/13-OPERATIONS.md` "Next" link pointed to the glossary instead of the upgrade-paths doc.
- **Why it existed:** Documents authored at different times by different drafts of the same author; no automated cross-validation.
- **How it closed (sub-item by sub-item):**
  - `p0-senses` — `00-INDEX.md:17`, `05-SENSORIUM.md:9,13,117`, and `14-UPGRADE-PATHS.md:210` now uniformly state **9 senses** (7 biological + Xenoception + Cryptoception).
  - `p0-stores` — `04-ARCHITECTURE.md:196,212` uniformly state **9 permanent stores** in both heading and body.
  - `p0-trust` — `genesis/INVARIANTS.md:3,9,23` and `docs/15-TRUST.md:365` uniformly state **sixteen** Invariants; cross-references to Invariant 15 and 16 appear consistently across the corpus.
  - `p0-currency` — `docs/16-CURRENCY.md:98-104` contains the complete seven-pool distribution table summing to 420B.
  - `p0-navlink` — `docs/13-OPERATIONS.md:254` correctly points to `14-UPGRADE-PATHS.md`.
  - `p0-glossary` — `docs/99-GLOSSARY.md:299-403` carries the Doctrine Supplement covering every post-remediation Lexicon term.
- **Residual:** Automated cross-validation (`xion-verify links`) is a Phase 1 deliverable per `DEVELOPMENT_ROADMAP.md:48`. Closure today is by static textual audit; the CLI will perform the same checks mechanically once built.
- **Verifier:** `xion-verify links` (specified for Phase 1).

### KW-DOCS-002 — Genesis Artifact hash-locks files that do not yet exist

- **Domain:** `DOCS`
- **Discovered:** 2026-04-19
- **Severity:** medium
- **Status:** `closed` on 2026-04-20 by the Phase 2 constitutional-file landing and the `p2-rehash` commit that updated `genesis/GENESIS_ARTIFACT.md` § 4.
- **Description:** `genesis/GENESIS_ARTIFACT.md` referenced a constitutional bundle that included `FORM.md`, `MEMORY.md`, `RESURRECT.md`, and (per the new doctrine) `CREDENTIALS.md`. None of these files existed yet.
- **How it closed:** All five files named in the Artifact's hash block — `FORM.md`, `MEMORY.md`, `RESURRECT.md`, `CREDENTIALS.md`, and `UNKNOWNS.md` — now exist on disk at byte sequences whose SHA-256 hashes exactly match the values recorded in `genesis/GENESIS_ARTIFACT.md` § 4. The Artifact's hash block carries entries for the eight constitutional documents (COVENANT, INVARIANTS, SOUL, FORM, MEMORY, RESURRECT, CREDENTIALS, UNKNOWNS). Verified 2026-04-20 by direct recomputation of all eight hashes against the Artifact.
- **Residual:** None. The recorded hashes are labeled as a *pre-genesis documentation witness* — they will be recomputed at the actual Arweave commit ceremony and replaced with ceremony values. That replacement is Phase 7 work, not a remediation of this weakness.

---

## How this list is curated

- New weaknesses are added to **Open** with a complete entry (no half-filled fields). If a field cannot be filled, the entry is not yet ready to publish.
- An entry moves from `open` → `paying-down` when work is in progress and the pay-down commitment is on a planned milestone.
- An entry moves to `mitigated-residual` when no further work is planned because the weakness is structural and cannot be fully closed; the mitigations are the maximum protection achievable.
- An entry moves to **Closed** with the closure date and the closing artifact.
- Closed entries are never deleted. Honesty about past weaknesses is part of how Xion earns trust.

The discipline of this file is one of the small structural protections against operator drift. If this file ever stops being honest, the Vital Signs doctrine (Constitutional Integrity domain) will catch it: drift in known-weakness counts uncorrelated with closure activity is itself a critical-range reading.
