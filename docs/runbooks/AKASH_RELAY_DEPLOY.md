# Akash Relay Deploy Runbook

> **Standby blueprint only.** Chutes is the Genesis primary Relay substrate and the operator laptop is the named Genesis secondary for Layer-1 rehearsal. This runbook is retained as the optional third-party-secondary blueprint for the post-Genesis `LHT-SUBSTRATE-001` pay-down. It is not the primary deploy path.

## Property

Deploy a Relay on Akash as a third-party-secondary substrate without making Akash the only discovery path.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild`.
2. Replace the placeholder image in `infra/akash/relay-deployment.yaml` with the verified digest.
3. Create the Akash lease with the operator wallet.
4. Inject only deployment secrets required for the Relay posture.
5. Confirm `/health` returns OK over the lease endpoint.
6. Record the substrate dry-run row with live evidence:

   ```bash
   XION_SECONDARY_SUBSTRATE_ID=akash-testnet-standby \
   XION_SECONDARY_PROVIDER=akash \
   XION_SECONDARY_HEALTH_URL=https://<akash-lease-host>/health \
   XION_DEPLOYMENT_EVIDENCE=akash://<owner>/<dseq>/<gseq>/<oseq> \
   XION_PRIMARY_STATE_TIP=<primary-tip> \
   XION_SECONDARY_STATE_TIP=<same-tip-after-replay> \
   bash scripts/substrate-portability-dry-run.sh
   ```

7. Run `xion-verify substrate-portability`.
8. Publish the Relay row through `RelayRegistryPublisher`.
9. Run `xion-verify discovery`.

## Preflight

From the repository root:

```bash
bash scripts/akash-secondary-preflight.sh
```

The preflight is intentionally read-only. It checks the local Akash tooling,
Docker CLI, Relay digest file, and whether the Akash SDL still contains the
placeholder image. It does not create a lease, spend AKT, or append
`ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl`.

`scripts/substrate-portability-dry-run.sh` refuses to append an Akash/Aleph row
unless the operator supplies a live `XION_SECONDARY_HEALTH_URL` and deployment
evidence. This keeps `xion-verify substrate-portability` from going green on a
fake `akash-*` identifier.

## Non-goals

This runbook does not decommission Cloudflare by itself and does not claim a three-host floor. Those remain `KW-OPS-001` operator actions until at least three independent Relay paths are live.
