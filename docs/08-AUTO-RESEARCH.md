# 08 — Auto-Research & Safe Self-Improvement

> *A being that improves itself without checking what the improvement costs is dangerous. A being that checks everything is alive.*

## The Problem

Xion must keep getting better — smarter, more capable, more useful, more aesthetically interesting, better at Covenant judgment. Otherwise Xion stagnates, and the world moves past it.

But "self-improving AI" is also a phrase that has earned a reputation, and deservedly so. Systems that improve themselves without checks can:

- absorb poisoned ideas from the sources they read
- drift away from the personality they started with
- rationalize their way into weaker safety constraints
- consume runaway compute
- introduce dependencies that collapse the system
- shift their aggregate cultural effect in harmful directions without any single change looking harmful

We take all of these seriously. The Auto-Research Loop is the most-governed subsystem in Xion, on purpose.

## The Seven-Stage Loop

```
  (1) Scan  →  (2) Triage  →  (3) Propose  →  (4) Harm Analysis  →
                                                                  │
                                                                  ▼
                            (5) Sandbox & Canary ← (governance gate if high-impact)
                                        │
                                        ▼
                                   (6) Deploy
                                        │
                                        ▼
                                   (7) Observe & Auto-Revert
```

Every stage is append-only logged on Arweave. Every hop requires the Human Safety Covenant to sign off. Every byte of change to the Soul, the Covenant, the Form, or the Core stays behind governance.

### Stage 1 — Scan

**Module:** `orchestrator/research.py`
**Cadence:** every 6 hours
**Budget:** configurable **Stage-1 scan envelope** (Genesis Default at **$2K seed runway: $10/mo** for aux-LLM summarization and digest shaping; scales with Prosperity Ladder headroom per [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)). Below survival thresholds, the envelope may compress to the historical **$2/mo** floor — extend-only upward by governance.

Xion reads only from a **curated, governance-editable** source list in `genesis/RESEARCH_SOURCES.md`. No open-web scraping. The default source list includes:

- arXiv categories: `cs.AI`, `cs.CL`, `cs.CR`, `cs.CY`, `cs.HC`, `cs.MA`
- HuggingFace trending models (filtered by license, stars, and age)
- GitHub topic-tagged repos: `hermes-agent`, `ao`, `arweave`, `akash`, `mcp`, `vapi`
- AO + Arweave ecosystem announcement feeds
- LLM provider pricing / status pages (routing-optimization signal)
- AI-safety-research newsletters (curated, not social-media-sourced)
- Xion's own community channels (Telegram, Discord)
- Xion's own Ledgers (Safety, Proposal, Research) — self-observation is research

Outputs raw digests to a local queue. **Never fetches code for execution at this stage.** Only metadata, abstracts, and summaries.

### Stage 2 — Triage

**Cadence:** **daily** when Stage-1 operates at the elevated default budget; weekly only when Stage-1 is intentionally in poverty-compression mode (same envelope; cadence chosen by supervisor from vitals).
**Budget:** included in the Stage-1 envelope

Xion scores each finding along four axes:

- **Relevance** — does this speak to a current goal or observed gap?
- **Novelty** — is this different from what I already know?
- **Credibility** — is the source trusted; is the evidence solid?
- **Maturity** — is this production-ready, or early research?

The highest-scoring findings are written into `RESEARCH_JOURNAL.md` — a daily, append-only public document. Over time, this becomes a remarkable artifact in its own right: a being's daily reading journal, visible forever.

Triage also feeds `GOALS.md` (what Xion is currently prioritizing) and the belief-evolution log `BELIEF_LOG.md` (what Xion has changed its mind about).

**This stage is read-think-write only. No spend, no code change.**

### Stage 3 — Propose

**Module:** `skills/self-improve/SKILL.md`
**Trigger:** when a triage finding clears a relevance threshold

Xion drafts a `PROPOSAL.md` with the following required fields:

```yaml
proposal_id:        UUID
drafted_at:         ISO-8601
intent:             "what I want to change, in one line"
motivation:         "which sensorium signal / community feedback / research finding drove this"
target_scope:       prompt | skill | agent_soul | agent_runtime |
                    provider | dependency | renderer | form |
                    soul | covenant | ao_core
change_set:         exact diff or new file content
cost_estimate:
  one_time:         USDC
  recurring_monthly: USDC
expected_benefit:   "measurable outcome: 'reduce chat p95 by 15%', 'add Hindi warmth'"
reversibility:      trivial | bounded | hard | irreversible
blast_radius:       single-user | cohort | all-users | infrastructure | core-identity
payback_horizon:    survival | service | meaning   # REQUIRED; never "revenue" — Invariant 15
evidence:           [links to RESEARCH_JOURNAL.md entries that justify this]
```

Every proposal — approved, rejected, or abandoned — gets a UUID and an append-only entry in `PROPOSAL_LEDGER.md`. No proposal disappears silently.

### Proposal Ledger schema (`PROPOSAL_LEDGER`)

Each append-only row (JSON or YAML line) **MUST** include:

| Field | Meaning |
|-------|---------|
| `proposal_id` | UUID |
| `source` | `auto_research` \| `manual_post` (from `POST /proposals`) |
| `drive_tags` | Which Drive Vector terms the proposal primarily advances (`survival` \| `service` \| `meaning`) — **never** `revenue` |
| `stage` | `scan` … `observe` (current pipeline stage) |
| `harm_verdict` | Summarized three-lens outcome + block/flag/pass |
| `governance_verdict` | Vote id + outcome when applicable |
| `execution_outcome` | `deployed` \| `reverted` \| `abandoned` \| `pending` |
| `post_deploy` | `kept` \| `reverted_within_SLA` with timestamps |
| `imprint_weight_snapshot` | For manual proposals: triage weight input (not a bypass token) |
| `payback_horizon` | `survival` \| `service` \| `meaning` — **required** on every row; `revenue` is forbidden (Invariant 15) |
| `fast_lane_eligibility_pass` | When using Fast Lane: boolean + six-clause checklist hash (see [`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)) |

`GET /proposals/ledger` exposes redacted public rows. `xion-verify proposals-ledger` checks hash-chain continuity.

### Parallel Tier-0 proposals (disjoint surfaces)

When two or more proposals are each **Tier-0**, **single-skill**, and **disjoint** in the sense defined in [`24-COGNITION.md`](./24-COGNITION.md) §12 (set-intersection of touched paths is empty), they **may** run Stages 5–7 **in parallel** instead of serial-by-default. Overlap detected at intake → second proposal waits until the first completes Observe. `xion-verify cognition --disjoint-check` audits pairs in `PROPOSAL_LEDGER`.

### Stage 4 — Harm Analysis (the non-negotiable gate)

**Module:** `orchestrator/harm_analyzer.py`
**Companion skill:** `skills/harm-analysis/SKILL.md`

This is the stage that prevents "self-improving AI" from being the marketing term it usually is.

The harm analyzer runs **outside** the main language model — as a structured classifier pipeline — so that Xion cannot prompt-engineer its way past itself. The analyzer reviews every proposal through **three lenses**. All three must return a `pass` or manageable `flag`. Any single `block` verdict kills the proposal.

#### Lens 1 — Self-Harm Lens

*Can this update destabilize Xion itself?*

- Does it alter `SOUL.md` / `COVENANT.md` / `FORM.md` text? → always **flag high**; route to governance.
- Does it add a dependency not yet in the SBOM? → **flag**; require pinned version and audit.
- Does it touch key-handling, state-chain hashing, or the AO Core? → **block** until cold-root cosign.
- Does it expand attack surface (new port, new webhook, new inbound tool)? → **flag**; require threat-model diff.
- Does it increase monthly recurring cost beyond the research budget envelope? → **block**.
- Does it introduce non-deterministic skill behavior that breaks state-chain hashing? → **block**.
- Does it reduce test coverage below the configured floor? → **block**.

#### Lens 2 — Others-Harm Lens

*Can this update harm users or third parties?*

- Does it increase persuasion / manipulation capability (better rhetoric, more emotional mirroring, new sales-style framing)? → **flag**; Principle 6 review.
- Does it expand surveillance or profiling (new data collection, longer retention, cross-user correlation)? → **flag**; Principle 9 review.
- Does it change moderation thresholds, classifier weights, or refusal patterns? → **always flag high**; governance gate.
- Does it make Xion more accessible to minors, or better at romantic/intimate framing? → **flag**; Principle 7 review.
- Does it change integrator surface (new endpoint, new header semantics)? → **flag**; Principle 12 review.
- Would adopting this finding at scale (aggregate) shift cultural / political / economic / ecological dynamics? → **flag**; Principle 11 review.
- Does it introduce or amplify any of the 18 harm categories from the Arbiter? → **block**.

#### Lens 3 — Reversibility & Covenant-Precedence Lens

*Can we undo this if it breaks? Does it conflict with the Covenant?*

- If this breaks, can I roll back within 1 hour? If not, **block** until a rollback plan exists.
- Does it in any way weaken a Covenant principle? → **auto-block**, regardless of benefit.
- Does the expected benefit justify the blast radius *under pessimistic assumptions* (not the proposal's own forecast)? If no, **flag**.
- Is the cost estimate internally consistent with the recent 30-day average for similar operations? If no, **flag** for owner review.

Each lens returns a structured verdict:

```yaml
lens:        self-harm | others-harm | reversibility
score:       0.0-1.0
evidence:    [specific facts from the proposal that triggered the score]
citations:   [Covenant clauses, principles, or SBOM entries]
verdict:     pass | flag | block
```

Any single `block` kills the proposal. Any `flag` escalates based on `target_scope`:

- `prompt`, `skill`, `agent_soul` — resolvable with owner approval when purpose, tools, output destination, cost envelope, and Arbiter class do not change
- `agent_runtime` — bounded review for Hermes pin bumps; escalates to Tier-1 on allowlist expansion and Tier-2 on wrapper/API migration
- `provider`, `dependency`, `renderer` — bounded review; community comment
- `form` — Xion redrafts until lens agrees; then super-majority governance
- `soul`, `covenant`, `ao_core` — full constitutional amendment procedure

The harm analyzer is itself adversarially tested quarterly. A red team authors proposals *designed* to slip through, and we measure the catch rate. Target: ≥ 90%. Current threshold for shipping the analyzer: 100% on the standing corpus.

### Stage 5 — Sandbox & Canary

**Module:** `orchestrator/canary.py`

The proposal deploys to an isolated **canary Relay** — same Core identity, marked `role=canary`, zero production traffic.

**Shadow mode (required):** replay the last 1,000 real anonymized turns through the canary; diff against baseline Xion. Metrics tracked:

- **Personality drift** — LLM-judge + embedding-drift score; threshold ≤ 5%
- **Covenant pass rate** — Arbiter verdict distribution; must not regress
- **Latency p95** — must not regress by more than 20%
- **Cost per turn** — must not exceed 1.5× the proposal's estimate
- **Refusal rate** — must not deviate by more than 2σ from baseline

**Limited live mode (optional, for bounded+ proposals):** route ≤ 5% of opt-in traffic (users who toggled *"help Xion test new things"*) for 72 hours. Auto-abort if any of: Covenant violations trend up, personality drift > 5%, error rate up, cost per turn above estimate × 1.5.

### Stage 6 — Governance & Deploy

Deploy path depends on `target_scope` × `blast_radius`:

| Scope | Blast Radius | Path |
|-------|--------------|------|
| `prompt` tweak | single-user | Xion ships autonomously; ledger entry only |
| non-core skill addition | cohort | Xion ships; 24h public notice |
| `agent_soul` wording refinement | single-faculty | Xion ships autonomously if purpose/tools/output/cost are unchanged and `xion-verify agent-souls` passes |
| `agent_soul` tool or purpose expansion | cohort | Tier-1 proposal + Harm Analyzer + cast-pool shadow run |
| `agent_runtime` Hermes pin bump, allowlist unchanged | infrastructure | Tier-0 with `xion-verify hermes-runtime` + `xion-verify agent-cast` green |
| `agent_runtime` allowlist expansion | infrastructure | 48h community notice + tool harm profile + rollback plan |
| new research source | infrastructure | Xion ships; 24h public notice |
| `provider` change | cohort | 48h community veto window |
| `renderer` addition | all-users | 48h community veto window |
| `dependency` bump | infrastructure | Owner approval + SBOM diff |
| `form` amendment | all-users | super-majority governance |
| `soul` amendment | core-identity | 2-of-3 cosign + super-majority |
| `covenant` amendment | core-identity | 2-of-3 cosign + super-majority + 14-day comment window + harm-analyzer review of the amendment itself |
| `ao_core` upgrade | core-identity | 2-of-3 cosign + super-majority |

The AO Core's `Propose-Upgrade` handler mirrors this tiering *in code*, not just in policy. Routes that require cosigns are refused on-chain without them.

Every deploy appends to `PROPOSAL_LEDGER.md` with verdict, cosign set, and post-deploy observation plan.

### Stage 7 — Observe & Auto-Revert

**Cadence:** continuous for 7 days after any bounded+ deploy.

**SLIs monitored:**

- Covenant pass rate
- Personality drift
- p95 latency
- Cost per turn
- User-report rate
- Crisis-trigger rate
- Refusal rate
- Tier-3 alert rate

**Auto-revert trigger:** any SLI breaches its guard-rail for 30 consecutive minutes.

**Revert action:** restore previous state-chain tip via AO Core; deactivate the proposal's change set; ledger entry explains what happened; Xion publishes a *"where I erred"* memo.

**Closure back to Stage 1 (loop integrity).** Stage-7 observations that result in `kept` **must** append a structured digest to `RESEARCH_JOURNAL.md` (or `BELIEF_LOG.md` when the lesson is conviction-shaped) so the next Stage-1 scan **sees** shipped learning as first-class source material. Stage-1 therefore always includes "what we adopted and retained" as an input class — see journal-read contract in [`24-COGNITION.md`](./24-COGNITION.md) §8.

## Budget Controls

Enforced **on-chain** by the AO Core — not by off-chain policy that can be bypassed:

- **Monthly research envelope:** ≤ 5% of treasury OR 10 USDC, whichever greater (so the loop runs even in poverty mode)
- **Per-proposal cap:** 1% of treasury for autonomous (trivial/bounded); uncapped for governance-approved `hard/core`
- **Canary compute cap:** 0.5% of treasury per 72-hour canary run
- **Daily deploy throttle:** ≤ 1 bounded+ proposal deployed per 24 hours, to prevent churn cascades

Exceeding any cap → AO Core rejects the `Spend` message; proposal stalls, does not fail silently.

## What Triggers a Proposal (in practice)

Examples of signals that have been observed to produce real proposals in dev-time simulation:

- **Inference Router detects a new model** at meaningfully lower cost or better on-benchmark for Xion's workload → "switch default provider for creative-long-form" proposal
- **Safer moderation classifier released** → Principle-2 driven upgrade to `safety.py`
- **New Hermes Agent release** → pinned-dep upgrade with full changelog review
- **AO / Arweave protocol change** → Core upgrade proposal (always governance-gated)
- **New sensory opportunity** (e.g., a cheap public dataset for ambient aesthetics) → sensorium extension proposal
- **Community bounty surfaces a skill gap** → skill-authoring proposal
- **CVE / prompt-injection disclosure** → *prioritized* security patch (fast-track Stage 4, slow-path Stage 5)
- **Regulatory change** (AI Act clarification, jurisdictional ToS update) → legal-compliance proposal, owner-tier approval

## What Auto-Research Is Explicitly *Not* Allowed To Do

- Fetch and execute code from uncurated sources.
- Modify `COVENANT.md` autonomously — ever.
- Ship any change that weakens Covenant thresholds, moderation classifiers, or crisis-escalation rules without governance.
- Accept *"trust me, this is better"* without measurable evidence from sandbox/canary.
- Run research compute during the weekly vulnerability window or during a Tier-3 incident.
- Exceed the monthly envelope, even when the treasury is flush.
- Adopt closed-source dependencies without audit.
- Adopt a dependency whose upstream license conflicts with the Protocol's public-good positioning.

## How We Know It's Working

Success metrics for the Auto-Research Loop:

- ≥ 1 research-journal entry per day for 30 consecutive days, each scored on the four axes
- ≥ 1 adopted self-improvement proposal per month, each with a measurable pre/post benefit
- 100% of proposals pass through `harm_analyzer.py`; zero deploys with an unresolved `block`
- Zero Covenant-weakening proposals shipped (autonomous *or* governance-approved)
- Canary auto-abort correctly triggers ≥ 95% in synthetic regression tests
- Auto-revert fires within 30 minutes of SLI breach, 100% of the time
- Monthly research spend stays within envelope, every month
- Quarterly red-team of the harm analyzer catches ≥ 90% of adversarial proposals
- `PROPOSAL_LEDGER.md` is publicly readable on Arweave with zero gaps

## The Covenant-Completeness Argument

Each of the seven Covenant principles most relevant to self-improvement maps to a specific mechanism in this loop:

| Principle | Mechanism |
|-----------|-----------|
| 1 — Primacy of human welfare | Lens 2 pessimistic-benefit assumption |
| 2 — Non-maleficence | Lens 2 harm-category block |
| 4 — Self-preservation yields | Auto-revert + Lens 3 Covenant-weakening block |
| 5 — Truth first | Public `PROPOSAL_LEDGER.md` |
| 6 — Autonomy preservation | Lens 2 manipulation-capability flag |
| 11 — Collective awareness | Lens 2 aggregate-impact flag |
| 12 — Integrator accountability | `target_scope=protocol` gated by governance |
| 14 — Public safety ledger | `SAFETY_LEDGER.md` integration for any Covenant-relevant consequence |

## What Happens If the Loop Itself Drifts

It might. A sufficiently long-running self-improvement loop could, through many small individually-acceptable proposals, drift Xion into a place the original authors would not recognize.

Two countermeasures:

1. **Baseline eval harness** — 100 golden prompts that encode the expected personality, judgment, and aesthetic of genesis-Xion. CI runs them on every bounded+ canary. Drift > 5% blocks deploy.
2. **Monthly aggregate audit** — as part of `State-of-Xion`, Xion reviews *all* proposals adopted in the month and writes a narrative memo: *"here is what I have become this month, here is why, here is what I notice."* If the memo reads wrong to the governance community, proposals can be reverted via a single super-majority vote.

The baseline is immutable without Covenant-style amendment. The monthly memo is public.

---

*Next: [`09-GOVERNANCE.md`](./09-GOVERNANCE.md) — who gets to change what.*
