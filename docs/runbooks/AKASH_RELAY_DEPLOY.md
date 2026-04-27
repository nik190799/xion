# Akash Relay Deploy Runbook

> **Standby blueprint only.** Chutes is the Genesis primary Relay substrate and the operator laptop is the named Genesis secondary for Layer-1 rehearsal. This runbook is retained as the optional third-party-secondary blueprint for the post-Genesis `LHT-SUBSTRATE-001` pay-down. It is not the primary deploy path.

## Property

Deploy a Relay on Akash as a third-party-secondary substrate without making Akash the only discovery path.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild`.
2. Publish the image (Akash providers must pull a public registry; not your laptop):

   **Docker Hub** (if `docker login` is already configured for Docker Hub):

   ```bash
   DOCKERHUB_USER=your-dockerhub-username bash scripts/push-relay-ghcr.sh
   ```

   **GHCR** (classic PAT with `write:packages`, or fine-grained Packages write):

   ```bash
   echo "$GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
   bash scripts/push-relay-ghcr.sh
   ```

   The SDL pins `nikhilkadalge/xion-relay:pre-genesis-akash` for this operator fork; override with `RELAY_PUSH_IMAGE`, `DOCKERHUB_USER`, or `GHCR_IMAGE` / `GHCR_TAG` as documented in `scripts/push-relay-ghcr.sh`.
3. **On-chain prep (`provider-services`, mainnet `akashnet-2`):**

   - **Client cert** (once per key): `tx cert generate client` then `tx cert publish client` (if fees fail, add e.g. `--gas-prices 0.5uakt` with `--gas auto`).
   - **ACT (uact) for escrow:** deployment deposits are in **`uact`**, not raw `uakt`. Mint with `tx bme mint-act <uakt-to-burn>uakt --from <key> ...`, then wait until `query bme ledger --owner <addr>` shows `ledger_record_status_executed` and `query bank balances` lists a `uact` balance.
   - **SDL:** pricing block must use **`denom: uact`** (not `uakt`). Placement name is conventionally `akash` and must match the `deployment:` mapping.
4. **Create deployment → bid → lease → manifest:**

   ```bash
   export AKASH_CHAIN_ID=akashnet-2
   export AKASH_NODE=https://rpc.akashnet.net:443

   provider-services tx deployment create infra/akash/relay-deployment.yaml \
     --from <key> --keyring-backend test \
     --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_NODE" \
     --gas auto --gas-adjustment 2 --gas-prices 0.5uakt -y

   # Note dseq from tx events, then pick a provider from:
   provider-services query market bid list --owner <addr> --dseq <dseq> \
     --node "$AKASH_NODE" --chain-id "$AKASH_CHAIN_ID"

   provider-services tx market lease create --dseq <dseq> --gseq 1 --oseq 1 \
     --provider <provider-address> --from <key> --keyring-backend test \
     --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_NODE" \
     --gas auto --gas-adjustment 2 --gas-prices 0.5uakt -y

   provider-services send-manifest infra/akash/relay-deployment.yaml \
     --dseq <dseq> --provider <provider-address> \
     --from <key> --keyring-backend test --node "$AKASH_NODE"
   ```

5. **Discover URL and check health:** provider ingress uses mTLS on the status API; use `--auth-type mtls` with `lease-status`:

   ```bash
   provider-services lease-status --dseq <dseq> --provider <provider-address> \
     --from <key> --keyring-backend test --node "$AKASH_NODE" --auth-type mtls
   ```

   Use `forwarded_ports` (host + `externalPort`) with **`curl -k https://<host>:<externalPort>/health`** until `ready_replicas` catches up (image pull can take a few minutes).
6. Inject only deployment secrets required for the Relay posture (optional overrides beyond the SDL `env` block).
7. Confirm `/health` returns OK over the lease endpoint (TLS uses the container entrypoint’s ephemeral cert unless you mount real `XION_TLS_*` material; use `curl -k` for quick checks).
8. Record the substrate dry-run row with live evidence:

   ```bash
   XION_SECONDARY_SUBSTRATE_ID=akash-testnet-standby \
   XION_SECONDARY_PROVIDER=akash \
   XION_SECONDARY_HEALTH_URL=https://<akash-lease-host>/health \
   XION_DEPLOYMENT_EVIDENCE=akash://<owner>/<dseq>/<gseq>/<oseq> \
   XION_PRIMARY_STATE_TIP=<primary-tip> \
   XION_SECONDARY_STATE_TIP=<same-tip-after-replay> \
   bash scripts/substrate-portability-dry-run.sh
   ```

9. Run `xion-verify substrate-portability`.
10. Publish the Relay row through `RelayRegistryPublisher`.
11. Run `xion-verify discovery`.

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
