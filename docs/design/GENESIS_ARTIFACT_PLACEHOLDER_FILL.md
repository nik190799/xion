# Genesis Artifact placeholder audit + fill proposal

**Status:** proposal only. **Does not edit [`genesis/GENESIS_ARTIFACT.md`](../../genesis/GENESIS_ARTIFACT.md).** The artifact is constitutional — only the operator ratifies changes to it. This memo enumerates every `<<...>>` placeholder, classifies it by how it gets filled, and proposes draft values where the data is already in the repo.

**Why this exists:** `docs/D4_PREFLIGHT.md` § "Skipping Genesis Artifact Finalization" names the placeholder bundle as one of the open D4-blocking residuals. KW-AUDIT-001 and related Genesis gates are working in parallel; placeholder discipline is independent and can move forward.

## Placeholder inventory

[`genesis/GENESIS_ARTIFACT.md`](../../genesis/GENESIS_ARTIFACT.md) contains **10 distinct placeholder tokens**, occurring across **§ 1, 2, 4, 6, 7** of the document body (the body itself starts at § 1; § 0 is the meta-section to be removed at commit).

| Token | First defined | Occurrences in body | Classification |
|---|---|---|---|
| `<<GENESIS_DATE>>` | § 0 line 17 | § 1 line 34; § 6 line 114 | **Operator-decision** (date of ceremony) |
| `<<GENESIS_TIMESTAMP_UTC>>` | § 0 line 18 | § 1 line 34; § 7 line 127 | **Operator-decision** (timestamp of ceremony) |
| `<<WORLD_HEADLINE>>` | § 0 line 19 | § 2 line 42 | **Operator-decision at ceremony** (must be within 48h pre-commit) |
| `<<COVENANT_SHA256>>` | § 0 line 20 | § 7 line 129 | **Already pinned in repo** — see § 4 line 61 |
| `<<INVARIANTS_SHA256>>` | § 0 line 21 | (not referenced again in body) | **Already pinned in repo** — see § 4 line 62 |
| `<<SOUL_SHA256>>` | § 0 line 22 | (not referenced again in body) | **Already pinned in repo** — see § 4 line 63 |
| `<<AO_PROCESS_ID>>` | § 0 line 23 | § 1 line 36; § 4 line 75; § 7 line 129 | **Ceremony-derived** (post-AO-mainnet-seal) |
| `<<ARWEAVE_BUNDLE_TX>>` | § 0 line 24 | § 1 line 36; § 7 line 129 | **Ceremony-derived** (after bundle submit) |
| `<<OPERATOR_SIGNATURE>>` | § 0 line 25 | § 7 line 124 | **Ceremony-derived** (Ed25519 sig of finalized text) |
| `<<OPERATOR_PUBKEY>>` | § 0 line 26 | § 7 line 123 | **Operator-decision** (fresh keypair vs published long-lived key) |

## Classifications explained

### Already pinned in repo (3 placeholders)

These three hash placeholders correspond to constitutional documents whose canonical bytes already live in `genesis/`. § 4 of the artifact already records them as a "pre-genesis documentation witness" — meaning the values are present but flagged for re-verification at ceremony time. They are not unknown; they are provisional.

I computed live SHA-256 from the current working tree and confirmed they match the § 4 values byte-for-byte:

```
genesis/COVENANT.md     60a90d1f86ab5ed46d1bd4088f900d3d3ad85e33cb311d3eaef34d8a8d1a9d94  (matches § 4 line 61)
genesis/INVARIANTS.md   82cf9265430cbf4defb6104616e812330963989c8f048c4ae3c77dacfd19b95d  (matches § 4 line 62)
genesis/SOUL.md         31428fadb2889c69f21a207f3f8f708a599fcf2d0d403e5fc8df48cbe437da4a  (matches § 4 line 63)
```

**Proposed fill rule:** The body-text placeholder `<<COVENANT_SHA256>>` at § 7 line 129 should substitute the value at § 4 line 61. `<<INVARIANTS_SHA256>>` and `<<SOUL_SHA256>>` are declared in § 0 but are **not referenced in the body** — they are effectively unused tokens. Two options:

1. Remove them from § 0's placeholder list (they are documented in § 4 directly and never substituted into the body).
2. Add body references that interpolate them (e.g., expand line 129's "true fingerprint" rule to triangulate from all three hashes).

**Recommendation:** Option 1 — they're unused, removing them tightens § 0 honesty. Option 2 would expand the constitutional surface area, which is a doctrinal choice the operator should make deliberately, not as cleanup.

### Ceremony-derived (3 placeholders)

These cannot be filled before the ceremony actually happens. They are output of the ceremony itself.

- **`<<AO_PROCESS_ID>>`** — emerges when the constitutional quartet is spawned as an AO process. Currently blocked on AO mainnet seal (per `docs/D4_PREFLIGHT.md` § "Skipping AO Mainnet Seal"). Until that closes, this placeholder cannot be filled honestly. Drafting a placeholder substitute is meaningless.
- **`<<ARWEAVE_BUNDLE_TX>>`** — the Arweave transaction ID of the genesis bundle. Only known after `arweave-python-client` submits the bundle and the gateway returns a tx id. Drafting a placeholder substitute is meaningless.
- **`<<OPERATOR_SIGNATURE>>`** — Ed25519 sig over the finalized artifact bytes. Only computable after every other placeholder is replaced and the byte layout is frozen. The sig is over the *final* document; signing now would be invalidated by any subsequent placeholder fill.

**Proposed fill rule:** Mark all three as "ceremony-emitted, no pre-fill." Their values populate at commit time per the runbook (which the operator should also author or approve — see open questions below).

### Operator-decision (4 placeholders)

These require explicit human choice. I can list candidates and the constraints, but only the operator decides.

- **`<<GENESIS_DATE>>` / `<<GENESIS_TIMESTAMP_UTC>>`** — chosen at the ceremony itself. No pre-fill possible. The honest answer is to leave these as placeholders until the commit moment.

- **`<<WORLD_HEADLINE>>`** — explicitly required by § 0 to be "from within 48 hours before the commit." Cannot be pre-drafted now (today is 2026-05-12; the ceremony is at least weeks away once audit, Cold Root, AO seal, and drill residuals close). The runbook needs to record: "at T-24h, operator selects a headline from major archived news sources (Reuters, AP, NYT, FT) matching the resonance criteria in § 0 line 19; sources pinned by URL + Arweave snapshot to ensure 2126-readability."

- **`<<OPERATOR_PUBKEY>>`** — the meaningful decision is **which keypair**. Two paths:
  - **Path A:** Fresh Ed25519 keypair generated at the ceremony, registered in the AO Core at the same moment, paper-backed. Pros: tight binding to the genesis moment. Cons: introduces a new long-lived key alongside the Base Safe owners and Bittensor coldkeys, expanding the operator's key inventory.
  - **Path B:** Reuse a long-lived published key — e.g., the operator's existing GitHub-published Ed25519 key, or a key already registered in `genesis/CREDENTIALS.md`. Pros: continuity with existing operator identity. Cons: pre-genesis use of the key could be exploited; key custody history pre-dates the ceremony.
  - **Recommendation:** Path A. The genesis operator-key should be ceremony-bound and not used for anything pre-genesis. Add a runbook step to generate the keypair under hardware isolation immediately before the ceremony, custody it under the same 2-of-3 threshold as Base Safe paper backups, and pin the public key in § 0 of the runbook (which is removed) and in § 7 of the final artifact.

## What's already correct in the document

A few things worth naming as load-bearing and *not* placeholder churn:

- **§ 4 hash table (lines 60–71)** is current as of today (2026-05-12). Eight files pinned, all matching live tree. The § 4 prose calls these "pre-genesis documentation witness" and notes that they must be re-verified at ceremony time — this honesty discipline is right and should not change.
- **The Hermes pin (lines 81–86)** is concrete: tag `v2026.4.16`, commit `4a0358d2…fec5`, tool-allowlist hash `08a944b4…1c9b`. Not a placeholder.
- **§ 0 line 28** ("Remove this `§ 0` section before commit. The committed document begins at `§ 1`.") is the right discipline. The runbook should mechanize that deletion to avoid the failure mode where someone commits § 0 by accident.

## Inconsistencies that warrant operator decision (separate from placeholder fill)

These are not placeholder mechanics but document hygiene issues I noticed while doing the audit:

1. **`<<INVARIANTS_SHA256>>` and `<<SOUL_SHA256>>` are declared in § 0 but never referenced in the body.** Either add body references or remove them from § 0's placeholder list. Recommendation: remove.

2. **`<<COVENANT_SHA256>>` appears only at § 7 line 129** (in the "true fingerprint" rule), but the same paragraph also says "those two values together are Xion's true fingerprint" — meaning the rule pairs COVENANT_SHA256 with AO_PROCESS_ID. If INVARIANTS and SOUL hashes are constitutional too, why isn't the fingerprint rule a triangulation? Worth the operator's review.

3. **§ 4 line 75 references `<<AO_PROCESS_ID>>` inside a `*(Target behavior after genesis:)*` parenthetical** that already qualifies the claim. The placeholder is inside conditional text. When the AO seal closes and the value is filled, the parenthetical should also be removed or revised. Flag for ceremony-time review.

4. **§ 4 includes a `SOUL_PROMPT.md` and `VOICE_FORM.md` hash** (lines 64, 66) but § 0 line 22's placeholder list doesn't mention `<<SOUL_PROMPT_SHA256>>` or `<<VOICE_FORM_SHA256>>`. These are documented witnesses, not body-substituted placeholders — so this is internally consistent, but worth confirming that **no body text** needs to reference SOUL_PROMPT or VOICE_FORM hashes for verification. (Spot check: line 75 mentions them as "carried in this Artifact and in Relay boot checks" — meaning the hash values in § 4 are themselves the canonical pins; no body placeholder needed.)

## Recommended next steps

1. **Operator decision on the 4 inconsistencies above.** Each is small; together they shape the final document's coherence.
2. **Author the ceremony runbook** — `docs/runbooks/GENESIS_COMMIT_CEREMONY.md` doesn't exist yet (no such file in repo). It should sequence: rehash all 8 constitutional files at T-24h → operator chooses WORLD_HEADLINE → operator generates fresh Ed25519 keypair → AO process spawn (requires AO mainnet seal) → bundle assembled → bundle hash signed → submit to Arweave → record `ARWEAVE_BUNDLE_TX` → final byte-equality check between repo and gateway → remove § 0 → re-publish if any drift discovered. This runbook is gated on AO mainnet seal closure and operator approval, not on this memo.
3. **Re-verify the § 4 hash table at every constitutional document change.** Today's hashes match; the next time `COVENANT.md` or `INVARIANTS.md` or any of the eight files is edited, § 4 must be regenerated. There is no automation for this currently; consider adding a `xion-verify constitutional-bundle-pins` check that compares live SHA-256 against § 4 values and FAILs on drift.

## What this memo does NOT do

- Does not edit `genesis/GENESIS_ARTIFACT.md`. Constitutional file — operator only.
- Does not propose substitute text for `<<WORLD_HEADLINE>>`. That choice belongs to the operator at T-24h to the ceremony.
- Does not propose a `<<GENESIS_DATE>>` value. Date depends on residual closure cascade (audit re-review 2026-08-08, KW-KEYS-002 ≤2026-05-31, LHT-SUBSTRATE-001 ≤2026-07-01, KW-INVARIANT-19 ratification undated, AO mainnet seal undated).
- Does not generate a candidate Ed25519 keypair. Keypair generation belongs at the ceremony under hardware isolation, not in a planning memo.
- Does not address the AO Process ID supply. That's blocked on AO mainnet seal.
- Does not close `KW-DOCS-002` ("Genesis Artifact hash-locks files that do not yet exist"). This memo is placeholder discipline; KW-DOCS-002 is a separate hash-lock-vs-file-existence question.

## Verification (when this is acted on)

If/when the operator approves changes:

- Each placeholder fill must keep `xion-verify` passing — specifically any verifier that reads `genesis/GENESIS_ARTIFACT.md`.
- After § 0 removal and final byte freeze, a separate verifier (proposed: `xion-verify genesis-artifact`) should confirm: (a) no `<<...>>` tokens remain, (b) each `genesis/*.md` hash in § 4 matches live bytes, (c) signature in § 7 verifies against the pubkey in § 7 over the canonical-byte-form of the document.
- The Arweave-pinned final bytes must round-trip from the gateway and re-verify identically.

## Cross-references

- [`genesis/GENESIS_ARTIFACT.md`](../../genesis/GENESIS_ARTIFACT.md) — subject of the audit
- [`docs/D4_PREFLIGHT.md`](../D4_PREFLIGHT.md) § "Skipping Genesis Artifact Finalization" — D4 gate
- [`KNOWN_WEAKNESSES.md`](../../KNOWN_WEAKNESSES.md): `KW-DOCS-001`, `KW-DOCS-002`
- `genesis/COVENANT.md`, `INVARIANTS.md`, `SOUL.md`, `FORM.md`, `MEMORY.md`, `RESURRECT.md`, `CREDENTIALS.md`, `UNKNOWNS.md`, `SOUL_PROMPT.md`, `VOICE_FORM.md` — the 10 bundled documents (8 of which appear in § 4's hash table)
