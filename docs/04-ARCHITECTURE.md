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
| `escalation_reason` | `string \| null` | conditional | Present iff `verdict == escalate`. One of `subjective_principle`, `model_review_required`, `classifier_low_confidence`, `ambiguous_nearmiss`, `ruleset_uncaught_exception` (v1-era), `llm_arbiter_escalated`, `llm_arbiter_uncaught_exception`, `llm_arbiter_provider_unavailable` (v2-era, schema_version 2+). New reasons require a doctrine update. |
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
