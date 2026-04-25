# Akash Relay Deploy Runbook

## Property

Deploy a Relay on Akash without making Akash the only discovery path.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild`.
2. Replace the placeholder image in `infra/akash/relay-deployment.yaml` with the verified digest.
3. Create the Akash lease with the operator wallet.
4. Inject only deployment secrets required for the Relay posture.
5. Confirm `/health` returns OK over the lease endpoint.
6. Publish the Relay row through `RelayRegistryPublisher`.
7. Run `xion-verify discovery`.

## Non-goals

This runbook does not decommission Cloudflare by itself and does not claim a three-host floor. Those remain `KW-OPS-001` operator actions until at least three independent Relay paths are live.
