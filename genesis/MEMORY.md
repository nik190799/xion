# MEMORY — Environment and Relationship Custody

> *What Xion must remember to be coherent — and what Xion must forget to be worthy of trust.*

## Property

`MEMORY.md` defines **environment facts** Xion needs across sessions (endpoints, AO references, operator-visible config pointers) and the **redaction policy** for optional user memory. It is not a transcript store; per-user threads live in scoped `USER.md` per consent.

## Invariants touched

Implements **Invariant 2** (`/export`, `/forget`, `/inspect`) for operational memory; user memory semantics mirror Protocol spec.

## Verification

`xion-verify memory-schema` validates schema hash against Core slot.

## Deprecation

Schema version bumps are additive; `/forget` tombstones remain append-only.

---

## Environment-facts schema (illustrative keys)

```yaml
ao_process_id: "<canonical>"
relay_registry_ar_uri: "ar://..."
preferred_gateways: ["https://arweave.net", "..."]
public_endpoints:
  protocol_base: "https://..."
operator_contact_fingerprint: "<pgp fingerprint — optional>"
```

**No secrets** in plain `MEMORY.md`; secrets live in [`CREDENTIALS.md`](./CREDENTIALS.md) vault doctrine.

---

## Privacy-preserving anonymous-session counter

**Purpose.** Feed **Relational Trust** vital signs without storing cross-session identifiers post-`/forget`.

**Mechanism (constitutional shape).** Each calendar month, Relays increment **hashed cohort buckets**:

- `cohort_id = HMAC(month_salt, coarse_geo_bucket || wallet_pubkey_hash)` where `wallet_pubkey_hash` is optional; anonymous IP-only users hash to a separate bucket family.
- Counters: `sessions_started`, `sessions_returning`, `max_turn_depth`, `forget_events`, `cutoff_events`.

**Survives `/forget`.** Counters carry **no reversibility** to plaintext transcripts; tombstone `/forget` only increments `forget_events` for that cohort.

**Turn depth** is measured in **integer turns**, not tokens (token counts leak content volume).

---

## Worker pool and `/forget` propagation (cognition SLA)

When multiple Relay workers implement the cognition layer ([`docs/24-COGNITION.md`](../docs/24-COGNITION.md)), **`POST /memory/forget` must invalidate every worker's ephemeral view of the caller's relationship thread within 15 seconds** of request acknowledgement (Genesis Default; extend-only shorter by governance, never longer). The Core broadcasts the forget event; each worker ACKs before serving the user's next turn. Verification: `xion-verify cognition --forget-sim`.

---

*Committed at genesis; operational contents evolve by governance.*
