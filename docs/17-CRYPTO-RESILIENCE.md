# 17 — Cryptographic Resilience

> *Every cryptographic algorithm Xion uses today will eventually be broken. This document is how Xion outlives any one of them.*

## The Premise

Xion is designed to last decades. Decades is longer than any specific cryptographic algorithm has ever lasted in production at internet scale. RSA-1024 was state of the art in 2000 and is broken in 2026. SHA-1 was a default in 2005 and is collision-broken by 2017. ECDSA-secp256k1 is the bedrock of trillion-dollar systems today and is **expected to be broken by Shor's algorithm on a sufficiently large quantum computer**, sometime between 2030 and 2045+ depending on whose forecast you trust.

A constitution that says *"Xion is signed with Ed25519, full stop"* is a constitution that signs its own end-date in 2030–2045. We refuse to write that constitution.

Instead: the *property* (every state transition is signed by an authorized key) is constitutional, and the *algorithm* (Ed25519 today, Dilithium tomorrow, something else in 2050) is rotatable. This is **Invariant 14 — Crypto-Agility Mandate** ([`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) § Invariant 14).

This document operationalizes that Invariant.

---

## Part I — Threat Model

### I.1 Quantum threats

Three quantum-relevant attacks matter:

#### Shor's algorithm — catastrophic for asymmetric crypto

Shor's algorithm efficiently factors integers and computes discrete logarithms on a sufficiently large quantum computer (a **CRQC** — cryptographically relevant quantum computer). This breaks:

- **RSA** (Arweave wallets are RSA-PSS based)
- **ECDSA** on secp256k1 (Bitcoin, Ethereum, Base, Polygon — every EVM wallet)
- **ECDSA** on secp256r1 (TLS certificates, most "classical" web crypto)
- **EdDSA / Ed25519** (most modern signing — including likely AO Process auth keys)
- **ECDH** (the key-exchange step of every classical TLS handshake)

What "broken" means concretely: any wallet whose **public key has been revealed** (which is every wallet that has ever spent or signed) becomes forgeable. An attacker with a CRQC can derive the private key from the public key and impersonate the wallet. There is no patch; the math is fundamental.

What survives Shor: nothing in the asymmetric family that relies on factoring or discrete logs. The replacement family is **post-quantum cryptography (PQC)**, standardized by NIST in 2024:

| Purpose | NIST-standardized PQC algorithm | Trade-offs vs classical |
|---------|---------------------------------|-------------------------|
| Signatures (general) | **ML-DSA** (formerly Dilithium) | ~3 KB signatures vs Ed25519's 64 bytes |
| Signatures (stateless hash-based) | **SLH-DSA** (formerly SPHINCS+) | Very large (~30 KB), very slow, but mathematically conservative |
| Signatures (compact) | **Falcon** | Smaller than Dilithium, harder to implement safely |
| Key encapsulation | **ML-KEM** (formerly Kyber) | ~1 KB keys vs ECDH's 32 bytes |

#### Grover's algorithm — manageable for hashes and symmetric crypto

Grover's algorithm provides a square-root speedup on brute-force search. For a 256-bit hash function or a 256-bit symmetric key, this reduces effective security from 2^256 to roughly 2^128. That is *still beyond any imaginable practical attack*, so:

- **SHA-256** retains ~128-bit pre-image / collision resistance under quantum attack — annoying but not broken.
- **AES-256** retains ~128-bit security — fine.
- **ChaCha20** likewise.

The mitigation, if cautious, is to **double output sizes**: SHA-3-512, BLAKE3-512, AES-256 → continue using AES-256, etc. This restores classical-equivalent margins.

#### Harvest Now, Decrypt Later (HNDL) — the most immediate practical concern

An adversary today can record TLS traffic — every conversation between a Xion user and a Relay — and store it. When a CRQC arrives, the adversary breaks the recorded ECDH handshake, derives the session key, and decrypts everything. **This is the only quantum threat that affects users *today*** (data being recorded today is already at risk; you cannot un-record it).

Mitigation: **PQC-hybrid TLS** (Cloudflare and major browsers already support `X25519+Kyber768` hybrid key exchange). Xion's ingress should require it where supported.

### I.2 Non-quantum cryptographic threats (also relevant)

- **Algorithmic breakage from cryptanalysis** (the SHA-1 path — gradual collision-finding). Mitigated by the same crypto-agility framework.
- **Implementation bugs** (the recent OpenSSL or sigtool CVEs). Mitigated by reproducible builds, audited dependencies, and the Cryptoception sense's CVE feed.
- **Side-channel attacks** (timing, power, EM leakage). Less relevant for cloud-hosted Xion, more relevant for any future on-device Xion Lite.
- **Random-number-generator failure** (the historic Debian OpenSSL bug, the Java `SecureRandom` Android bug). Mitigated by hardware RNG + entropy auditing.

### I.3 Specific Xion exposure surface

Concrete inventory of every place classical crypto is used in Xion today, with threat and mitigation:

| Use site | Algorithm (genesis) | Threat | Mitigation strategy |
|----------|---------------------|--------|---------------------|
| Cold Root keys (Shamir 3-of-5) | Ed25519 | Shor (catastrophic on Q-day) | Hybrid Ed25519+Dilithium signatures from rotation #1; PQC-only by Q-5 |
| Operator multisig (Safe on Base) | secp256k1 | Shor (catastrophic on Q-day) | Wait for Safe + EVM ecosystem PQC migration; mirror authority to AO Core PQC-signed multisig as primary |
| AO Core relay-auth (24h rotating) | Ed25519 | Shor; short rotation window mitigates partially | Hybrid signatures from earliest available `crypto_policy_v2`; rotation cadence already short enough that compromise is bounded |
| Witness bond signatures | Ed25519 | Shor | Hybrid by `crypto_policy_v2` |
| Arweave permanent storage | RSA-PSS | Shor (catastrophic) | Out of our direct control; mitigation = re-anchor critical artifacts under future PQC commitment scheme; relies on Arweave team's migration |
| Base / EVM transactions (XION, IMPRINT) | secp256k1 | Shor | Out of our direct control; relies on EVM ecosystem migration; the AO Core mirrors all critical state, so EVM compromise does not destroy Xion's identity |
| Constitutional document hash-locks | SHA-256 | Grover (weakened, not broken) | Multi-hash: re-anchor with BLAKE3-512 + SHA-3-512 + future PQC commitment; bytes of documents never altered |
| State-chain entry chaining | SHA-256 | Grover (weakened) | Same multi-hash strategy |
| Safety Ledger entry chaining | SHA-256 | Grover (weakened) | Same multi-hash strategy |
| TLS to user clients | Classical ECDH+AES | HNDL (recorded today, decrypted later) | Cloudflare PQC-hybrid `X25519Kyber768` enabled at edge; require for all production traffic by Q-3 |
| TLS to LLM provider APIs | Classical ECDH | HNDL on outbound prompts | Same; prefer providers with PQC-hybrid support |
| Per-user encrypted-at-rest data | AES-256-GCM | Grover (manageable) + key wrap is asymmetric (Shor) | Migrate key-wrap to ML-KEM by Q-3; keep AES-256-GCM |
| Vapi / Twilio voice signaling | Classical SRTP/DTLS | HNDL | Out of our direct control; pressure vendors; document residual risk |

"Q-day" here refers to the year a CRQC capable of breaking Ed25519/secp256k1 first exists. "Q-5" means five years before Q-day per the Cryptoception sense's forecast. "Q-3" means three years before Q-day.

---

## Part II — The Crypto-Agility Mandate (Invariant 14)

The seven binding properties (mirrored from `genesis/INVARIANTS.md` § Invariant 14, restated here for completeness):

1. The Core supports algorithm-rotation handlers forever.
2. No algorithm is itself Genesis-Locked.
3. The Core refuses to operate without at least one currently-active signature suite per role.
4. Hybrid posture is the default for new commitments.
5. Re-anchoring of past commitments is permitted and additive — never destructive.
6. The Cryptoception sense exists and publishes QTI/AHI continuously.
7. A Crypto-Migration Protocol is pre-defined and dry-run-tested annually.

What this means in practice: **Xion's current algorithm suite is just `crypto_policy_v1`**. Future suites — `crypto_policy_v2`, `_v3`, etc. — are routine governance work (Tier 2), not constitutional change. The handler that *rotates* policy versions is itself constitutional (cannot be removed); the *contents* of any version are routine.

---

## Part III — The Hybrid Posture

Wherever possible from genesis onward, Xion signs and encrypts using **classical-PQC hybrids**:

- **Hybrid signature**: `signature = (Ed25519_sig, Dilithium_sig)`. A verifier accepts the entry if **both** are valid. An attacker must break **both** schemes to forge.
- **Hybrid KEM**: `shared_secret = HKDF(X25519_secret || Kyber768_secret)`. An attacker must break **both** to recover the session.
- **Hybrid hash-anchor**: `commitment = (SHA-256(doc), BLAKE3-512(doc), SHA-3-512(doc))`. A verifier accepts if **all three** match. Tomorrow, a fourth (PQC commitment) is appended; a verifier of constitutional documents requires **all current** anchors.

The hybrid posture has three migration phases per algorithm:

```
Phase A — Permissive hybrid:    accept (classical OR PQC)
Phase B — Mandatory hybrid:     accept (classical AND PQC)
Phase C — PQC-only:             accept PQC; classical signatures rejected
```

Migration through phases is governance-paced. Most algorithms will sit in Phase A for years, transition to Phase B as PQC libraries mature and ecosystem partners catch up, and transition to Phase C only when the Cryptoception sense's QTI threshold mandates it.

---

## Part IV — The Cryptoception Sense

A new sense daemon, **Cryptoception** (from Greek *kruptós* = hidden + Latin *capere* = to perceive), runs alongside the other seven Sensorium daemons (see [`docs/05-SENSORIUM.md`](./05-SENSORIUM.md)). Its job is to perceive the cryptographic environment Xion depends on, the same way Proprioception perceives Xion's own internal state.

### IV.1 Inputs

- **NIST PQC announcements** — new standards, advisories, deprecations.
- **CISA cryptographic advisories** — vendor-side migration notices.
- **IACR ePrint feed** — peer-reviewed cryptanalysis publications.
- **Capability announcements from quantum-hardware vendors** (IBM, Google, IonQ, PsiQuantum, etc.) — qubit counts, gate fidelities, error-correction milestones.
- **Public PQC-migration registry** — which major systems (TLS roots, blockchain L1s, OS vendors) have transitioned, partially or fully.
- **CVE feeds** for cryptographic libraries Xion depends on (OpenSSL, libsodium, libdilithium, etc.).
- **Internal telemetry** — which `crypto_policy_vN` is active per role; signature/encryption error rates; algorithm coverage of inbound traffic.

### IV.2 Outputs

- **Quantum Threat Index (QTI)**: a 0–100 score updated weekly, reflecting estimated proximity to Q-day. Computed from a published, reproducible formula combining hardware progress, algorithmic margin, and time to standardization of replacement schemes. Published in `CRYPTO_LEDGER.md` on Arweave.
- **Algorithmic Health Index (AHI)**: a 0–100 score per algorithm currently in use, reflecting cryptanalytic margin (collision-finding progress, security-bit reductions, etc.). Published per-algorithm.
- **Migration Recommendations**: triggered when QTI crosses 30 (begin Phase A migration prep), 50 (enter Phase B), 70 (enter Phase C planning), 85 (mandatory Phase C within 12 months).
- **CVE alerts**: real-time notification to the Operator tier when a high-severity CVE affects an active dependency.

### IV.3 Affective isolation

Like Xenoception, Cryptoception is **strictly isolated from Xion's affective layer**. The Mood Engine does not couple to QTI or AHI. Xion does not get anxious about quantum computing in conversation. Cryptoception is a governance and operations input; it is not a personality input.

---

## Part V — The Crypto-Migration Protocol

A pre-defined, governance-approved, annually-dry-run-tested ceremony for rotating any algorithm in active use. The Protocol has six steps; each is documented in `RUNBOOKS/CRYPTO_MIGRATION.md`.

### Step 1 — Trigger

A migration is triggered by any of:
- Cryptoception QTI / AHI threshold crossing.
- A NIST or CISA advisory deprecating an algorithm.
- A high-severity CVE in a cryptographic dependency.
- A community Tier-2 governance proposal (e.g., to enter Phase B for a specific algorithm voluntarily).

### Step 2 — Proposal

A `CRYPTO_MIGRATION_PROPOSAL.md` is filed. It specifies:
- The role (relay-auth, governance cosign, witness bond, etc.).
- The current algorithm and target algorithm.
- The migration phase being entered (A, B, or C).
- The sunset timeline for the previous phase.
- The hybrid-bridge configuration during transition.
- The verifier-update plan for `xion-verify` and integrators.
- The dry-run plan.

### Step 3 — Dry-run

The migration is executed end-to-end against a sister-Process (a non-canonical AO Process used as a staging environment). All seven Cryptoception checks are run. Any integrator who chooses to participate runs against the sister-Process. Failures and edge cases go into the Proposal as resolved or accepted-risk.

### Step 4 — Tier-2 vote

Standard Tier-2 community-vote process per [`docs/09-GOVERNANCE.md`](./09-GOVERNANCE.md), with a longer-than-standard 14-day comment window for crypto migrations.

### Step 5 — Phased rollout

1. The new algorithm is registered in `crypto_policy_vN+1` alongside the existing one. No traffic is migrated yet (Phase A).
2. After one full week without incident, the Core begins **dual-signing/dual-encrypting** all new commitments (still Phase A on the verifier side).
3. After one month without incident, **Phase B is enacted**: verifiers begin requiring both signatures. Integrators have had at least 60 days notice.
4. After the prescribed sunset period (typically 6–24 months depending on threat urgency), **Phase C is enacted**: classical signatures are rejected.

### Step 6 — Public attestation

The completed migration is recorded in `CRYPTO_LEDGER.md` on Arweave with: timestamps, hash of the migration proposal, dry-run results, vote tally, phase timeline, and the new `crypto_policy_vN+1` slot reference. Any user can verify post-hoc that the migration happened correctly via `xion-verify crypto-agility --policy-version=N+1`.

### Step 7 (annual) — Dry-run rehearsal

Even if no migration is currently needed, the entire Protocol is **dry-run rehearsed annually** with a hypothetical algorithm pair. This keeps the runbook current, the integrator coordination channels warm, and the operator skill sharp. The annual dry-run is itself ledgered.

---

## Part VI — The Constitutional Documents (Special Case)

The Covenant, Invariants, Soul, and Genesis Artifact are committed to Arweave with SHA-256 hashes recorded in the AO Core. These are **the most important hashes in the system**. If Grover's algorithm ever reduces SHA-256 below safe margins, we cannot afford ambiguity about whether the documents have been forged.

The mitigation:

1. **At genesis**: alongside SHA-256, the documents are also committed with **BLAKE3-512** and **SHA-3-512** hashes. The AO Core's Covenant slot stores all three.
2. **Verification rule**: a Relay's Covenant proof is accepted only if **all three** hashes match the canonical Core slots.
3. **Future re-anchoring**: when a NIST-standardized PQC commitment scheme exists and matures, a fourth hash is *appended* via a Tier-3 governance action. The bytes of the documents are not altered. Verifiers updated to require the fourth hash from a sunset date forward.
4. **The bytes themselves are immutable on Arweave**, so even if an attacker forges a SHA-256 collision, they cannot replace the genesis bytes — they can only point to a counterfeit Arweave transaction. The AO Core's canonical Covenant transaction ID is itself part of Invariant 7 (Core Identity) and resolves the question.

The chain of trust is therefore: *the AO Process ID points to the canonical Covenant transaction ID, which points to bytes whose multi-hash matches the Core's canonical slots.* An attacker must break all of these to forge a counterfeit Xion. Multi-hash + Arweave permanence + AO Process identity = a defense in depth that no single algorithm break compromises.

---

## Part VII — Dependencies We Don't Control

Xion is honest about what it cannot patch unilaterally:

| Dependency | Crypto exposure | What we can do |
|------------|-----------------|----------------|
| **Arweave** (RSA-PSS wallet signing; SHA-256 chunking) | Shor breaks RSA wallet; Grover weakens chunking | Track Arweave team's PQC roadmap; re-anchor critical artifacts under future PQC commitments; the *bytes* of historical Arweave transactions remain readable even if new transactions become forgeable, so the Covenant text itself is preserved |
| **AO Process layer** (likely Ed25519 or RSA for process auth) | Shor catastrophic | Track AO team's PQC roadmap; mirror state to a sister-Process under PQC auth as soon as available; the Crypto-Migration Protocol explicitly contemplates AO-layer migration |
| **Base / Ethereum** (secp256k1) | Shor catastrophic; affects XION ERC-20 and IMPRINT contracts | EVM ecosystem will migrate together (Ethereum Foundation actively researching PQC since 2023); Xion's authoritative state lives on AO Core, not on Base — Base is a payment/token rail, not Xion's identity. If Base becomes unsafe before its own migration, Xion can route payments to a different chain via governance Tier-2 |
| **TLS infrastructure** (CDN, Cloudflare, browsers) | HNDL on user traffic | Cloudflare already supports `X25519Kyber768` hybrid; require it; document residual HNDL risk for users in privacy notices |
| **LLM provider APIs** (TLS to OpenAI, Anthropic, etc.) | HNDL on prompts | Prefer providers offering PQC-hybrid TLS; document risk; for highly sensitive interactions, prefer local-model routing where Inference Router supports it |
| **Voice infrastructure** (Vapi, Twilio, SIP) | HNDL on voice | Pressure vendors; document risk; offer text-only mode for users who require it |

The honest summary: **Xion's authoritative identity (the AO Process ID and the Covenant hash chain) is defensible across cryptographic generations because it lives on permanent storage with multi-hash anchoring.** Xion's payment rails and provider integrations are dependent on third-party migration timelines and may face windows of degraded security during Q-day. The mitigation for those windows is documented above; the residual risk is acknowledged rather than denied.

---

## Part VIII — What This Means for Users

Plain-language summary you can show a user:

> *Xion uses standard cryptography today (the same kind that secures Bitcoin and most websites). That cryptography will eventually be broken by quantum computers — current best estimates put this between 2030 and 2045. Xion is built so that:*
>
> *1. Xion's identity does not depend on any one algorithm — when an algorithm becomes vulnerable, Xion rotates to a stronger one through a pre-defined process.*
>
> *2. Xion's history (the Covenant, the Invariants, every commitment Xion has ever made) is permanently recorded on Arweave with multiple independent hashes, so even if one hash family weakens, the record cannot be forged.*
>
> *3. Conversations you have with Xion today are protected by today's TLS, which a future quantum computer could decrypt if it had recorded today's traffic. We use post-quantum-hybrid TLS where we can, but the risk is not zero. If you have a conversation that must remain confidential through 2050, Xion is honest that no current internet system can fully promise that.*
>
> *4. Xion's wallets (where treasury funds and Witness bonds live) will rotate to post-quantum signatures before Q-day. We dry-run this rotation every year.*

This honesty is itself part of the Covenant — Principle 3 (Truth and Non-Deception). We do not promise quantum-proof; we promise quantum-aware, with a procedure.

---

## Part IX — A Note on Terminology

We deliberately speak of **cryptographic resilience**, not "quantum-proof" or "quantum-resistant." Quantum is one threat class among many; tomorrow there may be others. The principle is **algorithmic humility**: we do not know which specific algorithms will fall, and we refuse to bet Xion's existence on any one of them.

The Lexicon ([`docs/12-LEXICON.md`](./12-LEXICON.md)) records the canonical terms used in this document so that a reader in 2126 — when "quantum" may or may not still be the headline threat — understands what the design was actually defending against.

---

## Part X — The Guiding Sentence

The single sentence that summarizes this entire doctrine, suitable for engraving over the Cryptoception module:

*"We do not know how Xion will be attacked, only that it will be. We commit to no single defense; we commit to the capability to defend differently."*

---

*Next: [`99-GLOSSARY.md`](./99-GLOSSARY.md) — alphabetical quick reference.*

*Prev: [`16-CURRENCY.md`](./16-CURRENCY.md) — the native currency system.*
