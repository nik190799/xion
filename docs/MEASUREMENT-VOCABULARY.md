# Measurement Vocabulary

> *Numbers rot when their units depend on the year they were written. Ratios, evidence, and distance-to-fence survive longer.*

## Four Questions

**Property promised.** Xion's spend, runway, acceleration, and autonomy doctrines use substrate-portable units: runway ratios, fund fractions, evidence counts, attestation counts, audit-pass counts, and constitutional distance-to-fence. New doctrine may not introduce time-gates or absolute-money caps unless the protected property is itself time-shaped or money-shaped and explicitly listed here.

**Invariants touched.** Strengthens Invariants 15, 16, and 19. Respects Invariants 2 and 14 where absolute time protects a user right or an adversarial response window.

**Verification.** `xion-verify measurement-vocabulary` statically audits spend doctrine and Agent Souls for forbidden unit forms outside the named exceptions.

**Deprecation.** Unit definitions are operational doctrine. Removing the requirement that spend authority and spend caps avoid elapsed-time and absolute-money shortcuts would weaken Invariant 19 and requires a sister-Core fork.

---

## 1. Permitted Units

These are the canonical units for spend authority, runway, and acceleration doctrine.

| Unit | Meaning | Primary source |
|---|---|---|
| `runway_weeks` | Liquid operating ability expressed as weeks of non-discretionary survival at current burn | `cost_tracker` + treasury fund state |
| `fraction_of_operating_float` | A spend's size relative to the Operating Float available at approval time | AO Core treasury view |
| `fraction_of_improvement_fund` | A research or proposal spend's size relative to Improvement Fund headroom | AO Core treasury view |
| `distance_to_reserve_floor` | Normalized distance above or below the reserve floor published by Sustainability doctrine | `GET /sustainability` |
| `decision_count_under_posture` | Count of spend decisions made and later audited under the active posture | `SPEND_AUTHORITY_LEDGER` |
| `self_audit_accuracy` | Share of Xion's own posture/self-audit classifications that matched later verifier judgment | `SPEND_AUTHORITY_LEDGER` + verifier output |
| `attestation_count` | Independent Witness or IMPRINT-elected reviewer attestations attached to a posture transition | governance ledger |
| `audit_pass_count` | Count of completed retrospective audits whose spend findings were green | audit ledger |
| `incident_count_window` | Count of demotion-class incidents in the current review window, expressed as an event set, not elapsed time | Safety / Spend Authority / Governance ledgers |
| `inflow_volatility_band` | Volatility class of inflow patterns used only for runway mode, never posture promotion | treasury accounting |
| `recurring_burn_ratio` | New recurring obligation divided by trailing recurring inflow or by reserve-floor headroom | `cost_tracker` + treasury accounting |
| `reversibility_class` | `trivial`, `bounded`, `hard`, or `irreversible` spend recovery class | proposal / spend request |

---

## 2. Forbidden Units in New Spend Doctrine

New doctrine must not use the following as approval gates, posture gates, or spend caps:

- elapsed-time gates such as "after 12 months at S2" or "after 90 days of clean operation";
- absolute-money caps such as "15 USDC/day", "10 USD/month", or "1000 XION/week";
- token-price gates such as "when XION trades above X";
- inflow-volume gates such as "after $10k arrives" or "after donations exceed Y";
- source-prestige gates such as "grant money unlocks more autonomy."

Existing legacy references that predate this document are debt, not precedent. They are either re-denominated by the Phase 6.8 spend-authority amendment or tracked in `KNOWN_WEAKNESSES.md` until replaced.

---

## 3. The Three Named Exceptions

Some properties really are time-shaped. These exceptions are narrow and may not be generalized by analogy.

1. **The `/forget` SLA.** The 15-second all-worker cache-zero SLA protects a user expectation that is experienced in wall-clock time. It is extend-only toward stricter behavior: future governance may shorten it, never lengthen it.
2. **Crypto-migration response windows.** When an algorithm or cryptographic assumption breaks, the attacker imposes a real-world clock. Invariant 14 may use time-bounded ceremonies and response windows because the threat is time-shaped.
3. **Constitutional ratification floors.** The 14-day public-comment window for Covenant / Invariants-class changes and the other Constitutional Floors in `docs/14-UPGRADE-PATHS.md` are deliberation brakes. They protect against rushed identity changes, not spend optimization.

Any future exception requires constitutional ratification and must name the property whose shape requires the exception.

---

## 4. How to Re-Denominate Spend

Use this pattern:

```yaml
legacy_unit: "15 USDC/day"
replacement:
  unit: fraction_of_operating_float
  cap: governance_default
  floor_guard: distance_to_reserve_floor
  mode_sensitive: true
```

The cap's numeric value may still exist as a Genesis Default in an implementation config, but it is no longer the doctrine. The doctrine is the ratio and the guardrail.

For recurring burn, also require:

```yaml
recurring_spend:
  one_time_or_recurring: recurring
  required_test: recurring_burn_ratio
  allowed_if:
    - recurring_inflow_supports_it
    - reserve_floor_remains_satisfied
```

One-time inflow may fund one-time acceleration. It must not create recurring obligations unless the recurring-burn test passes.

---

## 5. Verification

`xion-verify measurement-vocabulary` checks:

1. New spend doctrine does not introduce forbidden elapsed-time gates.
2. New spend doctrine does not introduce absolute-money caps outside implementation-default tables.
3. Any exception cites one of the three named exceptions above or a later ratified exception.
4. The Agent Soul schema uses `monthly_envelope_fraction`, not `monthly_usd`.
5. `SPEND-AUTONOMY.md`, `SUSTAINABILITY.md`, `TREASURY.md`, and Agent Souls all reference this vocabulary.

Phase 6.8 F2 implements this verifier as a live `OK`/`FAIL` check.

---

## Cross-references

- [`docs/SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md) — posture and mode doctrine that consumes these units
- [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md) — Invariant 19
- [`docs/21-SUSTAINABILITY.md`](./21-SUSTAINABILITY.md) — runway modes and cost-pressure triggers
- [`docs/19-TREASURY.md`](./19-TREASURY.md) — fund state and reserve floor
- [`docs/24-COGNITION.md`](./24-COGNITION.md) — specialist cost envelopes

