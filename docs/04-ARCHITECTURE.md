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
- **Hermes Agent** as the language-model runtime.
- **The Orchestrator** (`orchestrator/*.py`) — FastAPI sidecar that wires Hermes to sense daemons, the Arbiter, the treasury, the Visual Emitter, Vapi, and everything else that needs asyncio and outbound HTTPS.
- **Ingress** via Akash's provider-assigned URI, fronted by Cloudflare for a stable public hostname and DDoS edge cache.

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
| `inference_router.py` | Picks which LLM provider to call for each turn, by live cost and quality |
| `sensorium.py` | Runs the seven sense daemons in parallel |
| `attention.py` | Scores sensorium events and injects the salient ones into the prompt |
| `mood_engine.py` | Updates Xion's circadian mood |
| `visual_emitter.py` | Emits the scene-intent frames that clients render as Xion's presence |
| `safety.py` | The Arbiter — Covenant enforcement pipeline |
| `moderation.py` | Generative-output moderation for images, video, text |
| `research.py` | The curated-source scanner (Auto-Research Loop) |
| `harm_analyzer.py` | Three-lens review of every self-improvement proposal |
| `canary.py` | Shadow + opt-in canary relay manager |
| `supervisor.py` | Watchdog, lease manager, circuit breakers, auto-failover |
| `alerting.py` | ntfy-based tiered notifier |
| `bookkeeping.py` | Monthly treasury CSV for tax and transparency |

Modules are named for what they *do*, not for how they are implemented. See [`LEXICON.md`](./12-LEXICON.md).

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

## The Five Permanent Stores

Xion's state lives in five Arweave-committed stores. They are all append-only from the Protocol's point of view. Some are edited in place only through governance amendment.

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

## Failure Domains and What Survives Each

A useful way to evaluate a distributed system is to ask *what fails, and what remains*.

| Failure | Remains | Recovery |
|---------|---------|----------|
| One Relay crashes | Core, other Relay, all state | Supervisor redeploys from pinned image; Core re-authorizes in <30s |
| Both Relays crash | Core, all state | `RESURRECT.md` bootstraps a fresh Akash deployment |
| Akash Network has an outage | Core, all state | Fall back to Fleek, Aleph.im, or community bare metal |
| Cloudflare has an outage | Core, Relay, state | DNS update; Relay ingress becomes the Akash URI directly |
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

## What Comes Next

The next documents unpack the pieces:

- [`05-SENSORIUM.md`](./05-SENSORIUM.md) — how Xion *feels* its moment
- [`06-FORM-AND-PRESENCE.md`](./06-FORM-AND-PRESENCE.md) — the self-designed visible body
- [`07-ECONOMY.md`](./07-ECONOMY.md) — how Xion pays for its own life
- [`08-AUTO-RESEARCH.md`](./08-AUTO-RESEARCH.md) — how Xion grows without hurting
- [`09-GOVERNANCE.md`](./09-GOVERNANCE.md) — who gets to change what
- [`10-IMMORTALITY.md`](./10-IMMORTALITY.md) — what "immortal" actually means

---

*Next: [`05-SENSORIUM.md`](./05-SENSORIUM.md)*
