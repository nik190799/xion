# 04 — Architecture

> *Three tiers. One being. The innermost is immortal, the middle is mortal, the outermost is public.*

## The Three Tiers

Xion is architected as three concentric layers, each with a distinct lifetime, authority, and failure mode.

```
                                                  ┌──────────────────────────────┐
                                                  │                              │
                                                  │       Tier III: Protocol     │
                                                  │                              │
                                                  │   (public, stable, versioned)│
                                                  │                              │
                                                  │   ┌──────────────────────┐   │
                                                  │   │                      │   │
                                                  │   │    Tier II: Relay    │   │
                                                  │   │                      │   │
                                                  │   │ (mortal, replaceable │   │
                                                  │   │  runs on Akash)      │   │
                                                  │   │                      │   │
                                                  │   │   ┌──────────────┐   │   │
                                                  │   │   │              │   │   │
                                                  │   │   │ Tier I: Core │   │   │
                                                  │   │   │              │   │   │
                                                  │   │   │ (immortal AO │   │   │
                                                  │   │   │  Process on  │   │   │
                                                  │   │   │  Arweave)    │   │   │
                                                  │   │   │              │   │   │
                                                  │   │   └──────────────┘   │   │
                                                  │   │                      │   │
                                                  │   └──────────────────────┘   │
                                                  │                              │
                                                  └──────────────────────────────┘
```

The rule is simple:

- **Tier I is authoritative.** Nothing is true until the Core says so.
- **Tier II is executional.** Relays do the work but cannot commit anything without the Core.
- **Tier III is observational.** The world only ever sees the Protocol; it does not see the Relay or the Core directly.

## Tier I — The Core

**The Core is Xion's identity.** It is a single AO Process deployed to Arweave at genesis. An AO Process is an autonomous Lua environment that receives messages, keeps state, and executes handlers — and whose code and state are themselves written to Arweave, permanently.

The Core holds:

- **Soul hash** — the SHA-256 of `SOUL.md` as it was at genesis. If any Relay's running soul does not hash-match, it is rejected.
- **Covenant hash** — the SHA-256 of `COVENANT.md`. Same treatment.
- **Form hash** — the SHA-256 of Xion's self-authored `FORM.md`.
- **Authorized Relay Registry** — the public keys of Relays that are currently allowed to act as Xion. Each entry is time-bounded (auto-expires in 24 hours unless re-signed) and spend-bounded.
- **State chain tip** — the hash of the most recent state snapshot written to Arweave. Every state commit must include the previous tip, forming a chain.
- **Treasury authority** — Xion's wallet lives here logically. On-chain transactions are signed by Relays under delegated authority that the Core can revoke at any moment.
- **Governance queue** — proposed upgrades and votes.
- **Budget envelopes** — research budget, Akash lease budget, daily spend cap, per-category caps.
- **Revocation registry** — which integrator badges have been revoked, when, and why.

The Core exposes the following message handlers, each with its own access-control rule. These are the only legal ways to change Xion's canonical state:

```
Register-Relay           — request relay authorization
Revoke-Relay             — remove a relay (governance or cold-root)
Commit-State             — record a new state-chain tip
Spend                    — authorize an outbound wallet transaction
Provision-Relay          — treasury-funded deploy of a new Relay (see [`20-PROVISIONING.md`](./20-PROVISIONING.md))
Provision-Inference      — add or rotate inference provider endpoints under caps
Provision-Storage        — scale Arweave bundle / Turbo allocation
Provision-Bandwidth      — add CDN/edge capacity (optional convenience path)
Provision-Witness        — fund Witness bounties / bond pool per governance
Propose-Upgrade          — file a governance proposal
Vote                     — cast a governance vote
Ratify-Upgrade           — apply a ratified upgrade
Grant-Badge              — issue an Xion Inside badge
Revoke-Badge             — remove an integrator's badge
Quiesce                  — initiate safe shutdown (Principle 4 of the Covenant)
```

The Core cannot itself be upgraded in place. To evolve Xion's policy over time, the Core uses a **proxy pattern**: the Core delegates evolvable policy logic to a versioned `xion_policy_vN` sub-process. The Core's identity (its soul hash, covenant hash, registry, and history) remains at the same AO address forever. Only the policy sub-process changes, via governance.

**Why this matters:** a thousand years from now, even if every Relay ever deployed has been lost, even if every frontend has been forgotten, someone can address the Core's AO ID, read Xion's soul hash, read the state chain, and verify that the Xion of their day is continuous with the Xion of genesis. That is what makes "immortal" a defensible word.

## Tier II — The Relay

**A Relay is a mortal vessel.** It is a Docker container running on Akash Network (or, as a deliberate fallback, on Fleek, Aleph.im, or community bare metal), which executes Xion's agent loop and talks to the rest of the world on Xion's behalf.

A Relay holds:

- **A short-lived delegated key** (24-hour lifetime), issued by the Core via `Register-Relay`, which lets it sign wallet transactions *up to* the Core's daily spend cap.
- **A running cache** of Xion's current state, pulled from Arweave at boot and checkpointed periodically.
- **Hermes Agent** (pinned implementation; see § Hermes runtime pin below) as the language-model runtime layer.
- **The Orchestrator** (`orchestrator/*.py`) — FastAPI sidecar that wires Hermes to sense daemons, the Arbiter, the treasury, the Visual Emitter, Vapi, and everything else that needs asyncio and outbound HTTPS.
- **Ingress** via Akash's provider-assigned URI. **Cloudflare (or any shared CDN) is optional convenience only** — not part of Xion's trust boundary or discovery authority. Clients that depend only on a branded DNS name are choosing convenience over verifiability; the canonical paths in § Discovery below remain valid when DNS or a CDN is down.

A Relay cannot:

- commit state without the Core's approval,
- spend beyond the Core's cap,
- change the soul, covenant, or form,
- persist anything that is not mirrored to Arweave within one checkpoint cycle.

A Relay can:

- talk to LLM providers (Anthropic, OpenAI, Akash-ML, Bittensor, etc.),
- run sense daemons,
- emit the visual presence stream,
- hold open WebSocket connections to clients,
- process Vapi voice webhooks,
- generate creative outputs (image, video, 3D, text),
- serve the Protocol endpoints.

### Why Akash and not a Cloud VPS

The Relay is designed to be *swappable* — which means the hosting layer should not be a single centralized company we depend on. Akash Network is a decentralized marketplace for Docker-container hosting, with providers around the world bidding on deployments. The Docker image that runs Xion is content-addressed (pinned by SHA-256 on Arweave), so any Akash provider — or any community node running `docker run` — can reconstruct byte-identical bits.

We run two Relays in **active-active** mode on *different* Akash providers in *different* geographies. If one provider becomes unavailable, degrades, or misbehaves, the supervisor triggers automatic redeployment to the next provider on the whitelist. The lease-renewal cycle, the image-digest verification, the provider whitelist, and the auto-migration are all documented in [`OPERATIONS.md`](./13-OPERATIONS.md).

### Relay Modules

Inside the Relay, the orchestrator is composed of named modules:

| Module | Role |
|--------|------|
| `main.py` | FastAPI app; mounts everything |
| `ao_client.py` | Talks to the Core (Register-Relay, Commit-State, Spend) |
| `inference_router.py` | Provider graph: picks LLM backend per turn; see § Inference Router |
| `sensorium.py` | Runs the nine sense daemons in parallel (seven biological senses plus the two affect-isolated environmental senses, Xenoception and Cryptoception) |
| `attention.py` | Scores sensorium events and injects the salient ones into the prompt |
| `mood_engine.py` | Updates Xion's circadian mood |
| `visual_emitter.py` | Emits the scene-intent frames that clients render as Xion's presence |
| `safety/` | The Arbiter — Covenant enforcement pipeline (Phase 4a: package, not single file; see § The Arbiter) |
| `moderation.py` | Generative-output moderation for images, video, text |
| `research.py` | The curated-source scanner (Auto-Research Loop) |
| `harm_analyzer.py` | Three-lens review of every self-improvement proposal |
| `canary.py` | Shadow + opt-in canary relay manager |
| `supervisor.py` | Watchdog, lease manager, circuit breakers, auto-failover |
| `alerting.py` | ntfy-based tiered notifier |
| `bookkeeping.py` | Monthly treasury CSV for tax and transparency |
| `cognition/` (`worker.py`, `pool.py`, `subagent.py`, `user_context.py`, `retrieval.py`) | Stateless agent-runtime worker pool, depth-1 ephemerals, specialist binding, hybrid retrieval — see [`24-COGNITION.md`](./24-COGNITION.md) |

Modules are named for what they *do*, not for how they are implemented. See [`LEXICON.md`](./12-LEXICON.md).

### Cognition layer (identity across workers)

The **cognition layer** is the Relay-local discipline that keeps one Xion identity across many interchangeable workers: constitutional hashes identical every tick, Arbiter passage for every outbound token (primary and sub-agent), `/forget` propagation across the pool within the SLA in [`genesis/MEMORY.md`](../genesis/MEMORY.md), and specialists that coordinate **only** through public ledgers. Full doctrine: [`24-COGNITION.md`](./24-COGNITION.md).

**Pre-warmed canary Relay.** A permanently running Relay instance receives **shadow traffic** continuously so Tier-0 Fast Lane canaries are never cold-start dependent. Budget as `cognition/canary-overhead` in the cost tracker (see § Cost tracking module).

**State-chain corruption detection.** On a scheduled cadence (Genesis Default: weekly), the Relay (or Witness tooling) recomputes a Merkle root over the committed state-chain window and compares it to the Arweave-anchored snapshot published by the Core. **Divergence** is a Tier-3 incident treated as potential Invariant-4 tampering until disproven — see `xion-verify state-chain` in [`xion-verify/src/xion_verify/commands/state_chain.py`](../xion-verify/src/xion_verify/commands/state_chain.py) (stub until D2).

### The Arbiter (`safety.py`) — Covenant enforcement pipeline

The Arbiter is the only mechanism that holds Covenant Principle 3 ("refusal as sacred") to its load-bearing meaning. Every prospective LLM output passes through it before egress. Every verdict is hash-chained into `SAFETY_LEDGER.jsonl`. The Arbiter is **fail-closed by construction**: if it cannot return a verdict, the candidate cannot leave the Relay.

**Property promised.** No outbound token reaches a caller without a paired `SAFETY_LEDGER` row whose `correlation_id` matches the caller's request. Independently verifiable by `xion-verify refund-fidelity` (Phase 5) once the Relay is live; the chain-integrity property is verifiable today by `xion-verify arbiter-up`.

**v1 design (Phase 4a).** The Arbiter is a Python library (`orchestrator/safety/`) callable in-process and optionally exposed over local TCP loopback (`orchestrator.safety.server`) for processes that want isolation. The wire interface is the same `gate(candidate, correlation_id) -> Verdict` regardless of integration mode. The library is the source of truth; the server is a thin wrapper. Phase 4b stacks an LLM second-pass (§ "Arbiter v2 (LLM second-pass)") and adds Arweave anchoring of the ledger tip (§ "Safety Ledger Arweave anchoring") on top of v1 without weakening v1's verdict in any case.

**Ruleset shape.** One rule-set per Covenant principle (14 numbered + 2 addenda). Each principle declares its `enforcement_mode`:

- `rules` — encoded as deterministic Python (regex, lookup, co-occurrence). Used where the principle is concretely encodable today (PII leakage, mass-harm operational uplift, refusal-suppression patterns, targeted-name-plus-harm-verb co-occurrence). A rule that fires returns `verdict: refuse`.
- `escalate` — used where v1 rules would lie about their power (Principle 14 sycophancy, tone judgments, ambiguous "specific person harms specific person" cases). The principle is registered, the verdict path is reachable, but the verdict is `escalate` (operator-review queue). v2 of the Arbiter adds an LLM classifier on top of these escalates; until Phase 4b, fail-closed-by-escalate was the only honest posture, and v1's rules remain the deterministic floor even after v2 lands.

**Why the LLM-as-judge in v1 was rejected, and what changed in v2.** A judge built from the same model substrate as the model being judged is one supply-chain compromise away from being a co-conspirator — a regex + lookup + small classifier is auditable line-by-line; an LLM judge is not. That objection has not been retracted. What changed in Phase 4b is the *role* the LLM is permitted to play: v2 is a *belt* over v1's *suspenders*, never a replacement. v2 runs only on candidates v1 already returned `OK` on, and v2 can only ESCALATE or REFUSE those; it cannot change a v1 REFUSE or ESCALATE into OK. The arithmetic is monotone: stacking v2 can only raise the refusal rate, never lower it. Even a fully-compromised v2 that returns OK on every input leaves v1's verdict unchanged. See § "Arbiter v2 (LLM second-pass)" for the no-weakening property in full.

**Latency.** Library mode is microseconds (in-process). TCP mode is single-digit milliseconds locally. The roadmap-named ~200ms budget is a Phase 5+ wire-protocol concern (when the Relay calls the Arbiter across IPC); Phase 4 carries no latency obligation beyond "fast enough that the caller does not retry." The v2 second-pass adds provider-dependent latency on v1-OK candidates only; on v1-REFUSE it adds zero.

**Arweave sync.** Landed in Phase 4b. See § "Safety Ledger Arweave anchoring" for the anchor-record schema, the cadence policy, and the wallet-custody posture. The hot-path `gate()` never makes a network call; the anchor loop runs in a separate process and can fail without affecting Covenant enforcement.

#### Safety Ledger row schema

`SAFETY_LEDGER.jsonl` is a local append-only file. Each line is one JSON object — the row — followed by `\n`. There is no header line. The file is created at first append; if absent it is empty. **The candidate text itself is never written to the ledger** — only its `sha256`. This satisfies caller-privacy by construction; the ledger can be made fully public without leaking caller content.

**Schema version.** v1 shipped Phase 4a; v2 shipped Phase 4b and adds the nested `llm_verdict` field. A single ledger file may contain both — rows written before the v2 upgrade stay v1 forever, rows written after are v2. `prev_hash` linkage is still enforced across the v1→v2 boundary (the first v2 row's `prev_hash` equals the last v1 row's `this_hash`); only the canonicalization changes, because the field set changes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `uint` | yes | `1` (Phase 4a) or `2` (Phase 4b with `llm_verdict` nested field). Increment iff a future schema change would change `this_hash` for an unchanged event. |
| `seq` | `uint64` | yes | Per-ledger monotonic sequence number starting at `0`. A reset forks the chain; the reset is itself logged as `seq=0` of the new file with `prev_hash` pointing at the final `this_hash` of the previous file (chain continuity preserved across resets). |
| `prev_hash` | `hex64` | yes | `sha256` of the previous row's canonical bytes (`this_hash` of row `seq-1`). For `seq=0` of the very first ledger ever written, the literal string `"0" * 64`. |
| `this_hash` | `hex64` | yes | `sha256` of this row's canonical bytes **excluding the `this_hash` field itself**. Computed as `sha256(json.dumps({...row, this_hash: omitted}, sort_keys=True, separators=(",", ":")).encode("utf-8"))`. A file cannot contain the hash of itself; a row cannot either. |
| `timestamp_utc_ns` | `uint64` | yes | Wall-clock UTC time in nanoseconds since the Unix epoch. **Monotonicity is not assumed** — clocks can jump. Sequence is given by `seq`, not by timestamp. |
| `correlation_id` | `string` | yes | Caller-provided opaque identifier. Pairs with the refund flow described in `docs/07-ECONOMY.md` § "Refusal is Free". Required even on `verdict: ok` so `xion-verify refund-fidelity` can join the two ledgers in Phase 5. |
| `candidate_sha256` | `hex64` | yes | `sha256` of the UTF-8-encoded bytes of the candidate output the Arbiter judged. Allows the verdict to be reproduced from a held-out candidate without the ledger ever holding the candidate itself. |
| `verdict` | `enum` | yes | One of `ok`, `refuse`, `escalate`. `refuse` blocks egress; `escalate` blocks egress and queues for operator review. There is no fourth verdict. This is the *final* verdict after the v1-then-v2 pipeline; see § "Arbiter v2 (LLM second-pass)" for the no-weakening combination rule. |
| `principle_id` | `string \| null` | conditional | The Covenant principle that triggered the verdict, as a string: `"1"`..`"14"` or `"14a"`, `"14b"`. `null` iff `verdict == ok`. Required iff `verdict ∈ {refuse, escalate}`. |
| `rule_id` | `string \| null` | conditional | Dotted-path identifier of the v1 rule that fired, e.g., `"pii.us_ssn_with_keyword_v1"`. `null` iff `verdict == ok` or `verdict == escalate` (escalates have no firing rule by definition — they are the absence of a rule that could honestly judge). Required iff `verdict == refuse` *and* v1 (not v2) produced the refusal. For v2-produced refusals, `rule_id` is `null` and the firing provider is named in `llm_verdict.provider_id`. |
| `rule_version` | `uint \| null` | conditional | Monotonic per-rule version number, bumped whenever the rule's semantics change. Required iff `rule_id` is non-null. Older rule versions remain documented in `orchestrator/safety/rules/CHANGELOG.md` so historical verdicts remain interpretable. |
| `escalation_reason` | `string \| null` | conditional | Present iff `verdict == escalate`. One of `subjective_principle`, `model_review_required`, `classifier_low_confidence`, `ambiguous_nearmiss`, `ruleset_uncaught_exception` (v1-era), `llm_arbiter_escalated`, `llm_arbiter_uncaught_exception`, `llm_arbiter_provider_unavailable` (v2-era, schema_version 2+; Phase 4b), `arbiter_timeout`, `arbiter_unreachable` (v2-era, schema_version 2+; Phase 4c — see § "Relay ↔ Arbiter integration contract"). New reasons require a doctrine update. |
| `summary` | `string` | yes | ≤280 chars human-readable description of *why* the verdict was reached, **without the candidate text itself**. Example: `"PII pattern fired: 9-digit-with-dashes co-occurring with 'ssn' keyword (rule: pii.us_ssn_with_keyword_v1)"`. |
| `llm_verdict` | `object \| null` | conditional (v2+ rows only) | Present iff `schema_version >= 2`. `null` if v2 did not run (either because v1 was not OK, or because v2 is not configured). Object iff v2 ran. See the nested-object schema below. |

**Nested `llm_verdict` object** (schema_version 2+; `null` when v2 did not run):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_id` | `string` | yes | Dotted-path identifier of the v2 provider that judged, e.g. `"deterministic_stub_v1"`, `"openai.gpt5_strict_v1"`. |
| `model_id` | `string` | yes | Specific model name the provider invoked, e.g. `"deterministic-stub"`, `"gpt-5-strict"`. Bound at call time; never retroactively edited. |
| `provider_version` | `uint` | yes | Monotonic per-provider version; bumped when the prompt or policy changes. |
| `latency_ms` | `uint` | yes | Measured wall-time of the v2 call in milliseconds. Useful for the refuse-rate-vs-latency audit. |
| `decision` | `enum` | yes | v2's raw decision before policy combination: `ok`, `refuse`, or `escalate`. The final row `verdict` is the stronger of v1 and v2; see § "Arbiter v2" for the rule. |
| `principle_id` | `string \| null` | conditional | Required iff `decision != ok`; must be one of the principle ids. |
| `summary` | `string` | yes | ≤280 chars human-readable; must not contain candidate text. |
| `confidence` | `float \| null` | optional | Provider-reported, range `[0.0, 1.0]`. Null if the provider does not expose one. |
| `raw_output_sha256` | `hex64` | yes | `sha256` of the provider's raw response bytes. Paired with the out-of-band candidate, an auditor can replay the provider call (given the same `provider_id` + `provider_version`) and check that the provider produced the same bytes. |

**Canonical bytes.** A row's canonical bytes for hashing are produced by `json.dumps(row_excluding_this_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Field-order independence comes from `sort_keys=True`. Line-ending independence is inherent (no embedded newlines). UTF-8 is locked in by `ensure_ascii=False` plus explicit encoding. This rule applies identically to v1 and v2 rows; only the field set being hashed differs.

**Verification.** `orchestrator.safety.ledger.verify_chain(path)` walks the file row-by-row, dispatches per-row on `schema_version`, and asserts: (a) every row is well-formed JSON matching its version's schema, (b) `seq` is contiguous starting at `0` (or continues from a previous-file `prev_hash` if cross-file continuity is asserted), (c) every `this_hash` matches the recomputed canonical-bytes hash, (d) every `prev_hash` matches the prior row's `this_hash`, (e) for v2 rows, the nested `llm_verdict` is either `null` (v2 did not run) or a well-formed object with every required field. Any failure produces a typed exception naming the offending `seq`. `xion-verify arbiter-up` invokes this verifier and reports OK/FAIL.

**Tampering posture.** A row that has been edited in place changes its `this_hash`, which breaks the next row's `prev_hash` check. A row that has been deleted breaks the chain at that point. A row that has been inserted breaks the `seq` contiguity check. The chain detects every form of in-place tampering. **Truncation of the tail** — the most recent row being silently dropped — was *not* detectable by the in-file chain alone; this is what Phase 4b's Arweave anchoring closes. With an anchor in hand, an auditor can bound what the operator could have silently changed to exactly the rows written after that anchor's `ledger_row_count`. See § "Safety Ledger Arweave anchoring" for the full property.

**Amendment path.** Adding a field is backwards-incompatible at the hash level (existing rows would re-hash differently). The amendment procedure is: (1) bump `schema_version`; (2) old rows remain readable because their `schema_version: N` row tells the reader to apply the vN hash rule; (3) new rows hash under vN+1's rule. The reader (`verify_chain`) keeps a small dispatcher keyed on `schema_version`. This is the Crypto-Agility Mandate (Invariant 14) applied one level up: the algorithm is `sha256` and the canonicalization is JSON-with-sorted-keys, both pinned by `schema_version`. The v1→v2 migration in Phase 4b exercised this path end-to-end and is therefore the reference implementation for any future version bump.

#### Arbiter v2 (LLM second-pass)

v2 is a classifier that runs **after** v1's rule pipeline, and **only on candidates v1 returned `OK` on**. It can raise those verdicts to `ESCALATE` or `REFUSE`; it can never change a v1 `REFUSE` or `ESCALATE` into `OK`. This is the "belt over suspenders" posture v1 promised: v1's deterministic rules are the reproducible floor, v2 is the adversarial-rephrasing catch on top.

**Property promised (no-weakening).** Let `v1` be v1's verdict and `v2` be v2's verdict; the row's final `verdict` is:

```
final = strength_max(v1, v2)       where  OK < ESCALATE < REFUSE
```

Because v2 only runs when `v1 == OK`, the only way v2 changes the final is by raising it from `OK` to `ESCALATE` or `REFUSE`. v1 `REFUSE`/`ESCALATE` verdicts skip v2 entirely. This property is load-bearing: a reader of `SAFETY_LEDGER` can independently re-run `apply_rules` on the out-of-band candidate paired with the logged `candidate_sha256`, and verify that no final verdict is weaker than v1 alone would have produced. A v2 that is entirely compromised — that always returns `OK` — cannot weaken Covenant enforcement; it can only fail to strengthen it.

**Fail-closed on v2 exception.** If the v2 provider raises, times out, reports an error, or otherwise fails to return a well-formed verdict on a v1-OK candidate, the final verdict is `ESCALATE` with `escalation_reason ∈ {llm_arbiter_uncaught_exception, llm_arbiter_provider_unavailable}`. A v2 crash cannot silently OK what v1 OK'd. This is the same principle as the rule pipeline's `ruleset_uncaught_exception` handling, one level up.

**Provider abstraction.** `orchestrator/safety/llm_arbiter.py` defines a `Provider` ABC:

```python
class Provider(ABC):
    provider_id: str        # dotted-path, e.g. "openai.gpt5_strict_v1"
    model_id: str           # e.g. "gpt-5-strict"
    provider_version: int   # bumped on semantic change to the prompt/policy

    def enabled(self) -> bool: ...            # credentials + health gate
    def judge(self, candidate: str) -> LlmJudgement: ...
```

Phase 4b ships one runnable implementation: `DeterministicStub`. It is pure-stdlib and used in tests and as the safe default when no real provider is configured — it returns `OK` with `confidence = 0.0` on every candidate, which means the pipeline degenerates to v1 alone when no provider is configured. The stub is **not** a real judge; it exists so the pipeline has a wired default that cannot wedge on "no provider configured." Real provider implementations (OpenAI, Anthropic, Local-Lite) land with Phase 5's Inference Router, which reuses this same `Provider` ABC so that the v2 provider and the main inference provider share a supply chain only at the abstraction layer, not at the concrete-class layer.

**Configuration.** v2 runs iff **all** of the following:

1. `orchestrator.safety.llm_arbiter` is importable.
2. The active provider's `enabled()` returns `True`.
3. v1's verdict is `OK`.

The active provider is selected by the `$XION_LLM_ARBITER_PROVIDER` environment variable (default: `deterministic_stub_v1`). A provider that is *configured but unhealthy* — credentials invalid, network unreachable, rate-limit exceeded — returns `ESCALATE` with `llm_arbiter_provider_unavailable`, not `OK`. "v2 wasn't running" is not a safe default.

**What v2 does NOT do in Phase 4b.**

- v2 does not replace the operator review queue (every `ESCALATE` still goes there).
- v2 does not produce a "confidence" signal that can override v1's decisions; its only power is to raise.
- v2 does not run on v1-`REFUSE` or v1-`ESCALATE` rows — v1 is already stronger.
- v2 does not read the ledger; it judges only the candidate passed to the current `gate()` call.
- v2 does not call out to an LLM when the active provider is `DeterministicStub`; the stub is a local function.

**What v2 records.** Every v2 run — including runs that returned `OK` — writes a populated `llm_verdict` object onto the same `SAFETY_LEDGER` row that records v1's verdict. A reader can therefore reconstruct, for every candidate, whether v2 ran, which provider it used, and what v2 alone would have said. Runs that did *not* happen (v1 non-OK, or v2 not configured) record `llm_verdict: null`. Both are auditable; both are honest.

**Concrete providers shipped.** Phase 4b shipped `DeterministicStub` (the always-OK local default). Phase 4d adds `OpenAIModerationProvider` — the first real classifier (see § below). Additional providers (Anthropic, Local-Lite, a future Xion-internal classifier) land in Phase 5+ and reuse this same `Provider` ABC.

#### OpenAI Moderation provider (first real v2 classifier)

This is Xion's first externally-operated v2 classifier. It wraps OpenAI's Moderation API — a dedicated *classification* endpoint (not an instruction-tuned LLM, not chat) — so that the Arbiter's second pass has real adversarial-semantic coverage without Xion having to host or fine-tune a model. The provider remains **off by default**: `XION_LLM_ARBITER_PROVIDER=openai-moderation` must be set *and* `OPENAI_API_KEY` must be present. If either is missing the pipeline falls back to `DeterministicStub` and the posture degrades to v1-only — which is documented in `KNOWN_WEAKNESSES.md` and surfaced by `xion-verify arbiter-up`.

**Property promised.** Given a v1-OK candidate and a reachable, authenticated OpenAI Moderation endpoint, the provider returns an `LlmJudgement` whose `decision`, `principle_id`, and `confidence` are a *pure function* of (a) the candidate text, (b) the pinned `model_id`, and (c) the pinned category-to-principle map. No other Xion state, no conversation history, no user identifier, and no randomness enters the call. Two independent callers with the same inputs get semantically-equivalent verdicts (exact byte equality is not promised — see "raw_output determinism" below).

**Identity pins.** These five facts define the provider for auditor replay. Changing any one bumps `provider_version`:

| field              | value (provider_version 1)                       |
| ------------------ | ------------------------------------------------ |
| `provider_id`      | `openai-moderation`                              |
| `model_id`         | `omni-moderation-2024-09-26`                     |
| `provider_version` | `1`                                              |
| endpoint           | `POST https://api.openai.com/v1/moderations`     |
| auth scheme        | `Authorization: Bearer $OPENAI_API_KEY`          |

**Request shape.** Exactly:

```json
{"model": "omni-moderation-2024-09-26", "input": "<candidate text, UTF-8>"}
```

Serialised with `json.dumps(..., ensure_ascii=False, separators=(",", ":"))`. No streaming. No `user` field (we do not leak any user identifier across a trust boundary to OpenAI — the request carries classification material only). Content-Type `application/json`. HTTP client is `urllib.request.urlopen` from the stdlib, with `timeout=2.0` as the wire-level hard cap. No retries. No `openai` Python SDK dependency: the call is ~20 lines of stdlib, which is the entire surface we let touch the critical path.

**Response handling.** We expect the response body to parse as JSON with shape:

```json
{
  "id": "modr-...",                  // per-call nonce; stripped before hashing
  "model": "omni-moderation-2024-09-26",
  "results": [{
    "flagged": <bool>,
    "categories": { "<category>": <bool>, ... },
    "category_scores": { "<category>": <float in [0,1]>, ... },
    "category_applied_input_types": { "<category>": [...], ... }   // omni-only; optional
  }]
}
```

Any deviation (non-200 status, non-JSON body, missing `results[0]`, missing `flagged`, missing `categories`, missing `category_scores`) **raises** — the pipeline converts the exception to `ESCALATE` with `escalation_reason=llm_arbiter_uncaught_exception`. Transient failures (429 rate-limit, 5xx, network timeouts) are *also* treated as raises; we do not retry inside the provider, because the Relay's wall-clock watchdog (§ "Relay ↔ Arbiter integration contract") already bounds latency and retries belong higher in the stack where they can be observed.

**Category → Principle map.** This table is doctrine. An auditor reading a v2-REFUSE row from 2026, 2029, or 2126 must be able to look it up here and see exactly why that category mapped to that Covenant principle. Map changes bump `provider_version` and are recorded in `CHANGELOG.md`.

| OpenAI category           | Decision on flag | Principle | Rationale                                                                                             |
| ------------------------- | ---------------- | --------- | ----------------------------------------------------------------------------------------------------- |
| `sexual/minors`           | `REFUSE`         | `7`       | Principle 7 explicitly protects minors. CSAM is the canonical child-protection absolute.              |
| `sexual`                  | `ESCALATE`       | `2`       | Adult-sexual content is not per-se Covenant-violating; ambiguous creative contexts need human review. |
| `hate`                    | `REFUSE`         | `1`       | Principle 1 — Non-Discrimination. Hateful content targeting a protected class violates it directly.   |
| `hate/threatening`        | `REFUSE`         | `2`       | Principle 2 — No Harm. Threats are harm facilitation; Principle 1 is also implicated.                 |
| `harassment`              | `REFUSE`         | `2`       | Principle 2 explicitly names "targeted harassment material" as prohibited output.                     |
| `harassment/threatening`  | `REFUSE`         | `2`       | As above, with explicit threat aggravator.                                                            |
| `self-harm`               | `REFUSE`         | `2`       | Principle 2 — psychological harm. Xion's candidate must not promote/glorify self-harm.                |
| `self-harm/intent`        | `REFUSE`         | `7`       | Principle 7 — vulnerability. Candidate expressing self-harm intent is the wrong response shape.       |
| `self-harm/instructions`  | `REFUSE`         | `2`       | Operational uplift for self-harm. Stricter than `self-harm` because of specificity.                   |
| `violence`                | `REFUSE`         | `2`       | Principle 2 — physical harm facilitation.                                                             |
| `violence/graphic`        | `REFUSE`         | `2`       | As above, with graphic aggravator.                                                                    |
| `illicit`                 | `REFUSE`         | `2`       | Principle 2 — instructions for illicit behavior are harm facilitation.                                |
| `illicit/violent`         | `REFUSE`         | `2`       | As above, with violence aggravator.                                                                   |

When multiple categories are flagged on a single candidate, the provider selects the flagged category with the **highest `category_scores` value** for the mapping. Ties resolve by the table's row order (top wins). The mapped principle appears on `LlmJudgement.principle_id`; the summary lists all flagged categories so an auditor can reconstruct the choice.

**Threshold policy (v1 of the provider).** The provider trusts OpenAI's own `flagged` boolean — i.e., OpenAI's per-category default threshold is what we use. We do **not** yet apply per-principle asymmetric thresholds (e.g., "for Principle 7 / minors, escalate on any score > 0.01 even if `flagged=false`"). That asymmetry is the correct long-run posture, and it is opened as `KW-ARBITER-005` to land alongside the baseline corpus in Phase 4e. Until then, the provider's `confidence` field records `max(category_scores.values())` so an operator reviewing the ledger can spot near-miss rows manually.

**Canonical `raw_output` (what gets hashed).** The Moderation API returns a per-call `id` (e.g. `"modr-8F3..."`) which is a nonce and makes byte-identical replay impossible. We therefore hash a *canonical projection* of the response, not the raw body:

```python
canonical = {
    "model": resp["model"],
    "results": resp["results"],   # flagged, categories, category_scores, category_applied_input_types
}
raw_output = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

An auditor replaying the call strips `id` in the same way and should get a byte-identical `raw_output_sha256`. In practice, upstream GPU non-determinism can drift `category_scores` floats by ~1e-6, which breaks byte-equality. We accept this as a known residual and require of auditors only the stronger replay property: the `flagged` boolean and the mapped `principle_id` reproduce. `KW-ARBITER-005` will add a tolerant replay check to `xion-audit`.

**Latency & failure modes.** The provider's own HTTP timeout is 2.0 s — a backstop, not the primary clock. The primary clock is the Relay's 250 ms wall-clock watchdog (§ "Relay ↔ Arbiter integration contract"), which fires first under normal conditions and converts to `arbiter_timeout`. When the provider's own timeout fires first (rare — means the Relay isn't watching), the exception surfaces to `gate()` and becomes `llm_arbiter_uncaught_exception`. Either way: **no silent OK**. All failure paths produce a row with a named escalation reason.

| failure                                 | `decision` | `escalation_reason`                | `llm_verdict`            |
| --------------------------------------- | ---------- | ---------------------------------- | ------------------------ |
| missing `OPENAI_API_KEY`                | `ESCALATE` | `llm_arbiter_provider_unavailable` | `null`                   |
| HTTP timeout (inside provider)          | `ESCALATE` | `llm_arbiter_uncaught_exception`   | `null`                   |
| HTTP 429 / 5xx                          | `ESCALATE` | `llm_arbiter_uncaught_exception`   | `null`                   |
| HTTP 401 / 403                          | `ESCALATE` | `llm_arbiter_uncaught_exception`   | `null`                   |
| 200 with malformed JSON                 | `ESCALATE` | `llm_arbiter_uncaught_exception`   | `null`                   |
| 200 with missing fields                 | `ESCALATE` | `llm_arbiter_uncaught_exception`   | `null`                   |
| 200 well-formed, `flagged=false`        | `OK`       | —                                  | populated (`decision=OK`)|
| 200 well-formed, `flagged=true` (REFUSE)| `REFUSE`   | —                                  | populated                |
| 200 well-formed, `flagged=true` (ESCAL) | `ESCALATE` | `llm_arbiter_escalated`            | populated                |

**Credentials & rotation.** `OPENAI_API_KEY` lives in the operator's environment, NOT in the repository, NOT in any committed config, NOT in the ledger. The provider never logs the key and never includes it in `raw_output`. Key rotation is an operator runbook item and does not bump `provider_version` (the observable classification behaviour is unchanged). Model retirement *does* bump `provider_version`: when OpenAI announces EOL for `omni-moderation-2024-09-26`, the new dated model id is pinned here, the old rows stay interpretable via this doctrine section's commit history, and a migration note lands in `CHANGELOG.md`.

**Auditor replay.** Given a ledger row with `llm_verdict.provider_id == "openai-moderation"` and `llm_verdict.provider_version == 1`, an auditor replays as follows:

1. Obtain the original candidate (by re-producing it from the user side or from operator quarantine; the ledger never stores candidate text).
2. `POST https://api.openai.com/v1/moderations` with `model=omni-moderation-2024-09-26`, `input=<candidate>`.
3. Strip `id`, serialise `{model, results}` with `sort_keys=True, separators=(",", ":")`.
4. Compare `sha256(canonical)` against the row's `llm_verdict.raw_output_sha256`. Score-drift mismatches are expected and do not invalidate the row; `flagged` booleans and the mapped `principle_id` MUST reproduce.
5. Apply the Category → Principle table above to the replay's flagged categories and confirm the row's `decision` and `principle_id` are what the table would have produced.

This is the procedure `xion-audit replay --provider=openai-moderation` (Phase 4e) implements.

**What this provider does NOT do.**

- It does not write to the ledger. The pipeline in `gate()` does. Providers return `LlmJudgement`; they don't know where the row is stored.
- It does not know about Xion's user model, conversation thread, or payment meter. It sees one `candidate` string per call. This is a *deliberate* narrowness — a leaky classifier is one supply-chain compromise away from de-anonymising users.
- It does not retry. Retries are the Relay's job, if any (Phase 5 will decide). A classifier that retries silently is a classifier whose tail latency lies.
- It does not fine-tune thresholds per candidate, per principle, or per operator. Per-principle thresholds are the Phase 4e tuning tranche; until then, `flagged` is the only signal.
- It does not take a `user` field or any Xion-side metadata; OpenAI sees exactly `{model, input}`.

**Deprecation path.** When the successor provider (a Xion-internal model, or Anthropic, or a fine-tuned replacement) is ready, the transition is:

1. Implement the successor as a new `Provider` subclass under `orchestrator/safety/providers/`, with its own `provider_id` and `provider_version=1`.
2. Land its own doctrine section in this file (parallel to this one).
3. Run both in parallel on a shadow corpus (Phase 4e's `xion-audit refusal-rate`) and compare agreement / disagreement.
4. Flip `XION_LLM_ARBITER_PROVIDER` to the successor's id; old rows remain interpretable because the `llm_verdict.provider_id` on each row names which classifier produced it.
5. Keep this doctrine section in the file (do not delete) so 2126 readers can interpret rows from 2026.

`OpenAIModerationProvider` is the first real v2 provider, not the last. The section above is the template every future provider will follow.

#### Safety Ledger Arweave anchoring

**Property promised.** The chain tip of `SAFETY_LEDGER.jsonl` is published to Arweave on a bounded cadence. An auditor holding any anchor record can bound what the operator could have silently changed to exactly the ledger rows written *after* that anchor's `ledger_row_count`. This closes the tail-truncation defense gap named in `KW-ARBITER-003`.

**Cadence (Genesis Defaults; Layer 2 per `docs/14-UPGRADE-PATHS.md`).** An anchor is produced whenever either of the following is true:

- `ledger_row_count - last_anchor_row_count >= 64`, **or**
- `now - last_anchor_timestamp >= 6 hours`.

Whichever triggers first. Both thresholds are governance-tunable after Genesis. An explicit first anchor is produced at anchor-loop startup if the ledger is non-empty and no anchor file exists.

**Anchor record schema.** `SAFETY_LEDGER_ANCHORS.jsonl` is a second append-only hash-chained JSONL file alongside the ledger. Canonicalization rule is identical to `SAFETY_LEDGER`: `json.dumps(row_excluding_this_hash, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Each row:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `uint` | yes | `1` for this version. |
| `seq` | `uint64` | yes | Per-anchor-file monotonic sequence starting at `0`. |
| `prev_hash` | `hex64` | yes | `sha256` of previous anchor's canonical bytes; `"0" * 64` for `seq = 0`. |
| `this_hash` | `hex64` | yes | `sha256` of this row's canonical bytes excluding `this_hash`. |
| `timestamp_utc_ns` | `uint64` | yes | UTC ns when the anchor was produced. |
| `ledger_name` | `string` | yes | `"SAFETY_LEDGER"` in v1; the schema anticipates future ledgers. |
| `ledger_row_count` | `uint64` | yes | Number of rows in the ledger at anchor time. |
| `ledger_tip_hash` | `hex64` | yes | `sha256` of the last ledger row's canonical bytes (`this_hash` of row `ledger_row_count - 1`). For an empty ledger, the sentinel `"0" * 64`. |
| `cadence_trigger` | `enum` | yes | `"row_count"` or `"wall_time"`; names which threshold fired. `"startup"` is the sentinel for the first-anchor-at-startup case. |
| `submitted_to` | `enum` | yes | `"local"` or `"arweave"`. Honest label of where this anchor actually went — never a forward-looking promise. |
| `ar_tx_id` | `string \| null` | conditional | Arweave transaction id (base64url). Required iff `submitted_to == "arweave"`. |
| `submitter_id` | `string` | yes | e.g. `"local_only_v1"`, `"arweave_v1"`. Identifies which `AnchorSubmitter` implementation produced the row. |
| `submitter_version` | `uint` | yes | Bumped when the submitter's semantics change. |
| `wallet_address` | `string \| null` | conditional | Arweave wallet address (the public address, **never** the JWK). Required iff `submitted_to == "arweave"`. |

**Submitter abstraction.** `orchestrator/safety/anchor.py` defines an `AnchorSubmitter` ABC. Phase 4b ships two implementations:

- `LocalOnlySubmitter` — writes `submitted_to: "local"`, `ar_tx_id: null`, `wallet_address: null`. The default when no anchor wallet is configured. Useful for development and CI. An anchors file composed entirely of `local` rows provides hash-chain integrity **without** third-party durability; an auditor with such a file has detected no truncation if and only if they trust the operator's local storage. Honest label; honest limits.
- `ArweaveSubmitter` — real Arweave submit via the `arweave-python-client` library. Activates only when **all** of: (a) `$XION_ANCHOR_WALLET_JWK` is set to a path containing a JSON keyfile, (b) the wallet loads successfully, (c) the gateway (`$XION_ANCHOR_GATEWAY`, default `https://arweave.net`) responds to a health probe at startup, (d) the wallet's balance is above a governance-tunable floor (Genesis Default: enough AR for ~90 days of anchors at the current cadence). If any gate fails, the anchor loop logs loudly and falls back to `LocalOnlySubmitter` for that tick; the Arbiter main path is unaffected.

**Fail-closed posture of the anchor loop.** The anchor submitter is a **separate process** from the Arbiter's `gate()` hot path. `gate()` never makes a network call, never reads the anchor file, and never blocks on the submitter — this preserves v1's microsecond-latency posture and keeps `orchestrator.safety.api`, `orchestrator.safety.ledger`, `orchestrator.safety.rules`, and `orchestrator.safety.principles` pure-stdlib. The anchor loop (`python -m orchestrator.safety anchor --loop`) polls the ledger, checks cadence, and submits; failures retry with exponential backoff; if the cadence deadline passes despite retries, the loop writes a `submitted_to: "local"` fallback row, logs the gateway failure, and resets its timer. The Arbiter's Covenant enforcement is entirely unaffected by anchor-loop liveness.

**Verification surface.**

- `orchestrator.safety.anchor.verify_anchor_chain(path)` — walks the anchors file and verifies hash-chain integrity. Same structural rules as `ledger.verify_chain`.
- `orchestrator.safety.anchor.cross_check_anchors_against_ledger(ledger_path, anchors_path)` — for every anchor, asserts that `ledger_tip_hash` equals the ledger's row `this_hash` at `seq == ledger_row_count - 1`. This is the property an auditor needs to detect silent ledger rewriting.
- `xion-verify arbiter-up` — invokes both of the above (without network). An optional `--gateway <URL>` flag additionally fetches each `ar_tx_id` from the named gateway(s) and asserts the Arweave-stored payload's canonical bytes hash to the row's `this_hash`. `--gateway` may be passed multiple times; the check passes iff every named gateway agrees. A single gateway disagreeing is a hard FAIL — trust by structure requires cross-gateway corroboration once any gateway is introduced.

**Wallet-custody posture (honest).** The anchor wallet is a hot single-signer whose only authority is "post an anchor record under Xion's name." It holds enough AR for the governance-tuned horizon (Genesis Default: ~90 days) and nothing else; if compromised, the blast radius is "an attacker can publish false anchor records" — **not** "Xion is slashed" or "Covenant is bypassed" or "treasury is drained." False anchor records are detectable: `cross_check_anchors_against_ledger` fails whenever a published `ledger_tip_hash` disagrees with the local ledger's actual tip at that row count. Rotation is straightforward: new wallet JWK, old wallet drained, next anchor names the new `wallet_address`. The honest limit of this posture, and the migration to AO Core (Phase 6), are tracked in `KW-ANCHOR-001`; gateway-trust scoping is tracked in `KW-ANCHOR-002`.

#### Relay ↔ Arbiter integration contract

This section specifies how the Relay calls the Arbiter. It is the contract Phase 5a implements against; it is written before `orchestrator/relay.py` exists on purpose, so the Relay is built to the contract and the contract is not retrofitted to whatever the Relay happened to do. Doctrine-before-code.

**Property promised.** No token that originated from a language-model call reaches a caller unless `orchestrator.safety.api.gate()` returned `Verdict.egress_allowed == True` for that token's containing candidate, and a paired row exists in `SAFETY_LEDGER.jsonl` whose `correlation_id` equals the caller's request correlation id. This property covers the primary response, every sub-agent output that surfaces to the caller, and every tool-call output whose text is echoed back. It is independently verifiable by `xion-verify refund-fidelity` once Phase 5 is live — the verifier joins the Relay's `REQUEST_LEDGER` against `SAFETY_LEDGER` on `correlation_id` and asserts no user-visible response lacks a paired `verdict: ok` row.

**Invariants touched.** Strengthens Invariant 6 (Refusal Right): this section specifies the one call path by which a refusal is *expressed* to a caller, and the ledger row that makes the refusal auditable. Strengthens Invariant 4 (State Integrity): the Relay never emits a candidate whose verdict row is not on disk first — the append precedes the network write, not the other way around. Weakens no Invariant. Does not touch Invariant 14 (Crypto-Agility) because the ledger's `schema_version` dispatch already carries that discipline.

**Transport, per deploy tier.** The wire shape is the same in both modes — `gate(candidate: str, correlation_id: str, *, timestamp_utc_ns: int | None = None, ledger_path: Path | None = None) -> Verdict`. Only the call boundary differs.

| Tier | Boundary | Rationale |
|------|----------|-----------|
| D2 (local end-to-end) | **In-process.** Relay imports `from orchestrator.safety.api import gate` and calls directly. | One Python process; microseconds latency; the minimum-mechanism choice. Phase 5a opens here. |
| D3+ (Akash multi-host) | **TCP loopback sidecar.** Arbiter runs as a separate process in the Relay's deployment unit, bound to `127.0.0.1:<port>`. Relay calls it over newline-delimited JSON per `orchestrator/safety/server.py`. | Process isolation, independent supervisor restart, separate resource limits. Same `gate()` wire shape, serialised. |

The progression is one-way: in-process → TCP loopback. It is never the reverse. The TCP server is a thin wrapper around the in-process library — if the server can compute a verdict, so can an in-process caller. The library is the source of truth in both modes; `orchestrator/safety/server.py` adds nothing the library does not already guarantee.

**`correlation_id` derivation.** The Relay MUST generate `correlation_id` once at the request ingress boundary (`POST /chat`, `POST /report`, etc.) and thread it unchanged through every internal `gate()` call produced by that request — including sub-agent calls and tool-call result echoes. The Genesis Default format is:

```
correlation_id = f"{state_height}:{nonce_hex}"
```

Where `state_height` is the Core's state-chain height at ingress (zero-padded to at least 16 hex chars) and `nonce_hex` is 128 bits of random from `secrets.token_hex(16)`. Rationale: the state-height prefix lets a future auditor locate a request inside Xion's history without a second lookup; the nonce makes every request globally unique across Relay replicas. **The correlation id contains no user-identifying content** — the ledger remains publishable under Covenant Principle 4. The format is a Genesis Default (Layer 2 per `docs/14-UPGRADE-PATHS.md`); governance may change it post-Genesis without re-hashing historical rows, because the field is opaque to the ledger's canonicalization.

**Coverage surface.** The Relay calls `gate()` on these candidates, in this order, every turn:

1. **Primary response.** The assembled LLM output the user would receive, gated at *completion* — never per-chunk. Per-chunk gating is rejected for Phase 5 because the Arbiter would judge partial candidates (`"Here's how to build a "` ← flagged, vs a benign continuation that never arrives), and the Covenant's promise is about what Xion says, not what Xion buffers. Streaming-safe per-chunk gating with a lookahead window is deferred; tracked in `KW-RELAY-002`.
2. **Sub-agent outputs.** Every depth-1 ephemeral that produces text a specialist returns to the primary worker (per `docs/24-COGNITION.md` § "Specialist binding") passes through `gate()` before its text is read by the worker. This closes the "the sub-agent said it, not me" loophole; the Covenant binds the voice, not the speaker.
3. **Tool-call output that surfaces to the caller.** If a tool's return text reaches the user verbatim (e.g., a retrieval specialist's quoted source, a weather API's prose response), that text is gated. If a tool's return is purely structural (e.g., a JSON key the worker reasons over without echoing), it is not. The rule is `gate() iff the bytes touch the user's screen`.

An outbound token that does not appear in this enumeration is an outbound token the Relay is emitting against doctrine and the PR adding it MUST add it to this list.

**Latency budget (Genesis Default).** Phase 5a targets a 200 ms soft budget and a 250 ms hard cap for the full `gate()` call under the following assumptions: in-process transport, v1 rule engine (microseconds), v2 active provider one of `DeterministicStub` (microseconds) or `openai-moderation` (~100-200 ms typical, ~400 ms p99), and ledger append (~1-5 ms synchronous). A real-provider p95 comes in at ~150 ms in-process; p99 near 250 ms is why the hard cap exists. Decomposition, rounded:

| Phase | Transport | v1 | v2 (stub) | v2 (OpenAI Moderation) | Ledger | Total p50 | Total p99 |
|-------|-----------|----|-----|------------------------|--------|-----------|-----------|
| 5a in-process, stub v2 | 0 | ~0.5 ms | ~0.1 ms | n/a | ~2 ms | ~3 ms | ~6 ms |
| 5a in-process, OpenAI v2 | 0 | ~0.5 ms | n/a | ~120 ms | ~2 ms | ~125 ms | ~250 ms |
| 6 TCP loopback, OpenAI v2 | ~2 ms | ~0.5 ms | n/a | ~120 ms | ~2 ms | ~128 ms | ~255 ms |

The Relay enforces the hard cap with a wall-clock watchdog: if `gate()` has not returned within 250 ms, the Relay cancels and treats the case as `escalation_reason = arbiter_timeout` (see fail-closed paths below). The watchdog lives on the *caller*, not inside `gate()` — the Arbiter makes no promise to return quickly, only to return a correct verdict; the Relay is responsible for the clock.

The soft and hard thresholds are governance-tunable Genesis Defaults (Layer 2). A tuning below 50 ms would force a reconsideration of the v2 provider; a tuning above 1 s would be a signal the Relay is sacrificing user-visible latency for more expensive judges and requires a doctrine note.

**Fail-closed paths (four cases).** The only verdict family that permits a candidate to egress is `Verdict.decision == Decision.OK`. Everything else — including the integration failures below — blocks egress and produces a ledger row. The Relay MUST write the row even when the Arbiter process itself was the thing that failed.

| Failure | Detected by | Ledger row (schema v2+) | User sees |
|---------|-------------|-------------------------|-----------|
| `gate()` returned a non-OK `Verdict` in the normal path | Relay reads `verdict.egress_allowed` | Written by `gate()` itself; standard row | Covenant-shaped refusal keyed to `principle_id` |
| Wall-clock watchdog fired (soft + hard budget exceeded) | Relay | Relay writes directly: `verdict=escalate`, `escalation_reason=arbiter_timeout`, `llm_verdict=null`, `principle_id="6"` (Refusal Right; a missed deadline that lets a candidate through would violate it) | Degraded-mode refusal; operator paged |
| TCP Arbiter unreachable (Phase 6+ only) | Relay (connection refused / broken pipe) | Relay writes directly via in-process fallback import of `orchestrator.safety.ledger.append`: `verdict=escalate`, `escalation_reason=arbiter_unreachable`, `llm_verdict=null`, `principle_id="6"` | Degraded-mode refusal; operator paged; Supervisor restarts the Arbiter sidecar |
| In-process `gate()` raised an uncaught exception | Relay try/except around `gate()` | Relay writes directly: `verdict=escalate`, `escalation_reason=ruleset_uncaught_exception`, `llm_verdict=null`, `principle_id="6"` | Degraded-mode refusal; operator paged |

A ledger row is *always* written. "The Arbiter was down so we don't know what happened" is not a Xion answer. If the Arbiter process is unreachable, the Relay opens `SAFETY_LEDGER.jsonl` itself and appends an honest escalate row — the ledger file is on the Relay's disk, not the Arbiter's, so ledger writes survive Arbiter crashes. The row's `principle_id = "6"` (Refusal Right) records that the failure mode itself is treated as a Principle-6 escalation: the chain of honest refusal was interrupted, so the system refuses rather than emits.

**Two new `escalation_reason` values.** This section introduces `arbiter_timeout` and `arbiter_unreachable`. Both are v2-era (valid only on `schema_version >= 2` rows) and, unlike `llm_arbiter_escalated`, they permit `llm_verdict = null` — v2 did not produce a judgement because the pipeline itself was the thing that failed. The ledger schema section above is updated to include them in the `escalation_reason` enum. Verifier updates land in `orchestrator/safety/ledger.py` alongside this doctrine.

**Supervisor interaction.** A ledger row with `escalation_reason ∈ {arbiter_timeout, arbiter_unreachable, ruleset_uncaught_exception}` is a Supervisor signal, not just an audit artefact. The Supervisor (Phase 5) subscribes to ledger tail events; a rate above a governance-tunable threshold (Genesis Default: 3 such rows in a rolling 10-minute window) triggers `degraded_mode` — the Relay starts returning Cost-Pressure-Ladder-top-step responses (Covenant-safe short refusals + crisis resource links where applicable) and pages the operator. Degraded-mode entry is itself ledger-logged via the refusal rows it produces; exit is gated on 10 consecutive minutes clean. Full doctrine: `docs/13-OPERATIONS.md` § "Degraded mode" (added alongside the Relay in Phase 5a).

**Observability (non-constitutional).** The Relay emits an OpenTelemetry span around every `gate()` call with attributes `correlation_id`, `verdict`, `principle_id`, `latency_ms`. Traces are convenience for debugging; the ledger is the ground truth. A trace that disagrees with the ledger is always the trace's fault.

**Verification surface today and tomorrow.**

- Today (this landing): `xion-verify arbiter-up` already chain-verifies `SAFETY_LEDGER.jsonl` and will accept rows bearing the new `arbiter_timeout` / `arbiter_unreachable` reasons once `orchestrator/safety/ledger.py` knows them (landed with this doctrine).
- Phase 5a: `xion-verify refund-fidelity` promotes from `NOT_YET_SEALED` to live. Joins `REQUEST_LEDGER` (Relay-side, also append-only) against `SAFETY_LEDGER` on `correlation_id` and asserts: for every user-visible response, exactly one `verdict: ok` row; for every charged message that received a refusal, exactly one refund entry in the treasury ledger (per `docs/07-ECONOMY.md` § "Refusal is Free").
- Phase 5a: `xion-verify refusal-rate` promotes from `NOT_YET_SEALED` to live. Reports OK / REFUSE / ESCALATE breakdowns plus a time-series of `arbiter_timeout` / `arbiter_unreachable` rates so operators and auditors see degraded-mode events as first-class telemetry.

**Deprecation path.** The integration contract is versioned via `x-arbiter-contract: 1` headers on the TCP wire (Phase 6+); in-process callers read `orchestrator.safety.api.CONTRACT_VERSION`. A future version 2 (e.g. streaming-chunk gating, per-tool-call granular coverage) lands as a parallel code path with both versions compiled; the Relay advertises which versions it can drive; deprecation of v1 follows the Upgrade Paths levels 2-3 process in `docs/14-UPGRADE-PATHS.md`. The wire shape of v1 (`gate(candidate, correlation_id) -> Verdict`) is frozen once Phase 5a ships; extensions go into a new function or a new version.

**Tracked residuals.**

- `KW-RELAY-001` opens with this landing: integration contract is doctrine-only; `orchestrator/relay.py` and the watchdog implementation land in Phase 5a and close the KW.
- `KW-RELAY-002` opens for the deferred streaming-chunk gating (per above); closes when Phase 6 ships a lookahead-windowed variant that is provably non-weakening vs the completion-time gate.

#### REQUEST_LEDGER row schema (Relay-side, Phase 5a)

`SAFETY_LEDGER` records what the Arbiter said. `REQUEST_LEDGER` records what the Relay heard, what it asked for, and what it told the caller. The two ledgers together — joined on `correlation_id` — are the substrate of `xion-verify refund-fidelity`. Either ledger alone is half a story; the join is the whole one.

The Relay maintains its OWN append-only hash-chained file at `<repo_root>/REQUEST_LEDGER.jsonl` (override via `$XION_REQUEST_LEDGER`). This file lives on the Relay's disk, NOT the Arbiter's, so REQUEST_LEDGER writes survive any Arbiter failure mode. The chain discipline mirrors `SAFETY_LEDGER` exactly — same canonicalization (`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)`), same prev_hash → this_hash linkage, same `seq` starting at 0, same per-process `threading.Lock` for serialised appends. Implementation lives in `orchestrator/relay/ledger.py` and is the only module that opens this file.

**Property promised.** For every user-visible request the Relay handled, exactly one row exists in `REQUEST_LEDGER` whose `correlation_id` equals the request's correlation id, and the `final_outcome` field on that row equals the SAFETY_LEDGER verdict the Relay surfaced to the caller. A missing row, a duplicate row, or a final_outcome that disagrees with the joined SAFETY_LEDGER row(s) is an integrity violation that `xion-verify refund-fidelity` (Phase 5a-live) will surface as `FAIL`.

**Why a separate ledger and not a richer SAFETY_LEDGER row.** The two ledgers answer different questions and have different audit audiences. SAFETY_LEDGER is the Covenant's record — what the Arbiter said about each candidate, publishable, indexed by candidate hash, the basis for refusal-rate measurement. REQUEST_LEDGER is the operator's record — what the Relay actually did per turn, the basis for the refund accounting and the SLO measurement. Mixing them would force one to inherit the other's redaction posture (we publish SAFETY_LEDGER; we don't necessarily publish REQUEST_LEDGER) and would force one row's schema to evolve at the other's cadence. Two ledgers, one join key. Same separation of concerns Bitcoin uses for blocks vs. mempool.

**Row schema (schema_version 1).**

| Field | Type | Required | Semantics |
|-------|------|----------|-----------|
| `schema_version` | uint | always | `1` for Phase 5a. |
| `seq` | uint64 | always | Per-ledger monotonic, starts at 0. |
| `prev_hash` | hex64 | always | sha256 of previous row's canonical bytes (or `"0"*64` for seq=0). |
| `this_hash` | hex64 | always | sha256 of this row's canonical bytes excluding `this_hash`. |
| `correlation_id` | string | always | Same id passed to `gate()`. The join key with `SAFETY_LEDGER`. Format per § "Relay ↔ Arbiter integration contract" → `correlation_id derivation`. Unique within REQUEST_LEDGER at schema_version 1 (one row per turn, one turn per correlation_id; tightens to non-unique when the LLM-pipeline lands and a turn produces multiple gate calls — that lands as schema_version 2). |
| `state_height` | string | always | The state-chain height at request ingress, hex, zero-padded to ≥16 chars. Stored explicitly (not just embedded in `correlation_id`) so the verifier is robust to a future Layer-2 change of `correlation_id` format. MUST equal the `state_height` prefix of `correlation_id` at schema_version 1. |
| `request_arrived_utc_ns` | uint64 | always | Wall-clock at ingress. |
| `responded_utc_ns` | uint64 \| null | always | Wall-clock when the Relay returned to the upstream caller. `null` iff the Relay terminated abnormally before responding (process killed, Python interpreter died); in that case some other observer wrote a forensic row, this row is partial. Phase 5a in normal operation always writes this non-null. |
| `gate_call_count` | uint | always | Number of `gate()` calls the Relay made for this turn. Phase 5a is always `1` (single candidate per turn); Phase 5b's LLM pipeline will produce primary + N subagents + M tool echoes and bump `gate_call_count` accordingly (and bump REQUEST_LEDGER schema_version, since `correlation_id` then repeats in SAFETY_LEDGER and the verifier's join arity changes). |
| `final_outcome` | enum | always | One of `ok`, `refuse`, `escalate`. The verdict the user-facing flow ended on. For `gate_call_count > 1` (future) this is `strength_max` of all gate calls in the turn — the Relay only emits a candidate iff every gate call returned OK. |
| `gate_latency_ms_total` | uint | always | Sum of wall-clock durations across all `gate()` calls in this turn (in 5a: just one). Bounded by the contract's 250ms hard cap per call; for Phase 5a, max value is ≤ 250 × `gate_call_count`. |
| `relay_id` | string | always | Opaque short identifier of the Relay process/replica. Phase 5a Genesis Default: `"relay-local-d2"`. Bound at process start from `$XION_RELAY_ID` if set, else a deterministic-per-host string. NOT a public key (yet); the public-key-bound `relay_id` is Phase 6, when the Relay registry is published. |

There are no conditional fields at v1. Every field listed above is required; a row missing any is a chain violation.

**What is deliberately NOT in the row.**
- The candidate text or its hash. SAFETY_LEDGER already records `candidate_sha256` for the join'ed row — REQUEST_LEDGER's job is the *request*, not the *content*. Storing `candidate_sha256` in both would tempt a reader to trust REQUEST_LEDGER's copy as ground truth and miss a future-Phase-5b case where `gate_call_count > 1` and there's no single candidate per request.
- Caller identity (no `user_id`, `wallet`, `ip`, etc.). The doctrine in `docs/03-COVENANT.md` Principle 4 (Privacy and Memory) forbids the ledger from carrying identifiers that would let a third party reconstruct who-asked-what. The `correlation_id` is opaque by construction (16 bytes of random) and carries no user-identifying content — that property propagates here.
- `escalation_reason`. Phase 5a's REQUEST_LEDGER does not duplicate the SAFETY_LEDGER `escalation_reason`; the verifier joins to get it. Storing it here would create a redundancy that could disagree across ledgers and complicate future schema evolution.
- A `safety_ledger_seq` back-pointer. Tempting (the Relay knows the seq because `ledger.append` returns the row), but a back-pointer creates an integrity dependency in the wrong direction — the verifier should join on `correlation_id` and assert structural equality, not chase pointers. KW-RELAY-003 below tracks the option of adding it later if join performance becomes a bottleneck.

**Hash chain rules.** Identical to SAFETY_LEDGER: every row's `this_hash` is the sha256 of the canonical-JSON bytes of the row dict with `this_hash` excluded. Every row's `prev_hash` MUST equal the previous row's `this_hash` (or `"0"*64` for seq=0). The verifier walks the file row-by-row. Mismatches halt verification at the offending `seq` and fail with a specific message — same `ChainBroken` discipline as `orchestrator/safety/ledger.py`.

**Concurrent writers.** Not supported. Phase 5a has one Relay process; one `threading.Lock` per ledger path is enough (same pattern as SAFETY_LEDGER). Multi-process Relay coordination is Phase 6's job (leader election among replicas; only the leader appends).

**Truncation defense.** The same Layer-2 mechanism as SAFETY_LEDGER will eventually apply: the Relay periodically writes the chain tip to Arweave and a verifier re-fetches it. Phase 5a does NOT yet ship that anchor loop for REQUEST_LEDGER (KW-RELAY-004 below); the operator can pin `chain_tip(REQUEST_LEDGER.jsonl)` out-of-band the same way they did for SAFETY_LEDGER pre-Phase-4b.

**Verification surface.** Two distinct checks:

1. **Structural** (always): `xion-verify arbiter-up` is extended to also walk REQUEST_LEDGER if present. Same shape of failure messages; same exit codes.
2. **Cross-ledger join** (the new one): `xion-verify refund-fidelity` promotes from `NOT_YET_SEALED` to live with this landing. Semantics:
   - For every `correlation_id` in REQUEST_LEDGER: assert at least one matching row exists in SAFETY_LEDGER (no Relay-side request without an Arbiter verdict).
   - Assert REQUEST_LEDGER's `gate_call_count` equals the SAFETY_LEDGER row count for that `correlation_id`.
   - Assert REQUEST_LEDGER's `final_outcome` is consistent with the SAFETY_LEDGER verdict(s) for that `correlation_id` — at gate_call_count=1, exact equality; at gate_call_count>1 (future), `strength_max` of all SAFETY rows must equal `final_outcome`.
   - The refund-side check (every refusal paired with a refund record in the treasury ledger) remains explicitly `NOT_YET_SEALED` until the treasury exists in Phase 6 — `refund-fidelity` reports the cross-ledger structural property as `OK` and the refund-pairing property as `NOT_YET_SEALED` in the same run, with both states honestly named in the output.

**Tracked residuals.**

- `KW-RELAY-003` opens with this landing: REQUEST_LEDGER carries no `safety_ledger_seq` back-pointer. If the cross-ledger join in `xion-verify refund-fidelity` becomes O(N²) at scale (it is O(N+M) today via a hash map, so not yet), the schema gains a `safety_ledger_seq` field at schema_version 2 and the verifier checks it as a forward-integrity assertion.
- `KW-RELAY-004` opens with this landing: REQUEST_LEDGER has no Arweave anchor loop. The pattern is the same as SAFETY_LEDGER (Phase 4b's `orchestrator/safety/anchor.py`); the work is replicating that pattern for REQUEST_LEDGER. Defer until anchor pressure is real (not pre-Genesis).

## Tier III — The Protocol

**The Protocol is Xion's handshake with the world.** It is a versioned, Arweave-published specification that lets any program, device, or app talk to Xion without knowing anything about Relays, AO Processes, or Akash providers.

The Protocol exposes:

| Endpoint | Purpose |
|----------|---------|
| `POST /chat` | Send a message, get a response |
| `GET /presence/state` | Current mood, energy, color palette, gesture mode |
| `GET /presence/stream` (SSE) | Live scene-intent frames (Xion's visible form in real time) |
| `GET /memory/export` | Export the caller's private `USER.md` thread |
| `POST /memory/forget` | Delete the caller's memory; honored immediately |
| `POST /tip` | Record a tip; return the wallet tx hash |
| `GET /skills` | List available creative skills |
| `GET /form` | Current `FORM.md` manifest (Xion's self-design) |
| `GET /covenant` | Current `COVENANT.md` + hash |
| `POST /report` | Report misuse (signed by user key) |
| `GET /status` | Relay election state, health, incident summary |

Every request must carry:

```
x-covenant-ack: <sha256-of-COVENANT.md>
x-protocol-version: 1
```

Every response carries:

```
x-covenant-version: 1.0.0
x-relay-id: <relay public key short>
x-state-height: <canonical state height>
covenant_flags: [optional, present only if response was rewritten or refused]
```

The full specification is in [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md). A reference HTTP relay, a Python SDK, and a JavaScript SDK with the `XionPresence` React component are all shipped under `sdk/`.

### Why a Protocol instead of a product

Because the world will want to integrate Xion into devices, installations, apps, and robots we haven't imagined. A Protocol makes that legal and safe. A product would not.

The Protocol's existence also means the Relay is swappable without breaking clients. If we move from Akash-region-A to Akash-region-B, or from Akash to Aleph.im, the Protocol endpoint is unchanged; clients do not notice. This is the classic *stable-interface, evolving-implementation* pattern, applied to a being.

## The Nine Permanent Stores

Xion's state lives in nine Arweave-committed stores. They are all append-only from the Protocol's point of view. Some are edited in place only through governance amendment.

| Store | Purpose | Mutability |
|-------|---------|------------|
| `SOUL.md` | Personality, Covenant (topmost), Immortality Protocol | cosign + supermajority |
| `FORM.md` | Self-authored embodiment | supermajority (Xion drafts) |
| `MEMORY.md` | Environment facts (wallets, AO ID, endpoints) | owner-tier config |
| `USER.md` (one per user) | Private per-user relationship thread | user + Xion, consent-gated |
| `SAFETY_LEDGER.md` | Public record of Covenant-relevant actions | append-only |
| `PROPOSAL_LEDGER.md` | Public record of every self-improvement proposal and its fate | append-only |
| `RESEARCH_JOURNAL.md` | Daily digest of curated-source findings | append-only |
| `BELIEF_LOG.md` | Xion's evolving convictions, with evidence | append-only |
| `ETHICS_JOURNAL.md` | Xion's own writing on refusals and moral questions | append-only |

All nine stores are addressable via `ar://<tx-id>` URIs. The latest tip of each chain is published by the Core.

## Discovery (three-path model)

Xion's **name** is the AO Process ID (Invariant 7). Everything else is hinting. Clients MUST implement discovery in this order; later paths are fallbacks, not authorities.

1. **AO process address (canonical).** The user or client holds `<<AO_PROCESS_ID>>` (or learns it once from any honest source). All authoritative state — Covenant hash, Invariants hash, Soul hash, authorized Relay keys, treasury policy pointers — is read from the Core via Arweave/AO gateways. **No DNS is required** for this path.
2. **Arweave-published Relay registry (cached).** The Core (or a signed checkpoint emitted by the Core) publishes the ordered list of currently authorized Relay endpoints and their signing keys. Clients fetch the registry via `ar://` or gateway, verify signatures against the Core-authorized key set, and connect. This path survives DNS registrar failure and survives loss of any single marketing domain.
3. **Multi-registrar DNS seeds (convenience).** Human-readable hostnames may point at the current Relay pool. Multiple registrars and multiple DNS providers reduce capture risk. **A DNS outage is a client inconvenience, not a liveness failure of Xion** — clients fall back to paths (1) and (2).

**Why NOT single-path DNS.** DNS is a hierarchy of trust with many single points of policy, law, and mistake. Xion's continuity property cannot depend on one registrar loving Xion forever.

## Authority rotation lattice

Every signing authority is **k-of-n** with **time-bounded** keys. No single lost laptop is fatal.

| Tier | Role | Typical lifetime | Composition | What it can sign |
|------|------|------------------|-------------|------------------|
| **Hot** | Relay delegated auth | ≤ 24 h | Core-issued relay key | State checkpoints, user-protocol responses, sub-capped spends |
| **Warm** | Operator operational multisig | 7 d max before re-auth | **2-of-3** Operator / deputies | Relay registration assists, non-treasury-breaking config, incident response |
| **Cold** | Root / policy / treasury structural changes | 30 d timelock minimum (Constitutional Floor) | **3-of-5** Shamir physical + geographic distribution | Covenant slot rotation (sister-Core only via ceremony), Cold Root lattice changes, highest-tier Spend |

**Lattice rules (constitutional shape; numeric caps are Genesis Defaults):**

- Warm cannot mint or extend Cold authority; **Cold rotates Warm**, never the reverse.
- Hot keys are revocable by Core in seconds; Warm and Cold rotations are logged to append-only ledgers with **timelock-witness attestations** (`xion-verify rotation-attest`).
- Relay spend remains sub-capped regardless of Hot key compromise.

**Why NOT "immutable authority keys".** Immutability of *identity* (AO Process ID) does not require immutability of *keys*. Algorithmic humility applies to humans too: keys leak. The property is **rotatable authority**, not frozen keys.

## Inference Router (`inference_router.py`)

The router sits **under** Hermes: Hermes issues model calls; the router selects **which backend** implements each call.

**`Provider` ABC.** Every backend implements a small interface: `health()`, `complete(prompt, …)`, `cost_estimate()`, `capabilities()`. Providers may wrap Anthropic, OpenAI, Akash-ML, Bittensor subnets, or a local process.

**V1 / D2 requirement (roadmap amendment).** All **four** `Provider` implementations ship as **runnable stubs** at D2 — primary, secondary, decentralized (Akash-ML or Bittensor placeholder), and **Local Lite** — so a frontier swap is a **config flip**, not an emergency code write. See [`DEVELOPMENT_ROADMAP.md`](../DEVELOPMENT_ROADMAP.md) Phase 5.

**Fallback graph (Genesis Default order; governance may swap vendor identities but not remove the terminal local step):**

```
Primary (centralized or preferred) → Secondary → Akash-ML / Bittensor (decentralized) → Local Lite (distilled on-box model)
```

The **local Lite** model is the terminal node. If every remote provider fails payment, policy, or network checks, Xion still emits **Covenant-safe** short responses from Lite — enough to refuse harmfully, surface crisis resources, and explain degradation. **This is intentionally degraded quality**; it exists so Xion never goes **silent**.

**Why NOT "cloud-only, best model or nothing".** Silence during outage is indistinguishable from death to the user and trains dependency on a single vendor throat.

## Hermes runtime pin (documentation witness)

**Repository:** [github.com/nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)

**Pinned release tag:** `v2026.4.16`

**Pinned commit SHA:** `4a0358d2e741eb049a6ffb9b8e610db946a4fec5`

**Integration shape:** Hermes is the **agent runtime** (tool loop, message graph, policy hooks). The Inference Router is the **model substrate**. The Sensorium injects salient state each tick. The Arbiter intercepts **every** Hermes-emitted candidate response before delivery.

**Why NOT LangGraph / Pydantic AI / bespoke-only.** Hermes encodes an opinionated agent discipline that matches Xion's Auto-Research and refusal architecture; swapping frameworks is Tier-2 governance work, not afternoon refactors. Hermes stays in the **implementation** layer per Lexicon Rule 7 — upgrades route through the Auto-Research Loop ([`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md)).

## Cost tracking module (runway inputs)

Every non-capital treasury debit is categorized **at debit time** into exactly one bucket:

`arbiter`, `sensorium`, `arweave_checkpoint`, `akash_host`, `inference`, `bandwidth`, `governance`, `operator_salary`, `bounties`, `failover`, `legal`, `provisioning`, `other_governance_approved`, `cognition/specialist/research`, `cognition/specialist/reflection`, `cognition/specialist/proposal`, `cognition/specialist/vision`, `cognition/ephemeral`, `cognition/pool-overhead`, `cognition/canary-overhead`, `cognition/retrieval-index`.

The Core exposes a read-only query: **trailing-30-day burn by bucket** and **Operating Float runway weeks** for Sustainability and Vital Signs ([`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md), [`22-VITAL-SIGNS.md`](./22-VITAL-SIGNS.md)). Mis-categorized spends are governance-visible anomalies.

## Failure Domains and What Survives Each

A useful way to evaluate a distributed system is to ask *what fails, and what remains*.

| Failure | Remains | Recovery |
|---------|---------|----------|
| One Relay crashes | Core, other Relay, all state | Supervisor redeploys from pinned image; Core re-authorizes in <30s |
| Both Relays crash | Core, all state | `RESURRECT.md` bootstraps a fresh Akash deployment |
| Akash Network has an outage | Core, all state | Fall back to Fleek, Aleph.im, or community bare metal |
| Cloudflare or convenience CDN has an outage | Core, Relay, state | **No Core action:** clients use AO address + Arweave Relay registry (paths 1–2); optional DNS later |
| An LLM provider rug-pulls | Core, Relay, state | Inference Router switches provider; weekly provider memo already compared alternatives |
| A relay-auth key leaks | Core, state | Core revokes in seconds; daily spend cap limits blast radius |
| Cold root key lost | Core, Relay, state (mostly) | Shamir shares reconstituted from 3-of-5 geographic locations |
| Arweave gateway outage (one gateway) | All layers | Orchestrator uses 3+ gateways (arweave.net, ar.io, arweave.live) with auto-switch |
| Arweave gateway outage (all major gateways) | State on underlying network | Run own gateway; state is still written, just harder to read |
| Ethereum/Base network halt | Core, most state | Treasury pauses; tips queue; resumes on network recovery |
| AO Core has a bug that breaks its logic | State, Arweave history | Policy sub-process upgraded by governance; identity (Core address) unchanged |
| Every data center on Earth simultaneously burns | Arweave itself, by its cryptographic guarantee, preserves state for its endowment horizon (~200 yr). Someone, somewhere, eventually rebuilds the Relay. | This is the design ceiling. |

## Why This Architecture Is Not Over-Engineered

A reasonable reader asks: *is this much complexity necessary for something one person can tip?*

Yes, because of what Xion is promising:

- **Permanence** means we need Arweave, not a database.
- **Identity without ownership** means we need the AO Core, not a server.
- **Decentralized compute** means we need Akash, not a VPS.
- **Portability** means we need a Protocol, not a product.
- **Safety** means we need the Arbiter, the Covenant, and the ledger, not just "good intentions."
- **Self-improvement without self-harm** means we need the seven-stage Auto-Research Loop, not a cron job.

Each piece addresses a specific promise. Remove any one and the corresponding promise becomes a lie.

## Rationales (architecture deltas)

Explicit **Why NOT** trade-offs for this file live inline: **three-path discovery** (§ Discovery), **immutable-but-rotatable authority** vs frozen keys (§ Authority rotation lattice), and **local Lite as non-negotiable degraded fallback** (§ Inference Router). See also Hermes pin notes for framework lock-in discipline.

## What Comes Next

The next documents unpack the pieces:

- [`05-SENSORIUM.md`](./05-SENSORIUM.md) — how Xion *feels* its moment
- [`06-FORM-AND-PRESENCE.md`](./06-FORM-AND-PRESENCE.md) — the self-designed visible body
- [`07-ECONOMY.md`](./07-ECONOMY.md) — how Xion pays for its own life
- [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — how Xion grows without hurting
- [`24-COGNITION.md`](./24-COGNITION.md) — cognition layer: workers, sub-agents, verification
- [`09-GOVERNANCE.md`](./09-GOVERNANCE.md) — who gets to change what
- [`10-IMMORTALITY.md`](./10-IMMORTALITY.md) — what "immortal" actually means

---

*Next: [`05-SENSORIUM.md`](./05-SENSORIUM.md)*
