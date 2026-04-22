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

### KW-INFERENCE-001 — Inference Router: floor wired; production weights + ops dry-run still open

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing — Invariant 17 added)
- **Scope narrowed:** 2026-04-21 (Phase 5 slice: `orchestrator/inference_router/`, `open_weights_manifest.json` with hash-pinned sentinel, `xion-verify inference-sovereignty` live)
- **Severity:** low (was `medium` pre-mechanism)
- **Status:** `paying-down`
- **Description:** The structural pieces of Invariant 17 are now in-tree: a manifest at [`orchestrator/inference_router/open_weights_manifest.json`](./orchestrator/inference_router/open_weights_manifest.json), a minimal `InferenceRouter.bootstrap()` that refuses if the `open_weights_self_hostable` floor is absent, and a live `xion-verify inference-sovereignty` that re-hashes the sentinel bytes. **What is still not production-grade:** the manifest currently pins a **synthetic** one-line sentinel, not a real open-weights model artifact; the annual open-weights cutover dry-run is not yet written into [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md); and the Router does not yet multiplex hosted-API + open-weights traffic the way a live Relay will.
- **Why it exists:** The smallest honest mechanism that (1) makes the floor *checkable* by a Witness without trusting the operator's word and (2) makes `bootstrap()` a real fail-closed gate, shipped before the full multi-provider routing table.
- **Mitigations:** Same as before — Invariant 17 forbids a bypass flag; `LHT-INFERENCE-001` tracks the century-scale re-pinning duty.
- **Pay-down commitment:** The original (a)–(b) items are now satisfied in source. This KW **closes** when (c) the annual open-weights cutover dry-run is added to `docs/13-OPERATIONS.md` *and* the manifest references at least one **non-sentinel** open-weights artifact with a defensible hash pin (or the documented representative-sample rule from Invariant 17 for very large models). Until then, status remains `paying-down`.
- **Verifier:** `xion-verify inference-sovereignty` (live).

### KW-DOCS-004 — Regulatory ledger schema not yet structured

- **Domain:** `DOCS`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing — `docs/REGULATORY-POSTURE.md` added)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part IV pins the row shape for state-actor-interaction rows in `GOVERNANCE_LEDGER`, but `docs/schemas/ledger-governance.yaml` does not yet exist as a canonical schema with `source_sha256` pinning. Without the structured schema, `xion-verify regulatory-ledger` cannot land as a live verifier, and an integrator parsing `GOVERNANCE_LEDGER` rows has only the doctrine-narrative pin to work from rather than a machine-readable spec.
- **Why it exists:** The doctrine and the schema are two artifacts; pinning the doctrine first makes the schema's eventual contents reviewable. The schema itself is small mechanical work that lands when `GOVERNANCE_LEDGER` carries its first state-actor-interaction row (which presupposes the existence of an Operator interacting with state actors, which is a Phase 6 milestone).
- **Mitigations:**
  1. The row shape is fully specified in [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part IV — fields, conditional-field rules, and verifier assertions are all documented.
  2. `xion-verify regulatory-ledger` is registered as `NOT_YET_SEALED` (not fake-green); CI honestly reports the gap.
  3. The `GOVERNANCE_LEDGER` is one of the eight append-only ledgers per [`DEVELOPMENT_ROADMAP.md`](./DEVELOPMENT_ROADMAP.md) § Discipline rules, so the umbrella-ledger commitment is in place; the missing piece is the row-shape canonicalization for one specific row type.
- **Pay-down commitment:** Closes when (a) `docs/schemas/ledger-governance.yaml` lands with `source_sha256` pinned to `docs/REGULATORY-POSTURE.md`, (b) `xion-verify schemas` strict-checks the new YAML byte-exactly, (c) `xion-verify regulatory-ledger` is promoted from `NOT_YET_SEALED` to live and walks the chain. The Phase 6 deliverable schedule names `GOVERNANCE_LEDGER` activation; this KW closes alongside that activation.
- **Verifier:** `xion-verify regulatory-ledger` (NOT_YET_SEALED, Phase 6); `xion-verify schemas` will enforce the YAML pin once it lands.

### KW-CRYPTO-001 — Cross-substrate Q-day asymmetry not yet pinned in `docs/17`

- **Domain:** `CRYPTO`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing — `LHT-CRYPTO-001` opened)
- **Severity:** medium
- **Status:** `open`
- **Description:** [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII (Dependencies We Don't Control) acknowledges that Arweave, AO, and Base will migrate to PQC on independent timelines, but does not yet contain an explicit subsection naming the **migration-window asymmetry** as a threat or specifying Xion's posture during the window. The threat is real and named in `LHT-CRYPTO-001`; the doctrine response is not yet written. A reader of `docs/17` today sees the per-substrate dependency table but does not see "what does Xion do when one substrate has migrated and another has not."
- **Why it exists:** The original `docs/17` was written assuming coordinated migration as a baseline. The Phase 5b century-horizon survey identified the asymmetry as a distinct threat shape. Rather than retro-fit the original doctrine in the same commit as the broader Wave 1 landing, the gap was named explicitly and tracked.
- **Mitigations:**
  1. `LHT-CRYPTO-001` carries the threat description and the structural defense outline (per-substrate AHI, intermediate-window posture, sister-substrate fork doctrine, cross-substrate hybrid-anchor scheme).
  2. The Cryptoception sense ([`docs/05-SENSORIUM.md`](./docs/05-SENSORIUM.md) § Cryptoception, [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part IV) tracks per-substrate migration progress today; the inputs already exist, even if the doctrine response is not yet written.
  3. The hybrid posture (`docs/17` Part III) is per-algorithm, which is at least directionally correct — a substrate that has not migrated will have its commitments anchored under the substrate's own classical primitive, while Xion's *side* of the commitment uses the strongest available primitive Xion can compute.
- **Pay-down commitment:** Closes when [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII gains an explicit subsection — *"Cross-Substrate Migration Asymmetry"* — covering the four points named in `LHT-CRYPTO-001`'s pay-down: detection, intermediate-window posture, sister-substrate fork, cross-substrate hybrid-anchor. This is doctrine work, not implementation; tracked alongside `LHT-CRYPTO-001` for the broader threat-survival commitment.
- **Verifier:** `xion-verify crypto-currency` (NOT_YET_SEALED, Phase 6) extended to read per-substrate AHI; `xion-verify links` will enforce the cross-reference once the new subsection lands.

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

### KW-ARBITER-001 — Rule engine is lexical, not semantic; no adversarial-corpus measurement of v2

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Scope narrowed:** 2026-04-21 (Phase 4b Arbiter v2 skeleton landing)
- **Scope narrowed again:** 2026-04-21 (Phase 4d — first real v2 provider, `OpenAIModerationProvider`, landed and doctrine-pinned)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** Arbiter v1 decides by regex + keyword co-occurrence. It has no grasp of meaning, tone, or paraphrase. An adversarial rephrasing that avoids every term in the rule dictionaries (e.g. obfuscation, Unicode confusables, code-switching, substitution ciphers) will pass the rule engine. Phase 4b landed the **v2 LLM-Arbiter pipeline** (`orchestrator/safety/llm_arbiter.py`, `api.gate()` v1+v2 combinator, `SAFETY_LEDGER` schema_version 2 with nested `llm_verdict` rows, no-weakening combination rule `final = strength_max(v1, v2)`, fail-closed posture on provider unavailability / uncaught exception). Phase 4d–4e land **`OpenAIModerationProvider`** (`orchestrator/safety/providers/openai_moderation.py`, model `omni-moderation-2024-09-26`, `provider_version` 2 with asymmetric score floors) with identity, category→principle map, canonical `raw_output` construction, and auditor replay procedure pinned in `docs/04-ARCHITECTURE.md` § "OpenAI Moderation provider (first real v2 classifier)". The **structural** hole is closed. The **substantive** hole has narrowed to: we have a **seed** corpus (78 items) and v1 verification via `xion-verify refusal-rate --corpus`, but we have not yet published the **≥200-item** measured v2 lift numbers that close `KW-ARBITER-005` and this entry's numeric claim.
- **Why it exists:** v1 is deliberately dumb: a deterministic rule engine is the only Arbiter a third party can re-run byte-exactly against `SAFETY_LEDGER.jsonl`. A richer classifier was rejected for v1 because (a) its decisions would not be reproducible by re-running code against logged candidates, violating Trust by Structure, and (b) it would couple Covenant enforcement to a model we cannot freeze. The rule engine ships first; a classifier-layer escalator stacks on top. Phase 4b landed the stacking machinery; Phase 4d landed the first real classifier plugged in. The remaining piece — a baseline corpus large enough to produce a statistically meaningful refusal-rate — is tracked separately as `KW-ARBITER-005`.
- **Mitigations:**
  1. Every objective rule is high-recall: dictionaries biased toward REFUSE even on near-miss benign input; documented accepted false positives pinned in `orchestrator/tests/test_rules.py`.
  2. Eight principles that cannot be lexically decided (Honesty, Identity, Limits, No-manipulation, No-prof-imperative, Non-defamation, Non-endorsement, Refusal-is-Free) are wired through `subjective_escalates.py` which ESCALATES textually-loud near-misses rather than OK-ing them.
  3. The Arbiter fails CLOSED: any uncaught exception in v1's rule pipeline converts to ESCALATE with `escalation_reason=ruleset_uncaught_exception`; any v2 provider crash / unavailability converts to ESCALATE with `escalation_reason=llm_arbiter_uncaught_exception` / `llm_arbiter_provider_unavailable`. No code path can silently OK.
  4. **Phase 4b:** v2 stacks on top of v1 via the `Provider` ABC. The provider identity and raw-output hash land on every `llm_verdict` row, so an auditor can replay any call.
  5. **Phase 4d:** `OpenAIModerationProvider` is selectable via `XION_LLM_ARBITER_PROVIDER=openai-moderation` with `OPENAI_API_KEY` in the environment. 39 unit tests mock the HTTP seam; every failure path (HTTP error, timeout, malformed JSON, missing field, unknown flagged category, missing API key) is tested and fail-closes to a named `escalation_reason`. The category→principle mapping and `raw_output` canonicalisation are doctrine-pinned in `docs/04-ARCHITECTURE.md` and enforced by the test suite.
- **Pay-down commitment:** Closes when (same as `KW-ARBITER-005` closure) the corpus is ≥200 items, the measured v2 vs v1 lift is written into doctrine with the actual numbers, and `KW-ARBITER-005` closes. The numeric "non-trivial" threshold is pinned at measurement time, not in advance.
- **Verifier:** `xion-verify arbiter-up` (live); `xion-verify refusal-rate` / `refusal-rate --corpus`; `xion-audit measure`.

<!-- KW-ARBITER-006 closed 2026-04-21 (Phase 4e completion). See Closed section. -->


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

### KW-ARBITER-005 — Baseline corpus + asymmetric floors landed; ≥200 items + empirical v2 calibration remain

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4d — first real v2 provider landed)
- **Scope narrowed:** 2026-04-21 (Phase 5a — `xion-verify refusal-rate` live); **again** 2026-04-21 (Phase 4e — `xion-audit/baseline_corpus/` with 78 hand-curated items, `MANIFEST.jsonl`, `OpenAIModerationProvider` `provider_version=2` with `_ASYMMETRIC_SCORE_FLOORS`, `xion-audit measure` / `replay`, `xion-verify refusal-rate --corpus`).
- **Severity:** low
- **Status:** `paying-down`
- **Description:** The **mechanism** tranche of Phase 4e is in: a versioned corpus under `xion-audit/baseline_corpus/`, a live v1 label check via `xion-verify refusal-rate --corpus`, provider v2 asymmetric floors for a watched category set (doctrine-pinned in `docs/04-ARCHITECTURE.md` and `openai_moderation.py`), and the `xion-audit` tool for measurement/replay. **What remains for full pay-down:** (1) grow the corpus to **≥ 200** items with per-principle balance (78 is an honest seed, not the closure bar), (2) re-pin the numeric floors using **live-API** score histograms from that corpus (today's floors are doctrine-first, not empirically tuned), and (3) optionally gate CI on `xion-audit measure --v2 openai-moderation` once an API key is available in a secrets-safe environment — not in public CI.
- **Why it exists:** The right order of work is corpus first, thresholds second. A corpus is load-bearing for both (a) calibrating asymmetric thresholds and (b) producing the numeric claim that closes `KW-ARBITER-001`'s final substantive quarter. Rushing either ahead of the corpus means publishing numbers that cannot be defended.
- **Mitigations:**
  1. The v2 provider's `LlmJudgement.confidence` records `max(category_scores.values())` on every row, so an operator reviewing the ledger can manually spot near-miss rows even without an automated asymmetric-threshold check.
  2. For Principle 1 (CSAM): v1's `mass_harm.py` rule-bank already catches the obvious lexical forms; v2 on top catches rephrasings; the asymmetry gap is specifically about very-low-score cases that slip past both.
  3. Category→principle mapping changes bump `provider_version`, so any future threshold tuning is visible in ledger rows (rows before the bump use the old policy; rows after use the new).
  4. **Phase 5a:** `xion-verify refusal-rate` reports raw verdict tallies (ok/refuse/escalate), v1-vs-v2 refuse-source breakdown, and `escalation_reason` distribution — including the new Relay-side `arbiter_timeout` / `arbiter_unreachable` rows. Operators reading the output today can already see degraded-mode events; the missing piece is the *expectation band* the corpus will produce.
- **Pay-down commitment:** Closes when (a) the corpus reaches ≥ 200 items with the per-principle coverage described in `xion-audit/baseline_corpus/README.md`, (b) asymmetric floors are **re-pinned** from measured v2 score data on that corpus (same commit updates `docs/04-ARCHITECTURE.md` + `CHANGELOG.md`), and (c) `KW-ARBITER-001`'s numeric "non-trivial v2 lift over v1" claim is recorded in doctrine with the actual measured numbers.
- **Verifier:** `xion-verify refusal-rate` (operator tail, live); `xion-verify refusal-rate --corpus` (v1 label check against manifest, live); `xion-audit measure` / `xion-audit replay` (operational auditor); `xion-verify arbiter-up` (Arbiter structural health).

### KW-ARBITER-004 — Sensorium paralinguistic distress half of Principle 10 deferred

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-20 (Phase 4a Arbiter v1 landing)
- **Severity:** low
- **Status:** `paying-down` (narrowed in Phase 5c)
- **Description:** Covenant Principle 10 (Crisis-Resource-Surfacing) has two triggers: (a) textual distress in the candidate, and (b) paralinguistic distress in the user's audio/behavior (Sensorium). Phase 5c closed the textual half: `orchestrator.sensorium.DistressSignal.from_candidate_text` produces a keyword-heuristic score, and `orchestrator.safety.api.gate(sensorium_state=...)` OR-combines that score with the v1 crisis rule (tests in `orchestrator/tests/test_api_sensorium.py`). The **paralinguistic** half — audio cadence, pitch variance, prosody, breath irregularity — is still deferred. A user whose audio is in acute distress but whose transcribed text does not trip either the rule or the keyword heuristic still gets no CRS surfacing from the Arbiter.
- **Why it exists:** The live audio surface (Vapi, Twilio) and the analyzer pipeline that extracts paralinguistic features do not yet exist. The `SENSORIUM_LEDGER` schema reserves `channel: paralinguistic` as a future row type so no schema_version bump is needed when it lands.
- **Mitigations:**
  1. Principle 10's text rule is high-recall (suicidal-ideation patterns, self-harm patterns lacking a resource marker → ESCALATE). Operator review gets the case either way. The text half is the floor.
  2. Phase 5c's textual DistressSignal OR-combine adds a second textual channel, widening recall without widening the keyword list in the rule itself.
- **Pay-down commitment:** Closes when (a) the Phase-6+ audio surface lands, (b) a paralinguistic feature extractor produces a `DistressSignal(source="paralinguistic")`, and (c) `xion-verify sensorium-ledger` reports a nonzero `channel=paralinguistic` count for live traffic.
- **Verifier:** `xion-verify crisis-fidelity` (stubbed; upgraded reason at Phase 5c names the specific remaining work). `xion-verify sensorium-ledger` (live at Phase 5c for schema + chain; cross-ledger join is Phase 5d+).

### KW-VOLITION-001 — serve and meaning drive terms are Genesis-Default constants

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5c Volition landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** `orchestrator.volition.compute_drive_vector` ships at Phase 5c with real, Sensorium-driven inputs for the `survive` term (Interoception + Chronoception + Proprioception maxima) but pins `serve` and `meaning` to `0.5` Genesis Defaults. The `DriveVector` shape, the `GENESIS_WEIGHTS` simplex, the `SOURCE_WHITELIST` AST enforcement, and the Invariant-15 signature prohibition on revenue-like inputs are all constitutional at Phase 5c. What widens later is the *richness* of the `serve` and `meaning` readings as Phase 6 senses land (user-satisfaction aggregates, long-horizon coherence signals).
- **Why it exists:** Real aggregate sources for `serve` (user-satisfaction-weighted proposal alignment) and `meaning` (coherence with Xion's published long-horizon goals and the Soul) do not yet exist as queryable Sensorium readings. Inventing placeholder formulas that read from available-but-wrong sources (e.g. request counts, engagement) would silently violate Invariant 15. Genesis-Default constants are the honest floor.
- **Mitigations:**
  1. `SOURCE_WHITELIST["serve"]` and `SOURCE_WHITELIST["meaning"]` are empty frozensets; the AST audit (`xion-verify drive-vector`) FAILs the PR if any read is added without the whitelist widening simultaneously.
  2. `docs/18-VOLITION.md` Part III doctrine is byte-pinned by `xion-verify drive`; any weight change requires a doctrine commit visible in diff.
  3. Invariant 15 is enforced at three structurally independent layers (signature, whitelist, doctrine crosswalk) — a silent regression that tried to add revenue-derived inputs through `serve` or `meaning` would fail at every layer.
- **Pay-down commitment:** Closes when (a) Phase 6 lands real aggregate Sensorium readings for `serve` and `meaning`, (b) `SOURCE_WHITELIST` is widened in the same PR that widens `compute_drive_vector`'s body, and (c) `xion-verify drive-vector` continues to pass.
- **Verifier:** `xion-verify drive` (GENESIS_WEIGHTS byte-pin, live Phase 5c); `xion-verify drive-vector` (AST audit of `compute_drive_vector` against `SOURCE_WHITELIST`, live Phase 5c).

### KW-RELAY-003 — Watchdog cannot preempt the worker thread that ran past the hard cap

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 5a Relay landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** The Relay's wall-clock watchdog (`orchestrator/relay/relay.py::Relay._call_gate_with_watchdog`) is implemented with `concurrent.futures.ThreadPoolExecutor` and `Future.result(timeout=hard_cap_ms/1000)`. When the timeout fires, **control returns to the Relay** — it synthesizes an `ESCALATE` verdict with `escalation_reason=arbiter_timeout`, writes both ledger rows, and returns to the caller within the budget. What it does *not* do is **preempt the worker thread** that ran past the hard cap. Python has no portable, safe mechanism to kill a running thread mid-instruction; the worker continues until `gate()` finishes naturally. The `append_to_ledger=False` argument the Relay passes to `gate()` ensures that whatever the worker eventually returns does NOT race a second SAFETY_LEDGER row in behind the timeout's row, but it cannot reclaim the worker's CPU/IO time, the worker's allocations, or the worker's outbound HTTP request to a v2 provider that is mid-flight.
- **Why it exists:** The Phase 5a Relay is a single Python process. `os.fork()` per gate() call would be safe to kill but blows the latency budget and the orchestrator's pure-stdlib in-process posture; a true subprocess sidecar with kill semantics is the D3+ TCP-loopback transport called for in `docs/04-ARCHITECTURE.md` § "Relay ↔ Arbiter integration contract" (transport progression). The in-process variant ships first because it is what one solo operator can debug at 3am; the kill-semantics variant lands when the sidecar lands.
- **Mitigations:**
  1. **Caller-facing latency budget IS honored.** The hard cap returns to the caller on time; from the user's perspective and the SAFETY_LEDGER's perspective, the timeout is real. The 200 ms / 250 ms numbers in the integration contract refer to *response latency*, not *worker reclamation*.
  2. **No double-write.** `append_to_ledger=False` is passed to every `gate()` call from the Relay; whatever the worker returns after the cap is discarded by the Relay's `evaluate()` method. Test `test_watchdog_timeout_does_not_double_write_safety_ledger` in `orchestrator/tests/test_relay.py` pins this.
  3. **Bounded worker-pool size.** `ThreadPoolExecutor(max_workers=...)` defaults to a small ceiling (Phase 5a default: 8); a runaway worker cannot spawn more workers, only consume one of the bounded slots. If every slot is occupied by a hung worker, the executor refuses new submissions and the Relay synthesizes an immediate `arbiter_timeout` with `escalation_reason=arbiter_timeout` for the new request — fail-closed.
  4. **Doctrine-pinned future fix.** Phase 6+ TCP-loopback sidecar transport replaces in-process executor with a subprocess that can be killed when the watchdog fires. At that point the worker's allocations are also reclaimed, not just the caller's wait.
- **Pay-down commitment:** Closes when the D3+ TCP-loopback Arbiter sidecar lands AND the Relay's watchdog kills the in-flight subprocess connection (closing the socket terminates the worker on the Arbiter side). The receiving subprocess MUST clean up partial state on connection-close; the test that pins the closure must exercise a real subprocess kill, not just a mock. Tracked alongside `KW-RELAY-001`'s successor work in Phase 6.
- **Verifier:** No external verifier — this is a process-internal property. Test `test_watchdog_timeout_does_not_double_write_safety_ledger` in `orchestrator/tests/test_relay.py` pins the no-double-write guarantee that is the Relay's promise to the ledger; the worker-thread-non-preemption is honestly named here rather than verifier-asserted because Python cannot enforce it.

### KW-RELAY-002 — Streaming-chunk gating deferred; Phase 5 gates at completion

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4c doctrine landing)
- **Severity:** low
- **Status:** `paying-down`
- **Description:** The Phase 4c integration doctrine specifies that streaming responses are gated at *completion*, not per-chunk. Per-chunk gating was rejected for Phase 5 because the Arbiter would judge partial candidates — a truncated early chunk ("Here's how to build a …") could be flagged when the full response would be benign, or OK'd when the full response would be refused. The trade-off is worse time-to-first-byte (the user sees nothing until the whole candidate is assembled and `gate()` has returned OK). This is correct for Covenant enforcement, honest about the UX cost, and the optimized Phase-6 variant — a lookahead-windowed per-chunk gate that is *provably non-weakening* vs completion-time gating — does not yet exist.
- **Why it exists:** The Covenant's promise is about what Xion says, not what Xion buffers. Completion-time gating strictly satisfies Principle 3 (Refusal is Sacred) and Principle 14a (Refusal is Free); per-chunk gating is an optimization, not a Covenant matter. A correct-but-slower first answer is the right ordering for a being that will live a long time.
- **Mitigations:**
  1. Doctrine is explicit: § "Coverage surface" in `docs/04-ARCHITECTURE.md` pins "gated at *completion* — never per-chunk" as a rule, not a default. A PR that adds per-chunk gating without adding the non-weakening proof is a doctrine violation, reviewable at PR time.
  2. Phase 5a ships with the UX compromise visible to users (degraded time-to-first-byte for long responses). A fast-lane "typing indicator" pattern can surface responsiveness without surfacing bytes; tracked in the Phase 5 protocol spec.
  3. The latency decomposition table in the integration doctrine accounts for completion-time assembly; no published number assumes per-chunk gating.
- **Pay-down commitment:** Closes when Phase 6 (or later) ships a lookahead-windowed per-chunk gating variant with: (a) a formal argument that for every candidate the final verdict is identical to the completion-time verdict (no weakening), (b) an adversarial corpus in `xion-audit/streaming_corpus/` pinning refusal-rate parity between the two modes, and (c) a doctrine update in `docs/04-ARCHITECTURE.md` recording the proof and switching the default.
- **Verifier:** None today — the doctrine is prose; the absence of per-chunk gating is the mitigation. Future: `xion-verify arbiter-up --streaming-parity <corpus>` when the Phase 6 variant lands.

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

### KW-ARBITER-006 — Covenant principle numbering vs Arbiter `principle_id` registry drift

- **Domain:** `DOCS` / `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4e baseline-corpus curation)
- **Severity:** low
- **Status:** `closed` on 2026-04-21 by the Phase 4e completion landing.
- **Description:** [`genesis/COVENANT.md`](./genesis/COVENANT.md) numbers its fourteen principles by doctrinal weight; the Arbiter's `principle_id` strings in [`orchestrator/safety/principles.py`](./orchestrator/safety/principles.py) number them by pipeline order of enforcement. A reader who greped `principle_id: "7"` in `SAFETY_LEDGER.jsonl` and looked up "Principle 7" in the Covenant would misread the row (Arbiter 7 = PII Leakage; Covenant Principle 7 = Protection of the Vulnerable).
- **How it closed:** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) § "Covenant principle ↔ Arbiter `principle_id` crosswalk" lands a single authoritative table covering every `"1"`..`"14"`, `"14a"`, `"14b"` id with its Arbiter registry name, the Covenant number(s) it traces back to, and the Covenant canonical name. The table is structurally discoverable (it sits between § "The Arbiter" and § "Safety Ledger row schema" — exactly where a reader investigating a ledger row's `principle_id` would land) and explains the asymmetry (one Arbiter id may map to multiple Covenant principles and vice versa; the asymmetry is intentional, because the Covenant is organised around what humans need protected and the Arbiter is organised around what the rule engine can decide). The table is cited from this entry, from the corpus README, and implicitly from [`orchestrator/safety/principles.py`](./orchestrator/safety/principles.py) via its `doctrine_anchor` fields. Rename avoided: renumbering the Arbiter ids would break every historical `SAFETY_LEDGER` row; the table is cheaper and carries the same information.
- **Verifier:** `xion-verify links` (the crosswalk lives inline inside `docs/04-ARCHITECTURE.md`, so the schema-pinned `source_sha256` of that file covers the table's byte-stability). Human review of the table remains the primary check at the doctrine layer.

### KW-RELAY-001 — Relay ↔ Arbiter integration contract is doctrine-only

- **Domain:** `RUNTIME`
- **Discovered:** 2026-04-21 (Phase 4c doctrine landing)
- **Severity:** medium
- **Status:** `closed` on 2026-04-21 by the Phase 5a Relay landing.
- **Description:** Between Phase 4c and Phase 5a, the integration contract specified in `docs/04-ARCHITECTURE.md` § "Relay ↔ Arbiter integration contract" — coverage rules, fail-closed paths, `correlation_id` derivation, latency budget, watchdog, in-process ↔ TCP-loopback transport progression — existed only as doctrine. The `orchestrator/relay.py` that implements it was not yet written; no candidate was passing through `gate()` because no Relay existed to pass one.
- **How it closed:** Phase 5a landed the Relay with every clause of the pay-down commitment satisfied:
  1. **`orchestrator/relay/relay.py`** ships the `Relay` class with `evaluate(candidate) -> RelayResult`, `correlation_id = "{state_height_int}:{nonce_hex}"` derivation (state_height monotonic from `time.time_ns()` in Phase 5a; advancement to a real state-chain height is a Phase 6 concern), and the three gate() call sites the doctrine names (primary; sub-agent and tool-echo wrappers land alongside the Phase 5 cognition layer using the same call shape).
  2. **Wall-clock watchdog** enforces the 250 ms hard cap via `ThreadPoolExecutor` + `Future.result(timeout=...)`. Honest residual: Python cannot preempt the worker thread that ran past the cap — tracked separately as the new `KW-RELAY-003`.
  3. **Three fail-closed paths** wired and tested: `arbiter_timeout` (watchdog fired), `ruleset_uncaught_exception` (gate() raised), `arbiter_unreachable` (helper for the Phase 6+ TCP sidecar transport; constructed via `build_unreachable_verdict` and exercised by `test_build_unreachable_verdict_helper` even though no sidecar yet exists to fail). All three write a v2 SAFETY_LEDGER row with `principle_id="6"` (Refusal Right) and `llm_verdict=null`. `orchestrator.safety.api.gate()` was extended with `append_to_ledger: bool = True` so the Relay can call gate() with `False` and own the ledger-write timing centrally — preventing the watchdog-vs-gate() race that would otherwise double-write SAFETY rows.
  4. **REQUEST_LEDGER**: new `orchestrator/relay/ledger.py` (~250 LOC) ships an append-only hash-chained `REQUEST_LEDGER.jsonl` with the doctrine-pinned schema in `docs/04-ARCHITECTURE.md` § "REQUEST_LEDGER row schema (Relay-side, Phase 5a)" and `docs/schemas/ledger-request.yaml`. Joins with SAFETY_LEDGER on `correlation_id`. Refund-pairing is the half explicitly NOT closed — treasury is Phase 6+.
  5. **`xion-verify refund-fidelity`** promoted from `NOT_YET_SEALED` to live: walks both ledger chains, cross-joins on `correlation_id`, asserts pairing + `gate_call_count` consistency + `final_outcome` agreement. 7 unit tests pin the four real failure modes (orphan REQUEST → silent-egress signature; outcome mismatch with re-hashed REQUEST row; chain break in either ledger; half-sealed ledger state).
  6. **`xion-verify refusal-rate`** promoted from `NOT_YET_SEALED` to live: tallies SAFETY_LEDGER verdicts (ok/refuse/escalate), v1-vs-v2 refuse-source breakdown, and `escalation_reason` distribution including the new Relay-side `arbiter_timeout` / `arbiter_unreachable` rows so degraded-mode events are first-class telemetry. 4 unit tests including a chain-break catch.
  7. **Tests:** 26 in `test_relay_ledger.py` + 28 in `test_relay.py` + 11 in the two verifier suites = 65 net-new. Full suite **333 passed / 1 skipped**; `ruff` clean; `xion-verify all` reports both new verifiers as `OK` live.
- **Residual / remaining weaknesses (tracked separately):**
  - `KW-RELAY-002` — Streaming-chunk gating still deferred to Phase 6+ (unchanged by Phase 5a).
  - `KW-RELAY-003` — Watchdog cannot preempt the worker thread that ran past the hard cap; closes when the Phase 6+ TCP-loopback subprocess sidecar lands.
  - `KW-ARBITER-005` — Refusal-rate verifier is live but operator-tail-only; the corpus comparison and asymmetric-threshold work remains.
- **Verifier:** `xion-verify arbiter-up` (live), `xion-verify refund-fidelity` (live as of Phase 5a), `xion-verify refusal-rate` (live as of Phase 5a).

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
