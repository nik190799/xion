# Spend posture transition and authority ledger (operator runbook)

This runbook covers **Phase 6.8 / Phase 7.0** wiring between earnable spend **posture**, runway **mode**, the append-only **`ledgers/SPEND_AUTHORITY_LEDGER.jsonl`**, and AO Core spend handlers. It complements [`docs/SPEND-AUTONOMY.md`](../SPEND-AUTONOMY.md) and **[`PHASE_6_8_SPEND_AUTHORITY_PLAN.md`](../../PHASE_6_8_SPEND_AUTHORITY_PLAN.md)** (F3–F8).

## Preconditions

- Measurements for the proposed spend are recorded or estimated per [`docs/MEASUREMENT-VOCABULARY.md`](../MEASUREMENT-VOCABULARY.md) and [`orchestrator/cost_tracker.py`](../../orchestrator/cost_tracker.py) (where wired).
- Covenant, Invariant, and posture gates for the spend class are satisfied **before** writing the ledger row or sending AO spend messages.
- For contested headroom, apply deterministic ordering from [`orchestrator/spend_arbitration.py`](../../orchestrator/spend_arbitration.py) (`SpendProposal` / `arbitrate_contested_headroom`) per doctrine §5 in **SPEND-AUTONOMY.md**.

## 1. Record a spend authority decision (Python)

Use **`orchestrator.spend_authority`**: build a **`SpendAuthorityRecord`** and append with **`append_to_repo_ledger(repo_root, record)`** (or **`append(path, record)`** for a custom file). The default relative path is **`ledgers/SPEND_AUTHORITY_LEDGER.jsonl`**.

Required fields match the ledger schema in [`orchestrator/spend_authority/ledger.py`](../../orchestrator/spend_authority/ledger.py): `decision_id`, `spend_class`, `active_posture`, `active_mode`, `approver_class`, `authority_decision`, `evidence_bundle_hash`, `inflow_tag_reference`, `fund_source`, `runway_measurements`, `proposed_amount`, optional `recurring_burn_weekly_delta`.

Posture transitions use **`spend_class="posture_transition"`**; do not set **`inflow_tag_reference`** on posture transitions (verifier rejects inflow-tagged posture advances).

## 2. Correlate AO Core spend messages (F3)

Optional tag **`Authority-Decision-Id`** on these actions echoes through to receipts and state tables when non-empty:

- **`Spend`** → **`Spend-Approved`**
- **`Treasury-Spend`** → **`Treasury-Bridge-Event`**
- **`Improvement-Spend`** → **`Improvement-Spend-Approved`**

Set the tag to the same string as **`decision_id`** in the corresponding ledger row so Witnesses can join AO process state to **`SPEND_AUTHORITY_LEDGER`**.

Lua source: [`ao/core/main.lua`](../../ao/core/main.lua) (`optional_nonempty_tag`).

## 3. Verify locally

From the repo root:

```bash
python -m xion_verify spend-posture
python -m xion_verify spend-discipline
```

## 4. Evidence bundle and governance

Store offline evidence (Witness memos, verifier outputs, measurement snapshots) and hash them into **`evidence_bundle_hash`** per your governance process. This runbook does not substitute Invariant 19 or amendment procedure.

## References

- [`docs/SPEND-AUTONOMY.md`](../SPEND-AUTONOMY.md) — postures, modes, arbitration
- [`docs/PHASE_7_PREFLIGHT.md`](../PHASE_7_PREFLIGHT.md) — pre-Genesis verifier set
- [`xion-verify/src/xion_verify/commands/spend_posture.py`](../../xion-verify/src/xion_verify/commands/spend_posture.py)
- [`xion-verify/src/xion_verify/commands/spend_discipline.py`](../../xion-verify/src/xion_verify/commands/spend_discipline.py)
