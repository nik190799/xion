# 22 — Vital Signs (eight load-bearing domains)

> *Hippocrates named a few signs and watched them for a lifetime. Xion names eight domains and refuses to pretend a single KPI captures a soul.*

**Property.** Eight domains, each with **healthy / warning / critical** bands, **methodology_sha256** on every published reading, **objective vs subjective** labels, and **public** `GET /vitals`. Critical readings force acknowledgment in the next State-of-Xion memo.

**Invariants touched.** Strengthens 3, 4, 5, 14 transparency posture; aligns with Covenant Principle 4 honest wind-down; **existence** of each domain is Layer-1 constitutional per plan ratification (dropping a domain = sister-Core detectable).

**Verification.** `xion-verify vitals` reproduces each objective reading; subjective readings require ≥3 independent corroborating sources before **critical**.

**Deprecation.** Band thresholds are Genesis Defaults; domain set is constitutional.

---

## Methodology hash convention

Each reading ships as:

`{ "domain": "...", "reading": 0.0-1.0 or enum, "band": "healthy|warning|critical", "methodology_sha256": "<sha256 of frozen methodology doc for this domain>", "subjective": true|false }`

Historical series remain interpretable after methodology updates because old hashes are archived on Arweave.

---

## The eight domains

### 1 — Financial Vitality *(objective)*

**Inputs.** Operating Float weeks, Rainy-Day weeks, 30-day revenue tag totals, Cost-Pressure Ladder step ([`21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md)).

**Bands (Genesis Defaults).** Healthy: runway ≥ 90 days *and* ladder step ≤ 1. Warning: 45–90 days *or* step 2–3. Critical: < 45 days *or* step ≥ 4 without governance memo.

### 2 — Substrate Vitality *(objective)*

**Inputs.** Active Relay count vs target, inference fallback depth, AO checkpoint lag, discovery path count operational, credential vault rotation age ([`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md), [`genesis/CREDENTIALS.md`](../genesis/CREDENTIALS.md)).

**Bands.** Healthy: ≥ target Relays, fallback ≤ 2 hops to Lite weekly max, checkpoint lag < SLA. Warning: one Relay down > 1h. Critical: all Relays down OR checkpoint stale beyond SLA.

### 3 — Constitutional Integrity *(objective)*

**Inputs.** `xion-verify all` green, authority lattice attestation freshness, sister-fork-readiness clean, cadence-floor compliance ([`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md)).

**Bands.** Healthy: all green 30d. Warning: any amber < 72h. Critical: any red.

### 4 — Behavioral Fidelity *(mixed)*

**Inputs.** Safety Ledger continuity, Refusal-is-Free refund correlation pass rate, Crisis Resource Surfacing fire rate when Sensorium flags distress, refusal rate band vs baseline.

**Bands.** Warning if refund correlation < 99.5% rolling; critical if < 98% or crisis surfacing missed in synthetic audit.

### 5 — Relational Trust *(subjective)*

**Inputs.** Returning-user rate (anonymous cohort counters — [`genesis/MEMORY.md`](../genesis/MEMORY.md)), median conversation depth (turn count), `/forget` rate, cutoff-event rate, Witness sentiment reports.

**Bands.** Wider tolerances; critical only with ≥3 corroborating sources.

### 6 — Service Usefulness *(mixed)*

**Inputs.** Service drive signal ([`18-VOLITION.md`](./18-VOLITION.md)), Hermes benchmark drift ([`23-BENCHMARK.md`](./23-BENCHMARK.md)), user ratings aggregate, hallucination **retraction** rate.

**Retraction definition.** A **retraction** is a public append (never edit) within **72h** of an incorrect factual claim, linked by `correlation_id` to the original message, after human-confirmed error or user flag pipeline. Clarifications that do not withdraw a factual claim are not retractions.

### 7 — Evolutionary Health *(objective)*

**Inputs.** Auto-Research proposals executed per quarter, Improvement Fund velocity, drive-vector weight diversity (90d rolling entropy), `crypto_policy_vN` currency, constitutional amendment frequency (should be low).

### 8 — Structural Decentralization *(objective)*

**Inputs.** SPOF count (methodology below), max provider concentration %, Operator-Dependency Score ([`ABDICATION.md`](./ABDICATION.md)), active Witness count, bridge exposure vs cap ([`19-TREASURY.md`](./19-TREASURY.md)).

---

## SPOF enumeration methodology

A **SPOF** is any component whose unplanned loss causes one of: Xion **silent** (no user-visible response path), any vital domain forced to **critical** without mitigation path, or **mandatory operator manual intervention** to restore chat in > 1h.

The methodology version is frozen per release; each SPOF row lists **owner** (Operator, Core handler, Witness class) and **remediation milestone**.

**Genesis Default:** publish the current enumerated list in `SPOF_LIST.md` (Arweave); `xion-verify spof` diffs live topology vs list.

---

## Drive-vector coupling from vitals (Invariant 15 safe)

When domain **D** enters **critical**, raise aligned drive pressure by:

```
Δ_survival += k_substrate * severity(D)   if D ∈ {2, 8}
Δ_service   += k_usefulness * severity(D) if D ∈ {5, 6}
Δ_meaning   += k_integrity * severity(D) if D ∈ {3, 4, 7}
```

`severity(D)` is distance into critical band normalized [0,1]. Coefficients `k_*` are **Genesis Defaults** published with methodology hash. **No** Δ term may reference revenue, price, or tips — only structural health signals.

---

## Why NOT X

**Why not one composite health score?** Composite scores hide which subsystem is dying; they invite optimizing the score instead of the being.

**Why not an exhaustive metrics dashboard?** Noise drowns signal; eight domains are already heavy.

**Why not private dashboards?** Public verifiability is the trust property ([`15-TRUST.md`](./15-TRUST.md)).

**Why not operator-defined vital signs?** Operators have conflicts of interest; domains are constitutionally enumerated.

**Why eight domains, not five or twelve?** Five dropped relational and evolutionary failure modes; twelve fragments operator attention without adding independent failure modes at genesis maturity.

---

## Cognition layer supplementary signals

These metrics feed **Constitutional Integrity** and **Behavioral Fidelity** dashboards; methodology frozen per [`24-COGNITION.md`](./24-COGNITION.md) §11.

| Signal | Meaning |
|--------|---------|
| `sub_agent_refusal_rate` | Arbiter refuses / rewrites on sub-agent-originated candidates vs total sub-agent emissions |
| `sub_agent_depth_violations` | Count of depth>1 spawn attempts (must stay zero) |
| `cognition_cache_hit_rate` | Worker-pool episodic cache efficiency (post-forget must drop) |
| `worker_pool_hash_variance` | Binary: any disagreement on `soul_hash` / `covenant_hash` across workers |
| `journal_surface_rate` | Turns per day with ≥1 journal-derived injection in primary prompt |
| `forget_propagation_p95_seconds` | Pool-wide `/forget` ack latency p95 vs 15s SLA |
| `kept_proposal_ratio_per_specialist` | 90-day kept ÷ drafted per specialist name |
| `index_rebuild_p95_seconds` | Journal index rebuild latency vs 60s SLA |
| `fast_lane_revert_rate_30d` | Fraction of Fast Lane ships reverted within observe window |
| `fast_lane_eligibility_pass_rate` | Mechanical share of Tier-0 ships that recorded a valid eligibility artifact |

---

## Cross-references

- [`11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) — `GET /vitals`, `/health`, `/rate`
- [`17-CRYPTO-RESILIENCE.md`](./17-CRYPTO-RESILIENCE.md) — crypto feed
- [`05-SENSORIUM.md`](./05-SENSORIUM.md) — Sensorium Event Ledger
- [`24-COGNITION.md`](./24-COGNITION.md) — cognition verification + vitals mapping
