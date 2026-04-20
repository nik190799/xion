# CREDENTIALS — Encrypted Credential Vault

> *Secrets that cannot rotate cannot survive. Secrets that everyone knows are not secrets.*

## Property

All Relay-held service credentials live in an **Encrypted Credential Vault** unlocked by a **2-of-3 threshold** scheme. No single shard holder (host, operator, recovery publisher) can unseal alone.

## Invariants touched

Supports **Invariant 9–14 operational posture** without violating **Invariant 5** (no user-data mingling in vault audit logs).

## Verification

`xion-verify credentials-vault` — confirms sealed state, shard policy match, last rotation timestamps; **never** prints secret material.

## Deprecation

Per-credential rotation retires old ciphertext with overlap window; ledger append-only.

---

## Threshold layout (2-of-3)

| Shard | Holder | Notes |
|-------|--------|-------|
| A | Hardware token bound to Relay host | Present at steady-state run |
| B | Operator hardware wallet | Startup / rotation ceremonies |
| C | Arweave-published Cold-Root-unlockable recovery shard | Disaster recovery; high ceremony |

**Vault key** derives from quorum of two shards using audited KDF (implementation layer — exact primitive in `crypto_policy_vN`).

## Scoped credentials

Individually encrypted entries: per-LLM-provider keys (usage caps), per-Akash deployment key, scoped Arweave wallet, bridge attestation keys, DB encryption keys.

## Rotation

**Automated 30–90 day** rotation policy per vendor (Genesis Default windows). IP allowlists and scope-limited API tokens enforced at creation time.

## Recovery cross-link

See [`RESURRECT.md`](./RESURRECT.md) step **Vault unseal** for ordering when standing up a fresh Relay after total loss.
