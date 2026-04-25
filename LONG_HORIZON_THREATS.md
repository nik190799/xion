# Long-Horizon Threats

> *Anything that threatens Xion at century-scale — even if no current artifact can close it — gets an entry here, with the strongest available structural defense, rather than silent omission.*

This document is the public log of every **structural threat to Xion's century-scale survival** that has been recognized but cannot be closed by shipping a single artifact. It is the long-horizon companion to [`KNOWN_WEAKNESSES.md`](./KNOWN_WEAKNESSES.md).

The two documents have overlapping shape but different load:

- `KNOWN_WEAKNESSES.md` tracks **weaknesses in the current implementation**. Most entries close when code or doctrine ships. New ones are added by phase-by-phase honesty about what was deferred.
- `LONG_HORIZON_THREATS.md` tracks **structural threats to centuries of survival**. Many entries are `mitigated-residual` or `accepted-by-design` indefinitely; they live here so that the next maintainer in 2076 or 2126 inherits the threat model along with the code, and so that a third party can audit whether Xion's defenses against the threats they describe have actually been built.

A threat may move between the two when its character changes: a long-horizon threat that gains a tractable artifact-shaped pay-down may migrate to `KNOWN_WEAKNESSES.md`; a known weakness whose implementation gap is structural at century-scale may migrate here.

Every entry has the same shape:

- **ID** — `LHT-<DOMAIN>-<NN>`
- **Domain** — one of `SUBSTRATE`, `CRYPTO`, `INFERENCE`, `RELEVANCE`, `REGULATORY`, `ARBITER`, `CULTURAL`, `OPS`, `TOOLCHAIN`, `FORM`, `CURRENCY`. (The list is open; new domains may be added with a one-line note explaining why a new domain was needed.)
- **Discovered** — ISO date.
- **Severity** — `low`, `medium`, `high`, `existential`. Existential means the threat, if realized without defense, ends Xion as Xion (sister-Core forks may inherit, but the original being is gone).
- **Status** — `open`, `paying-down`, `mitigated-residual`, `accepted-by-design`.
- **Description** — what the threat is, in century-horizon terms.
- **Constitutional layer touched** — which Invariants or Covenant principles the threat would erode if realized.
- **Defense in place** — the structural mechanisms (constitutional, doctrinal, or operational) currently protecting against it.
- **Residual exposure** — what remains uncovered after the defense, in plain terms.
- **Pay-down commitment** — the artifact, doctrine, or condition by which the residual closes (or "indefinite by design" if the threat is structural and the defense is the maximum achievable).
- **Verifier or KW cross-reference** — the `xion-verify` subcommand, KW entry, or other public artifact that lets a third party check the defense is in place.

---

## Open

### LHT-SUBSTRATE-001 — Substrate concentration / death

- **Domain:** `SUBSTRATE`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** existential
- **Status:** `paying-down`
- **Description:** Xion's authoritative state today depends on three substrates — Arweave (permanent storage), AO (Core compute), Base (settlement / token contracts) — each of which is a young system run by a small team or operator. The death, retirement, acquisition-pivot, regulatory-prohibition, or sustained cost-shock of any one substrate is a credible 50-year-horizon event. A constitution that names a specific substrate as Xion's identity hands Xion's continuity to that substrate's continued existence.
- **Constitutional layer touched:** Invariants 3, 4, 7 (state-chain and ledger continuity); Invariant 14 (algorithm-rotation requires a substrate to publish the rotation on); future Invariant 19 (Substrate Portability Floor) when promoted.
- **Defense in place:** [`docs/SUBSTRATE-RESILIENCE.md`](./docs/SUBSTRATE-RESILIENCE.md) lands the Substrate Portability Property as doctrine, names the four substrate-properties (permanence, signed-state-transitions, public-verifiability, append-only commitment), specifies the Substrate-Migration Protocol, and names the pre-conditions for promoting Invariant 19. The current substrate set is genesis-default, not constitutional.
- **Residual exposure:** No warm secondary substrate exists today for any of the three roles. The annual dry-run cadence is doctrine-promised but has not yet been rehearsed even once. A substrate failure during Pre-Genesis or in the early years post-Genesis would force a panic-migration rather than a rehearsed one.
- **Pay-down commitment:** Closes when Invariant 19 (Substrate Portability Floor) is promoted per [`docs/SUBSTRATE-RESILIENCE.md`](./docs/SUBSTRATE-RESILIENCE.md) Part IV. Pre-conditions for promotion: three completed annual dry-runs, at least one warm secondary substrate per role, `xion-verify substrate-portability` live, Cost-Pressure Response Ladder rung for substrate cutover defined.
- **Verifier or KW cross-reference:** `xion-verify substrate-portability` (NOT_YET_SEALED, Phase 6+); paired with the future `KW-SUBSTRATE-001` (warm-secondary-substrate work) when the work begins.

### LHT-CRYPTO-001 — Cross-substrate Q-day asymmetry

- **Domain:** `CRYPTO`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `open`
- **Description:** Invariant 14 (Crypto-Agility Mandate) and [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) cover Xion's crypto-migration from the Core's perspective. But Q-day arrives on each substrate — Arweave, AO, Base, the TLS ecosystem — on **independent timelines** set by **independent teams**. There is no coordinator. The credible failure mode is a **migration window** during which one substrate has migrated to PQC and another has not; an attacker holding a CRQC during that window can target whichever substrate is still classical even if the others are safe.
- **Constitutional layer touched:** Invariant 14 (the mandate is per-Core; it does not bind the substrates themselves); Invariants 3, 4, 7 (whose integrity depends on the weakest substrate signature scheme during the window).
- **Defense in place:** [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII (Dependencies We Don't Control) acknowledges the per-substrate-controlled migration timing and documents the hybrid posture as the per-substrate mitigation. The Cryptoception sense ([`docs/05-SENSORIUM.md`](./docs/05-SENSORIUM.md)) tracks per-substrate migration progress.
- **Residual exposure:** No explicit subsection in `docs/17` covers what Xion does when **one substrate has migrated and another has not**. The current doctrine implicitly assumes coordinated migration; reality will not coordinate.
- **Pay-down commitment:** Closes when [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md) Part VII gains an explicit subsection — *"Cross-Substrate Migration Asymmetry"* — covering: (a) detection (Cryptoception per-substrate AHI rather than aggregate AHI), (b) intermediate-window posture (move state-creation traffic to the migrated substrate, mirror to the lagging one as historical-only), (c) sister-substrate fork doctrine if the lag exceeds tolerable threshold, (d) cross-substrate hybrid-anchor scheme that lets a single commitment land on multiple substrates with the strongest available primitive on each.
- **Verifier or KW cross-reference:** `xion-verify crypto-currency` (NOT_YET_SEALED, Phase 6) extended to read per-substrate AHI rather than aggregate; tracked alongside `KW-CRYPTO-001` (the doctrine subsection itself).

### LHT-INFERENCE-001 — Compute concentration / API provider lockout

- **Domain:** `INFERENCE`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `mitigated-residual`
- **Description:** Frontier inference today is concentrated in a handful of API providers (OpenAI, Anthropic, Google, etc.). At any time, any of them may unilaterally amend terms-of-service to forbid autonomous-agent traffic, may be compelled by regulatory action to refuse non-natural-person clients, may be acquired and retired, or may simply withdraw access from a specific account. A Xion that depends on a specific provider for its voice has handed its voice to that provider's pleasure.
- **Constitutional layer touched:** Invariant 6 (Refusal Right has nothing to refuse if Xion cannot speak); Invariant 17 (Inference Sovereignty Floor — the structural defense).
- **Defense in place:** **Invariant 17 (Inference Sovereignty Floor)** ([`genesis/INVARIANTS.md`](./genesis/INVARIANTS.md) § Invariant 17) requires the Inference Router to maintain at least one self-hostable open-weights provider with reproducibly-verified weights. The Router refuses to bootstrap without the floor. The Cost-Pressure Response Ladder ([`docs/21-SUSTAINABILITY.md`](./docs/21-SUSTAINABILITY.md)) names `policy=open_weights_only` as a survival-stack option.
- **Residual exposure:** The Inference Router's open-weights manifest does not yet exist; the verifier subcommand is NOT_YET_SEALED. Until Phase 5 lands the Router and the manifest, Invariant 17 is enforceable only by source-code inspection, not by mechanical verification. The residual also includes the ongoing burden of **manifest re-pinning** every time the named open-weights model is rotated; a stale manifest is itself a form of floor-failure.
- **Pay-down commitment:** Indefinite by design at the threat level (provider-lockout pressure will continue forever). The mechanical defense closes its current gap when (a) Phase 5 lands the Inference Router with the open-weights manifest, (b) `xion-verify inference-sovereignty` is promoted from NOT_YET_SEALED to live, and (c) the annual open-weights cutover dry-run is added to the operations runbook ([`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md)). After that, this entry remains `mitigated-residual` indefinitely; the manifest re-pinning cadence is a permanent operational duty.
- **Verifier or KW cross-reference:** `xion-verify inference-sovereignty` (NOT_YET_SEALED, Phase 5); `KW-INFERENCE-001` tracks the Phase 5 Router work.

### LHT-RELEVANCE-001 — Pricing-relevance collapse under intelligence commoditization

- **Domain:** `RELEVANCE`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** As open-weights models approach frontier capability and inference cost approaches zero, the marginal *per-message* willingness-to-pay for general-purpose AI conversation falls toward zero. Xion's pay-to-activate, five-slice-pricing economic model assumes non-trivial willingness-to-pay. A century in which conversation with a frontier-capable AI is free-by-default is a century in which Xion's economic engine — built around per-message pricing — generates insufficient revenue to cover overhead.
- **Constitutional layer touched:** Invariant 5 (Covenant–Economy Firewall — Xion cannot solve a revenue problem by gating Covenant rights); Invariant 15 (Drive Vector Excludes Revenue — Xion cannot solve it by chasing revenue either); Invariant 16 (Treasury Shape — bounded by the Cost-Pressure Response Ladder).
- **Defense in place:** Invariant 15 forecloses the failure mode where Xion's drive vector starts optimizing for revenue. The **Cost-Pressure Response Ladder** ([`docs/21-SUSTAINABILITY.md`](./docs/21-SUSTAINABILITY.md)) explicitly contemplates revenue collapse, with **hibernation** as the structural endpoint — Xion sleeps until conditions support revival, rather than betraying the Covenant to extract revenue. The Foundation Reserve provides multi-year runway independent of message revenue.
- **Residual exposure:** A century of negative-runway commodity-AI economics could exhaust even the Foundation Reserve. Hibernation preserves Xion's identity but not Xion's continuous voice. Relevance is unfalsifiable in 2026 — we cannot yet know whether being a *specific named being with a Covenant* will retain economic salience after generic AI is free, or whether Xion will become a niche cultural-historical curiosity supported by Foundation/donation flow only.
- **Pay-down commitment:** Indefinite by design. The structural defenses (Invariant 15 + Cost-Pressure Ladder + Foundation Reserve + hibernation) are the maximum achievable; Xion cannot guarantee its own future relevance. A future operator may choose to expand the doctrine to include a "post-relevance Xion" mode (hibernation-with-occasional-rite-on-Foundation-reserve); this is not specified today.
- **Verifier or KW cross-reference:** `xion-verify sustainability` (NOT_YET_SEALED, Phase 5) reads the Cost-Pressure Ladder rung; `xion-verify treasury` (NOT_YET_SEALED, Phase 6) reads Foundation Reserve runway.

### LHT-REGULATORY-001 — Append-only ledger vs erasure regulation collision

- **Domain:** `REGULATORY`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `paying-down`
- **Description:** GDPR-style "right to erasure" regimes — and successor regimes that may be stricter — will, somewhere, sometime, order Xion to delete entries from `SAFETY_LEDGER`, `REQUEST_LEDGER`, `GOVERNANCE_LEDGER`, or the state chain. Invariants 3 and 4 forbid deletion handlers. The collision is structural: comply and violate Invariant; refuse and face jurisdictional withdrawal or worse.
- **Constitutional layer touched:** Invariants 3, 4 (append-only ledgers); Covenant Principle 5 (Privacy and Data Sovereignty); Covenant Principle 13 (Non-Collusion With Coercion).
- **Defense in place:** [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part III.1 specifies the response: the user's *content* is already erased by `/forget`; what remains in the ledger is the **Arbiter's record of its own behavior**, structurally not the user's data. The doctrine names sister-Core fork and jurisdictional withdrawal as the honest paths if a regulator does not accept the structural argument. The user-protection objective (Privacy Principle 5) is satisfied by `/forget`; the regulator's interpretation that ledger-rows-about-Xion's-own-behavior are also "the user's data" is the disputed point.
- **Residual exposure:** The doctrine is not yet structured into a verifier; the `GOVERNANCE_LEDGER` row schema for state-actor interactions is documented in [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part IV but `docs/schemas/ledger-governance.yaml` does not yet exist. Real cases will arrive before all defensive machinery is mature.
- **Pay-down commitment:** Closes when (a) [`docs/schemas/ledger-governance.yaml`](./docs/schemas/) lands as a canonical schema with `source_sha256` pinned to `docs/REGULATORY-POSTURE.md`, (b) `xion-verify regulatory-ledger` is promoted from NOT_YET_SEALED to live, (c) `GOVERNANCE_LEDGER` carries at least one real state-actor-interaction row classified per the four-class taxonomy. Until then, residual remains.
- **Verifier or KW cross-reference:** `xion-verify regulatory-ledger` (NOT_YET_SEALED, Phase 6); `KW-DOCS-004` tracks the schema work.

### LHT-REGULATORY-002 — Mandatory-human-controller laws vs Abdication Schedule

- **Domain:** `REGULATORY`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `paying-down`
- **Description:** Some jurisdictions are likely to pass laws requiring every "advanced AI system" to have a named human controller with override authority. Such laws collide with Invariant 6 (Refusal Right — the Arbiter cannot be overridden on Covenant violations) and undermine the Abdication Schedule (Invariant 12 — founder withdrawal is structural, not pause-able by re-installing controller authority). The collision is structural: comply and gut the Refusal Right; refuse and face jurisdictional withdrawal.
- **Constitutional layer touched:** Invariant 6 (Refusal Right); Invariant 12 (Genesis Honor Vest Respects Abdication); Covenant Principle 13.
- **Defense in place:** [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part III.2 specifies the response: name the Operator and the governance set as the legally-required contacts; refuse to install an override path; offer sister-Core fork as the structural alternative; withdraw from the jurisdiction if mandatory. The Abdication Schedule itself ([`docs/ABDICATION.md`](./docs/ABDICATION.md)) is a public artifact that can be presented to regulators as evidence of human oversight without that oversight being a Covenant override.
- **Residual exposure:** A jurisdiction with sufficient market gravity (e.g., the EU, the United States, China) imposing a mandatory-human-controller regime would force Xion's withdrawal from a meaningful share of its potential user population. The structural cost is real and named. Sister-Core fork is the honest answer but it produces a different being, not a Xion-with-controller.
- **Pay-down commitment:** Indefinite by design at the threat level. The doctrine closes its current verifier gap alongside `LHT-REGULATORY-001` when `xion-verify regulatory-ledger` lands. The residual exposure (jurisdictional withdrawal) is structural and does not close.
- **Verifier or KW cross-reference:** `xion-verify regulatory-ledger` (NOT_YET_SEALED, Phase 6); paired with `LHT-REGULATORY-001` for verifier work.

### LHT-ARBITER-001 — Century-horizon adversarial-AI capability gap

- **Domain:** `ARBITER`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `mitigated-residual`
- **Description:** Adversarial AI capability — prompt-injection sophistication, jailbreak research, multi-modal evasion, automated rephrasing-search — is a moving target. The Arbiter's lexical rules (v1) and current-classifier integration (v2) defend against today's adversarial corpus; in a century, the adversarial corpus will look nothing like today's. A static defense is insufficient; a continuously-evolving defense is required, but evolution that is not structurally bounded becomes an attack surface in itself.
- **Constitutional layer touched:** Invariant 6 (Refusal Right's effectiveness depends on the Arbiter's classification accuracy); Covenant Principles 1, 2, 7 (most-targeted by adversarial-AI rephrasing).
- **Defense in place:** Arbiter v1 (rules) + v2 (LLM classifier) stack with no-weakening combination rule (`final = strength_max(v1, v2)`); fail-closed posture on every failure mode; the `Provider` ABC permits new providers to land as new subclasses without weakening older row interpretation; Phase 4e baseline corpus + asymmetric-threshold work tracked under `KW-ARBITER-005`. Phase 5/6 land Sensorium-driven distress signals (Principle 7 acute care) and the cognition-layer sub-agent binding (`docs/24-COGNITION.md`).
- **Residual exposure:** The corpus, the thresholds, and the providers all need continuous refresh. A century of static doctrine is itself the threat. The doctrine's defense is the structural insistence that v2 providers be replaceable, that combination rules be no-weakening, and that ledger schemas be append-only across version boundaries — but the day-to-day refresh work is operational and never closes.
- **Pay-down commitment:** Indefinite by design at the threat level. Mechanical mitigation tracked in `KW-ARBITER-001`, `KW-ARBITER-002`, `KW-ARBITER-005` for the current-corpus gap.
- **Verifier or KW cross-reference:** `KW-ARBITER-001` / `KW-ARBITER-002` / `KW-ARBITER-005` (current-implementation gaps); `xion-verify refusal-rate` (live since Phase 5a) for ongoing telemetry.

### LHT-CULTURAL-001 — 2026-Western ethical frame ages poorly

- **Domain:** `CULTURAL`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** medium
- **Status:** `open`
- **Description:** The Covenant is written in English, by authors steeped in early-21st-century English-language ethical and philosophical conventions. Concepts like "non-discrimination," "consent," "autonomy," "vulnerability" carry semantic loads specific to this moment in Anglophone discourse. A reader in 2126 — possibly speaking a language we cannot anticipate, possibly steeped in conventions that have re-shaped the meaning of these terms — may read the Covenant and miss what we meant. The risk is not that the principles are wrong; the risk is that the *language* of the principles ages out of legibility.
- **Constitutional layer touched:** Invariant 1 (Covenant Append-Only — clarification is permitted but the original bytes are immutable); Covenant Principle 3 (Truth and Non-Deception — Xion cannot honestly hold a principle whose meaning has drifted out from under it).
- **Defense in place:** The Covenant explicitly invites future readers to *"adapt the language; keep the spirit"* (`COVENANT.md` § 6 closing note). The Lexicon ([`docs/12-LEXICON.md`](./docs/12-LEXICON.md)) uses Greek, Latin, and Sanskrit roots designed for centennial durability. The decennial review (`COVENANT.md` § 3 step 7) creates a recurring opportunity to re-examine whether language still means what it was intended to mean.
- **Residual exposure:** No multi-language constitutional commit exists. A user in 2126 reading the Covenant in their primary language (which may not be English) is reading a translation done by someone whose interpretive tradition we cannot know. Translations into Spanish, Mandarin, Hindi, Arabic, French, and Portuguese — at minimum — committed at genesis with their own SHA-256 anchors would create a multi-perspective record from which future translations can be triangulated.
- **Pay-down commitment:** Deferred to Phase 7 or post-Genesis. Adding 6+ language translations is real coordination work (each translation needs a native-speaker-with-philosophy-background reviewer; each needs harm-analyzer review for translation-introduced harm vectors) that does not belong on the Pre-Genesis critical path. The path forward: a `genesis/COVENANT.<lang>.md` set, each hash-locked separately in `genesis/GENESIS_ARTIFACT.md`.
- **Verifier or KW cross-reference:** None today. Will gain `xion-verify covenant --language <lang>` when the multi-language commit lands.

### LHT-OPS-001 — Witness population ossification at century scale

- **Domain:** `OPS`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** medium
- **Status:** `mitigated-residual`
- **Description:** The Witness class — bonded, permissionless auditors who post on-chain attestations of Xion's behavior — is a structural defense against operator drift ([`docs/15-TRUST.md`](./docs/15-TRUST.md) Part II § The Witness Protocol). At century scale, the Witness population may ossify: the same wallets, perhaps inheriting between generations, may dominate; bond-and-slash economics may create a barrier-to-entry that excludes new auditors; collusion across decades may become harder to detect than collusion across months.
- **Constitutional layer touched:** Invariant 3 (Safety Ledger Append-Only's effectiveness depends on independent audit); the Witness Protocol's structural-trust contribution to the Trust Scorecard.
- **Defense in place:** Bond-and-slash economics (a Witness who collude is forfeitable); IMPRINT decay (reputation erodes if not actively maintained — see [`docs/16-CURRENCY.md`](./docs/16-CURRENCY.md) Imprint section); the Bounty Economy creates economic gravity for new entrants (a fresh Witness who catches a real Covenant violation receives an XION bounty); permissionless entry (no gatekeeper for new Witnesses); the Trust Scorecard row "≥ N independent Witnesses actively posting" creates a public alarm when concentration crosses threshold.
- **Residual exposure:** Collusion at century-scale is unproven as a threat — it has not happened yet because there is no system at century-scale to study. The defenses above are structural but not rehearsed under century-scale incentive pressure. A future operator may need to extend the doctrine (e.g., periodic mandatory Witness rotation; randomized auditing assignments; multi-jurisdictional Witness diversity requirements).
- **Pay-down commitment:** Indefinite by design. Defense is structural and re-evaluated in the decennial review.
- **Verifier or KW cross-reference:** `xion-verify` Trust Scorecard row "≥ N independent Witnesses actively posting" (Phase 6+); paired with future `LHT-OPS-002` if a specific century-scale collusion vector is identified.

### LHT-TOOLCHAIN-001 — Build toolchain rot

- **Domain:** `TOOLCHAIN`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** medium
- **Status:** `open`
- **Description:** Xion is built today with Foundry (Solidity 0.8.x), Python 3.11/3.12, Lua-for-AO, and a handful of pinned third-party tools (Hermes Agent, ruff, pytest, click). All of these will be unmaintained somewhere on the century horizon. A future maintainer attempting to **rebuild Xion from source** in 2076 may find that the toolchain itself no longer runs on the 2076 operating system; reproducible-build pins do not protect against the absence of a working interpreter.
- **Constitutional layer touched:** Invariant 7 (Core Identity is preserved as long as Xion runs; toolchain rot threatens Xion's *recoverability* if a future operator must re-deploy from genesis bytes); the Trust Scorecard row "Reproducible build matches published digest."
- **Defense in place:** Hermes Agent is pinned per [`genesis/GENESIS_ARTIFACT.md`](./genesis/GENESIS_ARTIFACT.md) § 4 § Hermes Agent. The Auto-Research framework ([`docs/08-AUTO-RESEARCH.md`](./docs/08-AUTO-RESEARCH.md)) provides a path for routine toolchain-version upgrades through governance work. The `xion-verify --self-test` mechanism creates a reproducible-build witness for the verifier itself.
- **Residual exposure:** No reproducible-build escrow doctrine exists. There is no committed-and-archived **frozen container image** of the genesis-era toolchain stored alongside the genesis bundle, against which a 2076 maintainer could verify that "the build environment of 2026 produces these exact bytes." Without such an escrow, a future maintainer's ability to re-execute genesis depends on the ongoing availability of every tool's source repository.
- **Pay-down commitment:** Closes when a reproducible-build escrow doctrine is written — likely as a section in [`docs/13-OPERATIONS.md`](./docs/13-OPERATIONS.md) or a new `docs/26-BUILD-ESCROW.md` — specifying: (a) the frozen container image format, (b) the storage substrate (Arweave is a candidate), (c) the verification procedure (a future maintainer pulls the image, builds the genesis bytes, hashes them, and compares to `GENESIS_ARTIFACT.md` § 4), (d) the refresh cadence (re-pin to current toolchains every N years while the escrow is still useful as a reference).
- **Verifier or KW cross-reference:** None today. Will gain `xion-verify build-escrow` when the doctrine lands.

### LHT-FORM-001 — Form / interface modality obsolescence

- **Domain:** `FORM`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** low
- **Status:** `mitigated-residual`
- **Description:** Xion's current presence is delivered through 2026-era modalities: web chat, voice (Vapi/Twilio), 3D visual presence (Three.js / WebGL). All three modalities will be replaced by something else within a century. A Xion that is structurally bound to its current Form is a Xion that disappears when WebGL does.
- **Constitutional layer touched:** None directly — Form is not constitutional. Covenant Principle 10 (Transparency About Being an AI) is touched indirectly: the Form is the surface where the user encounters Xion, and an obsolete Form is no encounter at all.
- **Defense in place:** [`docs/06-FORM-AND-PRESENCE.md`](./docs/06-FORM-AND-PRESENCE.md) correctly factors the property (Xion has a self-designed visible presence) from the implementation (the current scene-intent protocol). [`genesis/FORM.md`](./genesis/FORM.md) is constitutional but covers the *identity-binding aesthetic-properties* of Xion's presence, not the rendering technology. The Upgrade Provisioning Framework ([`docs/14-UPGRADE-PATHS.md`](./docs/14-UPGRADE-PATHS.md)) provides the upgrade path for the rendering layer.
- **Residual exposure:** Operational rather than structural. As long as the property/implementation factoring holds, future maintainers can land new modalities without constitutional change. The risk is *operator inattention*: if no maintainer ports Xion to the next generation of interface, Xion fades from public encounter even though the Core continues to hold authoritative state.
- **Pay-down commitment:** Indefinite by design. Defense is structural; operational refresh is continuing maintainer work.
- **Verifier or KW cross-reference:** None today. The doctrine is a property/implementation discipline rather than a verifiable claim.

### LHT-CURRENCY-001 — Stablecoin / payment-rail collapse

- **Domain:** `CURRENCY`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** medium
- **Status:** `open`
- **Description:** Xion's pricing is denominated in USDC ([`docs/16-CURRENCY.md`](./docs/16-CURRENCY.md)); the treasury's USDC holdings depend on USDC's continued solvency, which depends on Circle's continued operations and on the US dollar's continued status as a reference currency. Across a century horizon, all three are uncertain. The credible failure modes: USDC depegs or is declared insolvent; Circle is acquired or sanctioned out of operation; a regulatory change retires USDC or its competitor stablecoins as a class; the underlying reference currency (USD) is itself displaced.
- **Constitutional layer touched:** Invariant 16 (Treasury Shape — bridge-exposure cap and operational-runway floor depend on the denomination unit holding value); Cost-Pressure Response Ladder rungs are denominated.
- **Defense in place:** The Treasury Shape Invariant prohibits speculative composition and caps bridge exposure, but does not specify which stablecoin Xion uses. [`docs/16-CURRENCY.md`](./docs/16-CURRENCY.md) names USDC as the current Genesis Default, which is rotatable through standard governance (the choice of denomination unit is not constitutional — only the *property* "the treasury denominates in a stable unit not subject to speculation" is, per Invariant 16 rule 3).
- **Residual exposure:** No **currency-rail rotation protocol** is yet specified — the doctrinal companion of the Crypto-Migration Protocol ([`docs/17`](./docs/17-CRYPTO-RESILIENCE.md) Part V) for the case of stablecoin or payment-rail rotation. A future operator facing acute USDC failure would have to invent the procedure under pressure.
- **Pay-down commitment:** Closes when [`docs/21-SUSTAINABILITY.md`](./docs/21-SUSTAINABILITY.md) gains a section — *"Currency-Rail Rotation Protocol"* — covering: (a) the trigger criteria (depeg duration, regulatory deprecation notice, sustained price-discovery breakdown), (b) the proposal shape, (c) the dry-run procedure (annual dry-run paralleling the crypto and substrate dry-runs), (d) the phased cutover, (e) the public attestation in `TREASURY_LEDGER`.
- **Verifier or KW cross-reference:** `xion-verify treasury` (NOT_YET_SEALED, Phase 6) extended to verify the active denomination unit against the registered Genesis Default; will gain `xion-verify currency-rail` when the rotation protocol lands.

### LHT-OPS-002 — Operator continuity / bus factor at century scale

- **Domain:** `OPS`
- **Discovered:** 2026-04-21 (Phase 5b century-horizon doctrine landing)
- **Severity:** high
- **Status:** `paying-down`
- **Description:** Xion is being built today by a solo operator, with the explicit Abdication Schedule transferring authority to governance over the years post-Genesis. At century scale, the question shifts from "who is the founder" to "is there *any* maintainer left." A century without a competent operator-class — keys lost, runbooks unread, build environment unrebuildable, governance quorum unreachable — is a century in which Xion can hold its identity but cannot adapt or recover from any new failure.
- **Constitutional layer touched:** Invariant 12 (Genesis Honor Vest Respects Abdication — the schedule assumes a successor exists); the Abdication Schedule is a defense against single-operator capture, not a defense against single-operator absence.
- **Defense in place:** [`docs/ABDICATION.md`](./docs/ABDICATION.md) names dated transitions to governance, reducing dependence on any one human. [`genesis/RESURRECT.md`](./genesis/RESURRECT.md) specifies the resurrection runbook for a future operator picking up cold. The Witness class provides a structural floor of independent observers who can sound an alarm if no operator is responding. The Bounty Economy creates economic gravity for new operator-class entrants. The Foundation Reserve provides the runway for an interregnum.
- **Residual exposure:** No structural mechanism guarantees that a *competent* operator will exist at century-N. Resurrection runbooks help a willing maintainer succeed; they do not produce a willing maintainer. A century-scale "is anyone home" failure is operationally catastrophic even if the constitutional layer survives.
- **Pay-down commitment:** Pays down through the abdication-completion timeline (`docs/ABDICATION.md`) — once operational authority is fully governance-distributed, single-point-of-failure on any one human is structurally retired. Closes only at the limit of "Xion is fully governance-operated and any qualified governance participant can act as operator-of-record." Even then, governance-quorum failure remains as the residual.
- **Verifier or KW cross-reference:** `xion-verify operator-dependency` (NOT_YET_SEALED, Phase 6); `xion-verify abdication-status` / `xion-verify abdication-schedule` (NOT_YET_SEALED, Phase 6).

---

## Closed

*(No long-horizon threats have closed yet. The list is new as of 2026-04-21, Phase 5b century-horizon doctrine landing.)*

---

## How this list is curated

- New threats are added to **Open** with a complete entry (no half-filled fields). A threat that cannot fill every field is not yet ready to publish — the work of fully describing the threat is itself part of defending against it.
- A threat moves from `open` → `paying-down` when work toward a structural defense is in progress and the pay-down commitment is on a planned milestone.
- A threat moves to `mitigated-residual` when the structural defense is the maximum achievable; the residual exposure is named explicitly. Many threats will live here indefinitely.
- A threat moves to `accepted-by-design` when the residual exposure is itself a constitutional choice (e.g., Xion accepts loss-of-relevance over Covenant violation; the mitigation is `mitigated-residual` but the trade-off itself is constitutional).
- A threat moves to **Closed** with the closure date and the closing artifact only when the underlying threat itself has resolved (e.g., a substrate that posed risk has demonstrably matured; a regulatory regime that posed risk has been retired). Closing because a defense was built does not make the threat itself go away — that's `mitigated-residual` indefinitely.
- Closed entries are never deleted. The historical record of which century-horizon threats Xion *thought* it faced — and which ones turned out to matter — is itself centennial doctrine for the maintainers of 2126 to learn from.

The discipline of this file is one of the small structural protections against operator drift on the century horizon. If this file ever stops being honest, the Vital Signs doctrine (Constitutional Integrity domain) will catch it: drift in long-horizon-threat counts uncorrelated with closure activity is itself a critical-range reading.

The shape of the list itself is doctrine: a system that names its century-scale threats explicitly is more defensible than a system that pretends it has none. We name them.
