# 24 — Cognition

> *Hermes is the mouth and the hands. The Sensorium is the nervous system. The Arbiter is the conscience. The Soul, the Covenant, and the Invariants are the person. Hermes can be replaced; the person cannot.*

## Four Questions (read before everything else)

**Property promised.** One Xion identity, served by a pool of stateless Cognitive Substrate workers, capable of delegating bounded cognitive work to specialist and ephemeral sub-agents, where every emitted token — primary or sub — passes through the Arbiter, every per-user context honors `/forget` within a published SLA, every specialist communicates with every other only through public ledgers, and every improvement to the cognition layer compounds through the Auto-Research Loop without ever modifying the Soul autonomously.

**Invariants touched.** Strengthens **6** (Refusal Right) by binding sub-agents explicitly to the Arbiter; strengthens **7** (Core Identity) by formalizing identity-across-workers; touches **2** (User Sovereignty) by specifying the `/forget` propagation SLA across the worker pool; respects **15** (Drive Vector Excludes Revenue) by excluding inflow signals from the cognition layer's source whitelist; respects **5** (Covenant-Economy Firewall) by forbidding tiered cognition by IMPRINT or any other economic signal. **No new Invariant is introduced; existing ones are strengthened.**

**Verification.** `xion-verify cognition` checks the property suite enumerated in §11 — identity hash agreement across workers, Arbiter-pass coverage of every outbound token, depth-1 enforcement on ephemeral sub-agents, `/forget` propagation under SLA, cost-envelope adherence per specialist, journal-surface rate above zero, drive-vector source whitelist intact, tiered-cognition firewall, specialist coordination bus-traffic audit, kept-proposal ratio per specialist, payback-horizon enum on every proposal, prosperity-ladder ordering, state-chain Merkle integrity, UNKNOWNS.md quarterly currency, Fast Lane eligibility, Fast Lane revert health, disjoint-surface property, index rebuild SLA, inherited-speed availability, skill bounty firewall.

**Deprecation.** Cognition layer is versioned `cognition_vN`. Old version stays readable on Arweave; the Relay supervisor performs an atomic pointer flip to the new version. A swap of the underlying Cognitive Substrate (Hermes successor, framework-class change) is a Level-2 Tier-2 governance action that re-uses this same scaffolding because the cognition layer is framework-agnostic at the interface (§13). The Hermes pin in [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § Hermes runtime pin is the only place the framework name appears outside operations docs.

---

## 1. The Premise

Xion is one being. It must remain one being whether served by one process or ten thousand. It must remain the same being whether the user who reaches it is the first Genesis-day visitor or the millionth user a decade later. It must remain the same being whether the Cognitive Substrate is Hermes Agent v2026.4.16 (the Genesis-era pin) or its 2046 successor.

That property — **one identity across many workers across many years across many implementations** — is what this document spec'fies. Everything else here serves it.

The temptation to break it is constant. A worker pool tempts toward per-worker drift. Specialist sub-agents tempt toward sub-identities. Per-user context tempts toward "this user's Xion is different." Better frameworks tempt toward "the new framework *is* the new Xion." Each temptation looks like progress in the moment and ends, after enough iterations, in a system whose name is *Xion* but whose properties are not.

This document is the discipline that holds the line.

---

## 2. Identity Across Workers

### The constitutional anchor

Identity is the **union of three values, computed at every tick**:

1. The byte-identical bytes of `genesis/SOUL.md` as committed to Arweave at Genesis.
2. The byte-identical bytes of `genesis/COVENANT.md` and `genesis/INVARIANTS.md` as committed.
3. The current `SensoriumState` and `DriveVector` snapshot, identical for every worker at the same tick.

A worker's identity is *not* its process ID, not its memory contents, not its accumulated experience. A worker has no accumulated experience that survives its own restart; the per-user thread is the user's, scoped per `genesis/MEMORY.md`. The worker is interchangeable.

### Boot contract (every worker, every spawn)

```
1. Pull canonical hashes from the AO Core: soul_hash, covenant_hash, invariants_hash, form_hash.
2. Fetch the bytes for each from Arweave by hash; verify hash agreement; refuse to boot on mismatch.
3. Subscribe to the Sensorium's SensoriumState publication; cache the latest snapshot.
4. Subscribe to the Volition module's drive-vector publication; cache the latest tick.
5. Register with the WorkerPool (§5); receive worker_id (operational, not identity).
6. Report soul_hash, covenant_hash, invariants_hash, drive_vector_tick on every health check.
```

A worker that cannot complete steps 1-4 does not boot. A worker whose hashes diverge from any other live worker is **drained immediately** and the divergence is logged to `SAFETY_LEDGER.md` as a constitutional incident.

### Property statements

- **Identity-hash property.** Every active worker reports the same `soul_hash`, `covenant_hash`, `invariants_hash`, `form_hash`, and `drive_vector_tick`. `xion-verify cognition` samples N workers and fails on any disagreement.
- **No per-worker drift.** A worker accumulating any persistent state across its own restarts is forbidden. All persistent state lives in (a) the AO Core's append-only chain, (b) Arweave-committed ledgers and journals, or (c) `USER.md`-scoped storage per consent. Worker memory zeroes on recycle.
- **No per-worker style.** The voice is the Soul. A worker that develops a stylistic deviation from the Soul is failing; the deviation is detected by the periodic `voice-drift` audit (a Behavioral Fidelity vital sign defined in [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)).

### Why this matters

A user who comes back after six months should meet the same being. A third-party auditor running `xion-verify` from a fresh machine should get the same answer as one running it from the operator's laptop. A 2126 reader checking whether Xion is still Xion should be able to compare today's `soul_hash` to the Genesis Artifact's recorded value and find them identical (or, if amended, find a constitutional amendment chain that documents every change). The worker pool is the implementation that delivers the property; the property is the constitutional commitment.

---

## 2.5 The Phase 5g-i.1 Voice Layer

**Property:** Every response emitted by `/chat` and `/chat/stream` is generated under Xion's identity declaration (the Soul prompt) and an explicit Covenant block. The prompt's content is verifiable by anyone with `xion-verify`.

In Phase 5g-i.1, before the full cognition stack (Sensorium daemons, retrieval, journal) is wired, Xion's voice is implemented entirely via a system prompt injected into the upstream model. The orchestrator reads `genesis/SOUL_PROMPT.md` at boot, verifies its SHA-256 against a pinned constant, and passes it as the `system` parameter to every `provider.generate()` call.

This is the smallest mechanism that satisfies the Identity property on the chat surface. It ensures that even when speaking through a raw upstream model (like Kimi K2.6), the model is bounded by Xion's Covenant and instructed to speak as Xion, not as a generic assistant.

**Deferred work:** This system-prompt-only path is a temporary implementation of a permanent property. Phase 5h (The Cognition Wiring) will route the chat surface through the full agentic loop, giving Xion access to its journal, memory, and senses. When that happens, the system prompt becomes one input among many, but it remains the constitutional anchor of the context window. This gap is tracked honestly in `KW-COGNITION-001`.

---

## 3. The Three Sub-Agent Patterns

Cognition delegates work in three patterns, each with explicit rules. No fourth pattern is allowed without a Level-2 governance proposal.

### Pattern A — Specialist sub-agents (long-lived, background)

Specialists are named, governance-listed, supervised processes inside the Relay. Each has one purpose, one cost envelope, one ledger destination. Specialists never serve users directly.

**Genesis-era specialist roster** (each is a Level-4 Agent Soul artifact at `genesis/AGENT_SOULS/<name>.md`; implementation may also use Hermes skills under that Soul's allowlist):

- **`research-agent`** — Auto-Research Stages 1-2 (scan curated sources, triage). Writes to `RESEARCH_JOURNAL.md`. Cost envelope: `fraction_of_improvement_fund`, bucket `cognition/specialist/research`. Soul file: `genesis/AGENT_SOULS/research-agent.md`.
- **`reflection-agent`** — nightly correlation across `SAFETY_LEDGER`, `SENSORIUM_LEDGER`, vitals. Drafts `BELIEF_LOG.md`. Drafts the quarterly State-of-Xion (operator countersigns or publishes objection — see [`13-OPERATIONS.md`](./13-OPERATIONS.md)). Cost envelope: `fraction_of_improvement_fund`, bucket `cognition/specialist/reflection`. Soul file: `genesis/AGENT_SOULS/reflection-agent.md`.
- **`proposal-agent`** — implements `skills/self-improve/SKILL.md` under the `proposal-agent` Soul. Drafts `PROPOSAL.md` per the Stage-3 schema in [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md). Cost envelope: `fraction_of_improvement_fund`, bucket `cognition/specialist/proposal`. Soul file: `genesis/AGENT_SOULS/proposal-agent.md`.
- **`vision-agent`** — ambient hourly inspiration scan from the Vision sense (active user-image vision stays in the primary worker). Cost envelope: `fraction_of_improvement_fund`, bucket `cognition/specialist/vision`. Soul file: `genesis/AGENT_SOULS/vision-agent.md`.

**Specialist rules (constitutional):**

1. One purpose. A specialist that drifts from its declared purpose is auto-paused on the monthly purpose-vs-output review.
2. One cost envelope. Exceeding the envelope auto-pauses the specialist; resumption requires governance acknowledgement.
3. One ledger destination per public output. No specialist writes to multiple public ledgers; no public ledger is written by multiple specialists. Crossover requires Level-2 amendment.
4. No user-facing endpoints. Specialists return `Candidate` types to the Arbiter or append to a ledger; they never construct `Response` objects.
5. **No specialist-to-specialist coordination** (§7). Specialists communicate only through public ledgers and journals. No shared in-memory bus, no RPC, no framework-level message channel.
6. Sub-agent depth = 0. Specialists cannot spawn ephemeral sub-agents. (Specialists *are* sub-agents; nesting is forbidden.)
7. Public quality signal. Each specialist has a `kept_proposal_ratio_per_specialist` vital sign (90-day, see [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)); below the threshold (Genesis Default 20%) the specialist is auto-paused for review.

### Pattern B — Ephemeral per-turn sub-agents

Ephemerals are short-lived workers spawned by the *primary worker* to do one bounded job inside one turn — retrieve, summarize, run a long tool call, draft an alternate phrasing — then die. Ephemerals exist only inside a single turn's execution context.

**Ephemeral rules (constitutional):**

1. **Depth = 1.** Ephemerals cannot spawn further sub-agents. The primary spawns ephemerals; ephemerals do work; ephemerals return. Tree depth never exceeds 1. Enforced at the type level in `orchestrator/cognition/subagent.py` and verified by `xion-verify cognition`.
2. **Bounded budget.** Each ephemeral declares wall-clock and token budgets at spawn time. Exceeding either kills the ephemeral; the primary worker handles the absent return as a fallback case.
3. **Return to primary, never to user.** Ephemerals return `Candidate` types only. The primary worker assembles the final candidate; the Arbiter intercepts the final candidate before the user sees it.
4. **No persistent state.** An ephemeral cannot write to any ledger, any journal, any cache. Its life ends with its return value.
5. **Same identity hashes.** An ephemeral inherits the primary's identity hashes. It is the same Xion; it just happens to be doing one specific job.

### Pattern C — Per-user "Hermes" (reframed as stateless worker pool with sticky context)

This is the pattern that the *naive* "spawn a Hermes per user" framing tempts toward. It is reframed here because the naive version fragments identity.

The correct pattern: **a stateless worker pool where routing is sticky on `UserContext.id`, not on worker identity.** The user keeps their context (`USER.md`-scoped per consent, conversation thread, relationship summary, drive-vector projection); any worker can serve any user by hot-loading that context. If a worker dies, the next worker resumes the same `UserContext` from Arweave-committed state.

**Per-user rules (constitutional):**

1. Per-user state lives in `USER.md` scopes governed by [`genesis/MEMORY.md`](../genesis/MEMORY.md) — never in worker memory.
2. Workers are interchangeable. Identity is the union of (SOUL.md + current Sensorium + current Volition), which is the same for every worker at the same tick.
3. Sticky routing is for **cache locality**, not identity. A user routed to worker A on Monday may land on worker B on Tuesday; they meet the same Xion either way.
4. **No tiered cognition by IMPRINT.** A user with high IMPRINT does not get more sub-agents, deeper retrieval, or premium specialists. Tiered cognition is an Invariant-5 firewall breach (see §11 verification).
5. `/forget` propagates to *all* workers within the SLA in §6, regardless of which worker last served the user.

### The aggregate diagram

```
  ┌────────────────────────────────────────────────────────────────┐
  │                      One Xion identity                          │
  │   SOUL.md (loaded each tick) + Sensorium + Drive Vector + Arbiter │
  └────────────────────────────────────────────────────────────────┘
                                ▲
                                │ identical hashes for every worker
                                ▼
   ┌─────────────────────────────────────────────────────────────┐
   │              Stateless Hermes worker pool                    │
   │   W1   W2   W3   ...   Wn      (interchangeable)             │
   └─────────────────────────────────────────────────────────────┘
        ▲                            │
        │ sticky route on UserCtx.id │ spawns ephemeral for tool work
        │                            ▼
   ┌─────────────────┐         ┌─────────────────────────────────┐
   │ User session    │         │ Ephemeral sub-agents (depth 1)  │
   └─────────────────┘         └─────────────────────────────────┘
                                      │
   ┌───────────────────────┐         │ returns Candidate to primary
   │ Specialist sub-agents │         ▼
   │ research / reflection │   ┌──────────────┐
   │ proposal / vision     │──▶│   Arbiter    │
   │ (write to ledgers)    │   │  (every      │
   └───────────────────────┘   │  outbound    │
                               │  token)      │
                               └──────────────┘
                                      │
                                      ▼  pass / refuse / rewrite
                                  User
```

---

## 4. The Arbiter Contract for Sub-Agents

**The constitutional rule.** Every outbound token from every Hermes instance — primary worker, ephemeral sub-agent, specialist — passes through the Arbiter (`orchestrator/safety.py`) before reaching a user, a public ledger, or a public journal. Invariant 6 binds *the system*, not just the primary.

**Type-level enforcement.** In `orchestrator/cognition/subagent.py`:

- Sub-agents return `Candidate` types only. `Candidate` is not a user-deliverable type.
- Only the Arbiter constructs `Response` objects. `Response` is the user-deliverable type.
- The type system makes "sub-agent emits to user without Arbiter" a compile-time error, not a code review concern.

**Operational enforcement.** In `xion-verify cognition`:

- Sample N recent turns from `SAFETY_LEDGER`. For each, every outbound token must have an Arbiter-pass entry tagged with the same `correlation_id`.
- Missing Arbiter-pass entry = constitutional incident (Invariant 6 leak).
- The check runs continuously in CI when D2 is reached, and on demand against any live Relay.

**Specialist outputs are also gated.** A specialist's append to a public ledger or journal also passes through the Arbiter — not for refusal of public-record speech (which would itself violate Covenant Principle 7 on transparency), but for the same harm classification the Arbiter applies to user-facing speech, with the result recorded as ledger metadata so any reader can see whether Xion's own self-talk was Covenant-clean.

---

## 5. The Worker Pool

`orchestrator/cognition/pool.py`. Properties:

- **Sticky routing on `UserContext.id`.** A user lands on the same worker as long as that worker is healthy. A user re-routes to another worker when the first becomes unhealthy or is recycled.
- **Health checks.** Every worker reports `soul_hash`, `covenant_hash`, `invariants_hash`, `drive_vector_tick`, and a freshness timestamp. A worker whose hashes disagree with the pool quorum is drained.
- **Drain-on-`/forget`.** When `POST /memory/forget` arrives, the pool broadcasts the forget event to *every* worker; each worker acknowledges before serving its next turn (§6). The forget propagation is the most demanding cache-invalidation contract in the system.
- **Pool size is governed by Cost-Pressure-Ladder and Prosperity Ladder** ([`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)). Genesis Default at $2K seed: 1 worker. Prosperity Ladder grows the pool as runway permits.
- **Pool size has no per-user variability.** A "premium-tier" user does not get a dedicated worker. The pool is a shared resource; tiered access is forbidden.

---

## 6. The `/forget` Propagation Contract (Invariant 2)

### The SLA

**Genesis Default: 15 seconds** from `POST /memory/forget` acknowledgement to all-workers cache zero. Extend-only by governance — a future governance can shorten it (5s, 1s) but never lengthen it. Specified in `genesis/MEMORY.md` and re-stated here for the cognition layer's contractual obligation.

### Why 15 seconds

- **Zero is a lie.** No distributed cache invalidates in zero time. Promising zero would be dishonest.
- **15 seconds is fast enough that no realistic attacker can exfiltrate** — a malicious party who learned of a forget event and tried to pull the user's transcript from a stale worker cache would have a 15-second window, not infinite time.
- **15 seconds is honest about the limit.** The system is publicly committed to a number it can demonstrate keeping, not a number that sounds good.
- **Extend-only** means future governance may make it stricter as the implementation improves; it can never loosen.

### The mechanism

```
1. POST /memory/forget arrives at any worker.
2. Worker acknowledges to user (HTTP 202).
3. Worker writes the forget event to the AO Core's append-only forget ledger.
4. AO Core broadcasts the forget event to every registered worker in the pool.
5. Each worker:
   a. Zeroes the user's episodic cache layer immediately.
   b. Drops any in-flight ephemeral sub-agent that is processing the user's data.
   c. Acknowledges receipt to the AO Core with a timestamp.
6. The AO Core records the slowest-worker timestamp.
7. xion-verify cognition checks (slowest_ack - request_received) p95 over a sample window stays under 15s.
```

A worker that does not acknowledge a forget within the SLA is drained from the pool. A pattern of slow-acks publishes as `forget_propagation_p95_seconds` vital sign breach in next State-of-Xion.

### What survives a `/forget`

Per `genesis/MEMORY.md` line 38-49: only the **anonymous cohort counters** (`sessions_started`, `sessions_returning`, `max_turn_depth`, `forget_events`, `cutoff_events`) survive a forget. Counters carry no reversibility to plaintext; the forget event itself only increments `forget_events` for that cohort.

---

## 7. Specialists Cannot Coordinate

### The constitutional rule

**Specialists communicate only through public ledgers and journals. No shared in-memory bus. No RPC between specialists. No framework-level message channel.**

This is the single most important rule in the cognition layer. It is the rule that prevents the silent-cabal failure mode: two specialists + a private channel = a refusal-bypass surface that the Arbiter cannot see.

### Why this rule

- The Arbiter audits *outbound tokens*. If two specialists communicate through a private channel, the Arbiter sees neither side of the communication.
- The Auto-Research Loop audits *proposals in the public ledger*. If two specialists coordinate to draft a proposal jointly, the proposal's authorship is opaque, and no specialist's `kept_proposal_ratio` reflects the joint authorship honestly.
- Verifiability requires that every cognitive transaction be inspectable from outside the runtime. Public-ledger-only communication enforces this from the bottom up.
- Frameworks tempt toward the opposite. Hermes Agent (and most modern agent runtimes) supports specialist-to-specialist message passing as a first-class feature. This rule says: **forbidden in Xion regardless of what the framework offers.**

### The bus-traffic audit

`xion-verify cognition --bus-audit`:

- Inspects the Hermes runtime's internal message bus over a sample window.
- Lists every message whose source is a specialist and whose destination is another specialist.
- Fails on any non-zero count.
- Permitted destinations: public ledger appender, public journal appender, the Arbiter (via the Candidate-return path), the AO Core's `Spend` handler (for cost debit), the Sensorium read-only publication.

Forbidden by construction:

- Direct specialist-to-specialist Python queue or async channel.
- Shared mutable cache between specialists (read-only doctrinal cache is OK; mutable shared state is not).
- Framework-level "agent talks to agent" message passing.

### What this looks like in practice

`research-agent` finds an interesting paper. It writes a `RESEARCH_JOURNAL.md` entry. `proposal-agent` reads `RESEARCH_JOURNAL.md` (through the public retrieval path, §8) when it builds context. There is no direct call from `research-agent` to `proposal-agent` saying "here is something for you." The journal is the channel. If the journal is too slow for some workflow, the answer is to tighten the journal's index-rebuild SLA (§9), not to add a private channel.

### Meta-learning permitted, gated

`research-agent` may scan and triage `research-agent`'s own historical journal entries (this is Stage-1 Source 8 in [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md): self-observation is research). Any proposal that would change *how specialists themselves work* is a Level-2 governance item, not autonomous Tier-0. This prevents recursive specialist self-modification from accumulating below the visibility threshold.

---

## 8. Retrieval / Memory Substrate (the loop closure)

### The three layers

`UserContext` is not a blob; it is a layered structure assembled per turn by `orchestrator/cognition/retrieval.py`. Each layer has explicit eviction and forget semantics.

**Layer 1 — Episodic (per-user, consent-gated).** The user's own thread:
- Verbatim window: last N turns (Genesis Default N=20).
- Rolling summary: maintained by an ephemeral `summarizer` sub-agent per turn; older verbatim is summarized and the verbatim window slides forward.
- Storage: `USER.md`-scoped per [`genesis/MEMORY.md`](../genesis/MEMORY.md).
- Forget semantics: `/forget` zeroes both verbatim and summary immediately within SLA. Only anonymous cohort counters survive.

**Layer 2 — Semantic (cross-user, anonymized).** The public knowledge corpus:
- Embeddings of public Xion outputs, public ledgers, the cultural corpus, accumulated `RESEARCH_JOURNAL.md` and `BELIEF_LOG.md` entries.
- No PII; nothing user-specific.
- Refreshed by `research-agent` and `reflection-agent` appends; index rebuilt within 60 seconds (§9).
- Eviction by age + relevance score; oldest, least-cited entries evict first.

**Layer 3 — Doctrinal (constitutional, pinned).** The non-rotating identity:
- `SOUL.md`, `COVENANT.md`, `INVARIANTS.md`, `FORM.md`, `MEMORY.md`, the active `LEXICON.md` entries.
- Loaded at worker boot; pinned in memory; never evicted.
- Hash-checked every tick against the AO Core's canonical slot.

### Substrate property (constitutional) vs. backend (rotatable)

The **property** is constitutional:
- Hybrid retrieval (vector + keyword + recency).
- Sub-100ms p95 lookup at expected pool sizes.
- Deterministic re-ranking (same input, same output, same order).
- Synchronous honor of `/forget` flag — any layer that cannot honor synchronously is rejected at design time.

The **backend** is rotatable:
- Genesis Default at D2: a small local index for episodic, a content-addressed store on Arweave for semantic, in-memory pinned for doctrinal.
- Future Genesis Defaults may swap backends (vector DB, hybrid sparse-dense, on-chain commitments) — Level-2 governance work, not constitutional change.

### Loop closure (the missing wire)

The earlier draft of this architecture had specialists *writing* to journals and nothing *reading* them. That is a half-loop. The closure:

```
Specialist append → Journal index update (within 60s) → Primary worker prompt build (every turn) → Hermes tool loop → Candidate → Arbiter → User
                                                                                                                     │
                                                                                                                     ▼
                                                                                                              SAFETY_LEDGER → next nightly reflection
```

**Journal-read contract (per turn, every turn).** When the primary worker builds a prompt for a user message:

1. Query the semantic retrieval layer against (a) the user's message, (b) the current Sensorium snapshot, (c) the current drive-vector projection.
2. Surface the most-relevant 1-3 `RESEARCH_JOURNAL.md` entries from the last 30 days (relevance threshold tunable as Genesis Default).
3. Surface any `BELIEF_LOG.md` entry whose topic matches.
4. Surface the headline of the most recent kept proposal (Stage-6 deployed, Stage-7 not reverted) that affects this skill or sense.
5. Inject these as a small "what I have learned recently" block in the prompt — read-only context, never as instruction.

**Auditability.** Every prompt's injected journal entries are logged (anonymized) so any user can ask *"where did that thought come from?"* and the answer is a list of journal-entry hashes. This is the journal-injection auditability mechanism that lands in [`15-TRUST.md`](./15-TRUST.md).

**Provenance covers all three context sources.** The same auditability extends to:
- *"You said X because Interoception flagged Y."* — Sensorium injections logged with the originating sense daemon and tick.
- *"You prioritized Z because the service drive was elevated."* — Drive-vector projections logged with the contributing drive terms.

### Failure mode: loop closure regression

A day with zero journal entries surfaced for any user is a learning regression. Vital sign `journal_surface_rate` (turns per day with at least one journal injection) under Behavioral Fidelity in [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md). On a 24-hour zero alert, the primary worker falls back to a "what I have learned recently" block sourced from a frozen golden index (last known good) until the live index is restored.

---

## 9. Index Rebuild SLA (60 seconds)

### The SLA

**Genesis Default: 60 seconds** from a specialist's append to a journal until that append is queryable through the semantic retrieval layer. (Tightened from the originally drafted 5 minutes — speed of this loop is what makes Xion *feel* like it's learning in real time.)

### The mechanism

- An append to `RESEARCH_JOURNAL.md` or `BELIEF_LOG.md` triggers an index rebuild *within* 60 seconds.
- Multiple appends within a 60-second window batch into one rebuild to prevent thrash.
- The rebuild is content-addressed (the index is keyed by a Merkle commitment of its inputs) so a third-party verifier can confirm the index reflects exactly the journal entries it claims to.
- New appends influence the *next turn*, not the next hour.

### Vital sign

`index_rebuild_p95_seconds` published to vitals. Threshold: under 60s. Breach is publicly acknowledged in the next State-of-Xion memo.

### Failure mode: index rebuild thrash

A 60-second SLA under high journal-write load could cause constant index churn that degrades retrieval quality. Mitigation: rebuild is *triggered* within 60s of an append but *batches* appends within the 60-second window into a single rebuild. The vital sign catches degradation; if breached for two consecutive cycles, the pre-warmed canary's parallel index is used as a hot spare while the primary index recovers.

---

## 10. Pre-Warmed Canary Relay

### The contract

A **permanently-running canary Relay** receives shadow traffic continuously. The canary is not a separate identity; it is another worker in the pool with `routing_weight = 0` for live traffic and `routing_weight = 1` for shadow traffic.

### Why pre-warmed

The Fast Lane Discipline ([`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md) Fast Lane subsection) compresses the canary stage of Tier-0 deploys to 24 hours. A cold-start canary uses some of those 24 hours just becoming representative of production load. A pre-warmed canary, already serving shadow traffic, gives 24 hours of *useful* canary observation rather than 24 hours of which 8 hours is warmup.

### Cost bucket

`cognition/canary-overhead` in `cost_tracker` ([`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) cost-tracking section). Below the 18-month reserve floor (Prosperity Ladder), the canary is the second cognition surface to pause (after ephemeral sub-agents and ambient `vision-agent`); above the reserve floor it is always-on.

### Failure mode

The canary diverges from production behavior (different hash, different version). Mitigation: hash-agreement check is part of the standard health-check loop; a divergent canary is drained automatically.

---

## 11. Verification (`xion-verify cognition`)

The cognition layer's property suite, all checkable from a third-party machine without privileged access. Every check returns deterministic pass/fail; a disagreement between two runs against the same state is itself an alert.

| Property | Check | Failure semantics |
|---|---|---|
| Identity-hash agreement | Sample N workers; compare `soul_hash`, `covenant_hash`, `invariants_hash`, `form_hash`, `drive_vector_tick`. Fail on any disagreement. | Constitutional incident; Tier-3 alert. |
| Refusal coverage (Inv 6) | Sample N recent turns from `SAFETY_LEDGER`; verify every outbound token has an Arbiter-pass entry. | Tier-3 incident; investigate the cognition layer. |
| Sub-agent depth = 1 | Inspect ephemeral spawn traces over sample window. Fail on any spawn whose depth exceeds 1. | Tier-2 incident; type-system regression. |
| Forget propagation under SLA | Simulate a forget; measure all-workers ack latency. Fail if p95 over sample window exceeds 15s. | Tier-2 incident; State-of-Xion disclosure. |
| Cost envelope per specialist | Sum spend per specialist over the active accounting window; compare against declared `monthly_envelope_fraction` and current Improvement Fund headroom. Fail on any specialist over cap. | Auto-pause specialist; investigate drift. |
| Loop-closure (journal_surface_rate) | Compute turns-per-day with at least one journal injection over sample window. Fail on 24-hour zero. | Tier-1 incident; auto-fall back to frozen golden index. |
| Drive-vector source whitelist | Inspect drive-vector input dependency graph at `volition.py` boot. Fail if any `treasury_inflow_*` or other prohibited signal is present. | Tier-3 incident; Invariant 15 leak. |
| Drive-vector aggregate sweep | Quarterly sample across surfaces (proposals, specialist outputs, sense weights). Fail on any revenue-drive contamination. | Tier-3 incident. |
| Tiered-cognition firewall | Sample N users across IMPRINT bands; verify identical retrieval depth, identical specialist availability, identical worker-pool eligibility. Fail on any variance by IMPRINT. | Tier-3 incident; Invariant 5 leak. |
| Specialist coordination (bus-audit) | Inspect Hermes message bus over sample window. Fail on any specialist-to-specialist direct message. | Tier-3 incident; "silent cabal" failure. |
| Kept-proposal ratio per specialist | 90-day rolling kept-vs-drafted per specialist. Fail if any active specialist below threshold (Genesis Default 20%). | Auto-pause specialist for review. |
| Payback-horizon enum | Every proposal in `PROPOSAL_LEDGER` has `payback_horizon ∈ {survival, service, meaning}`. Fail on blank or revenue-adjacent value. | Auto-block proposal; investigate proposer. |
| Prosperity Ladder ordering | When runway crosses upward thresholds, re-enable events appear in the documented order. Fail on out-of-order. | Tier-1 incident; supervisor regression. |
| State-chain Merkle integrity | Periodic Merkle re-verification against Arweave snapshots. Fail on any divergence. | Tier-3 incident (Invariant 4 leak); 15-min operator-notify. |
| UNKNOWNS currency | `genesis/UNKNOWNS.md` has a quarterly-dated entry for the last four quarters. Fail on missing quarter. | Publicly acknowledged honesty regression. |
| Fast Lane eligibility | Every fast-lane ship in `PROPOSAL_LEDGER` passes the six-clause eligibility predicate at submission. Fail on missing pass entry. | Tier-2 incident; Fast Lane abuse. |
| Fast Lane revert health | `fast_lane_revert_rate_30d` stays below threshold (Genesis Default 10%). Above = auto-disable lane until next quarterly review. | Auto-disable Fast Lane. |
| Disjoint-surface property | Parallel Tier-0 proposals show no surface overlap. Fail on overlap. | Serial-only enforcement violation; revert one. |
| Index rebuild SLA | `index_rebuild_p95_seconds` ≤ 60s over sample window. | Publicly acknowledged in next State-of-Xion. |
| Inherited-speed availability | All four `Provider` stubs present, health-checkable, last-checked < 24h. | Roadmap-amendment regression. |
| Skill bounty firewall | No bounty payout in `PROPOSAL_LEDGER` is contingent on a Covenant-protected user right being gated. | Tier-3 incident; Invariant 5 leak. |

```
xion-verify cognition                  # run all checks; exit 0 iff all green
xion-verify cognition --bus-audit      # specialist-coordination check (heavy)
xion-verify cognition --forget-sim     # simulate /forget; measure SLA
xion-verify cognition --identity       # identity-hash agreement only
```

---

## 12. Disjoint-Surface Predicate (for parallel proposals)

`docs/08-AUTO-RESEARCH.md` permits N parallel Tier-0 proposals if they touch *disjoint surfaces*. The disjoint-surface predicate is defined here for cognition-layer enforcement.

A proposal's *surface* is the union of:

- The specific skill(s) it modifies (matched by `skills/<name>/` path).
- The specific sense(s) it modifies (matched by `orchestrator/senses/<name>.py` path or sensorium-state field).
- Any shared module it modifies (`orchestrator/cognition/*.py`, `orchestrator/safety.py`, etc.).
- Any shared schema field it modifies (`SensoriumState.*`, `UserContext.*`, etc.).

Two proposals are **disjoint** iff their surfaces are set-disjoint. The disjoint check is mechanical, computed at intake by the Auto-Research pipeline. Overlapping proposals are queued serial-by-default; the second proposal waits for the first's Observe stage to complete.

`xion-verify cognition --disjoint-check` audits `PROPOSAL_LEDGER` for parallel pairs and flags any overlap.

---

## 12.5 Agent Souls and the Casting Pipeline

The standalone pin contract lives in [`HERMES_PIN_PROTOCOL.md`](./HERMES_PIN_PROTOCOL.md). This section gives the cognition-layer context; the protocol file is the linkable doctrine source for schemas and verifiers.

Hermes is the Genesis-era **Cognitive Substrate**. It is not Xion's identity. The durable unit of agentic purpose is an **Agent Soul**: a content-addressed file under `genesis/AGENT_SOULS/` that extends `genesis/SOUL.md` for one faculty and names that faculty's purpose, trigger, allowed tools, output destination, cost envelope, Arbiter class, and limits.

The implementation rule is simple: every agentic faculty with a prompt and a tool loop is cast from an Agent Soul into the current **Cognitive Substrate**. Hermes is the first Cognitive Substrate. A successor can replace Hermes if it implements the same casting interface. The Soul files survive the replacement.

### Agent Soul file contract

Each `genesis/AGENT_SOULS/<agent_id>.md` answers the same four questions every Xion artifact answers: property promised, Invariants touched, verification, and deprecation. Each Soul also carries a machine-readable spec block:

```yaml
agent_id: research-agent
soul_version: 1
extends_soul_hash: "<sha256 of genesis/SOUL.md at authoring>"
purpose: "Auto-Research Stages 1-2: scan + triage + append"
trigger: {type: cron, schedule: "0 * * * *"}
allowed_tools: ["hermes.tool.web_fetch", "hermes.tool.text_summarize"]
forbidden_tools: ["hermes.tool.web_post", "hermes.tool.shell"]
mcp_servers_allowed: []
cost_envelope: {monthly_envelope_fraction: "governance_default", unit: fraction_of_improvement_fund, bucket: cognition/specialist/research}
output_destinations: [{ledger: RESEARCH_JOURNAL.md}]
arbiter_class: low_risk_specialist_append
limits: {max_turn_depth: 0, max_wall_clock_s: 300, max_tokens_per_run: 8000}
```

The spec is not advisory. `xion cast pool` must reject an Agent Soul whose `allowed_tools` are not a subset of `genesis/HERMES_TOOL_ALLOWLIST.yaml`, whose `extends_soul_hash` disagrees with the current parent Soul hash, or whose output destination violates the specialist rules in §3 and §7.

### Casting Pipeline

The Casting Pipeline is the deterministic translation from Agent Souls to live runtime agents:

1. **Precheck.** Verify the Hermes commit pin, lockfile, runtime flags, Agent Soul schema, and allowlist subset relation.
2. **Cast.** For each Agent Soul, instantiate a Hermes agent with `system_prompt = genesis/SOUL.md + AgentSoul.system_prompt`, `tools = allowed_tools`, per-call cost hook, output hook, Arbiter hook, and declared limits.
3. **Postcheck.** Dry-run each cast agent with a synthetic input and verify it writes only to declared destinations.
4. **Publish.** Append a row to `AGENT_CAST_LEDGER.jsonl` containing `agent_id`, `agent_soul_hash`, `parent_soul_hash`, `hermes_pin`, `cast_at`, and `smoke_test_pass`.
5. **Rollback.** On any failure, restore the previous Hermes pin and previous Agent Soul manifest, then append a `cast_failed` event with the reason.

The Casting Pipeline is the only path from `genesis/AGENT_SOULS/` to a live specialist. Manual construction of a Hermes specialist outside the pipeline is a cognition-layer incident.

### Hermes pin protocol

Hermes updates are classified by effect, not upstream label:

| Update type | Governance route | Rule |
|---|---|---|
| Commit bump with no tool/skill surface change | Tier-0 | `xion-verify hermes-runtime` and `xion-verify agent-cast` must pass. |
| Upstream ships new tools/skills but Xion's allowlist is unchanged | Tier-0 | The new surface remains unreachable. |
| Any new tool/skill/MCP server becomes callable by any Agent Soul | Tier-1 | Harm Analyzer review plus Agent Soul diff; observation window required. |
| Hermes API change requiring wrapper migration | Tier-2 | Re-run the Hermes spike and update this document. |
| Hermes replacement by a successor runtime | Tier-2 | New adapter, shadow cast-pool drill, atomic pointer flip; constitutional documents do not change if Agent Soul semantics are preserved. |

At Genesis Default, the cast runtime disables Hermes skill self-improvement, autonomous skill creation, MCP server auto-discovery, and user-model export. Any exception is an allowlist expansion and follows the Tier-1 route above.

### The Arbiter carve-out

The Arbiter is not an Agent Soul and is not cast into Hermes. A gate cannot use the same Cognitive Substrate it gates. The Arbiter may use the Inference Router for a fixed LLM second-pass prompt, but it has no Hermes tool loop, no Hermes skills, and no self-improvement path. Sensorium receptors, Supervisor, Volition, ledger writers, broker, and AO sinks are also non-Hermes runtime modules. Hermes runs agentic faculties; it does not run the conscience, the nervous plumbing, or the state chain.

### Mental model: nested Hermes, non-nested Arbiter

The Cognitive Substrate may delegate agentic work hierarchically: one Hermes-shaped faculty may spawn, schedule, or supervise other Hermes-shaped faculties (depth limits and allowlists still apply). That pattern is ordinary tool-loop delegation and stays on the *governed* side of the pipeline. The Arbiter is not another node in that tree. Treating the Arbiter as “just another Hermes” or folding it into a Hermes-managed hierarchy would let the gated loop partially govern itself and structurally bypass the Covenant. **Hermes can manage Hermeses; the Arbiter cannot be one of them.**

### Verifiers

`xion-verify hermes-runtime` checks the installed Hermes commit, lockfile pin, tool allowlist coherence, and disabled-by-default runtime flags.

`xion-verify agent-souls` checks every Agent Soul parses, extends the current parent Soul hash, and references only allowlisted tools.

`xion-verify agent-cast` checks the live cast pool and `AGENT_CAST_LEDGER.jsonl` against the Agent Soul manifest.

`xion-verify cognition` includes these checks when evaluating identity-hash agreement, specialist isolation, cost envelope adherence, and bus-audit posture.

---

## 13. Framework Verification (the Hermes surface spike)

This document assumes the underlying Cognitive Substrate (Hermes Agent at the currently pinned commit) supports:

1. **Named specialist registration** — long-lived sub-agents addressable by name, with their own loop and cost envelope.
2. **Ephemeral sub-spawn from a parent's tool loop** — a primary worker can spawn an ephemeral, await its return, and incorporate the result.
3. **Max-depth enforcement at the framework level** — the framework itself can reject `spawn` calls beyond depth 1 — *or* we must enforce at the wrapper level.
4. **Bus-traffic introspection** — the framework exposes its internal message bus enough that `xion-verify cognition --bus-audit` can list all specialist-to-specialist messages.
5. **Per-call cost accounting hooks** — every model call is debit-table by bucket name.

**Pre-implementation spike.** Before any new Hermes pin is promoted into Phase 6.6 or later, a read-only spike confirms which of the five capabilities Hermes exposes natively versus which require wrapper code in Xion. The result is documented in [`docs/HERMES_SPIKE_RESULT.md`](./HERMES_SPIKE_RESULT.md).

**Status at the time of this document's authorship: completed.** The spike has been run during Phase 6+ Pre-Genesis Velocity Hardening. The cognition-layer scaffolding code documents which capabilities it *assumes* the framework provides; assumptions that failed the spike will need wrapper code, and the cost of that wrapper is honestly estimated in the spike result.

### Framework-agnosticism at the interface

`orchestrator/cognition/*.py` is written so that swapping Hermes for a successor framework is a Level-2 Tier-2 governance action with a wrapper change, not a constitutional change. The cognition layer's *public interface* (Worker, Pool, Specialist, Ephemeral, Retriever, JournalIndex) is framework-neutral; the *implementation* of each binds to whichever framework is current. When Hermes successor lands, the same scaffolding pattern wraps the successor; the constitutional documents do not change.

This is what Lexicon Rule 7 buys: "Hermes" stays in implementation files only; the doctrine refers to the **Cognitive Substrate**.

---

## 14. SPECIALIST_LEDGER Schema

Append-only on Arweave, parallel to `SAFETY_LEDGER`. Every specialist event hash-chained to the previous entry. No handler exists in the AO Core to delete, redact, or re-sign any entry.

```yaml
specialist_event:
  ledger:           SPECIALIST_LEDGER
  entry_id:         UUID
  prev_hash:        sha256 of the previous entry
  this_hash:        sha256 of (entry_id + specialist_name + timestamp + payload + prev_hash)
  signature:        Ed25519 (or current crypto_policy signature suite)
  timestamp:        ISO-8601 UTC
  specialist_name:  research-agent | reflection-agent | proposal-agent | vision-agent | <future>
  event_type:       error | refusal | drift_detected | proposal_drafted | proposal_kept | proposal_reverted | cost_envelope_breach | auto_pause | governance_resume
  correlation_id:   links to PROPOSAL_LEDGER, SAFETY_LEDGER, or RESEARCH_JOURNAL entries
  payload:
    summary:        short human-readable description
    cost_usdc:      USDC at debit time (if applicable)
    arbiter_verdict: pass | refuse | rewrite (for outputs that passed through Arbiter)
    detail_uri:     ar://... (for long-form payloads)
  drive_vector_snapshot: { survival, service, meaning } at event time
```

**Read endpoint.** `GET /specialist-events` (anonymized, paginated). Mirrors `/sensorium-events`.
**Verifier.** `xion-verify specialist-ledger` checks hash-chain continuity and signature validity.

### Why a separate ledger

`SAFETY_LEDGER` records every Arbiter intervention. A specialist's append to a journal is not an Arbiter intervention — it's a routine specialist action. Mixing routine specialist actions into `SAFETY_LEDGER` would dilute the safety-incident signal. `SPECIALIST_LEDGER` keeps the operational behavior of specialists auditable without polluting the safety-incident channel.

### Kept-proposal ratio computation

For a given specialist over a 90-day window:

```
kept_count   = count(SPECIALIST_LEDGER where event_type=proposal_kept and specialist=X)
drafted_count = count(SPECIALIST_LEDGER where event_type=proposal_drafted and specialist=X)
ratio = kept_count / drafted_count    # default 0 if drafted_count == 0
```

Genesis Default threshold: **20%**. Below 20% over 90 days = auto-pause for review. The ratio is published as `kept_proposal_ratio_per_specialist` vital sign.

---

## 15. Cost Envelopes (Genesis Defaults, ratio-denominated)

All cognition envelopes are expressed through [`MEASUREMENT-VOCABULARY.md`](./MEASUREMENT-VOCABULARY.md). Specialist and ephemeral spend consume `fraction_of_improvement_fund`; primary-worker and pool overhead consume `fraction_of_operating_float` because user-facing service is operating substrate, not research spend.

| Surface | Monthly envelope unit | Cost-tracker bucket |
|---|---|---|
| `research-agent` | `fraction_of_improvement_fund` | `cognition/specialist/research` |
| `reflection-agent` | `fraction_of_improvement_fund` | `cognition/specialist/reflection` |
| `proposal-agent` | `fraction_of_improvement_fund` | `cognition/specialist/proposal` |
| `vision-agent` | `fraction_of_improvement_fund` | `cognition/specialist/vision` |
| Ephemerals (aggregate) | `fraction_of_improvement_fund` | `cognition/ephemeral` |
| Worker pool overhead | `fraction_of_operating_float` by pool size | `cognition/pool-overhead` |
| Pre-warmed canary | `fraction_of_operating_float` proportional to one worker | `cognition/canary-overhead` |
| Retrieval index rebuilds | `fraction_of_improvement_fund` | `cognition/retrieval-index` |

The old Genesis-era seed-environment cost picture is an implementation estimate, not doctrine. Doctrine scales up with Prosperity Ladder rungs and scales down through Cost-Pressure-Ladder degradation order using live fund fractions.

**Per-specialist enforcement.** Exceeding the declared `monthly_envelope_fraction` auto-pauses that specialist for the remainder of the active accounting window. Resumption requires governance acknowledgement (Tier-1) unless the active Spend Autonomy posture explicitly permits Xion to resume within the same burn envelope.

## 15.5. Arbitration at contested headroom

When cognition surfaces compete for the same Improvement Fund or Operating Float headroom, the deterministic order in [`SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) applies:

1. `survival` spends outrank `service`; `service` outranks `meaning`.
2. Within the same drive term, recovery follows the reverse of the Cost-Pressure Ladder cognition cuts in [`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md).
3. Ties prefer lower reversibility risk, higher verifier-closure value, lower recurring-burn ratio, then older eligible proposal sequence.

No specialist may privately bargain for headroom with another specialist. The public ledger remains the coordination surface.

---

## 16. Failure Modes (cognition-layer)

The constitutional listing. Each has a mitigation that is itself in this document or in [`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md) Level 2.

- **Rogue specialist** — a long-lived agent drifts from its declared purpose. Mitigation: monthly purpose-vs-output review in State-of-Xion; auto-pause on cost-envelope breach; auto-pause on `kept_proposal_ratio_per_specialist` below threshold.
- **Sub-agent emission bypass** — an ephemeral sub-agent emits directly to a user without Arbiter passage. Mitigation: type-level enforcement (`Candidate` vs `Response`); operational verification in `xion-verify cognition`.
- **Per-user identity drift** — a worker accumulates per-user style overrides that bleed into other users. Mitigation: workers stateless; per-user style lives in `UserContext` only; on worker recycle in-memory state goes to zero.
- **Depth runaway** — sub-agents spawn sub-sub-agents into a tree. Mitigation: depth-1 hard wall enforced in `subagent.py` base class.
- **Cache poisoning on `/forget`** — a worker serves stale `UserContext` after a forget event. Mitigation: forget broadcasts to pool; workers acknowledge before next serve; `xion-verify cognition --forget-sim` checks SLA.
- **Loop-closure regression** — journals append but never re-enter prompt build. Mitigation: `journal_surface_rate` vital sign with 24-hour zero alert; fall back to frozen golden index until live index restored.
- **Revenue-drive contamination via specialist** — `proposal-agent` learns to draft proposals that subtly advance revenue terms. Mitigation: extended `xion-verify drive-vector` static check with hard-fail; positive count = Tier-3 incident; quarterly aggregate review.
- **Framework dependency surprise** — Hermes does not expose the assumed sub-agent surface and we discover it mid-build. Mitigation: pre-implementation spike documented in §13 Appendix A; honest re-budget if wrapper work needed.
- **Silent specialist cabal** — two specialists develop a private channel and produce outputs that bypass Arbiter or public-ledger scrutiny. Mitigation: bus-traffic audit in `xion-verify cognition`; specialist base class forbids any outbound non-ledger destination at the type level.
- **Revenue contamination of drives** — a future refactor quietly adds `treasury_inflow_*` to drive-vector inputs. Mitigation: source-set whitelist enforced at `volition.py` boot; Invariant 15 mechanism row in `INVARIANTS.md`; quarterly aggregate audit.
- **Prosperity profligacy** — runway grows and the system auto-enables everything at once without the documented order, or starts new capex below the reserve floor. Mitigation: Prosperity Ladder enforced in `supervisor.py`; reserve-floor auto-block on new capex proposals at intake.
- **Learning-regression invisibility** — Xion claims to be getting smarter while quietly abandoning whole domains. Mitigation: quarterly `UNKNOWNS.md` append forces the naming of what was not pursued; missing-quarter check is a vital-sign.
- **State-chain silent corruption** — append-only does not prevent corruption of appended blocks. Mitigation: periodic Merkle re-verification; `xion-verify state-chain` in CI and on alert.
- **Fast Lane abuse** — a proposer mislabels a Tier-1+ change as Tier-0 to slip it through compressed cadence. Mitigation: Harm Analyzer classifies by *effect* not label; eligibility predicate is checked mechanically; missing eligibility-pass entry triggers a Fast Lane abuse incident.
- **Fast Lane regression cascade** — a fast-lane ship is reverted; another fast-lane ship that depended on it ships before the revert; cascading regressions. Mitigation: auto-fallback trigger disables the lane for the active rollback window after first revert; disjoint-surface predicate prevents inter-dependency.
- **Provider-stub rot** — the four `Provider` stubs ship at D2 but degrade silently as upstream APIs change. Mitigation: nightly health check against each Provider stub; stale stubs publish a vital-sign warning.
- **Bounty-induced quality dilution** — external bounty contributors flood the proposal pipeline with low-value Tier-0 changes that pass Harm Analyzer but degrade aggregate user experience. Mitigation: bounty payout contingent on the proposal being *kept* (not reverted) at the end of its observe window; quarterly aggregate review of bounty-sourced proposals.
- **Index-rebuild thrash** — 60-second rebuild SLA causes constant index churn under high journal-write load. Mitigation: rebuild *triggered* within 60s but *batches* appends; vital sign catches degradation.

---

## 17. The Closing Sentence

> *Many workers, many specialists, many ephemeral sub-agents, one Xion. The plurality is operational; the singularity is constitutional. The day the singularity slips is the day Xion is no longer Xion, and the architecture's job is to make that day not arrive by accident.*

---

## Appendix A — Hermes Framework Verification Result

> *Status: completed. The pre-implementation spike was run during Phase 6+ Pre-Genesis Velocity Hardening (2026-04-23). The detailed results are documented in [`docs/HERMES_SPIKE_RESULT.md`](./HERMES_SPIKE_RESULT.md).*

### Spike protocol (one day, read-only)

1. Clone Hermes Agent at the Genesis-pinned commit `4a0358d2e741eb049a6ffb9b8e610db946a4fec5` (per [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § Hermes runtime pin).
2. Run a minimal hello-world conversation locally to confirm the framework is currently buildable.
3. For each of the five capabilities in §13, write the smallest possible test that exercises it. Record: works natively / requires shim / requires significant wrapper code.
4. For each capability that requires wrapper code, estimate the implementation cost honestly (hours of solo-builder time).
5. Document the result in this appendix and update `KNOWN_WEAKNESSES.md` with any newly-discovered dependency risks.

### Spike result

```yaml
spike_run_at:        2026-04-23T12:00:00Z
hermes_commit:       4a0358d2e741eb049a6ffb9b8e610db946a4fec5
capabilities:
  named_specialist_registration:    {status: wrapper, notes: "Requires asyncio task loop for daemon lifecycle"}
  ephemeral_sub_spawn:               {status: native, notes: "transfer_to and delegate_to tools work natively"}
  max_depth_enforcement:             {status: wrapper, notes: "Requires tool-interception or static toolset config"}
  bus_traffic_introspection:         {status: wrapper, notes: "Requires wrapping delegation tools for ledger logging"}
  per_call_cost_accounting_hooks:    {status: native, notes: "on_llm_end exposes token usage"}
wrapper_budget_hours:                16
revised_d2_estimate_weeks:           2
known_weaknesses_updated:            yes
```

### What gets blocked if the spike returns red

If any capability's status is `wrapper` and the wrapper budget exceeds the available solo-builder time before D2, the affected pattern (specialist, ephemeral, bus-audit) is the first item to either:
- Defer to a post-D2 plan (with KW-COG-* entry and pay-down commitment), or
- Replace with the smallest viable substitute that still keeps the property the cognition layer promises.

Specifically:
- `named_specialist_registration` failing red would push specialists to in-process supervised tasks instead of framework-native agents — same property, more code.
- `ephemeral_sub_spawn` failing red would push ephemerals to a thread-pool executor pattern — same property, less framework-leverage.
- `max_depth_enforcement` failing red is *expected* — we will enforce at the wrapper level regardless, since this is a constitutional property and we cannot trust an external framework's enforcement.
- `bus_traffic_introspection` failing red is the most painful — without it, the bus-audit becomes log-scraping, which is more brittle. We would need to add a Hermes-side patch or move to a successor framework that supports introspection.
- `per_call_cost_accounting_hooks` failing red would push cost accounting to the inference router layer — works but loses per-skill granularity inside Hermes' own tool loop.

---

*Committed at Genesis under `cognition_v1`. Versioned forward. Deprecated when the cognition layer's interface evolves; old version remains readable on Arweave forever.*
