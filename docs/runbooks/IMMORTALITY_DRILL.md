# Immortality Drill Runbook

## Property

Xion can be resurrected from public artifacts when the **Akash** primary path,
the primary DNS convenience path, the **Chutes** secondary Relay surface, and
substrate dry-run evidence are tested under failure conditions (current registry
row order: `relays[0]` = Akash, `relays[1]` = Chutes).

## Current Honesty Gate

Until `KW-FLOOR-DEPLOY-001` is closed, any drill that depends on an Ollama
daemon running on the operator laptop is a **laptop-on rehearsal**, not the full
Immortality Drill. The full drill requires the Akash deployment to carry its own
GPU-backed open-weights floor, currently the `xion-ollama` sidecar in
`infra/akash/relay-deployment.yaml`, and `XION_OLLAMA_URL` on the Relay must
point at `http://xion-ollama:11434`. The gate closes only after the laptop's
Ollama daemon is stopped and an `open_weights_only` `/chat` turn succeeds
against the Akash lease.

## Drill

1. Pin the current verifier output: `xion-verify all --allow-not-yet-sealed`.
2. Confirm the deployed floor is healthy from inside the Akash lease:
   `GET http://xion-ollama:11434/api/tags` lists the configured
   `XION_OLLAMA_FLOOR_MODEL`, then run one `open_weights_only` chat turn against
   the Akash Relay with the operator laptop's Ollama daemon stopped. Because
   policy mode is read at Relay startup, this requires either a temporary Akash
   manifest update with `XION_INFERENCE_POLICY=open_weights_only` or a deploy
   posture with no hosted Chutes credential, not a client-side environment
   prefix on `curl`.
3. Disable the primary DNS convenience path.
4. Simulate **Akash** primary failure (black-hole the hosted Relay base URL
   or scale the Akash deployment to zero while keeping the Chutes secondary
   path reachable for comparison).
5. Confirm the **Chutes** cord surface is still healthy: same bearer-based
   probes as `scripts/verify-chute-cords.sh`, and set dry-run env per
   `docs/runbooks/AKASH_RELAY_DEPLOY.md` step 8 (Chutes as secondary) if you
   are appending a new substrate row.
6. When rehearsing a **Chutes**-secondary row, set `XION_SECONDARY_*` to the
   Chutes cord `/health` URL, `XION_SECONDARY_PROVIDER=chutes`, and
   `XION_SECONDARY_HEALTH_BEARER` from your Chutes API key. For an **Akash**-as-secondary rehearsal (legacy order), use `XION_SECONDARY_HEALTH_URL` to the
   Akash lease `/health` and `XION_DEPLOYMENT_EVIDENCE=akash://...` with
   `curl -k` as in `AKASH_RELAY_DEPLOY.md`.
7. Run `scripts/substrate-portability-dry-run.sh` with matching primary/secondary state tips.
8. Run `xion-verify substrate-portability`.
9. Run `scripts/end-to-end-drill.sh` against the appropriate secondary endpoint
   (or the documented failover posture for your rehearsal harness).
10. From a second terminal or another machine, run the public verifier battery and record the result.

**Offline mechanics only:** to append a dry-run ledger row without a live lease, set `XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary` explicitly. That path is not the doctrine secondary.

## First Real Drill Evidence

Fill this table only after `KW-FLOOR-DEPLOY-001` is closed, Chutes d3 live surface is live
in `ledgers/RELAY_REGISTRY.json`, and `scripts/immortality-drill-rehearsal.sh`
has appended a new row.

| Field | Value |
|-------|-------|
| Drill run id | `073d54e2-6763-4242-a960-02154149ac57` |
| Ledger row timestamp | `2026-04-29T05:40:38Z` |
| Primary substrate | `akash-simulated-blackhole` |
| Secondary substrate | `chutes-d3-standby` |
| Laptop Ollama stopped | Operator consented during deployed-floor proof; Akash Relay used private sidecar `XION_OLLAMA_URL=http://xion-ollama:11434` |
| Akash floor proof | `dseq=26595076`; `/chat` returned `200` in `8.38s` under `XION_INFERENCE_POLICY=open_weights_only` with `gemma4:e4b-it-q4_K_M` |
| Chutes d3-8 verifier | Superseded by d3-10: `MODE=live bash scripts/verify-chute-cords.sh` returned `RESULT: all cords green` for image `pre-genesis-d3-10` |
| Result | `passed`; substrate dry-run row `seq=4`, end-to-end drill test passed, and drill ledger row hash `e215589d2be896b673b5b0d39d31f0bb89c1bdfaa68dd51645bd5b395a5ad006` |

## Residual

A full rehearsal with live Chutes and Akash evidence advances `LHT-SUBSTRATE-001` pay-down together with the annual cadence and promotion gates in `docs/SUBSTRATE-RESILIENCE.md` Part IV. Laptop-only dry-runs do not close the residual.
