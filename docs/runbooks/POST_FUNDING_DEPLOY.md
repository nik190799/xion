# Post-Funding Deploy Runbook

## Property

Complete the funded pre-Genesis deployment closure in one reproducible pass: a GPU-backed Akash open-weights floor, a live Chutes d3 secondary cord (d3-10 in the final operator run), a republished Arweave Relay registry, and the first meaningful Immortality Drill rehearsal.

## Invariants Touched

Strengthens Invariant 17 by moving the open-weights floor out of the operator laptop and into the deployed Akash substrate. Strengthens the Substrate Portability Property by requiring live Akash + Chutes evidence before registry publication. Does not mutate constitutional state.

## Verification

Run `xion-verify inference-sovereignty`, `xion-verify discovery`, and `xion-verify substrate-portability` after the external deployment evidence is captured. `xion-verify schemas` may still report pre-existing source-hash drift unrelated to this deploy; record that drift separately instead of repinning it in this pass.

## Deprecation

This runbook is a closure ledger for the post-funding pre-Genesis deploy. After Genesis, replace it with a standing release checklist and retain this file as historical operator evidence.

## Pre-flight

From the repository root:

```bash
python -c "import yaml; yaml.safe_load(open('infra/akash/relay-deployment.yaml'))"
python -m py_compile xion_relay_chute.py
python -m xion_verify inference-sovereignty
```

Before chain operations, confirm:

- The Arweave registry wallet has AR for `scripts/publish-relay-registry-wsl.sh`.
- The Akash wallet has spendable `uact`, not only `uakt`.
- Chutes credentials are available through the gitignored Chutes env file.
- The operator laptop's Ollama daemon can be stopped during the deployed-floor proof.

## Block A - Akash GPU Sidecar

Use a new Akash deployment sequence when the SDL topology changes:

```bash
export AKASH_CHAIN_ID=akashnet-2
export AKASH_NODE=https://rpc.akashnet.net:443

provider-services tx deployment create infra/akash/relay-deployment.yaml \
  --from <key> --keyring-backend test \
  --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_NODE" \
  --gas auto --gas-adjustment 2 --gas-prices 0.5uakt -y

provider-services query market bid list --owner <addr> --dseq <dseq> \
  --node "$AKASH_NODE" --chain-id "$AKASH_CHAIN_ID"

provider-services tx market lease create --dseq <dseq> --gseq 1 --oseq 1 \
  --provider <provider-address> --from <key> --keyring-backend test \
  --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_NODE" \
  --gas auto --gas-adjustment 2 --gas-prices 0.5uakt -y

provider-services send-manifest infra/akash/relay-deployment.yaml \
  --dseq <dseq> --provider <provider-address> \
  --from <key> --keyring-backend test --node "$AKASH_NODE"

provider-services lease-status --dseq <dseq> --provider <provider-address> \
  --from <key> --keyring-backend test --node "$AKASH_NODE" --auth-type mtls
```

Record after execution:

| Field | Value |
|-------|-------|
| New dseq | `26595076` |
| Provider | `akash1rja3y2ctj3tzmesvh0zfhzzx95rfjw405hwt8d` |
| Accepted `xion-ollama` bid | `429.375054 uact/block` (`rtx3090`) |
| Forwarded HTTPS base | `https://provider.pronto-ai.pp.ua:31503` |
| `send-manifest` to `ready_replicas` | `ready_replicas=1` observed by `provider-services lease-status --auth-type mtls`; exact wall-clock not captured |
| `ready_replicas` to `/health` 200 | `/health` 200 observed after Ollama generation-ready startup gate settled |
| Ollama GPU detected in logs | CUDA backend loaded; `GPULayers:43[ID:GPU-ba251223-c268-a9a2-ed44-619a94cf01f1 Layers:43(0..42)]` |

## Block B - Deployed-Floor Proof

Stop the operator laptop's Ollama daemon, then temporarily set `XION_INFERENCE_POLICY=open_weights_only` in the Akash SDL/env and resend the manifest. Do not set this only on the client-side `curl`; the Relay reads the policy at process start.

```bash
curl -k -sS https://<lease-host>:<externalPort>/health

curl -k -sS -X POST https://<lease-host>:<externalPort>/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"deployed floor smoke: answer in one short sentence","max_tokens":256}'
```

Record after execution:

| Field | Value |
|-------|-------|
| Laptop Ollama stopped | Operator consented; proof path used Akash private `XION_OLLAMA_URL=http://xion-ollama:11434`, not laptop loopback |
| Policy manifest sent | `XION_INFERENCE_POLICY=open_weights_only` update sent after tx `71448122...`; restored to `hosted_api_first` after tx `ADD2D7DED3DE529EC46250D88806914AB7908E39E53B08E7BB68118EFBF476F1` |
| `/chat` status | `200` |
| Wall-clock latency | `8.38s` |
| Provider response snippet | Successful `gemma4:e4b-it-q4_K_M` generated response to `deployed floor smoke: answer in one short sentence` |

Only close `KW-FLOOR-DEPLOY-001` after this table is filled with a successful Akash lease run.

## Block C - Chutes d3-8

The five-command happy path:

```bash
chutes images list --limit 5
pytest orchestrator/tests/test_launcher.py -x
python scripts/verify-chute-import.py
chutes build xion_relay_chute:chute --wait
MODE=live bash scripts/verify-chute-cords.sh
```

If the instance is cold, redeploy/warm and poll before verification:

```bash
chutes deploy xion_relay_chute:chute
chutes chutes get <chute_id>
```

Record after execution:

| Field | Value |
|-------|-------|
| Chute id | `89866bfc-5ddd-5382-b887-116d8901808f` |
| Image id | `a5ab815c-9fb5-5cb9-bcbd-a51535f1abe9` |
| Instance id | `98f0cdf3-e8a0-461d-8a75-a4d3240e0389` (from live worker id `chute-98f0cdf3-e8a0-461d-8a75-a4d3240e0389-hwvrz-205`) |
| Build wall-clock | `6m12s` (`2026-04-29T03:36:27Z` to `2026-04-29T03:42:39Z`) |
| Warmup wall-clock | `3m47s` from warmup start `2026-04-29T05:30:22Z` to all-cords-green verifier |
| Verifier command | `MODE=live bash scripts/verify-chute-cords.sh` |
| Verifier result | `RESULT: all cords green` (`/health`, `/quote`, `/self` all 200) |

Only close `KW-RELAY-CHUTES-D3-001` after the live verifier is green and the registry carries this non-smoke row.

## Block D - Registry Republish

After Akash and Chutes evidence are live, update `ledgers/RELAY_REGISTRY.json`, recompute `payload_sha256`, and publish:

```bash
bash scripts/publish-relay-registry-wsl.sh
python -m xion_verify discovery
python -m xion_verify substrate-portability
```

Record after execution:

| Field | Value |
|-------|-------|
| Registry `as_of_utc_ns` | `1777440937298896100` |
| `payload_sha256` first 16 | `26c69c5f50bd9d8a` |
| Arweave tx id | `KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs` |
| Discovery verifier | `discovery: OK (Relay registry declares Akash primary, Chutes secondary, Arweave, AO, DNS paths)` |
| Substrate-portability verifier | `substrate-portability: OK (dry-run ledger chain and tip parity verified)` after dry-run row `seq=3` |

## Block E - Immortality Drill Rehearsal

Run only after Blocks B-D are green:

```bash
bash scripts/immortality-drill-rehearsal.sh
```

Record after execution:

| Field | Value |
|-------|-------|
| Drill run id | `073d54e2-6763-4242-a960-02154149ac57` |
| Ledger row timestamp | `2026-04-29T05:40:38Z` |
| Primary substrate | `akash-simulated-blackhole` |
| Secondary substrate | `chutes-d3-standby` |
| Result | `passed`; `substrate-portability` row `seq=4`, `orchestrator/tests/test_end_to_end_drill.py` passed, `pre-genesis drill: OK (962dea11-4445-4f96-bfcc-e27da8e08f88)` |

## Cost Ledger

| Item | Observed cost |
|------|---------------|
| Akash lease bid | `429.375054 uact/block` active bid for the combined `xion-ollama` GPU + `xion-relay` workload |
| Akash `xion-ollama` GPU bid | `429.375054 uact/block` (`rtx3090` accepted provider bid) |
| Arweave registry publish | Tx `KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`; exact AR fee not printed by the publish wrapper |
| Chutes build/warmup credit impact | Build consumed one image-history quota slot; warmup allocated one `pro_6000` worker at estimated `$0.20/hour` minimum |

## Time-Budget Ledger

| Step | Observed time |
|------|---------------|
| Akash bid wait | Bid list for `dseq=26595076` returned three providers; exact wait not captured |
| Akash manifest to ready | `ready_replicas=1` confirmed by `lease-status`; exact wait not captured |
| Ollama model pull | Logs show 9.6 GB `gemma4:e4b-it-q4_K_M` pull followed by generation-ready retry and CUDA load |
| Chutes image build | `6m12s` |
| Chutes warmup | `3m47s` to green verifier after a transient `/health` 404 |
| Registry publish confirmation | `10.1s` to tx id and `RELAY_REGISTRY_ARWEAVE_TX.txt` write |

## Failure Modes Seen

- Akash RPC returned one `502 Bad Gateway` during deployment creation; retrying against `https://rpc.akashnet.net:443` succeeded.
- Prior Akash lease `26593426` closed with `insufficient_funds`; operator consented to a new GPU deployment `26595076`.
- Relay initially cached `open_weights_floor_unsatisfied` before the Ollama sidecar was generation-ready. The SDL now gates Relay startup on both `/api/tags` and a one-token `/api/generate`.
- Chutes warmup briefly returned `/health` 404 while `/quote` and `/self` were already live; retry after route propagation returned `RESULT: all cords green`.
