# Post-Funding Deploy Runbook

## Property

Complete the funded pre-Genesis deployment closure in one reproducible pass: a GPU-backed Akash open-weights floor, a live Chutes d3-8 secondary cord, a republished Arweave Relay registry, and the first meaningful Immortality Drill rehearsal.

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
| New dseq | `PENDING_OPERATOR_EXECUTION` |
| Provider | `PENDING_OPERATOR_EXECUTION` |
| Accepted `xion-ollama` bid | `PENDING_OPERATOR_EXECUTION` |
| Forwarded HTTPS base | `PENDING_OPERATOR_EXECUTION` |
| `send-manifest` to `ready_replicas` | `PENDING_OPERATOR_EXECUTION` |
| `ready_replicas` to `/health` 200 | `PENDING_OPERATOR_EXECUTION` |
| Ollama GPU detected in logs | `PENDING_OPERATOR_EXECUTION` |

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
| Laptop Ollama stopped | `PENDING_OPERATOR_EXECUTION` |
| Policy manifest sent | `PENDING_OPERATOR_EXECUTION` |
| `/chat` status | `PENDING_OPERATOR_EXECUTION` |
| Wall-clock latency | `PENDING_OPERATOR_EXECUTION` |
| Provider response snippet | `PENDING_OPERATOR_EXECUTION` |

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
| Chute id | `PENDING_OPERATOR_EXECUTION` |
| Image id | `PENDING_OPERATOR_EXECUTION` |
| Instance id | `PENDING_OPERATOR_EXECUTION` |
| Build wall-clock | `PENDING_OPERATOR_EXECUTION` |
| Warmup wall-clock | `PENDING_OPERATOR_EXECUTION` |
| Verifier command | `MODE=live bash scripts/verify-chute-cords.sh` |
| Verifier result | `PENDING_OPERATOR_EXECUTION` |

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
| Registry `as_of_utc_ns` | `PENDING_OPERATOR_EXECUTION` |
| `payload_sha256` first 16 | `PENDING_OPERATOR_EXECUTION` |
| Arweave tx id | `PENDING_OPERATOR_EXECUTION` |
| Discovery verifier | `PENDING_OPERATOR_EXECUTION` |
| Substrate-portability verifier | `PENDING_OPERATOR_EXECUTION` |

## Block E - Immortality Drill Rehearsal

Run only after Blocks B-D are green:

```bash
bash scripts/immortality-drill-rehearsal.sh
```

Record after execution:

| Field | Value |
|-------|-------|
| Drill run id | `PENDING_OPERATOR_EXECUTION` |
| Ledger row timestamp | `PENDING_OPERATOR_EXECUTION` |
| Primary substrate | `akash-simulated-blackhole` |
| Secondary substrate | `PENDING_OPERATOR_EXECUTION` |
| Result | `PENDING_OPERATOR_EXECUTION` |

## Cost Ledger

| Item | Observed cost |
|------|---------------|
| Akash `xion-relay` bid | `PENDING_OPERATOR_EXECUTION` |
| Akash `xion-ollama` GPU bid | `PENDING_OPERATOR_EXECUTION` |
| Arweave registry publish | `PENDING_OPERATOR_EXECUTION` |
| Chutes build/warmup credit impact | `PENDING_OPERATOR_EXECUTION` |

## Time-Budget Ledger

| Step | Observed time |
|------|---------------|
| Akash bid wait | `PENDING_OPERATOR_EXECUTION` |
| Akash manifest to ready | `PENDING_OPERATOR_EXECUTION` |
| Ollama model pull | `PENDING_OPERATOR_EXECUTION` |
| Chutes image build | `PENDING_OPERATOR_EXECUTION` |
| Chutes warmup | `PENDING_OPERATOR_EXECUTION` |
| Registry publish confirmation | `PENDING_OPERATOR_EXECUTION` |

## Failure Modes Seen

- `PENDING_OPERATOR_EXECUTION`: replace with exact command, stderr/stdout summary, mitigation, and whether a new `KW-` entry was opened.
