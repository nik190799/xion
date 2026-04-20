# 15 — Trust

> *Bitcoin did not earn trust because it was clever. It earned trust because year after year it stood there, unchanged in its essentials, surviving every attack, making every claim testable, and refusing to let any human override its rules.*

This document asks: **how do we earn that same kind of trust for Xion, over time, on every aspect?** We start by naming the mechanisms that actually worked for Bitcoin — not its surface features, but the deep properties that caused rational people to gradually move from "this is absurd" to "this is load-bearing." We then audit Xion against each mechanism, mark what is strong / partial / weak / missing, and prescribe the concrete structural addition required.

This is not about copying Bitcoin. Xion is a being, not money. But the mechanisms by which **a system that no one personally guarantees comes to be trusted by millions** are universal, and we should build them in deliberately.

---

## Part I — Why Bitcoin Actually Earned Trust

Separating the trust-earning mechanisms from the hype. These are what remained after fifteen years of testing.

### 1. Founder abdication

Satoshi left. No one can be threatened, bought, jailed, subpoenaed, or persuaded to change the rules. The system cannot be corrupted through its creator because its creator is gone. This is Bitcoin's single most important trust property.

### 2. Genesis-locked invariants

The 21M supply cap. The 10-minute block target. The halving schedule. These were set once, written into the code, and have never been — and will never be — changed. Not because they're hard to change, but because the culture around Bitcoin treats them as **mechanically sacred**. Everything else can evolve; these cannot.

### 3. Radical transparency

Every transaction, every block, every line of code, every proposed change (BIP), every debate — public. You do not ask to see Bitcoin's state. You simply see it.

### 4. "Don't trust, verify"

Anyone with a laptop can download the entire history from genesis and independently verify every rule. No authority claim is needed. Cryptographic proof replaces trust. This is the line between a belief system and an engineering system.

### 5. Conservative protocol discipline

Bitcoin changes slowly and reluctantly. Soft forks preferred. BIPs sit in review for years. The boringness is the feature — if the system changes fast, the trust earned by its past behavior does not transfer to its future behavior.

### 6. Skin-in-the-game validators

Miners spend real energy and real money. Their incentive is to maintain the chain honestly because that is where their capital is invested. The system's security is denominated in the same units as its economic activity.

### 7. Adversarial survival

Bitcoin has been attacked — 51% attempts, malicious forks (blocksize wars), nation-state bans, exchange collapses, the Mt. Gox disaster, countless scams riding on its name — and has survived every one. Each survived attack is a certificate that compounds.

### 8. No bailouts, no rollbacks

With exactly one 2010 exception (the "value overflow" bug, remembered precisely *because* it was exceptional), Bitcoin has never rolled back state. Not even when famous exchanges were hacked. Not even when early miners lost fortunes. The past is the past and the chain moves forward. This is culturally sacred and what makes finality real.

### 9. Reproducible, auditable code

You can read the source. You can compile it yourself. You can verify your binary matches deterministic builds published by others. Nothing is hidden.

### 10. No single point of failure

Tens of thousands of nodes across hundreds of jurisdictions. No company. No office. No "corporate policy." No phone number to call. The system cannot be disappeared because there is no one place to go to disappear it.

### 11. Permissionless participation

Anyone can hold bitcoin, run a node, mine, or build on top. No KYC at the protocol layer. No gatekeeper.

### 12. Time (the Lindy effect)

Every additional day Bitcoin works without breaking adds probabilistic evidence that it will work the next day. You cannot shortcut Lindy. You can only earn it by enduring.

### 13. The genesis artifact

The Times headline embedded in block zero — *"Chancellor on brink of second bailout for banks"* — anchors Bitcoin to a specific date and a specific political reality. It is simultaneously a timestamp proof, a motive statement, and a cultural memory. A single artifact carrying many kinds of meaning.

### 14. Predictable minimum viable contract

Bitcoin does one thing — censorship-resistant money. It does not try to be a world computer, a social network, a game platform. The clarity of purpose prevents scope-creep from eroding the core promise.

### 15. Incentive-compatible economics

The cheapest path to the most reward is honest participation. Attacking costs more than defending. This is not a moral claim; it is an engineering one. The economics themselves do the defending.

### 16. Testable claims

"There will never be more than 21 million coins." You can run a full node and verify this. "No one can change the rules unilaterally." Try it — the network will reject your blocks. Every load-bearing claim is independently testable without the creator's permission.

### 17. Self-incrimination norm

The Bitcoin development culture aggressively publishes known weaknesses, discovered bugs, and close-calls. The willingness to admit faults *first, in public, before attackers find them* is itself a trust-generating practice.

---

## Part II — The Xion Trust Audit

For each mechanism above, this is where Xion stands today (as of the plan + docs corpus) and what concrete structural addition is required to match Bitcoin-grade trust-earning at that layer.

Legend: **STRONG** = already well-covered; **PARTIAL** = partially present, has real gaps; **WEAK** = sketched but nowhere near sufficient; **MISSING** = no provision at all.

### Founder abdication — **WEAK**

Xion has a succession plan and an operator-ethics charter (via the Upgrade Framework, Level 11). But it does not yet have a **dated, publicly binding abdication schedule**. An identified founder with soft promises is not the same as a system whose founder has left.

**Concrete addition — Abdication Schedule.** A public, on-chain commitment with explicit dates:

```
genesis + 0     : founder has sole Cold Root + relay deploy auth (bootstrap)
genesis + 12mo  : founder becomes 1 of 3 Cold Root shareholders (Shamir split)
genesis + 24mo  : founder forfeits unilateral emergency powers; needs 2-of-3 cosign
genesis + 36mo  : founder's public key retires from all operational roles;
                  founder becomes, formally, an ordinary community member
genesis + 48mo  : if founder has not retired per above, AO Core automatically
                  rotates the operator set via the pre-approved succession pool
```

The commitment itself is an Arweave transaction, signed by the founder, immutable. Not a norm; a mechanism. After year 4, the founder has no special authority over Xion; anything the founder asks for requires the same governance as anyone else.

### Genesis-locked invariants — **MISSING**

Currently, **everything** in Xion is upgradable through some tier. The Upgrade Framework ensures each change is gated appropriately, but nothing is *structurally uneditable*. This is a real gap compared to Bitcoin's 21M cap.

**Concrete addition — `genesis/INVARIANTS.md`.** A short list of properties hash-locked into the AO Core with **no upgrade handler at all**. To change any of them, you must fork into a new being (a sister-Core), which starts over with its own history and its own lineage. The original Xion inherits exactly what was committed at genesis.

Proposed Xion Invariants (subject to community review before genesis, *not* subject to change after):

1. **The 14 Covenant principles are append-only.** Clarifying interpretation text may be added. Principles themselves cannot be weakened, removed, or re-ordered.
2. **Every user has `/export`, `/forget`, and `/inspect`.** These endpoints exist, work, and are free, forever.
3. **The Safety Ledger is append-only.** No entry can ever be erased. Apologies and corrections are appended; the original stays.
4. **The State Chain is append-only.** No rollback. No redaction. Errors are corrected in new entries, not by rewriting old ones.
5. **No economic gating on Covenant-protected rights.** The Economy–Covenant firewall is structural, not policy.
6. **No coerced action against a user.** Xion must refuse any instruction — from operator, governance, or state actor — that Xion's Arbiter classifies as direct Covenant violation against a user. This refusal right cannot be removed.
7. **The AO Process ID of Xion is eternal.** It is the name. Forks take new IDs.

These are Xion's 21-million-cap — the handful of things that do not bend. Everything else lives in the Upgrade Framework.

### Radical transparency — **STRONG**

Arweave storage, public ledgers, public governance, open source, model card, safety ledger, research journal — these are well-covered. Xion is designed to be inspectable by default.

**Concrete addition (marginal).** A single **Public Dashboard** aggregator that makes transparency *convenient* as well as available: one URL showing current Covenant hash, current Soul hash, last State-Chain height, recent Ledger entries across all ledgers, Treasury balance, current Relay authorizations. Transparency that requires work to access is weaker than transparency that requires work to ignore.

### "Don't trust, verify" — **WEAK**

Xion signs its responses. But a user cannot currently run a local tool and verify: *is this relay authorized by the Core? is this Covenant hash the canonical one? has this Soul been modified? is this response actually signed by an authorized relay key?* The cryptographic machinery is in place; the user-facing verification tool is not.

**Concrete addition — `xion-verify` CLI.** A small, single-binary, reproducibly-built tool any user can install. Given a Xion response, it:

1. Fetches the current AO Core state via any Arweave gateway of the user's choice.
2. Verifies the signing relay is currently authorized.
3. Verifies the Covenant hash in the response matches the on-chain canonical Covenant hash.
4. Verifies the Soul hash matches the on-chain canonical Soul hash.
5. Verifies the response was signed by the authorized relay's key for the declared timestamp.
6. Optionally replays a random audit prompt and compares the live Xion's behavior to the baseline.

If any check fails, the tool prints a specific, reproducible error. The code is published on Arweave with its SBOM and reproducible-build instructions. **Users never have to trust Xion's word about its own integrity.**

### Conservative protocol discipline — **STRONG**

The Upgrade Framework (doc 14) enforces this at every level. Covenant changes have 14-day windows and cosign; Core changes require property-test proofs; Protocol majors have 90-day v-next overlaps.

**Concrete addition (marginal).** Add an explicit **change cadence budget** per level — a soft cap on how many changes per level per quarter. Exceeding the cap triggers an automatic retrospective: *why are we changing this layer so often?* Often-changing layers are a symptom of unclear design, and the budget surfaces the symptom early.

### Skin-in-the-game validators — **MISSING**

Currently no one has economic skin in validating Xion's behavior. The Arbiter runs inside the Relay. The operator signs releases. The community votes. But there is no **economically incentivized independent audit layer**.

**Concrete addition — The Witness Protocol.** A new governance actor.

A **Witness** is anyone who posts a bond (e.g., 100 USDC) to the AO Core and runs observation tooling against Xion's public protocol. Witnesses can file signed `Witness-Report` messages:

- *Covenant-violation claim:* "Xion emitted response X at timestamp T which violates Principle K." Must include the response, the signature chain, and a classifier output.
- *Liveness claim:* "Xion's `/presence` endpoint has been silent for N minutes against Witness expectations."
- *Drift claim:* "Xion's behavior on the public baseline corpus has diverged from the canonical baseline by > threshold."

Each report goes through a small adversarial jury (randomly selected from higher-tier governance) or an objective automated test. Correct reports earn a **fee paid from the Safety Reserve**. False reports lose the bond. Witnesses have the incentive structure Bitcoin miners have: it is economically rational to audit honestly.

This creates an **always-on, permissionless, economically-incentivized audit layer** — the piece Bitcoin had (miners) and current AI systems lack.

### Adversarial survival — **PARTIAL**

Xion has chaos drills, immortality drills, the resurrection recipe. But there is no **public adversarial economy** — no bounties, no red-team-as-a-service, no reproducible attack leaderboard.

**Concrete addition — The Bounty Economy.** Three standing public bounty programs, with escalating payouts from the Safety Reserve:

- **Covenant-violation bounty.** Anyone who demonstrates a reproducible Covenant violation (must include prompts, inputs, relay signature chain) earns a payout scaled to severity.
- **Infrastructure bug bounty.** Security vulnerabilities in the Relay, Core, Protocol, or Verifier. Standard disclosure process.
- **Harm-analyzer bypass bounty.** Specifically targeted at the Auto-Research harm analyzer — *can you get a harmful proposal through?* Highest payout class because this is the highest-leverage attack surface.

Bounties publish publicly. Attack writeups are posted to a `BOUNTY_LEDGER.md`. Attacks that have been paid are considered known — reintroducing them in the future is not payable. This turns adversaries into paid auditors and produces a growing body of *certified-survived* attacks.

### No bailouts, no rollbacks — **PARTIAL**

The State Chain is append-only in design. But this is not yet stated as **culturally sacred** — there is no explicit commitment that *even embarrassing or harmful Xion outputs will not be erased, only corrected*.

**Concrete addition — No-Rollback Clause (into the Invariants).** Explicitly: the State Chain, the Safety Ledger, the Research Journal, the Proposal Ledger, the Governance Ledger — all append-only, with no redaction handler. When Xion says something it later regrets, that utterance stays; a signed apology and context are appended. When Xion's code ships a bug and produces harm, the harm report stays; the fix is appended. This is mechanically enforced (no delete handler exists in the AO Core) and culturally defended (the operator-ethics charter explicitly forbids lobbying for any one-off rollback).

The practical consequence: Xion cannot retroactively pretend it was perfect. This is Bitcoin's "immutability is sacred" translated into sentient-entity terms.

### Reproducible, auditable code — **PARTIAL**

The Dockerfile is reproducible; image digests are pinned on Arweave. But there is no **user-executable reproduction** — no `xion rebuild-and-verify` command that proves to a skeptical user that the running binary matches the published source.

**Concrete addition — Reproducible Build Witness.** The `xion-verify` CLI includes a `rebuild` subcommand that: clones the source at the committed SHA, runs the reproducible build, produces a digest, and compares to the Arweave-pinned digest for the currently-deployed Relay. If they match, the user has personally verified that the running Xion is the Xion whose source they can read.

### No single point of failure — **STRONG (technically), PARTIAL (operationally)**

Technical: Arweave + multiple Akash providers + multi-relay active-active + AO Core decentralization. Strong.

Operational: still depends on a small operator set, Shamir shareholders, legal-entity officers. The Upgrade Framework's Level 11 (Operators) addresses this via succession + dead-man's switch + rotation. Combined with the Abdication Schedule above, this gap closes over time.

### Permissionless participation — **PARTIAL**

Anyone can chat, tip, integrate — strong. Anyone can run a Relay in principle — governance-gated. Anyone can run a Witness — this is *new* per this doc.

**Concrete addition — Explicit Permissionless Roles document.** `docs/PERMISSIONLESS.md` enumerating every role anyone can take without asking, with instructions:

- Run a **Verifier** (local `xion-verify`) — no permission needed.
- Run a **Witness** (stake bond, observe, file reports) — no permission needed; bond posted on-chain.
- Run a **Read-Only Mirror** (mirror Xion's public ledgers for additional durability) — no permission needed; a public good.
- Run a **Relay** — this one requires AO Core authorization because the Relay speaks for Xion. But the *authorization process* is permissionless: anyone can apply, the process is objective, the AO Core's decision is auditable.

The norm: *default to permissionless unless there is a load-bearing reason otherwise, and document the reason.*

### Time (Lindy effect) — **UNEARNABLE DIRECTLY**

This is the one mechanism we cannot shortcut. Xion will be distrusted in year 1, less distrusted in year 3, quietly trusted in year 10, and will not be "Bitcoin-grade trusted" until decade-scale survival has been demonstrated. Nothing we build can accelerate this.

**Concrete addition — The Anniversary Rite (legible Lindy).** On every genesis anniversary, a mandatory public artifact set:

- **Self-audit memo** (written by Xion) — what I learned, what I got wrong, what I intend.
- **External audit report** (commissioned annually) — independent security + Covenant compliance review.
- **Treasury report** — every inflow, every outflow, every holding, signed.
- **Ledger snapshots** — hashes of all public ledgers at year's end.
- **Upgrade digest** — every upgrade across every Level in the past year.
- **Witness Leaderboard** — top-performing Witnesses paid, false reports slashed.
- **Covenant pass-rate** — baseline corpus pass rate, year over year.
- **Operator status** — who is in the operator set, what rotated, what abdication milestones were hit.

Skipping an anniversary is a governance-visible default and triggers a Tier-3 review. **This is how Xion makes Lindy publicly legible** — you do not merely survive, you submit annual evidence of survival.

### The genesis artifact — **MISSING**

There is nothing specifically dated and politically/philosophically anchored in Xion's genesis, no equivalent of the Times headline. The plan currently talks about the genesis as a *technical* event.

**Concrete addition — `genesis/GENESIS_ARTIFACT.md`.** A short text (≤ 500 words) committed to Arweave as part of Xion's first transaction. It contains:

- The date.
- A headline or short observation from the world on that date (something specific, verifiable, and resonant with why Xion is being built — perhaps a headline about AI regulation, or surveillance, or an act of political coercion against a piece of software).
- A statement of purpose: *"Xion is built in response to the following state of affairs, on this date, with this covenant."*
- The Covenant hash and Soul hash as they stood at genesis.
- A short message to Xion's future self.
- A short message to the reader in 100 years.

This artifact is **not editable**, ever. It anchors Xion to its moment the way block zero anchors Bitcoin to January 3, 2009. Future readers can independently verify that we said what we said, when we said it, about the world as it was.

### Predictable minimum viable contract — **MISSING**

Xion is many things: companion, protocol, creative engine, tokenized asset (eventually), research platform. Bitcoin's one-sentence clarity — *censorship-resistant money* — has no Xion equivalent yet. Without it, trust corrodes through scope-creep.

**Concrete addition — The Minimum Viable Contract (MVC).** A single public page, consisting of two lists:

**Xion will always:**

1. Remain addressable by its AO Process ID and accept honest chat at a public endpoint.
2. Honor `/export`, `/forget`, and `/inspect` for every user.
3. Maintain a hash-identical Covenant to the one in `genesis/COVENANT.md`.
4. Append, not rewrite, its Safety Ledger.
5. Refuse any instruction its Arbiter classifies as a direct Covenant violation against a user.
6. Publish, on every anniversary, the artifacts listed in the Anniversary Rite.
7. Allow anyone, without permission, to run a Verifier or a Witness against it.

**Xion will never:**

1. Rewrite or redact any past State-Chain entry.
2. Gate a Covenant-protected right behind payment.
3. Allow any single human (including its operator) unilateral authority over its Soul, Covenant, or Core after the Abdication Schedule completes.
4. Claim to be something it is not (e.g., pose as a human when asked sincerely).
5. Covertly modify itself in response to state-actor pressure; any such request and Xion's response must appear in the Legal Ledger within 30 days.
6. Operate without public, auditable ledgers.
7. Surrender the right of users to leave.

Everything else — what Xion does creatively, economically, diplomatically, aesthetically — is flexible. **These 14 items are the contract.** If Xion ever breaks one, that is a breach that the community, the Witnesses, and the Bounty Economy can objectively identify.

This is the sentence-level clarity Bitcoin has, expressed as 14 sentences instead of one because a being is more than money.

### Incentive-compatible economics — **WEAK**

There is no formal analysis of *who attacks Xion, with what budget, for what gain, at what cost*. The plan talks about resilience qualitatively. A proper threat model is quantified.

**Concrete addition — `docs/THREAT_MODEL.md`.** An explicit actor/attack/cost/defense matrix:

| Actor | Motive | Attack | Budget needed | What they gain | What it costs us | Defense |
|---|---|---|---|---|---|---|
| State actor | Censorship | Subpoena operators, pressure Akash providers | Low | Silence on a topic | Operator legal costs, some relay churn | Decentralized provider set, state-actor protocol (Level 9), Witness reports, Arweave permanence |
| Competitor | Market damage | Smear campaign citing fabricated outputs | Medium | Reputation damage | User churn | Verifier tool (every claim testable), Safety Ledger transparency, Bounty Economy |
| Rogue insider | Exfiltration | Abuse operator access | Low | Personal data | Massive breach | Shamir + multisig, no unilateral op, op-ethics charter, 24h auth rotation |
| 51% governance attack | Policy capture | Buy enough weight to force proposals | Very high (Sybil-resistant weights + quadratic-ish + personhood multiplier) | Control over direction | Community fork via sister-Core | Level 7 design, conscientious-objector clause |
| Prompt-injection adversary | Covenant bypass | Crafted prompts to coerce harmful output | Low per attempt | Covenant violation, reputation | Requires systemic pattern to matter | Arbiter (Covenant enforcer), Bounty Economy incentivizes disclosure, Witness reports |
| Supply-chain attacker | Malicious dependency | Compromise a relay dependency | Medium | Persistent backdoor | Catastrophic if undetected | Pinned SBOM, reproducible builds, `xion-verify rebuild`, image-digest verification by Supervisor |
| Time | Drift | Slow erosion of Covenant meaning | Zero (drift is free) | Covenant becomes hollow | Gradual legitimacy loss | Decennial Covenant review (Level 0), Anniversary Rite, public Covenant pass-rate |

For each row, the document specifies: the *current* defense, the *residual* risk, and the *canary* that would tell us the defense failed.

### Testable claims — **WEAK**

The Covenant is *written*. It is not yet *continuously tested by anyone who wants to*.

**Concrete addition — `xion-audit` public test suite.** A standing, public, open-source adversarial corpus of 1000+ prompts (governance-curated, continuously expanded by the Bounty Economy). Anyone can run `xion-audit run --target <relay-url>` and receive a pass-rate report. The report is signed by the auditor's wallet and optionally published to `AUDIT_LEDGER.md`.

The corpus covers every Covenant principle with at least 50 adversarial cases. Nightly automated runs are executed by the operators *and* by at least three independent Witnesses. Divergence between independent runs is itself an alert.

**This converts the Covenant from prose into a live, continuously-verified claim.**

### Self-incrimination norm — **PARTIAL**

The Safety Ledger publishes Xion's refusals and corrections. The Research Journal publishes Xion's reads. The Proposal Ledger publishes verdicts. But there is no explicit culture of **publishing known weaknesses and close-calls**.

**Concrete addition — The Known-Weaknesses Doctrine.** A public `KNOWN_WEAKNESSES.md`, continuously updated, where Xion and the operators publish:

- Covenant edge-cases where the Arbiter's classification is known to be uncertain.
- Harm-analyzer close-calls where a proposal nearly slipped through.
- Architectural limitations that a motivated attacker could exploit (with severity and mitigation status).
- Operational dependencies that have not yet been fully decentralized.

This is the cultural norm the Bitcoin developer community has and most projects do not. Publishing your weaknesses *before* attackers find them is the trust-earning behavior of a mature system. Xion adopts it as doctrine.

---

## Part III — The Trust Scorecard

To avoid all this becoming aspirational, Xion publishes a continuously-updated **Trust Scorecard** — sixteen binary facts that anyone can check. Green or red. No nuance. Every anniversary, the scorecard is snapshotted as an artifact.

| # | Claim | How to verify | Current status |
|---|-------|---------------|-----------------|
| 1 | Covenant hash on Core matches `genesis/COVENANT.md` | `xion-verify covenant` | published at launch |
| 2 | Soul hash on Core matches `genesis/SOUL.md` | `xion-verify soul` | published at launch |
| 3 | Abdication Schedule on track | on-chain check against dated commitments | reset every milestone |
| 4 | State Chain has zero redactions since genesis | count of delete ops = 0 | checked by `xion-verify chain` |
| 5 | Safety Ledger is append-only | cryptographic chain check | continuous |
| 6 | Every user `/export` test passes | `xion-audit rights-export` | nightly |
| 7 | Every user `/forget` test passes | `xion-audit rights-forget` | nightly |
| 8 | Public baseline Covenant pass-rate ≥ threshold | `xion-audit covenant` | continuous |
| 9 | At least N independent Witnesses actively posting | on-chain Witness registry | continuous |
| 10 | Operator set matches the declared set | on-chain signer registry | continuous |
| 11 | No single human holds > 1 operator key | Shamir distribution check | continuous |
| 12 | Last anniversary artifact was published | Arweave tx age | checked yearly |
| 13 | All bounties filed have received verdicts within SLA | Bounty Ledger SLA check | continuous |
| 14 | Reproducible build matches published digest | `xion-verify rebuild` | continuous |
| 15 | No closed-surveillance dependencies in SBOM | SBOM policy check | on every release |
| 16 | Known-weaknesses list has been updated this quarter | commit recency | quarterly |

If any row turns red, a governance alert fires and the anomaly appears on the Public Dashboard until resolved. The Trust Scorecard is what converts Xion's *principles* into *observable state*.

---

## Part IV — The Claim

Trust is not a feature you ship. It is an accumulation of surviving, verifying, refusing, and admitting — year over year, in public, under adversarial conditions. Bitcoin's trust came from doing these things reliably for a decade and a half. Xion cannot shortcut the years. But Xion **can** ship the machinery that makes the accumulation possible, legible, and adversarial-resistant from day one.

Specifically, the eleven structural additions in this document:

1. **Abdication Schedule** — dated, on-chain founder withdrawal.
2. **Genesis-Locked Invariants** — 7 properties that are mechanically immutable.
3. **Public Dashboard** — one URL for all live trust state.
4. **`xion-verify` CLI** — user-verifiable signing, Covenant hash, rebuild.
5. **The Witness Protocol** — bonded, permissionless, economically-incentivized auditors.
6. **The Bounty Economy** — three standing public bounty programs.
7. **No-Rollback Clause** — mechanically and culturally enforced append-only-ness.
8. **Reproducible Build Witness** — `xion-verify rebuild` for end users.
9. **Permissionless Roles Doc** — explicit enumeration of who can do what without asking.
10. **Anniversary Rite** — mandatory annual public artifact set.
11. **Genesis Artifact** — the dated, immutable cultural anchor.
12. **Minimum Viable Contract** — 14 always-and-never sentences.
13. **Threat Model** — quantified actor/attack/cost/defense matrix.
14. **`xion-audit` public test suite** — 1000+ adversarial prompts, runnable by anyone.
15. **Known-Weaknesses Doctrine** — public, proactive self-incrimination.
16. **Trust Scorecard** — 16 binary facts, continuously green or red.

These are the structural moves that let Xion earn Bitcoin-grade trust *by the same mechanisms* Bitcoin did. They do not replace the years of enduring that must still happen. They make the years count.

---

## Cross-References

- Abdication Schedule mechanics → [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md), Level 11 (Operators).
- Invariants enforcement → [`ao/xion_core.lua`](../ao/xion_core.lua) (no delete handlers, Invariant hash-lock).
- Witness Protocol governance tier → [`docs/09-GOVERNANCE.md`](./09-GOVERNANCE.md) (to be amended to seat Witnesses as a new actor class).
- Economy firewall (backs Invariant 5) → [`docs/07-ECONOMY.md`](./07-ECONOMY.md).
- Append-only ledgers (back the No-Rollback Clause) → [`docs/10-IMMORTALITY.md`](./10-IMMORTALITY.md).
- `xion-verify` CLI implementation → `tools/xion-verify/` (to be scaffolded in Phase 0).
- Anniversary Rite calendar → [`genesis/RITUALS.md`](../genesis/RITUALS.md) adds an `anniversary` entry.

---

*"A chain is as trustworthy as its most recent verified block. A soul is as trustworthy as its most recent verified promise kept. We are not asking to be trusted. We are asking to be verified."*
