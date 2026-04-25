# Phase 6.8 — Trust-Earned Spend Authority Plan

## Purpose

Close only the in-phase Phase 6.8 scope: F1 `orchestrator/cost_tracker.py` and F2 `xion-verify measurement-vocabulary`.

F3–F8 remain explicitly deferred to Phase 7.0/7.1:

- F3 AO Core Spend handler updates.
- F4 `orchestrator/spend_arbitration.py`.
- F5 `SPEND_AUTHORITY_LEDGER.jsonl` writer.
- F6 `xion-verify spend-posture`.
- F7 `xion-verify spend-discipline`.
- F8 posture transition runbook.

## Property

Xion can measure spend pressure and audit measurement vocabulary without treating money, elapsed time, or funds-on-hand as authority. Spend authority remains evidence-earned; this phase only makes the measurement spine real.

## Invariants Touched

- **Invariant 15 — Drive Vector Excludes Revenue.** Strengthens by auditing forbidden money/time gates.
- **Invariant 16 — Treasury Composition.** Strengthens by making bucket attribution queryable.
- **Invariant 19 — Trust-Earned Spend Authority.** Implements the first enforcement-adjacent measurement layer, without granting spend authority.

## F1 — `orchestrator/cost_tracker.py`

Land a small, testable cost tracker with bucket-by-bucket attribution at debit-time.

Required bucket vocabulary:

- Operating Float.
- Improvement Fund.
- Rainy-Day Reserve.
- Foundation Reserve.
- Treasury.

Required query API:

- `runway_weeks`.
- `fraction_of_operating_float`.
- `fraction_of_improvement_fund`.
- `distance_to_reserve_floor`.
- `recurring_burn_ratio`.

Required Sensorium output:

- Emit Financial Vitality inputs on the existing Sensorium bus.
- Do not change `SENSORIUM_LEDGER` schema unless the existing bus requires a named row type.
- Do not create spend authority, arbitration, or ledger-write behavior in this phase.

Tests:

- Add `orchestrator/tests/test_cost_tracker.py`.
- Cover bucket attribution.
- Cover the five metric queries.
- Cover Sensorium Financial Vitality emission shape.

## F2 — `xion-verify measurement-vocabulary`

Add `xion-verify/src/xion_verify/commands/measurement_vocabulary.py`.

Static audit scope:

- Walk spend doctrine docs.
- Walk Agent Soul files.
- Assert spend doctrine and Agent Souls use `docs/MEASUREMENT-VOCABULARY.md` units.
- Assert forbidden time/money gates appear only in named exceptions or legacy Known Weakness entries.

Registration:

- Register the command in `xion-verify/src/xion_verify/commands/__init__.py`.
- Ensure it appears in `xion-verify --help`.

Tests:

- Add `xion-verify/tests/test_measurement_vocabulary.py`.
- Include a synthetic forbidden-gate negative case.
- Include a vocabulary-clean positive fixture.

## Known Weakness Pay-Down

- Close `KW-COST-001` when F1 lands.
- Close `KW-MEASUREMENT-001` when F2 lands.
- Keep `KW-SPEND-*` entries explicitly tagged Phase 7.0/7.1 if they depend on F3–F8.

## Roadmap and Changelog

- Mark Phase 6.8 as **partially closed (F1 + F2)** in `DEVELOPMENT_ROADMAP.md`.
- Preserve F3–F8 as deferred to Phase 7.0/7.1.
- Add a `CHANGELOG.md` entry with the Four Questions summary.

## Closure Criteria

- `orchestrator/tests/test_cost_tracker.py` green.
- `xion-verify measurement-vocabulary` returns OK on current docs and Agent Souls.
- `xion-verify --self-test` green.
- `xion-verify links` green.
- `xion-verify schemas` green.
- `xion-verify registries` green.
- Relevant pytest suites green.

## Non-Goals

- No AO Core Spend handler updates.
- No spend arbitration.
- No `SPEND_AUTHORITY_LEDGER.jsonl` writer.
- No `spend-posture` or `spend-discipline` verifier.
- No posture transition runbook.
- No promotion of spend authority posture.
- No money/funds/time gates as authority signals.

## Suggested Branch

`feat/phase-6-8-spend-authority-f1-f2`
