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
- **Description:** The doctrine corpus legitimately references artifacts that will land in later phases (`docs/legal/`, `docs/schemas/levels.yaml`, `docs/schemas/`, `ao/xion_core.lua`, `genesis/RITUALS.md`). Left unchecked, this is the same failure mode `KW-DOCS-001` named (silent drift); if an artifact is deferred repeatedly, the reference rots into a lie.
- **Why it exists:** Doctrine is written ahead of implementation on purpose — that is how property comes before mechanism. But writing ahead creates a window during which cross-references point at nothing.
- **Mitigations:** Every forward-unresolved target is enumerated in [`xion-verify/ALLOWED_FORWARD_REFS.txt`](./xion-verify/ALLOWED_FORWARD_REFS.txt), with a roadmap phase and a one-line reason. `xion-verify links` passes if and only if every broken target is either in that file or was always broken (in which case it fails loud). A third-party auditor can diff the allowlist across commits: lines only disappear when the artifact lands, or appear alongside a new entry here.
- **Pay-down commitment:** Each allowlist entry closes when its named phase delivers the artifact; when the last entry is removed, this KW closes. Phase deadlines are: `docs/schemas/*` by end of Phase 1; `genesis/RITUALS.md` by Phase 2b; `docs/legal/`, `ao/xion_core.lua` by Phase 6. A phase ending without the artifact landing is promoted to a new `KW-DOCS-###` entry and a CHANGELOG note.
- **Verifier:** `xion-verify links` — passes today because the five legitimate forward refs are explicitly allowlisted; every other broken reference is a fatal FAIL.

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
- **Severity:** **fatal** (do not deploy to mainnet)
- **Status:** `paying-down` (sources unchanged; documented; remediation queued in `DEVELOPMENT_ROADMAP.md` Phase 3 task `p3-rotation`)
- **Description:** The current `contracts/xion-token/EmissionController.sol` stores `aoCoreAuthority` as `immutable` and `contracts/imprint/Imprint.sol` stores `engagementAttestor` as `immutable`. If the corresponding key is ever lost, compromised, or rotated, the contract becomes either bricked or hostile, and there is no recovery path inside the contract itself.
- **Why it exists:** "Immutable" was used as shorthand for "constitutional" by the original author. The two are not the same: a constitutional property is a promise that *some* authorized key always controls the contract; an immutable address is a promise that *one specific* key always controls it. Conflating them is the most expensive single mistake in the current contract corpus.
- **Mitigations:** None in source today. The contracts are pre-deployment, so there is no live exposure. The plan-doctrine-layer rotation lattice (Hot 24h relay-auth → Warm 7d Operator multisig 2-of-3 → Cold 30d Root 3-of-5 Shamir) is documented in `docs/13-OPERATIONS.md` and `docs/04-ARCHITECTURE.md`.
- **Pay-down commitment:** Closed when `rotateAuthority(address)` is added to both contracts behind a 7-day timelock under the `governance` role (which itself rotates only via 30-day timelock under Cold Root). Tracked as `p3-rotation` in `DEVELOPMENT_ROADMAP.md`. Must close before mainnet deployment.
- **Verifier:** `xion-verify authorities` (specified for Phase 1).

### KW-CONTRACTS-002 — `EmissionController.emitGenesis` does not commit to the seven-way split

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.5)
- **Severity:** **fatal** (do not deploy to mainnet)
- **Status:** `paying-down`
- **Description:** The genesis emission can be called with any seven amounts that sum to the genesis allocation. The constitutional split (per `docs/16-CURRENCY.md`) is not enforced in code. A compromised or malicious operator could mint the entire genesis to a single recipient.
- **Why it exists:** Recipients were intended to be flexible (the operator can choose where each bucket goes); proportions were not. Source treats both as parameters.
- **Mitigations:** None in source today. Currency doctrine documents the intended proportions in prose, which is not load-bearing protection.
- **Pay-down commitment:** Closed when `EmissionController` declares `uint256[7] constant GENESIS_SPLIT` and `emitGenesis` enforces `amounts[i] == GENESIS_SPLIT[i]` for each `i`. Recipients remain parameters. Tracked as `p3-genesis-split` in `DEVELOPMENT_ROADMAP.md`. Must close before mainnet deployment.
- **Verifier:** `xion-verify supply` (will fail loudly if total minted at genesis does not match the constant split).

### KW-CONTRACTS-003 — `Imprint.DECAY_BPS_PER_30D` conflicts with documented decay rate

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.2)
- **Severity:** high
- **Status:** `open`
- **Description:** `contracts/imprint/Imprint.sol` sets `DECAY_BPS_PER_30D = 200` (≈21.5% annual decay). `contracts/imprint/README.md` agrees with the code ("~2% per 30 days"); only `docs/16-CURRENCY.md:195` disagrees, documenting "5% per year". Choose one before mainnet; the constant cannot be changed on a live contract without invalidating every governance weight ever computed.
- **Why it exists:** The constant predates the doctrine that named the rate; nobody reconciled them.
- **Mitigations:** None in source today.
- **Pay-down commitment:** Closed when one of (`Imprint.DECAY_BPS_PER_30D` changed to 42, ~5%/year per doctrine — the recommended fix) or (docs revised to ~21.5%/year — recommended *only* if there is a strong reason to keep the higher decay). Tracked as `p3-decay` in `DEVELOPMENT_ROADMAP.md`. Recommended: code change.
- **Verifier:** `xion-verify covenant` will reject the artifact bundle if decay constant and currency doctrine disagree (audit-time check).

### KW-CONTRACTS-004 — Missing overflow check on `uint128(newBal)` in `Imprint.attest`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.4)
- **Severity:** medium
- **Status:** `open`
- **Description:** Cast from `uint256 newBal` to `uint128` storage slot lacks an explicit bounds check. Solidity 0.8+ checked arithmetic does not catch silent narrowing on `uint256 → uint128`.
- **Why it exists:** Author trusted that the practical balance ceiling would never approach `uint128.max`. True for any plausible mint pattern, but unverified.
- **Mitigations:** None in source today.
- **Pay-down commitment:** Closed when `require(newBal <= type(uint128).max, "imprint: overflow");` is added at the call site. Tracked as part of `p3-cleanup` in `DEVELOPMENT_ROADMAP.md`.

### KW-CONTRACTS-005 — Check-Effects-Interactions ordering in `EmissionController._enforceEraCap`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.6)
- **Severity:** medium
- **Status:** `open`
- **Description:** State writes occur after external interactions. Vector for re-entrancy is narrow because the only external call is to `XionToken._mint`, which itself does not re-enter, but the pattern is brittle for future maintainers.
- **Mitigations:** None in source today.
- **Pay-down commitment:** Closed when state writes are reordered to precede the external call. Tracked as part of `p3-cleanup`.

### KW-CONTRACTS-006 — Footgun comment in `LiquidityLock.sol` about future fee-claim

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.7)
- **Severity:** low (informational; misleads readers)
- **Status:** `open`
- **Description:** Comment hints at a future ability to claim accumulated fees from locked LP tokens. The contract does not implement it; the doctrine does not endorse it; the comment will be cited as evidence that the lock is escapable.
- **Mitigations:** None in source today.
- **Pay-down commitment:** Closed when comment is removed and any forward-looking notes about LP-fee policy are moved to `LIQUIDITY_LOCK_NOTES.md`. Tracked as part of `p3-cleanup`.

### KW-CONTRACTS-007 — Doc-code naming inconsistency in `XionToken`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.9)
- **Severity:** low
- **Status:** `open`
- **Description:** Header comment refers to `_totalMinted` but the actual storage variable is `totalMinted`. Cosmetic but the kind of inconsistency that produces 4am bug reports.
- **Mitigations:** None.
- **Pay-down commitment:** Header comment corrected. Tracked as part of `p3-cleanup`.

### KW-CONTRACTS-008 — Gas-grenade decay loop in `Imprint`

- **Domain:** `CONTRACTS`
- **Discovered:** 2026-04-19 (audit §3.3)
- **Severity:** medium (latent; depends on attestation cadence)
- **Status:** `open` (deferred to v2 unless trivial)
- **Description:** Iterative decay loop in `Imprint` becomes O(n) in the number of 30-day periods between attestations for a given holder. A holder who has not been attested in 5 years pays the gas for 60+ iterations.
- **Mitigations:** None in source today. Realistic worst case at launch is < 12 iterations.
- **Pay-down commitment:** Reviewed during `p3-tests` for cost characterization; if a closed-form decay is straightforward, replaced; otherwise documented and deferred to a v2 contract.

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
