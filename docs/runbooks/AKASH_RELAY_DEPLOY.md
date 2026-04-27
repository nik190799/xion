# Akash Relay Deploy Runbook

> **Current registry posture: Akash primary, Chutes secondary.** `ledgers/RELAY_REGISTRY.json` lists **Akash at `relays[0]`** and **Chutes at `relays[1]`**; `xion-verify discovery` enforces that order. (Earlier docs called Chutes “primary” and Akash “secondary” when Chutes was listed first; the verifier now keys off list order, not the word “primary” in runbooks.) The operator laptop is for local rehearsal (`xion local`) only, not the doctrine redundant path.

## Property

Deploy a Relay on Akash as the **genesis primary** hosted substrate in the registry (row order), with Chutes as the long-lived secondary cord surface when applicable. The registry still lists every discovery path (`arweave_registry`, `ao_process`, `dns_seed`, and the `akash_secondary` name — the path label is not the same as “Akash is listed second”).

## Single-page model (bookmark)

**What Akash is doing.** You define a deployment in SDL (YAML): image, CPU/RAM/storage, env, exposed port, and **pricing in the right denom**. On-chain: create the deployment, providers bid, you accept a lease, then `send-manifest` so the provider runs the workload. The provider returns a **forwarded host + port** (often `*.nip.io`); that HTTPS URL is the public entry to the container.

**Money & denom (easy to get wrong).** Escrow and deployment deposits use **`uact` (ACT)**, not `uakt`, in the pricing block. Mint ACT with BME: burn/send `uakt` via `tx bme mint-act`, then wait until the BME ledger row is **`ledger_record_status_executed`** and **`uact` appears in bank balances**; pending mints are not spendable as `uact` yet. SDL `placement.*.pricing` must say **`denom: uact`**; using `uakt` there leads to denomination / deposit errors.

**Chain & CLI.** Mainnet: `akashnet-2`, RPC e.g. `https://rpc.akashnet.net:443` (same as **Steps** below). Tooling: `provider-services` (deployment create, lease, manifest, `lease-status`). If txs fail with insufficient fees, raise `--gas-prices` (e.g. `0.5uakt`) with `--gas auto` / adjustment.

**Certificates.** A **client cert** must exist on disk before `deployment create`: `tx cert generate client` then `tx cert publish client` for the same key / keyring.

**Provider API / URL.** `lease-status` against the provider gateway: default JWT auth failed in practice; use **`--auth-type mtls`**. **Forwarded ports** (`host`, `externalPort`) are per lease/provider — always re-read `lease-status`; do not assume a fixed URL.

**Container / TLS / health.** Image must be pullable (e.g. public Docker Hub; SDL may pin `nikhilkadalge/xion-relay:pre-genesis-akash`). Ingress is HTTPS on the forwarded port; the Relay image may use **ephemeral TLS** unless you mount real `XION_TLS_*` — quick checks: **`curl -k https://…/health`**. After manifest `PASS`, allow time for image pull and `ready_replicas` before `/health` is stable.

**SDL gotchas.** The `placement` key (e.g. `akash`) must match the leaf under `deployment.xion-relay` (see `infra/akash/relay-deployment.yaml`). On SDL v2, `storage` under the compute profile is a list (e.g. `- size: 10Gi`). **`amount` in `pricing` is a max bid per block in `uact`** — tune to market.

**Real datapoint.** Example mainnet deployment: `dseq=26563373`, health eventually OK on forwarded `*.nip.io` after manifest pass and pull.

**Doctrine / verifiers.** For the **Akash** row in `ledgers/RELAY_REGISTRY.json`, set `relays[0].endpoint` to that HTTPS base (see `scripts/closeout-genesis-akash-primary-wsl.sh`). For **substrate-portability** drills, the current posture often tests **Chutes** as secondary (step 8 below: Bearer on `/health`). To instead record an **Akash-lease** secondary line (legacy), capture `XION_SECONDARY_HEALTH_URL`, `XION_DEPLOYMENT_EVIDENCE` as `akash://<owner>/<dseq>/<gseq>/<oseq>`, and run `scripts/substrate-portability-dry-run.sh` / `xion-verify substrate-portability` as in **Steps** and **§ Important findings** below.

## Important findings (verified mainnet, 2026-04-26)

These are load-bearing for anyone repeating the CLI path; they are easy to misread from generic Akash docs.

| Finding | Symptom if wrong | Mitigation |
|--------|-------------------|------------|
| Escrow is **`uact` (ACT)**, not `uakt` | `deposit invalid: insufficient balance` while wallet shows plenty of AKT | `tx bme mint-act …uakt`; wait until `query bme ledger --owner <addr>` is **`ledger_record_status_executed`** before `deployment create`. Pending mints do not credit `uact` yet. |
| SDL pricing **`denom: uact`** | `Mismatched denominations (uact != uakt)` or deposit errors | Keep pricing block on **`uact`**; do not put `uakt` in `placement.*.pricing`. |
| **`gas-prices`** too low | `insufficient fees` on `cert publish` / other txs | e.g. `--gas auto --gas-adjustment 2 --gas-prices 0.5uakt` (values drift with network). |
| Client **cert** missing | `could not open certificate PEM file` on `deployment create` | `tx cert generate client` then `tx cert publish client` (same key / keyring). |
| Provider status API **auth** | `JWT has invalid claims` on `lease-status` | Use **`--auth-type mtls`** (default JWT path failed in practice against provider gateway). |
| Forwarded URL + TLS | Connection errors or cert warnings | Ingress uses **HTTPS** on forwarded port; Relay uses **ephemeral TLS** in image unless you mount real `XION_TLS_*` — use **`curl -k`** for smoke checks. |
| Hostname / port | Stale bookmarks | `forwarded_ports` (**`host` + `externalPort`**) change per lease/provider; always re-read **`lease-status`**. |

**Live proof (one deployment):** `dseq=26563373`, health reachable at forwarded `*.nip.io` after manifest `PASS` and image pull (allow several minutes for `ready_replicas`).

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
8. When **Chutes is the secondary** substrate in the current posture, record the dry-run against **Chutes** `/health` (Bearer from `chutes.env`, same as `scripts/verify-chute-cords.sh`):

   ```bash
   export XION_SECONDARY_SUBSTRATE_ID=chutes-d3-standby
   export XION_SECONDARY_PROVIDER=chutes
   export XION_SECONDARY_HEALTH_URL="https://<chute-host>/health"
   export XION_DEPLOYMENT_EVIDENCE="chutes://<chute_id>/<instance_id>"
   export XION_PRIMARY_STATE_TIP=<tip>
   export XION_SECONDARY_STATE_TIP=<tip>
   export XION_SECONDARY_HEALTH_BEARER="$CHUTES_API_KEY"
   bash scripts/substrate-portability-dry-run.sh
   ```

   (Legacy: if the secondary under test is an Akash lease, use `akash-testnet-standby`, `XION_SECONDARY_PROVIDER=akash`, and `XION_DEPLOYMENT_EVIDENCE=akash://...`; for TLS ingress self-signed certs, set `XION_SECONDARY_HEALTH_CURL_INSECURE=1`.) Optional one-shot (sets registry Akash base + dry-run): `XION_AKASH_HTTPS_BASE=https://<lease-host:port> bash scripts/closeout-genesis-akash-primary-wsl.sh`

9. Run `xion-verify substrate-portability`.
10. **Publish** the committed `ledgers/RELAY_REGISTRY.json` to Arweave (genesis snapshot). `relays[0]` **must** be the real Akash lease HTTPS base (not `…-pending.invalid`). Use `bash scripts/closeout-genesis-akash-primary-wsl.sh` with `XION_AKASH_HTTPS_BASE` first if the file still has a placeholder.
11. Run `xion-verify discovery` (expect `NOT_YET_SEALED` until non-placeholder `public_key` values are bound on both relays).

### Arweave registry snapshot (genesis)

From the repository root (Python path must include the repo for `orchestrator`):

```bash
export XION_REGISTRY_WALLET_JWK_PATH=/path/to/registry_wallet.json   # or default $HOME/.aos.json via wrapper
# The wallet must hold **AR** (non-zero winston balance) or the transaction will not land.
# Optional: only if you intentionally publish before fixing the Akash URL in git:
# export XION_ALLOW_PENDING_AKASH_ENDPOINT=1

bash scripts/publish-relay-registry-wsl.sh
# (creates .venv-arweave if needed, then runs publish-relay-registry-arweave.py)
```

On success the transaction id is printed and should be written as **a single line** to **`ledgers/RELAY_REGISTRY_ARWEAVE_TX.txt`**. Record that id in **[CHANGELOG.md](../../CHANGELOG.md)** and in the table below. If the wallet had **0 AR**, the script exits **4**; fund the JWK’s Arweave address, then re-run.

| as_of (ledger) | payload_sha256 (first 16 hex) | Arweave tx id | Notes |
|----------------|------------------------------|---------------|--------|
| `1777250293007090619` | `fc3b3db0175087e8` | *NOT_CONFIRMED — registry JWK had **0 AR**; `publish-relay-registry-wsl.sh` now exits 4 until funded* | `relays[0]` = `https://provider.161.97.85.20.nip.io:30564` (lease dseq=26563373). See `ledgers/RELAY_REGISTRY_ARWEAVE_TX.txt` for wallet address + retry steps. |

The script uses the same JSON bytes as the on-disk registry (minified, sorted keys) so `payload_sha256` matches `xion-verify discovery` hashing.

## Preflight

From the repository root:

```bash
bash scripts/akash-secondary-preflight.sh
```

The preflight is intentionally read-only. It checks the local Akash tooling,
Docker CLI, Relay digest file, and whether the Akash SDL still contains the
placeholder image. It does not create a lease, spend AKT, or append
`ledgers/SUBSTRATE_DRYRUN_LEDGER.jsonl`.

`scripts/substrate-portability-dry-run.sh` refuses to append a non-laptop
secondary row (Akash, Aleph, or Chutes) without a live `XION_SECONDARY_HEALTH_URL`
and deployment evidence. This keeps `xion-verify substrate-portability` from
going green on fake substrate ids.

## Non-goals

This runbook does not decommission Cloudflare by itself and does not claim a three-host floor. Those remain `KW-OPS-001` operator actions until Chutes + Akash + any additional whitelisted paths are live and verified.
