# Immortality Drill Runbook

## Property

Xion can be resurrected from public artifacts when the **Akash** primary path,
the primary DNS convenience path, the **Chutes** secondary Relay surface, and
substrate dry-run evidence are tested under failure conditions (current registry
row order: `relays[0]` = Akash, `relays[1]` = Chutes).

## Drill

1. Pin the current verifier output: `xion-verify all --allow-not-yet-sealed`.
2. Disable the primary DNS convenience path.
3. Simulate **Akash** primary failure (black-hole the hosted Relay base URL
   or scale the Akash deployment to zero while keeping the Chutes secondary
   path reachable for comparison).
4. Confirm the **Chutes** cord surface is still healthy: same bearer-based
   probes as `scripts/verify-chute-cords.sh`, and set dry-run env per
   `docs/runbooks/AKASH_RELAY_DEPLOY.md` step 8 (Chutes as secondary) if you
   are appending a new substrate row.
5. When rehearsing a **Chutes**-secondary row, set `XION_SECONDARY_*` to the
   Chutes cord `/health` URL, `XION_SECONDARY_PROVIDER=chutes`, and
   `XION_SECONDARY_HEALTH_BEARER` from your Chutes API key. For an **Akash**-as-secondary rehearsal (legacy order), use `XION_SECONDARY_HEALTH_URL` to the
   Akash lease `/health` and `XION_DEPLOYMENT_EVIDENCE=akash://...` with
   `curl -k` as in `AKASH_RELAY_DEPLOY.md`.
6. Run `scripts/substrate-portability-dry-run.sh` with matching primary/secondary state tips.
7. Run `xion-verify substrate-portability`.
8. Run `scripts/end-to-end-drill.sh` against the appropriate secondary endpoint
   (or the documented failover posture for your rehearsal harness).
9. From a second terminal or another machine, run the public verifier battery and record the result.

**Offline mechanics only:** to append a dry-run ledger row without a live lease, set `XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary` explicitly. That path is not the doctrine secondary.

## Residual

A full rehearsal with live Chutes and Akash evidence advances `LHT-SUBSTRATE-001` pay-down together with the annual cadence and promotion gates in `docs/SUBSTRATE-RESILIENCE.md` Part IV. Laptop-only dry-runs do not close the residual.
