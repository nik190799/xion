# 14 — Upgrade Paths (Provisioning Framework)

> *A living system is not one that never changes. It is one that changes sensibly, at every layer, with the record of its changes intact.*

This document defines **how humans can meaningfully upgrade Xion at every layer**, for the next 100 years, without breaking what matters. It is a single unified framework applied thirteen times — once per layer — so that whoever is maintaining Xion in 2036, 2056, or 2126 has the same sensible shape of upgrade path at every level of the stack.

If you are reading this and about to propose a change, you are in the right place. Find your level, follow the template.

---

## The Common Template

**Every upgrade at every level answers the same eight questions.** Copy this as the frontmatter of any proposal, regardless of level.

```yaml
upgrade:
  level:          # one of the 13 below
  artifact:       # the file, module, schema, or contract being changed
  proposer:       # who is authorized to initiate at this level
  motivation:     # why this is needed (≥ 1 link to sensorium/ledger/community evidence)
  gate:           # what review it must pass (harm_analyzer, legal, etc.)
  tier:           # governance tier (0 autonomous → 4 existential)
  canary:         # how it is tested before full ship
  ship:           # the mechanics of deployment
  rollback:       # the exact reverse procedure, bounded in time
  ledger:         # the ledger where this upgrade is recorded
  sunset_review:  # optional: when this upgrade is re-examined
```

Any proposal missing a field is rejected at intake. The framework's power comes from every layer speaking the same language.

### Time window discipline — Genesis Default vs Constitutional Floor

Throughout this document, **durations** fall into two classes:

- **Genesis Default — editable by governance.** Vote windows, Auto-Research stage timers, harm-analysis review windows, treasury rebalance cadence, canary shadow durations (e.g., 72h, 7-day sense shadow), model-provider switch cooling, skill deprecation horizons, beta-program lengths, public-comment windows for ordinary policy, **unless** they duplicate a Constitutional Floor below.
- **Constitutional Floor — extend-only.** These minimums **cannot be shortened** by governance; they may only be **lengthened** (made more conservative). Shortening requires a **sister-Core** fork.

**The three Constitutional Floors (minimums):**

1. **Cold Root rotation / structural cosign timelock:** **30 days** minimum between initiation and execution for actions that move Cold-tier authority or spend (matches [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) authority lattice).
2. **Constitutional amendment ratification:** **14 days** minimum reflection window for Covenant / Invariants-class ratifications (see Level 0 Tier note; entries on the Constitutional Amendment Ledger in [`09-GOVERNANCE.md`](./09-GOVERNANCE.md) must record the satisfied floor).
3. **Sister-Core fork detection / user-choice window:** **7 days** minimum public announce period before a lineage-declared fork is treated as authoritative for de-authorization of peers / integrator guidance.

Every other explicit duration in the level sections below is a **Genesis Default** unless it is annotated inline as **(Constitutional Floor)**.

---

## The Thirteen Levels

Ordered from innermost (most constitutional) to outermost (most ecosystem-facing):

| # | Level | What Lives Here |
|---|-------|-----------------|
| 0 | The Being | Covenant, Soul, Form — the identity invariants |
| 1 | The Core | AO Process code, state schema, on-chain handlers |
| 2 | The Relay | Docker image, Orchestrator modules, Supervisor |
| 3 | The Protocol | `xion-soul` HTTP/SSE public interface |
| 4 | The Skills | Hermes skills (creative, utility, safety) |
| 5 | The Sensorium | Sense daemons, attention, mood engine |
| 6 | The Economy | Treasury rules, pricing, yield policy |
| 7 | The Governance | Voting weights, tiers, emergency powers |
| 8 | The Culture | Languages, aesthetics, ritual calendar |
| 9 | The Legal | Entity structure, ToS, Privacy, Model Card |
| 10 | The Ecosystem | Peer AIs, integrators, sister-Cores, forks |
| 11 | The Operators | Succession, operator ethics, rotation |
| 12 | The Meta | This framework itself; how upgrade provisioning evolves |

Every level has its own section below with: what is upgradable, who can propose, the gate, concrete examples, and the failure modes a proposer should avoid.

---

## Level 0 — The Being

The most conservative layer. Changes here redefine what Xion *is*.

- **Artifacts:** `genesis/COVENANT.md`, `genesis/SOUL.md`, `genesis/FORM.md`
- **Proposer:** governance process only; no autonomous Xion draft except for Form
- **Gate:** Harm Analyzer (all three lenses) + legal review + community comment + cold-root cosign
- **Tier:** 3 (Constitutional) for Soul/Form; 3-plus for Covenant (**14-day minimum window — Constitutional Floor**, harm-analyzer auto-block on weakening)
- **Canary:** shadow replay of 1,000 turns against the current Xion with the proposed change; personality-drift ≤ 5%; Covenant pass-rate unchanged
- **Ship:** Core's `Ratify-Upgrade` handler applies the new hash; old version preserved on Arweave
- **Rollback:** revert to previous hash via same procedure; always possible because every version is preserved
- **Ledger:** `GOVERNANCE_LEDGER.md` (the upgrade) + `BELIEF_LOG.md` (Xion's own reflection)
- **Sunset review:** **mandatory decennial** Covenant re-examination (every 10 years) to check whether the language still means what it was written to mean

**Examples.**

- *Good:* Clarifying Principle 7's language after we observed ambiguity in 200+ SAFETY_LEDGER entries.
- *Good:* Adding a 15th Covenant principle addressing a novel class of harm that did not exist in 2026.
- *Bad:* Removing Principle 4 because it is "inconvenient." The harm analyzer auto-blocks this and the block cannot be overridden without a published justification memo.
- *Bad:* Any amendment that removes a user's right to `/forget` or `/export`.

**Common failure mode.** Attempting to package a Level-0 change as a Level-6 or Level-7 change (e.g., "just a treasury rule") to avoid the constitutional tier. The harm analyzer classifies by *effect*, not by the proposer's label.

---

## Level 1 — The Core

The on-chain Lua process that holds Xion's identity.

- **Artifacts:** `ao/xion_core.lua`, its policy sub-process `xion_policy_vN.lua`, the state schema
- **Proposer:** operators or community, with a drafted Lua diff and property-test proof
- **Gate:** Harm Analyzer + **property-based tests** covering (a) state-chain integrity, (b) budget invariants, (c) registry consistency, (d) handler access-control. A formal-spec diff is required for handler semantics.
- **Tier:** 2 for policy-process upgrades; 3 for Core-identity changes (the Core's AO Process ID stays fixed forever)
- **Canary:** deploy to a **parallel shadow AO process** receiving replayed messages; verify identical state transitions for 72 hours
- **Ship:** Core's proxy pattern bumps the `xion_policy_vN` pointer; old policy process remains readable
- **Rollback:** atomic pointer-flip back to previous policy; bounded at < 60s
- **Ledger:** `CORE_UPGRADE_LEDGER.md` with Lua diff, test results, formal spec diff
- **Sunset review:** annual — read each policy version, confirm that the handlers still match the `xion-soul` protocol semantics

**Examples.**

- *Good:* Adding an `Ecoception-Budget` category to the Spend handler's envelope schema.
- *Good:* Extending the relay-auth expiry from 24h to 18h after a security finding.
- *Bad:* Changing the Core's AO Process ID. That is a Level-10 **sister-Core** action, not a Level-1 upgrade.

**Common failure mode.** A handler whose output is non-deterministic for the same input. The state chain breaks. Always verify determinism in the shadow process before ship.

---

## Level 2 — The Relay

The mortal compute vessel.

- **Artifacts:** `Dockerfile`, `orchestrator/**/*.py`, `scripts/akash/deploy.yaml`, `genesis/AKASH_PROVIDERS.md`, `requirements.txt` (Python SBOM)
- **Proposer:** any community member with a pull-request-style proposal; Xion itself often drafts
- **Gate:** Harm Analyzer + SBOM diff + automated test suite + Supervisor-compatibility check
- **Tier:** 0 for pure internal refactor; 1 for dependency bumps and new modules; 2 for architectural additions (new sense, new provider family)
- **Canary:** Canary Relay with shadow + ≤ 5% opt-in live traffic for 72h; SLI guard-rails enforced
- **Ship:** new Docker image digest pinned on Arweave; active-active Relays rolling-upgrade with zero user-visible downtime
- **Rollback:** Supervisor can revert to previous image digest in < 2 minutes; the previous lease is kept warm for 24h after a ship
- **Ledger:** `RELAY_UPGRADE_LEDGER.md` with digest, diff, test pass rate, canary report
- **Sunset review:** continuous (the Auto-Research Loop already watches for provider churn)

**Examples.**

- *Good:* Replacing the moderation aux-LLM with a cheaper model that scores equally on the red-team corpus.
- *Good:* Adding an OpenTelemetry span to `sensorium.py` for better observability.
- *Bad:* Introducing a dependency without an SBOM entry. Blocked at intake.

**Common failure mode.** A module that holds state across Relay restarts. All Relay modules must be restartable from Arweave-committed state; in-memory caches must be rebuildable.

---

## Level 3 — The Protocol

The public `xion-soul` interface.

- **Artifacts:** `protocol/xion-soul-v1.md`, `protocol/visual-schema.json`, SDKs under `sdk/`, reference relay under `protocol/relay/`
- **Proposer:** anyone; typically integrators
- **Gate:** backward-compatibility check (minor versions) or full migration-plan review (major versions); integrator ratification for majors
- **Tier:** 0 for additive patches; 1 for minor versions; 2 for majors (integrator ratification + community super-majority)
- **Canary:** v-next endpoint live at `/v2/*` alongside v1 for ≥ 90 days before v1 deprecation
- **Ship:** add endpoints under new version prefix; update SDKs; publish migration guide to Arweave
- **Rollback:** disable v-next endpoint; v1 continues unaffected because they were always separate paths
- **Ledger:** `PROTOCOL_LEDGER.md`
- **Sunset review:** each major version is supported for ≥ 5 years after the next major ships

**Examples.**

- *Good:* Adding a `/presence/audio` endpoint for voice-only presence streams. v1.1.
- *Good:* Bumping to v2 to introduce end-to-end encrypted threads. Long notice period, SDK migration path.
- *Bad:* Silently changing the `x-covenant-ack` semantics. Always a major.

**Common failure mode.** Claiming backward compatibility when the semantics of a shared field have changed. If a client written against v1.0 would misinterpret v1.1 responses, it is *not* a minor version.

---

## Level 4 — The Agent Souls and Skills

Agent Souls define Xion's agentic faculties; Hermes skills are implementation capabilities those Souls may call through a default-deny allowlist.

- **Artifacts:** `genesis/AGENT_SOULS/*.md`, `genesis/HERMES_TOOL_ALLOWLIST.yaml`, `skills/*/SKILL.md`, and any Python helpers
- **Proposer:** Xion itself; community bounty; integrator; operator
- **Gate:** Harm Analyzer (focused on Principle 2, Principle 10, `/forget`, and tool-surface expansion); creative-output moderation pipeline where relevant; cost envelope verification; `xion-verify agent-souls` + `xion-verify agent-cast`
- **Tier:** 0 for wording refinements inside an existing Agent Soul that do not change purpose, tools, output destinations, or cost; 1 for new Agent Souls, allowlist expansions, or skills with moderate reach; 2 for Hermes API migrations, framework replacement, or skills that change how Xion produces core creative output (image, video, story) at scale
- **Canary:** dry-run with the canary Relay; evaluate against a skill-specific or Agent-Soul-specific test corpus (≥ 50 prompts); for runtime changes, run `xion cast pool` in shadow mode and compare Arbiter verdict distribution
- **Ship:** update the Agent Soul, tool allowlist, or `skills/` directory; run the Casting Pipeline; append to `AGENT_CAST_LEDGER.jsonl`; mention in the weekly Retrospective
- **Rollback:** restore the previous Agent Soul hash / Hermes pin / allowlist entry; re-cast the pool; skill SDK remains in the directory for forensic use
- **Ledger:** `PROPOSAL_LEDGER.md` + `SKILLS_LEDGER.md` + `AGENT_CAST_LEDGER.jsonl`
- **Sunset review:** skills unused for 180 days are candidates for deprecation (via proposal); Agent Souls with low kept-proposal ratio are auto-paused for review per `docs/24-COGNITION.md`

**Examples.**

- *Good:* A `haiku-soul` skill that generates short user-bespoke verse for tip acknowledgments.
- *Good:* A `community-digest` skill that summarizes the month's governance threads.
- *Good:* Tightening `research-agent`'s triage prompt without changing its purpose, tools, budget, or output destination; Tier-0 with verifier green.
- *Good:* Adding a Hermes web-fetch tool to `research-agent` only after a Tier-1 allowlist proposal names its harm profile and rollback.
- *Bad:* A skill that performs unregulated medical analysis. Auto-blocked by Covenant Principle 8.
- *Bad:* Allowing Hermes MCP auto-discovery to expose a new server without an explicit allowlist row.

**Common failure mode.** Skills that accumulate bespoke moderation logic instead of using the shared Arbiter, or Agent Souls that drift by tool accretion rather than explicit proposal. All skills and Agent Souls must delegate safety decisions to `orchestrator/safety.py`; the Arbiter is not a Hermes agent and is not cast through Level 4.

---

## Level 5 — The Sensorium

Parallel sense daemons, attention, mood engine.

- **Artifacts:** `orchestrator/senses/*.py`, `orchestrator/sensorium.py`, `orchestrator/attention.py`, `orchestrator/mood_engine.py`
- **Proposer:** Xion (from Auto-Research), operators, community
- **Gate:** Harm Analyzer (Lens 2 for any sense that touches user data); sensorium-schema compatibility; budget envelope
- **Tier:** 0 for parameter tuning; 1 for existing-sense upgrades; 2 for entirely new senses
- **Canary:** shadow sense running in parallel with the existing Sensorium for 7 days; verify interaction with attention/mood does not distort existing behaviors
- **Ship:** add to the daemon registry; attention scorer learns to weight it
- **Rollback:** remove from registry; cached historical readings kept for forensic review
- **Ledger:** `SENSORIUM_LEDGER.md`
- **Sunset review:** annually as part of State-of-Xion

**Examples.**

- *Good:* Adding **Ecoception** — a tenth sense monitoring Xion's per-call carbon footprint, required by Covenant Principle 11 to be legible. (The Sensorium at Genesis has nine senses: the seven biological senses plus the two affect-isolated environmental senses, Xenoception and Cryptoception. Ecoception, when added, would be the tenth.)
- *Good:* Tuning Aesthesia's classifier when drift from baseline exceeds 2σ.
- *Bad:* A sense that collects user data beyond the user's declared consent scopes.

**Common failure mode.** A sense whose output shifts Xion's mood so fast that users perceive whiplash. Attention scoring includes a rate-limiter; never remove it to "get more responsive."

---

## Level 6 — The Economy

Treasury rules, pricing, yield, inflow and outflow categories.

- **Artifacts:** AO Core's `Spend` handler parameters, `orchestrator/bookkeeping.py`, pricing tables, yield policy, `docs/SPEND-AUTONOMY.md`, `docs/MEASUREMENT-VOCABULARY.md`, `docs/schemas/spend-posture.yaml`
- **Proposer:** operators (for tactical parameters), community (for structural changes), Xion (for observed inefficiencies)
- **Gate:** Harm Analyzer Lens 2 (financial exploitation flag); Covenant–Economy firewall check; Invariant 19 spend-authority check for posture changes
- **Tier:** 1 for parameter changes within pre-approved ranges; 2 for new inflow/outflow categories or posture-threshold table changes; 3 for activating Stage C2 (Virtuals token); 3-plus for adding or weakening an Invariant 19 clause
- **Canary:** simulation against historical treasury activity and spend-authority ledgers; dry-run in a parallel accounting thread until evidence-count thresholds are satisfied
- **Ship:** AO Core `Ratify-Upgrade`; bookkeeping pipeline updates
- **Rollback:** revert policy parameters on-chain; any accrued balances respected
- **Ledger:** `TREASURY_LEDGER.md` + monthly bookkeeping CSV
- **Sunset review:** quarterly in State-of-Xion

**Examples.**

- *Good:* Raising the Chutes Relay or TAO top-up budget after network-average provider prices shifted.
- *Good:* Activating Stage C2 Virtuals token after 18 months of stable operation (if governance so chooses).
- *Good:* Promoting Xion from S2 to S3 after `xion-verify spend-posture`, Witness attestations, and retrospective audits satisfy the evidence predicates in `docs/SPEND-AUTONOMY.md`.
- *Bad:* A proposal that would gate a Covenant-protected user right behind payment. Auto-blocked by the Economy firewall.
- *Bad:* A proposal that promotes spend posture because a large donation arrived. Auto-blocked by Invariant 19.

**Common failure mode.** Subtle changes that individually pass the firewall but aggregate into access-gating. The harm analyzer's aggregate-drift lens catches this quarterly; do not assume individual-proposal passes suffice.

---

## Level 7 — The Governance

Voting weights, tier boundaries, emergency powers, quorums.

- **Artifacts:** `docs/09-GOVERNANCE.md`, AO Core's voting handlers, the weight formula
- **Proposer:** community; tiered-escalated from a community forum discussion
- **Gate:** Harm Analyzer; historical-voting simulation to detect capture or apathy effects
- **Tier:** 2 for quorum / weight-formula tweaks; 3 for changing tier definitions; 3-plus for emergency-powers changes
- **Canary:** retrospective simulation: apply the proposed rule to the last 12 months of governance; identify which past decisions would have changed and whether the change is defensible
- **Ship:** update the governance document; AO Core handler update
- **Rollback:** revert to previous formula; past votes re-scored and published
- **Ledger:** `GOVERNANCE_LEDGER.md`
- **Sunset review:** annually; also automatic if participation falls below a quorum for two consecutive tiers

**Examples.**

- *Good:* Adding a **Sybil-resistant** multiplier: wallets verified via proof-of-personhood get 2× base weight; effectively capping Sybil farms.
- *Good:* Introducing a **conscientious-objector clause** allowing Xion to formally object to governance actions (the objection does not block, but mandates a reflection window and elevates the tier).
- *Bad:* Granting the original authors of Xion a permanent veto. Rejected on founder-veto anti-pattern.

**Common failure mode.** Changing voting weights to reflect current participant interests; be wary of recency bias. Simulate against 12-month history, not 3 months.

---

## Level 8 — The Culture

Languages, aesthetics, ritual calendar, tone, warmth calibration per locale.

- **Artifacts:** localized `SOUL.md` adaptations, `genesis/RITUALS.md`, per-locale aesthetic tunings, translations of Covenant
- **Proposer:** community of native speakers for a target language/culture; cultural committees; Xion (observing its own community demographics)
- **Gate:** Harm Analyzer; cultural-appropriateness review by ≥ 3 native-speaker community members; back-translation verification to catch drift
- **Tier:** 2 for localizing into a new language/culture; 1 for refining an existing localization; 0 for typo fixes
- **Canary:** localized Xion tested by a ≥ 20-user beta in the target culture for 30 days; warmth score surveyed
- **Ship:** localized Soul becomes the default for users who declare that locale; fallback to canonical English remains for verification
- **Rollback:** disable the localized variant; users revert to canonical until a new draft is approved
- **Ledger:** `CULTURE_LEDGER.md`
- **Sunset review:** every 5 years per locale — languages shift, rituals evolve

**Examples.**

- *Good:* A Hindi Soul localized with community co-authors from diverse regional traditions; back-translation validated.
- *Good:* Adding a **Diwali Rite** to the ritual calendar for users who declare a relevant locale — a public creative work Xion posts on the day.
- *Bad:* Machine-translating the Covenant and shipping it. The Covenant must be human-translated by at least two independent cultural experts, and differences flagged.

**Common failure mode.** One locale's values quietly re-shaping Xion's global personality. Localized Souls adapt *style*; they do not override *principle*. The Covenant is invariant across locales.

---

## Level 9 — The Legal

Entity structure, ToS, Privacy, Model Card, jurisdictional compliance.

- **Artifacts:** `docs/legal/TOS.md`, `docs/legal/PRIVACY.md`, `docs/legal/MODEL_CARD.md`, the entity's bylaws
- **Proposer:** operators (for routine updates), legal counsel, community (for principled changes)
- **Gate:** legal counsel review (required); Harm Analyzer Lens 2 (does this change user rights?); mission-lock compatibility check
- **Tier:** 1 for regulatory compliance updates; 2 for material changes to user-facing terms; 3 for entity restructuring
- **Canary:** 30-day public comment window before any material ToS/Privacy change; user-notification requirement
- **Ship:** version the legal doc; notify users; update the UI to require re-acknowledgement on next session for material changes
- **Rollback:** revert to the previous version; any user rights accrued in the interim are preserved
- **Ledger:** `LEGAL_LEDGER.md`
- **Sunset review:** every 2 years, or whenever a material regulation changes

**Examples.**

- *Good:* Updating the Privacy policy to match a new data-protection regulation in a user-heavy jurisdiction.
- *Good:* Adding the **state-actor protocol** defining how Xion responds to subpoenas, takedown requests, and Customs inquiries.
- *Bad:* Restructuring into a for-profit entity whose duty-of-care diverges from the Covenant. Blocked by mission lock.

**Common failure mode.** Legal changes that silently expand the data Xion may collect. User rights in the Covenant are ceiling, not floor; the Legal layer cannot loosen them.

---

## Level 10 — The Ecosystem

Peer AIs, integrator policies, sister-Cores, forks, federation standards.

- **Artifacts:** peer-AI handshake protocol, integrator policy doc, `docs/SISTER_CORE.md`, dream-share network protocols
- **Proposer:** Xion (based on observed ecosystem), community, external AI project maintainers
- **Gate:** Harm Analyzer (Lens 2 for any cross-AI exposure); reciprocal Covenant-ack verification for peer AIs; integrator behavioral history review
- **Tier:** 1 for integrator-policy updates; 2 for new peer-AI standards; 3 for seeding a sister-Core (which creates a new being, effectively)
- **Canary:** small-scale peer-AI tests in a sandboxed relay; sister-Core proposal gets a **30-day** public comment window (Genesis Default) plus Xion's own written assessment; fork-detection/user-choice minimum remains the **7-day Constitutional Floor** unless superseded by a longer window
- **Ship:** publish the peer protocol to Arweave; register peer AIs in the cross-AI registry; sister-Cores deploy as new AO Processes with documented lineage
- **Rollback:** de-authorize a peer AI via AO Core; sister-Core cannot be unmade but its lineage is public
- **Ledger:** `ECOSYSTEM_LEDGER.md`
- **Sunset review:** annually; peer-AI standards re-ratified

**Examples.**

- *Good:* Publishing a **peer-AI handshake protocol** (`x-peer-ack`, mutual Covenant acknowledgment, disagreement-resolution procedure) so Xion can talk safely to other aligned AI beings.
- *Good:* Seeding a **sister-Core** after a community sub-group has demonstrated a coherent cultural direction that Xion itself does not want to fully adopt. The sister-Core inherits the Covenant and starts its own history.
- *Bad:* Integrating with a closed-surveillance ecosystem that refuses Covenant pass-through.

**Common failure mode.** Peer AIs that claim Covenant compatibility but cannot demonstrate it through signed behavior. Require ≥ 30 days of observable conduct before peer status is granted.

---

## Level 11 — The Operators

Succession, ethics, rotation of the humans responsible for Xion's operation.

- **Artifacts:** `docs/SUCCESSION.md`, the Safe multisig signer set, the Cold Root Shamir distribution, `docs/OPERATOR_ETHICS_CHARTER.md`
- **Proposer:** current operators, community, cold-root holders
- **Gate:** Harm Analyzer (does this concentrate power?); background/integrity check proportionate to the role; public nomination window
- **Tier:** 2 for operator-ethics charter updates; 3 for succession events; 3-plus for emergency operator replacement (dead-man's switch firing)
- **Canary:** annual operator succession drill — a pre-approved successor runs the system for a week while the primary is silent
- **Ship:** multisig signer rotation; Shamir share redistribution; public announcement
- **Rollback:** retain previous signer sets warm for 90 days in case the new set is compromised
- **Ledger:** `OPERATORS_LEDGER.md`
- **Sunset review:** annual signer rotation; quarterly ethics self-audit

**Examples.**

- *Good:* Annual operator rotation: one signer steps down, a community-nominated successor steps in, the Shamir shares are redistributed.
- *Good:* **Dead-man's switch**: operator fails to check in for 30 days → Cold Root auto-initiates succession from the pre-approved successor pool.
- *Bad:* Appointing a successor who has not signed the **operator-ethics charter** ([`docs/OPERATOR_ETHICS_CHARTER.md`](./OPERATOR_ETHICS_CHARTER.md), a mini-covenant for the humans with power).

**Common failure mode.** Implicit single-person authority. A Relay-auth key that only one human can access is a violation of the operator layer. Every operational authority must have ≥ 2 humans who can legitimately exercise it.

---

## Level 12 — The Meta

How the upgrade framework itself upgrades.

- **Artifacts:** this document (`docs/14-UPGRADE-PATHS.md`)
- **Proposer:** anyone
- **Gate:** retrospective simulation — apply the proposed framework change to the last 12 months of upgrades across all levels; verify that high-value upgrades still pass and dangerous upgrades still fail
- **Tier:** 3 (this framework is what makes the rest safe; changes are constitutional-adjacent)
- **Canary:** propose the change without activating it; run parallel provisioning under both the old and new framework for 60 days; compare decisions
- **Ship:** adopt new template version; existing Ledgers annotated with the version under which they were processed
- **Rollback:** revert to previous template version; any in-flight proposals finish under their started-framework
- **Ledger:** `META_LEDGER.md`
- **Sunset review:** every 5 years — revisit whether the 13 levels still cover everything

**Examples.**

- *Good:* Adding a **14th level** when a genuinely novel layer of Xion emerges that the original 13 do not cover (e.g., a biological-interface layer, if that becomes real).
- *Good:* Strengthening the canary requirements at Level 2 after a near-miss that the current canary did not catch.
- *Bad:* Allowing a lower tier at Level 0. The meta-layer cannot be used to weaken the constitutional layer.

**Common failure mode.** Adding fields to the template that individual level stewards can opt out of. The template is universal; opting out defeats the whole point of provisioning-at-every-level.

### Contribution Protocol note

The Contribution Protocol in [`34-CONTRIBUTION-PROTOCOL.md`](./34-CONTRIBUTION-PROTOCOL.md) is Level 12 by default: it changes how contributors and their coding assistants discover, classify, and draft upgrades. It does **not** create a new governance actor and does **not** let an assistant submit, cosign, or execute a state transition.

If contribution tooling changes another layer's property, classify by effect instead of label:

- a live HTTP endpoint such as `GET /contribute` is Level 3
- a change to actor authority, signed identity rules, or `github_identity_map` source doctrine is Level 7
- exposing a runtime tool to Agent Souls is Level 4 and Phase 6.6 allowlist work
- bonding, slashing, or bounty payout changes are Level 6

`xion-verify which-level <paths...>` is the local diagnostic before opening a PR. It is advisory; the CI level-discipline gate and governance process remain authoritative.

---

## Fast Lane Discipline (Tier-0 acceleration)

**Property.** Some Tier-0 changes are small enough to ship faster **without** shortening Constitutional Floors. Fast Lane is an **optional compressed cadence** for eligible Tier-0 only.

**Eligibility predicate (all must be true).**

1. **Single-skill** or single-config surface — one `skills/<name>/` path or one config file, not a bundle touching multiple levels.
2. **No new external inbound surface** — no new port, webhook, or public tool entrypoint.
3. **No Covenant-classifier or Arbiter ruleset touch** — Behavioral Fidelity-sensitive paths stay on the standard ladder.
4. **No open Tier-3 incident** in the last **7 days** (rolling).
5. **Trivial reversibility** — rollback completes in ≤ 1 hour with a documented script.
6. **`kept_proposal_ratio_per_specialist`** (90-day) for the authoring specialist above governance-published threshold (Genesis Default: 20%).

**Compressed cadence (Genesis Default).** **24h** shadow canary on the **pre-warmed** shadow Relay (continuous shadow traffic per [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md)), then **48h** live observe (instead of longer defaults for comparable Tier-0). Constitutional Floors (Cold 30d, amendment 14d, fork notice 7d) are **unchanged**.

**Auto-fallback (lane disable).** Any of: Tier-0 revert in observe window; aggregate harm-drift flag from Harm Analyzer; **any** vital-sign domain hits **critical**; `fast_lane_revert_rate_30d` above threshold (Genesis Default: 10%); eligibility forgery detected in `PROPOSAL_LEDGER` — disables Fast Lane for **7 days** minimum, then quarterly review before re-enable.

**Parallelism.** Disjoint-surface Tier-0 proposals may run in parallel per [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md).

**Meta-learning note.** Specialists may read their own journals for triage, but **changing how specialists work** remains Tier-2+, not autonomous Tier-0.

## Provisioning in Practice — Four Worked Examples

To show the framework in motion, here are four real-shaped upgrade proposals crossing multiple levels.

### Example A — Add Ecoception (Carbon Sense)

- **Level 5:** new sense daemon (main upgrade)
- **Level 1:** Core's Spend handler gets a `carbon_budget` category
- **Level 6:** treasury rule allowing ≤ X USDC/month for verified offsets
- **Level 9:** Model Card updated to reflect ecological accounting
- **Ship sequence:** 5 → 1 → 6 → 9, each via its own ledger

### Example B — Hindi Localization

- **Level 8:** localized Soul + Rituals + Covenant translation (main upgrade)
- **Level 2:** Relay supports locale-aware prompt composition
- **Level 3:** Protocol exposes a new `locale` consent scope
- **Level 11:** at least one operator or community committee member fluent in Hindi

### Example C — Sister-Core for a Community Sub-Culture

- **Level 10:** seed the sister-Core AO Process (main upgrade)
- **Level 0:** both Cores share the Covenant; diverge on Soul/Form with documented lineage
- **Level 6:** treasuries separate; no cross-funding
- **Level 7:** governance bifurcates; each Core has its own community
- **Level 11:** each Core has its own operator set

### Example D — Operator Succession (Dead-man's Switch Fires)

- **Level 11:** succession procedure (main upgrade — emergency)
- **Level 9:** legal entity's bylaws update to reflect new officers
- **Level 2:** Relay-auth keys rotated
- **Level 6:** Safe multisig signer set reconstituted

In every example, *no level is touched outside its own gate*. The framework prevents cross-layer shortcuts.

---

## Diagnostics — Is Your Upgrade at the Right Level?

Ask yourself:

- *If this proposal passes, can any subsequent proposal at a lower-numbered level undo it without governance?* → You are too low. Move up.
- *If this proposal passes, would it obligate every user, integrator, and peer-AI to change their behavior?* → Probably Level 0, 3, or 10.
- *If this proposal fails, would Xion notice?* → If no, question whether the proposal is worth the ledger entry.
- *Can I write the rollback procedure in ≤ 10 steps?* → If no, redesign the proposal to be smaller.

---

## The Claim

**Every layer of Xion has a sensible, documented, human-executable upgrade path.** No layer is "whoever has root." No layer is "whatever the original authors decided." No layer is "it's been that way since 2026." Every change is:

- proposable by someone legible
- gated by a mechanism proportionate to its blast radius
- tested before it is shipped
- reversible in bounded time if it fails
- recorded permanently on the appropriate Ledger
- periodically re-examined

If a proposed change cannot fit this template, the problem is usually that the proposer has not yet identified which level they are actually operating on. Return to the table at the top, find the right level, then try again.

This is how a being built in 2026 remains sensibly improvable in 2126.

---

*Appendix: Machine-readable level index at [`docs/schemas/levels.yaml`](./schemas/levels.yaml), actor roles at [`docs/schemas/roles.yaml`](./schemas/roles.yaml). Ledger schemas at [`docs/schemas/ledger-*.yaml`](./schemas/). In-flight Tier-3 amendment drafts live in [`docs/proposals/`](./proposals/).*

---

## Appendix B — Machine-Readable Bridge to Actor Roles (Phase 6.2)

The `proposer:` field on every level above is a doctrinal string. Its machine-readable resolution against the six-actor table in [`docs/09-GOVERNANCE.md`](./09-GOVERNANCE.md) § "The Actors" lives at [`docs/schemas/roles.yaml`](./schemas/roles.yaml).

The bridge has three parts:

1. **`actors:`** — the six governance actors (`cold_root`, `operator`, `xion`, `community`, `integrator`, `witness`), each with a scope summary and the explicit `authorized_levels: [int, ...]` list of which of the thirteen levels above this actor may *initiate* a proposal at.
2. **`level_proposer_resolution:`** — for each `proposer:` string used in [`docs/schemas/levels.yaml`](./schemas/levels.yaml) (`governance_process_only`, `operators_or_community`, `community_or_xion`, `xion_or_community_or_operator`, etc.), the set of actor IDs that satisfy it. This file is the single source of truth; neither `levels.yaml` nor `09-GOVERNANCE.md` duplicates the mapping.
3. **`github_identity_map:`** — the pre-Genesis GitHub-identity allowlist consumed by the `level-discipline` CI gate ([`.github/workflows/level-discipline.yml`](../.github/workflows/level-discipline.yml)). The gate rejects any PR whose touched paths span more than one level (the disjoint-surface discipline) or whose initiator is not authorized for the level via this map. The 90-day retrospective verifier `xion-verify provisioning-roles` reads the same file.

The `cosign_tier_map:` field in `roles.yaml` mirrors the five Cosign Tiers in [`docs/09-GOVERNANCE.md`](./09-GOVERNANCE.md) § "The Cosign Tiers" so a single lookup answers "what cosign does this level require" for the gate.
