# Immortality Drill Runbook

## Property

Xion can be resurrected from public artifacts when the operator laptop, primary
DNS path, and primary Relay substrate fail.

## Drill

1. Pin the current verifier output: `xion-verify all --allow-not-yet-sealed`.
2. Stop the operator laptop Relay.
3. Disable the primary DNS convenience path.
4. Stop the primary Akash lease or equivalent primary substrate.
5. Bring up the secondary substrate using the latest `genesis/RESURRECT.md`.
6. Run `scripts/substrate-portability-dry-run.sh` with matching primary and secondary tips.
7. Run `xion-verify substrate-portability`.
8. From a third-party machine, run the public verifier battery and record the result.

## Residual

A placeholder dry-run row proves the ledger and verifier mechanics. A real
Immortality Drill requires a warm secondary substrate and remains an operator
preflight action before Genesis.
