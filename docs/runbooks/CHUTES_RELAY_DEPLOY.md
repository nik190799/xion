# Chutes Relay Deploy Runbook

## Property

Deploy a hosted Relay **Chutes** surface. In the committed registry (`ledgers/RELAY_REGISTRY.json`), **Chutes is `relays[1]` (genesis secondary cord)** and **Akash is `relays[0]` (genesis primary)** — see `xion-verify discovery` and `**docs/runbooks/AKASH_RELAY_DEPLOY.md`** for publication and lease URL. The operator laptop is for local rehearsal only, not the doctrine redundant path.

## Invariants Touched

Strengthens Invariant 17 (Inference Sovereignty Floor) and the Substrate Portability Property. Leaves the local Ollama floor unchanged.

## Verification

Run `MODE=live bash scripts/verify-chute-cords.sh`, `xion-verify discovery`, `xion-verify substrate-portability`, and the Immortality Drill rehearsal after publishing the Relay registry row.

## Local Pre-Flight

Before consuming a Chutes image-history slot for the live Relay image, prove the
same dependency shape locally:

1. Run `pytest orchestrator/tests/test_launcher.py -x` to confirm
  `orchestrator.api.launcher.build_app()` constructs a real `Relay` and full
   `AppDeps`.
2. Run `python -m orchestrator.api` with the Chutes runtime environment and probe
  the configured loopback port (`8010` for `pre-genesis-d3-10`) at `/health`,
   `/pricing`, and `/self`.
3. Run `scripts/verify-chute-import.py` under the Chutes pipx environment to
  confirm `xion_relay_chute:chute` imports and exposes `/health`, `/quote`,
   and `/self`.
4. Only after those checks are green, run the Chutes build/deploy commands.

## Steps

1. Build and verify the Relay image digest with `xion-verify rebuild` or the current release build command.
2. Confirm the local floor is healthy with `xion-verify inference-sovereignty`.
3. Set `XION_CHUTES_API_KEY`, `XION_CHUTES_BASE_URL`, `XION_CHUTES_API_BASE_URL`, `XION_CHUTES_HOSTED_MODEL`, and `XION_CHUTES_TEE_REQUIRED=true` from the encrypted credential vault.
4. Deploy the verified Relay image to the Chutes deployment surface. For updates, use `chutes deploy xion_relay_chute:chute --accept-fee`; without `--accept-fee`, the API/CLI can report stale version metadata even though the platform created a new chute version.
5. Confirm `/health`, `/quote`, and `/self` return OK over the Chutes endpoint with `scripts/verify-chute-cords.sh`. If verifying a smoke image while the next image is blocked by Chutes' image-history quota, pin the assertion explicitly, e.g. `EXPECTED_IMAGE_TAG=pre-genesis-d3-6 bash scripts/verify-chute-cords.sh`. The Chutes platform reserves/intercepts pricing-like routes, so the Relay cord intentionally avoids `/pricing`; a platform pricing response at `/pricing` is expected.
6. Publish the Relay row through `RelayRegistryPublisher` with `substrate="chutes"` and the verified image digest.
7. Run `xion-verify discovery` from the operator laptop.
8. Run `scripts/immortality-drill-rehearsal.sh` before Genesis ceremony with Chutes secondary env (`XION_SECONDARY_HEALTH_URL`, `XION_DEPLOYMENT_EVIDENCE`) to prove the doctrine secondary path; use `XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary` only for offline ledger mechanics.

## Current D3 Live Registry Row

The current live deployment is `pre-genesis-d3-10` at
`https://nikhilkadalge-xion-relay-pre-genesis-d3.chutes.ai`.

- Chute id: `89866bfc-5ddd-5382-b887-116d8901808f`
- Image id: `a5ab815c-9fb5-5cb9-bcbd-a51535f1abe9`
- Instance id: `98f0cdf3-e8a0-461d-8a75-a4d3240e0389` (from worker id `chute-98f0cdf3-e8a0-461d-8a75-a4d3240e0389-hwvrz-205`)
- Service disclosure: `xion-relay-chutes`
- Version: `afaf8384-9915-57f8-a134-0cb743ada71c`
- Verification: `MODE=live bash scripts/verify-chute-cords.sh` returned `RESULT: all cords green` after warmup route propagation.

This row is the non-smoke registry row published in `ledgers/RELAY_REGISTRY.json`
and anchored by Arweave tx `KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`.

Chutes can still return to `COLD` with zero visible instances. Do not treat a
historic registry row as fresh liveness evidence: re-run warmup and the live
cord verifier immediately before any future registry publication or drill.

## d3-10 Live Registry Row Evidence

Filled from the 2026-04-29 operator run.


| Field              | Value                                                      |
| ------------------ | ---------------------------------------------------------- |
| Chute id           | `89866bfc-5ddd-5382-b887-116d8901808f`                     |
| Image id           | `a5ab815c-9fb5-5cb9-bcbd-a51535f1abe9`                     |
| Instance id        | `98f0cdf3-e8a0-461d-8a75-a4d3240e0389`                     |
| Service disclosure | `xion-relay-chutes`                                        |
| Image tag          | `pre-genesis-d3-10`                                        |
| Build wall-clock   | `6m12s` (`2026-04-29T03:36:27Z` to `2026-04-29T03:42:39Z`) |
| Warmup wall-clock  | `3m47s` from warmup start to all-cords-green verifier      |
| Verifier command   | `MODE=live bash scripts/verify-chute-cords.sh`             |
| Verifier result    | `RESULT: all cords green`                                  |


## Findings From Live Chutes Deployment

- **Image-history quota is real:** Chutes enforces `You may only update/create 24 imagehistorys per 24 hours.` Once hit, do not keep trying builds; wait for the rolling window.
- **`--accept-fee` matters on update:** `chutes deploy` without `--accept-fee` can leave CLI/API views stale. Use `chutes deploy xion_relay_chute:chute --accept-fee` for the live update path.
- **Image env was not enough:** Chutes image `.with_env(...)` did not reliably become the Relay subprocess environment. The deployed module now constructs `RELAY_ENV_OVERRIDES`, passes `env=` and `cwd=` to `subprocess.Popen`, and verifies that contract in `scripts/verify-chute-import.py`.
- **Avoid port `8000`:** Chutes Hypercorn owns the main runtime port. The Relay subprocess now binds loopback `127.0.0.1:8010` and Chutes cords proxy into it.
- **Route propagation can lag warmup:** A warmed worker may return live `/quote` and `/self` while `/health` briefly returns `404 {"error":"not found"}`. Wait briefly and rerun the verifier before changing code.
- **Pricing-like paths are platform-owned:** `/pricing`, `/xion/pricing`, and even renamed pricing variants were intercepted or rejected by the platform. Use `/quote` as the public cord that proxies the Relay's local `/pricing`.

## Live Gate Sequence

1. Local pre-flight in this runbook (pytest launcher, loopback API, `verify-chute-import.py`).
2. `chutes images list --limit 5` and confirm the rolling 24-hour image-history quota has cleared.
3. `chutes build xion_relay_chute:chute --wait` → current tag `**pre-genesis-d3-10`**, deploy, warmup (~240s or longer on cold GPU workers).
4. If the chute remains cold, `chutes deploy xion_relay_chute:chute --accept-fee`, then poll `chutes chutes get <chute_id>` until instances are non-zero or run `chutes warmup <chute_id>`.
5. `MODE=live bash scripts/verify-chute-cords.sh` (no smoke envelope; asserts Relay JSON shapes).
6. Update `**ledgers/RELAY_REGISTRY.json**` `relays[1]`: `service: "xion-relay-chutes"`, new `image_id` / `image_tag` / `instance_id`, `last_seen_utc_ns`, recompute `**payload_sha256**`.
7. `**bash scripts/publish-relay-registry-wsl.sh**` to append a new Arweave anchor; update `**ledgers/RELAY_REGISTRY_ARWEAVE_TX.txt**` and `**docs/runbooks/AKASH_RELAY_DEPLOY.md**` snapshot table.
8. Close `**KW-RELAY-CHUTES-D3-001**` live-surface pay-down in `**KNOWN_WEAKNESSES.md**` when the row and verifier evidence match.

## Fallbacks

- If the Chutes hosted model is unhealthy, the Inference Router falls through to the deployed Akash `xion-ollama` floor in Genesis posture, or the local Ollama floor only in D2/local rehearsal.
- If the Chutes Relay endpoint is unavailable, cut user traffic to the **Akash genesis primary** lease URL in `relays[0]` (registry order) and re-publish the registry if the Akash forward changes.
- For additional tertiary substrates post-Genesis, follow `SUBSTRATE-RESILIENCE.md` and extend the provider whitelist (Aleph, Fleek, bare metal, etc.).

## Non-Goals

This runbook does not close `LHT-SUBSTRATE-001` by itself. That residual closes per `docs/SUBSTRATE-RESILIENCE.md` Part IV when portability promotion pre-conditions are met, including verified `xion-verify discovery` and `xion-verify substrate-portability` against a warm doctrine secondary (Chutes in the current registry order) and the annual dry-run cadence.