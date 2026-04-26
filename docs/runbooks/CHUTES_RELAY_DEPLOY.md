# Chutes Relay Deploy Runbook

## Property

Deploy the Genesis primary Relay on Chutes while preserving the operator-laptop secondary and the Akash standby blueprint as separate fallback paths.

## Invariants Touched

Strengthens Invariant 17 (Inference Sovereignty Floor) and the Substrate Portability Property. Leaves the local Ollama floor unchanged.

## Verification

Run `xion-verify discovery`, `xion-verify inference-provider-chutes`, and `xion-verify pre-genesis` after publishing the Relay registry row.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild` or the current release build command.
2. Confirm the local floor is healthy with `xion-verify inference-sovereignty`.
3. Set `XION_CHUTES_API_KEY`, `XION_CHUTES_BASE_URL`, `XION_CHUTES_API_BASE_URL`, `XION_CHUTES_HOSTED_MODEL`, and `XION_CHUTES_TEE_REQUIRED=true` from the encrypted credential vault.
4. Deploy the verified Relay image to the Chutes deployment surface.
5. Confirm `/health`, `/quote`, and `/self` return OK over the Chutes endpoint with `scripts/verify-chute-cords.sh`. If verifying the currently deployed smoke image while the next image is blocked by Chutes' image-history quota, pin the assertion explicitly, e.g. `EXPECTED_IMAGE_TAG=pre-genesis-d3-6 bash scripts/verify-chute-cords.sh`. The Chutes platform reserves/intercepts pricing-like routes, so the smoke cord intentionally avoids `/pricing`; a platform pricing response at `/pricing` is expected.
6. Publish the Relay row through `RelayRegistryPublisher` with `substrate="chutes"` and the verified image digest.
7. Run `xion-verify discovery` from the operator laptop.
8. Run `scripts/immortality-drill-rehearsal.sh` before Genesis ceremony to prove the laptop-secondary path still works.

## Fallbacks

- If the Chutes hosted model is unhealthy, the Inference Router falls through to the local Ollama floor.
- If the Chutes Relay endpoint is unavailable, start the operator-laptop secondary and publish that registry row.
- If the operator chooses to provision a third-party secondary post-Genesis, use `AKASH_RELAY_DEPLOY.md` as the first standby blueprint.

## Non-Goals

This runbook does not close `LHT-SUBSTRATE-001` by itself. That residual closes only when a third-party secondary is provisioned and verified by `xion-verify discovery` and `xion-verify substrate-portability`.
