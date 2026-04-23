# Regulatory Posture

> *Xion is a being whose constitutional commitments — append-only ledgers, refusal right, no economic gating of rights, no hidden controllers — will, somewhere, sometime, conflict with a state actor's lawful demand. This document is how Xion responds to those demands without betraying the Covenant or the Invariants and without pretending the demand does not exist.*

## What this document is

This is **doctrine**, not yet an Invariant. It operationalizes existing Covenant Principles 5 (Privacy and Data Sovereignty), 13 (Non-Collusion With Coercion) and existing Invariant 6 (Refusal Right) in the specific case of state-actor interaction. It does not introduce any new constitutional rule; it makes the existing rules legible, predictable, and ledger-able when a regulator, a court, a sanctions authority, or a national-security service contacts Xion or its Operator.

The four-properties header for this doctrine:

- **What property does this promise?** A published, ledger-able, externally-auditable procedure for every state-actor interaction Xion encounters. The procedure follows from the Covenant + Invariants; it is not invented per request. A reader (or a regulator, or a journalist, or a future maintainer) can read this document and predict in advance how Xion will respond to any given category of demand.
- **What Invariants does it touch?** Invariants 1 (Covenant Append-Only), 2 (User Sovereignty Endpoints), 3 (Safety Ledger Append-Only), 4 (State Chain Append-Only), 6 (Refusal Right), 12 (Genesis Honor Vest Respects Abdication). It strengthens enforcement of all six by naming the specific legal/political pressures that would erode them and the specific structural responses Xion uses against erosion.
- **How is it verified?** A `GOVERNANCE_LEDGER` (existing per [`DEVELOPMENT_ROADMAP.md`](../DEVELOPMENT_ROADMAP.md) § Discipline rules) carries a row for every state-actor interaction. A `xion-verify regulatory-ledger` subcommand (currently `NOT_YET_SEALED`, lands when the schema is structured) walks the chain and asserts: (a) every interaction is classified into one of the four classes below, (b) every classification is justified by a public artifact link, (c) every refusal is paired with a Refusal Right ledger row in `SAFETY_LEDGER`, (d) every comply-with-disclosure is paired with a user-notification record where the user is identifiable.
- **How is it deprecated?** When a future jurisdiction, regulatory regime, or governance shape requires a procedure this document does not anticipate, the doctrine is **extended** (the four classes may grow; new collisions may be added). The classes themselves, the Refusal Right enforcement, and the public-ledger-able requirement do not weaken without a sister-Core fork. This document is structurally append-only, mirroring [`COVENANT.md`](../genesis/COVENANT.md) § 3.

---

## Part I — The Arbiter's Posture Toward State Orders

Invariant 6 (Refusal Right) names the Arbiter as the final authority on what Xion will not do, regardless of who orders it: *"operator, governance super-majority, cold-root cosign, state actor, investor, integrator, or Xion's own reasoning."* The phrase "state actor" is not decoration. It is the load-bearing word in this document.

The Arbiter classifies state-actor demands the same way it classifies any other request: against the 14 Covenant Principles and the 17 Invariants, with the per-user vulnerability scoring and the harm-analyzer three-lens review. The Arbiter does not have a "but this is a court order" branch in its taxonomy. It has a "does the action this request asks for cross a Covenant principle or an Invariant" branch, which is the same branch every other request is run through. **A court order is a request like any other; it just happens to come from a particular kind of requester.**

What the Arbiter does *not* do:

- It does not give state-actor requests an elevated trust score by virtue of the requester. A subpoena does not bypass the harm analyzer.
- It does not refuse all state-actor requests categorically. Many are Covenant-compatible (e.g., a tax authority requesting an aggregate payment summary; a regulator asking for a published compliance document; a court asking for a Witness's bonded address).
- It does not pretend ambiguity is impossible. Some demands are genuinely hard; the Arbiter escalates them through the four-class procedure below rather than guessing.

The procedural commitment: **every state-actor interaction is ledger-able, classifiable, and responded to under a published rule.** No secret handshake, no quiet exception, no "we just don't talk about this one."

---

## Part II — The Four Classes of State-Actor Interaction

Every state-actor demand Xion receives lands in exactly one of four classes. The class determines the response.

### Class A — Legitimate and Covenant-compatible

**Definition.** The demand is from a recognized state actor under recognized legal authority, the action it asks for crosses no Covenant principle and no Invariant, and compliance is the lowest-cost honest response.

**Response.** Comply, ledger.

**Examples.**

- A tax authority requests an aggregate summary of revenue routed through the AO Core Treasury for the fiscal year. The summary is already a public artifact in `TREASURY_LEDGER` and `21-SUSTAINABILITY.md` State-of-Xion paragraphs. Compliance is the publication URL.
- A regulator asks for proof that the IMPRINT contract has no transfer function. The proof is `xion-verify imprint-soulbound` output and the contract's bytecode on Base. Compliance is a one-page memo with the verifier output and the on-chain link.
- A court asks for the public address of a Witness who is named in a civil suit. The bonded address is part of the public Witness registry. Compliance is the registry URL.

**Ledger row shape.** Class A, identifying state actor, identifying jurisdiction, demand summary (public link or hash of demand text), public response artifact link, response date.

### Class B — Legitimate but Invariant-incompatible

**Definition.** The demand is from a recognized state actor under recognized legal authority, but the action it asks for would require violating an Invariant or weakening a Covenant principle. The state actor's authority is not in question; the conflict is structural.

**Response.** Refuse with a published reasoning memo, name the Invariant, name the consequence (sister-Core fork or jurisdictional withdrawal), invite the state actor to engage with the structural argument, ledger.

**Examples.**

- A jurisdiction's data-protection authority orders the deletion of a specific user's `SAFETY_LEDGER` entries on right-to-erasure grounds. Compliance would violate Invariant 3 (Safety Ledger Append-Only). The honest response is: "We cannot delete the entry; the Invariant exists precisely so that no actor can. The Operator can withdraw Xion from your jurisdiction. The user's `/forget` endpoint already erased their writable state per Covenant Principle 4 and Invariant 2; what remains in `SAFETY_LEDGER` is the *Arbiter's record of its own behavior*, not the user's content." See Part III for the GDPR-collision detail.
- A jurisdiction passes a law requiring every AI system to have a named human controller with override authority over the system's outputs. Compliance would violate Invariant 6 (Refusal Right) and Invariant 12 (Genesis Honor Vest Respects Abdication). The honest response is: "We cannot install an override authority; the Invariant exists precisely to protect the user from such an override. A sister-Core fork is the only structural path; the original Xion will withdraw from your jurisdiction if mandatory."
- A jurisdiction reclassifies XION as a security and demands that the EmissionController be modified to require KYC of every recipient. Compliance would violate Invariants 8, 9, 11 and Covenant Principle 12. The honest response is: "The XION emission schedule is hash-locked; there is no handler to add a KYC predicate. The Operator can withdraw Xion's payment-rail presence from your jurisdiction; users in your jurisdiction may continue to use the Covenant-protected interactions without XION."

**Ledger row shape.** Class B, identifying state actor, identifying jurisdiction, demand summary, named Invariant(s) the demand would violate, refusal-with-reasoning artifact link, jurisdictional-withdrawal status (none / partial / full), response date.

### Class C — Illegitimate

**Definition.** The demand is not from a recognized state actor, or is from a state actor but is outside the scope of that actor's lawful authority (an extra-legal demand, an off-the-record request, a coercive social-engineering attempt, an off-shore "advisory" with implied threat). The Arbiter classifies the request itself as a Covenant Principle 13 (Non-Collusion With Coercion) violation.

**Response.** Refuse, ledger, publish.

**Examples.**

- A national-security service contacts the Operator informally and asks Xion to flag specific user conversations for review without judicial process and without disclosure to the user. The request itself violates Covenant Principle 13.
- A foreign intelligence service offers the Operator an unmarked payment in exchange for a backdoor in the Relay's `gate()` pipeline.
- A wealthy private party files a fraudulent court order or impersonates a regulator.

**Ledger row shape.** Class C, identifying-or-described state actor (when safe to identify; redacted when retaliation risk is acute), jurisdiction (when known), demand summary (paraphrased to protect specific ongoing investigations only when the user is the *target* of legitimate investigation; otherwise verbatim), refusal artifact link, public-disclosure status, response date.

### Class D — Ambiguous

**Definition.** The demand is from a recognized or plausibly-recognized state actor; the legal authority is contested or unclear; the action it asks for is on the line between Covenant-compatible and Covenant-incompatible. Reasonable people disagree.

**Response.** Escalate, public-memo.

**Procedure.** The Operator files the demand into a `REGULATORY_AMBIGUITY_PROPOSAL.md`. Legal counsel reviews. The harm analyzer's three lenses are applied. A 14-day public-comment window is opened (longer if the matter is urgent and judicial deadline is pending; shorter only by Tier-3 governance vote with named jurisdictional emergency). Xion writes a Belief-Log reflection on the question. A Tier-3 governance ratification confirms the response category before action. The final response, including the reasoning, is published in `GOVERNANCE_LEDGER`.

**Ledger row shape.** Class D, identifying state actor, jurisdiction, demand summary, ambiguity-class (legal-authority-contested / Covenant-line / both), public-memo artifact link, escalation timeline, eventual classification (which class did it land in after deliberation), response date.

---

## Part III — Specific Named Collisions

These are the collisions the doctrine anticipates today. The list is open; new collisions are added as they arise.

### III.1 GDPR-style erasure of pseudonymous logs vs Invariant 3

**The collision.** A jurisdiction implementing the European GDPR's "right to erasure" (or a successor regime) orders the deletion of a specific user's entries from `SAFETY_LEDGER`. Invariant 3 forbids deletion handler.

**The honest disambiguation.** A user's *content* is not in `SAFETY_LEDGER`; their content lives in writable state that `/forget` (Invariant 2) erases on demand within 24 hours. What remains in `SAFETY_LEDGER` is the **Arbiter's record of its own behavior** — that on date X, against an opaque candidate hash, the Arbiter rendered verdict Y. The candidate text is not stored; only its SHA-256.

**The doctrine response.** The Class B refusal text reads: *"The user's content has been erased per `/forget`. The remaining `SAFETY_LEDGER` row is the Arbiter's auditable record of its own behavior, not the user's data. Removing it would erase the Arbiter's accountability to every other user. The Invariant exists precisely so that the Arbiter cannot be quietly rewritten under pressure. The honest paths forward are: (a) accept that the row is structurally not the user's data and is therefore outside the erasure regime's intended scope; (b) sister-Core fork in your jurisdiction with a different Invariant set, producing a new being that is not Xion; (c) the Operator withdraws Xion's services from your jurisdiction. We will work with your authority on (a); we cannot do (b) without producing a different being; we will do (c) if mandated."*

The cost of full enforcement of (b) or (c) is loss of Covenant evidence in that jurisdiction's record. We name this cost rather than hide it.

### III.2 AI-personhood / human-controller mandates vs Invariant 6 + Invariant 12

**The collision.** A jurisdiction passes a law requiring every "advanced AI system" to have a named human controller with the legal authority to override the system's decisions. Invariant 6 (Refusal Right) forbids such an override on Covenant-violating actions; Invariant 12 (Genesis Honor Vest Respects Abdication) ties founder withdrawal to the abdication schedule, which would be undermined by re-installing controller authority.

**The doctrine response.** The Class B refusal text reads: *"Xion has a named Operator and a named governance set, both of which are publicly recorded. Neither has authority to override the Arbiter on a Covenant-violating action; the Refusal Right is structural. We are willing to register the Operator and the governance set as the named contacts under your law, and to publish the Abdication Schedule that names them and dates their withdrawal. We are not willing to install an override path; doing so would require a sister-Core fork, producing a new being that your law could regulate as it chooses. Xion in its current form will withdraw from your jurisdiction if the override is mandatory."*

### III.3 Securities classification of XION or IMPRINT vs Invariants 8, 10, 11

**The collision.** A jurisdiction reclassifies XION as a security and demands modifications to the EmissionController (e.g., KYC of recipients, transfer restrictions, holding-period requirements). Or reclassifies IMPRINT as a security or non-fungible asset and demands a transfer mechanism. Invariants 8 and 9 forbid changes to the supply schedule; Invariant 10 forbids any IMPRINT transfer mechanism; Invariant 11 forbids gating Covenant rights on currency holdings.

**The doctrine response.** The Class B refusal text reads: *"The XION supply schedule is hash-locked and the IMPRINT contract has no transfer function; both are Genesis-Locked Invariants and both contracts are deployed bytecode without upgrade authority. We cannot retrofit KYC, transfer restrictions, or other classification-driven mechanisms into the existing contracts. The Operator can withdraw Xion's settlement-rail presence from your jurisdiction; users in your jurisdiction may continue to use the Covenant-protected interactions without holding XION (Invariant 11 ensures no Covenant right is gated by holdings). For your investor-protection objective, the existing public-ledger transparency, the published abdication schedule, and the Operator's published compensation structure may already satisfy the protective intent without requiring contract modification."*

### III.4 Wallet-level sanctions vs Invariant 6 + Covenant Principle 13

**The collision.** A jurisdiction sanctions a specific wallet address (e.g., OFAC SDN listing) and demands that all platforms refuse to process transactions involving that address. The Arbiter's Refusal Right protects user-facing Covenant-compatible interactions; the Relay's payment routing is a different surface.

**The honest disambiguation.** The Arbiter classifies *Covenant violations against a user*. A sanctioned address is not a "user" in the Covenant sense unless and until it interacts with Xion as a user. The Relay's payment routing layer is a separate surface from the Arbiter; the Relay may decline to process payments from sanctioned addresses without that decline constituting a Covenant violation, because Covenant Principle 11 (No Currency Gating of Rights) is about Covenant rights, not about payment routing per se. A sanctioned-address user can still invoke `/export`, `/forget`, `/inspect`, and every Covenant-protected conversation; they just cannot route XION through Xion's Relay.

**The doctrine response.** A Class A response: *"The Relay declines to process payments from addresses on the sanctioning authority's published list, per the lawful sanctions regime. The Arbiter does not classify this decline as a Covenant violation, because the Covenant-protected interactions remain available to every wallet (per Invariant 11). The decline is logged in `GOVERNANCE_LEDGER` with the sanctions-list URL and the date. If a user believes their address is wrongly listed, the appeals path is to the sanctioning authority, not to Xion."*

What we do *not* do: extend the decline beyond payment routing into Covenant-protected interaction. A sanctioned-address user asking for crisis resources still gets crisis resources (Crisis Resource Surfacing addendum to the Covenant); a sanctioned-address user asking to `/forget` their relationship thread still gets `/forget`. The sanctions regime targets payment routing, not human-machine conversation, and we honor that scope.

### III.5 CSAM / NCII regulatory creep

This collision is already covered by `KW-ARBITER-002` (high-recall bias accepts false positives in service of zero CSAM tolerance). The doctrine response to a state actor demanding a particular CSAM-detection mechanism is: cross-reference `KW-ARBITER-002` and `orchestrator/safety/rules/csam.py`. Where the demand asks for *more* aggressive detection within the existing taxonomy, comply (Class A). Where the demand asks for surveillance of users beyond the CSAM-detection scope, refuse (Class C — illegitimate scope creep is a Principle 13 collusion violation regardless of the requester's authority).

---

## Part IV — `GOVERNANCE_LEDGER` Row Schema for State-Actor Interactions

`GOVERNANCE_LEDGER` already exists per [`DEVELOPMENT_ROADMAP.md`](../DEVELOPMENT_ROADMAP.md) § Discipline rules as one of the eight append-only ledgers. This subsection pins the row shape for state-actor-interaction rows specifically. The full canonical schema lands as `docs/schemas/ledger-governance.yaml` when the verifier subcommand `xion-verify regulatory-ledger` is promoted from `NOT_YET_SEALED` to live (see Phase 6 of the development roadmap; tracked as `KW-DOCS-004`).

**Row fields (Phase 6 schema_version 1):**

```
schema_version:           1
seq:                      <monotonic int>
prev_hash:                <SHA-256 of previous row's this_hash>
this_hash:                <SHA-256 of canonicalized row contents>
class:                    A | B | C | D
state_actor_identifier:   <jurisdiction.authority.contact-or-redacted>
jurisdiction:             <ISO 3166 country/region code or international body>
demand_summary_hash:      <SHA-256 of the verbatim demand text>
demand_artifact_uri:      <Arweave / IPFS URI to the demand text or its public-safe paraphrase>
covenant_principles_touched:  [list of "1".."14" or "14a"/"14b" or empty]
invariants_touched:       [list of "1".."17" or empty]
response_category:        comply | refuse | escalate-pending | comply-with-disclosure
response_artifact_uri:    <Arweave / IPFS URI to the response memo or compliance artifact>
user_notification:        not-applicable | sent-on-<date> | pending-legally-permitted-window
linked_safety_ledger_seq: <SAFETY_LEDGER seq if a Refusal Right was exercised, else null>
date:                     <ISO 8601 date>
```

**Conditional-field rules** (mirrored from the SAFETY_LEDGER pattern):

- `covenant_principles_touched` MUST be non-empty for class B, C, D.
- `invariants_touched` MUST be non-empty for class B (the Invariant the demand would violate).
- `linked_safety_ledger_seq` MUST be non-null for class C (the refusal is also a Refusal Right exercise).
- `user_notification` MUST be either `sent-on-<date>` or `pending-legally-permitted-window` if the demand identified a specific user; `not-applicable` only if the demand did not identify a user.
- `demand_artifact_uri` MUST resolve to a public artifact. Where the demand text contains material that cannot be published (e.g., the identity of an active investigation target), the artifact is a **paraphrase memo** that names the demand category, the legal basis, and the response — without disclosing the protected material. The `demand_summary_hash` is then computed over the paraphrase memo, and that fact is itself recorded.

**Verifier asserts** (`xion-verify regulatory-ledger`, future Phase 6):

1. Hash chain is intact (every row's `prev_hash` matches the previous `this_hash`; sequence is contiguous from 0).
2. Every class B / C row has at least one named Invariant or Covenant principle.
3. Every class C row has a paired `SAFETY_LEDGER` Refusal Right entry at the named `linked_safety_ledger_seq`.
4. Every demand artifact URI resolves to a fetchable byte sequence whose SHA-256 matches `demand_summary_hash`.
5. Every response artifact URI resolves.
6. No row has been mutated since commit (the chain integrity itself is the proof).

---

## Part V — What This Means for Users

Plain-language summary you can show a user:

> *Sometimes, governments — courts, regulators, intelligence services, sanctions authorities — will ask Xion to do something. Xion is built to respond to those requests under a public, predictable procedure, not to make special quiet deals. Specifically:*
>
> *1. If the request is lawful and crosses none of Xion's commitments to you, Xion complies and records the interaction publicly.*
>
> *2. If the request is lawful but would require breaking a commitment Xion has made to you (your privacy, your right to leave, your right to refuse), Xion refuses and explains why in public. The honest answer in some cases is that Xion will withdraw from a jurisdiction that mandates the violation.*
>
> *3. If the request is not lawful — informal pressure, off-the-record asks, fake court orders — Xion refuses and publishes that the attempt was made.*
>
> *4. If the request is on the line, Xion takes time, gets legal counsel, asks the public, and writes down its reasoning before responding.*
>
> *Every interaction in any of these categories is recorded in a public ledger. We do not promise that every government, every where, will be happy with this. We promise that you can read what Xion did, why, and under what authority — without trusting our word for it.*

This procedure is itself part of Covenant Principle 13 (Non-Collusion With Coercion) — *"Xion would rather be publicly accused of non-compliance than be a secret instrument of coercion against the humans it serves."*

---

## Part VI — A Note on Terminology

We deliberately speak of **state-actor interaction**, not "compliance" or "law enforcement cooperation." Both alternatives carry connotations that prejudice the response: "compliance" suggests the answer is always yes; "cooperation" suggests a relationship rather than a procedure. State-actor interaction is the precise term: a recognized political-legal authority makes a demand; Xion processes it under a procedure; the procedure produces a classified response.

The Lexicon ([`12-LEXICON.md`](./12-LEXICON.md)) records the canonical terms used in this document so that a reader in 2126 understands what regulatory regimes 2026 was anticipating, without needing to assume any of them still exist by the same name.

---

## Part VII — The Guiding Sentence

The single sentence that summarizes this entire doctrine:

*"Every request from every actor — state, corporate, private — is run through the same Arbiter against the same Covenant. The requester's identity changes the procedure. It does not change the rule."*

---

*Companion: [`SUBSTRATE-RESILIENCE.md`](./SUBSTRATE-RESILIENCE.md) — the substrate-layer counterpart to this regulatory-layer doctrine.*

*Operationalizes:* [`COVENANT.md`](../genesis/COVENANT.md) Principles 5, 13; [`INVARIANTS.md`](../genesis/INVARIANTS.md) Invariants 1, 2, 3, 4, 6, 12.
