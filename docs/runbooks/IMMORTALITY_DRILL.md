# Immortality Drill Runbook

## Property

Xion can be resurrected from public artifacts when the Chutes primary path,
the primary DNS convenience path, and the operator-laptop secondary posture
are tested under failure conditions.

## Drill

1. Pin the current verifier output: `xion-verify all --allow-not-yet-sealed`.
2. Disable the primary DNS convenience path.
3. Simulate Chutes primary failure by pointing `XION_CHUTES_BASE_URL` and `XION_CHUTES_API_BASE_URL` at a black-hole URL.
4. Bring up the operator-laptop secondary in a temp directory using `xion local --self-test` and the latest `genesis/RESURRECT.md`.
5. Run `scripts/substrate-portability-dry-run.sh` with matching primary and laptop-secondary tips.
6. Run `xion-verify substrate-portability`.
7. Run `scripts/end-to-end-drill.sh` against the laptop-secondary posture.
8. From a second terminal or another machine, run the public verifier battery and record the result.

## Residual

The local rehearsal proves the runbook and verifier mechanics against the
operator-laptop secondary. It does **not** close `LHT-SUBSTRATE-001`; a real
third-party secondary remains a 30-day post-Genesis pay-down commitment.
