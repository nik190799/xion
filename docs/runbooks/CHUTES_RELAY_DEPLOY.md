# Chutes Relay Deploy Runbook

## Property

Deploy a hosted Relay **Chutes** surface. In the committed registry (`ledgers/RELAY_REGISTRY.json`), **Chutes is `relays[1]` (genesis secondary cord)** and **Akash is `relays[0]` (genesis primary)** — see `xion-verify discovery` and **`docs/runbooks/AKASH_RELAY_DEPLOY.md`** for publication and lease URL. The operator laptop is for local rehearsal only, not the doctrine redundant path.

## Invariants Touched

Strengthens Invariant 17 (Inference Sovereignty Floor) and the Substrate Portability Property. Leaves the local Ollama floor unchanged.

## Verification

Run `xion-verify discovery`, `xion-verify inference-provider-chutes`, and `xion-verify pre-genesis` after publishing the Relay registry row.

## Local Pre-Flight

Before consuming a Chutes image-history slot for the live Relay image, prove the
same dependency shape locally:

1. Run `pytest orchestrator/tests/test_launcher.py -x` to confirm
   `orchestrator.api.launcher.build_app()` constructs a real `Relay` and full
   `AppDeps`.
2. Run `python -m orchestrator.api` with the Step 3 environment and probe
   `http://127.0.0.1:8000/health`, `/pricing`, and `/self`.
3. Run `scripts/verify-chute-import.py` under the Chutes pipx environment to
   confirm `xion_relay_chute:chute` imports and exposes `/health`, `/quote`,
   and `/self`.
4. Only after those checks are green, run the Chutes build/deploy commands.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild` or the current release build command.
2. Confirm the local floor is healthy with `xion-verify inference-sovereignty`.
3. Set `XION_CHUTES_API_KEY`, `XION_CHUTES_BASE_URL`, `XION_CHUTES_API_BASE_URL`, `XION_CHUTES_HOSTED_MODEL`, and `XION_CHUTES_TEE_REQUIRED=true` from the encrypted credential vault.
4. Deploy the verified Relay image to the Chutes deployment surface.
5. Confirm `/health`, `/quote`, and `/self` return OK over the Chutes endpoint with `scripts/verify-chute-cords.sh`. If verifying the currently deployed smoke image while the next image is blocked by Chutes' image-history quota, pin the assertion explicitly, e.g. `EXPECTED_IMAGE_TAG=pre-genesis-d3-6 bash scripts/verify-chute-cords.sh`. The Chutes platform reserves/intercepts pricing-like routes, so the smoke cord intentionally avoids `/pricing`; a platform pricing response at `/pricing` is expected.
6. Publish the Relay row through `RelayRegistryPublisher` with `substrate="chutes"` and the verified image digest.
7. Run `xion-verify discovery` from the operator laptop.
8. Run `scripts/immortality-drill-rehearsal.sh` before Genesis ceremony with Akash secondary env (`XION_SECONDARY_HEALTH_URL`, `XION_DEPLOYMENT_EVIDENCE`) to prove the doctrine secondary path; use `XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary` only for offline ledger mechanics.

## Current D3 Smoke Registry Row

The currently warmed smoke deployment is `pre-genesis-d3-6` at
`https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai`.

- Chute id: `89866bfc-5ddd-5382-b887-116d8901808f`
- Image id: `971ea1ac-1850-5b26-86af-bc0aa23c7f06`
- Instance id: `02ad3583-f329-437e-b136-00388325a6d2`
- Service disclosure: `xion-relay-chutes-smoke`

This row is suitable for cord-pipeline discovery only. It does not close the
live Relay surface until `scripts/verify-chute-cords.sh --mode=live` passes
against a non-smoke image and the registry row is re-published with the live
image id.

As of the 2026-04-26 live-surface preflight, the d3-6 chute was `COLD` with
zero instances and public probes returned Chutes `503 No instances available`.
Do not publish or promote the row while that state holds. Re-run warmup and the
cord verifier immediately before any registry publication.

## Fallbacks

- If the Chutes hosted model is unhealthy, the Inference Router falls through to the local Ollama floor.
- If the Chutes Relay endpoint is unavailable, cut over to the Akash secondary and publish that registry row (`substrate: "akash"`).
- For additional tertiary substrates post-Genesis, follow `SUBSTRATE-RESILIENCE.md` and extend the provider whitelist (Aleph, Fleek, bare metal, etc.).

## Non-Goals

This runbook does not close `LHT-SUBSTRATE-001` by itself. That residual closes per `docs/SUBSTRATE-RESILIENCE.md` Part IV when portability promotion pre-conditions are met, including verified `xion-verify discovery` and `xion-verify substrate-portability` against a warm Akash secondary (and the annual dry-run cadence).
