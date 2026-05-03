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

**Container / TLS / health.** Image must be pullable (e.g. public Docker Hub; SDL may pin `nikhilkadalge/xion-relay:pre-genesis-akash`). Ingress is HTTPS on the forwarded port; the Relay image may use **ephemeral TLS** unless you mount real `XION_TLS_*` — quick checks: **`curl -k https://…/health`**. After manifest `PASS`, allow time for image pull, the GPU-backed `xion-ollama` sidecar to pull `gemma4:e4b-it-q4_K_M`, and `ready_replicas` before `/health` and `open_weights_only` are stable.

**SDL gotchas.** The `placement` key (e.g. `akash`) must match the leaf under `deployment.xion-relay` (see `infra/akash/relay-deployment.yaml`). On SDL v2, `storage` under the compute profile is a list (e.g. `- size: 10Gi`). **`amount` in `pricing` is a max bid per block in `uact`** — tune to market. Adding or removing a service, such as the `xion-ollama` sidecar, changes deployment topology; create a new dseq instead of trying to treat that as an in-place `tx deployment update`.

**Real datapoint.** Example mainnet deployment: `dseq=26563373`, health eventually OK on forwarded `*.nip.io` after manifest pass and pull.

**Doctrine / verifiers.** For the **Akash** row in `ledgers/RELAY_REGISTRY.json`, set `relays[0].endpoint` to that HTTPS base (see `scripts/closeout-genesis-akash-primary-wsl.sh`). For **substrate-portability** drills, the current posture often tests **Chutes** as secondary (step 9 below: Bearer on `/health`). To instead record an **Akash-lease** secondary line (legacy), capture `XION_SECONDARY_HEALTH_URL`, `XION_DEPLOYMENT_EVIDENCE` as `akash://<owner>/<dseq>/<gseq>/<oseq>`, and run `scripts/substrate-portability-dry-run.sh` / `xion-verify substrate-portability` as in **Steps** and **§ Important findings** below.

## Important findings (verified mainnet, 2026-04-26)

These are load-bearing for anyone repeating the CLI path; they are easy to misread from generic Akash docs.

| Finding | Symptom if wrong | Mitigation |
|--------|-------------------|------------|
| Escrow is **`uact` (ACT)**, not `uakt` | `deposit invalid: insufficient balance` while wallet shows plenty of AKT | `tx bme mint-act …uakt`; wait until `query bme ledger --owner <addr>` is **`ledger_record_status_executed`** before `deployment create`. Pending mints do not credit `uact` yet. |
| SDL pricing **`denom: uact`** | `Mismatched denominations (uact != uakt)` or deposit errors | Keep pricing block on **`uact`**; do not put `uakt` in `placement.*.pricing`. |
| **`gas-prices`** too low | `insufficient fees` on `cert publish` / other txs | e.g. `--gas auto --gas-adjustment 2 --gas-prices 0.5uakt` (values drift with network). |
| Client **cert** missing | `could not open certificate PEM file` on `deployment create` | `tx cert generate client` then `tx cert publish client` (same key / keyring). |
| Provider status API **auth** | `JWT has invalid claims` on `lease-status` | Use **`--auth-type mtls`** (default JWT path failed in practice against provider gateway). |
| Forwarded URL + TLS | Connection errors or cert warnings | Ingress uses **HTTPS** on forwarded port; Relay uses **ephemeral TLS** in image unless you mount real `XION_TLS_*` — use **`curl -k`** for smoke checks. **`xion_ops akash deploy`** probes **`GET /health`** via **WSL `curl -k`** on Windows (falls back to urllib on non-Windows) because native Windows stacks sometimes time out toward provider forwards that WSL reaches. |
| **Registry publish automation** | Operator forgets manual Arweave publication after lease | **`python -m xion_ops deploy relay-akash`** publishes `ledgers/RELAY_REGISTRY.json` after lease health unless **`--no-publish-registry`** — use `--no-publish-registry` for rehearsals / dry leases. |
| Hostname / port | Stale bookmarks | `forwarded_ports` (**`host` + `externalPort`**) change per lease/provider; always re-read **`lease-status`**. |
| Open-weights floor location | `open_weights_only` works only while the operator laptop is on | The SDL carries a private `xion-ollama` sidecar and sets `XION_OLLAMA_URL=http://xion-ollama:11434`; do not count a laptop-local Ollama daemon as deployed-floor evidence. |
| GPU sidecar pricing | CPU-sized bids never clear GPU leases, or the provider schedules a CPU-only floor that times out | The `xion-ollama` sidecar starts at **`10000 uact`/block** and requests one NVIDIA GPU. Tune this from observed `bid list`, then record the accepted bid in `docs/runbooks/POST_FUNDING_DEPLOY.md`. |
| RPC node reliability | `deployment create` fails with `502 Bad Gateway` / invalid JSON from the RPC server | Retry against a stable RPC such as `https://rpc.akashnet.net:443`; do not treat one RPC 502 as a deployment design failure. |
| Closed lease after funding drift | Public endpoint refuses connections and `lease-status` shows closed / `insufficient_funds` | Check the lease state before editing the registry. If the lease is closed, create a new deployment/lease with operator consent instead of republishing a dead endpoint. |
| Ollama `/api/tags` is not enough readiness | Relay boots, caches `open_weights_floor_unsatisfied`, and `/chat` returns 503 even though the model appears in tags | Gate Relay startup on a successful small `/api/generate` call after `/api/tags` lists the model. The current SDL does this before `exec /usr/local/bin/entrypoint-xion-orchestrator-api.sh`. |
| `open_weights_only` is read at process start | Client-side `XION_INFERENCE_POLICY=open_weights_only curl ...` does not change the deployed Relay policy | Temporarily edit the SDL/env and `send-manifest`, wait for the Relay restart, run the proof, then restore `hosted_api_first` with a second manifest update. |
| Chat smoke payload validation | `/chat` returns 422 for too-small `max_tokens` | Use `max_tokens >= 1024` for the deployed proof payload. |

**Historical proof (CPU-only Relay deployment):** `dseq=26563373`, health reachable at forwarded `*.nip.io` after manifest `PASS` and image pull. This predates the GPU-backed `xion-ollama` sidecar and does **not** close `KW-FLOOR-DEPLOY-001`.

**GPU floor proof ledger (fill during next live deploy):**

| Field | Value |
|-------|-------|
| New dseq | `26595076` |
| Provider | `akash1rja3y2ctj3tzmesvh0zfhzzx95rfjw405hwt8d` |
| Accepted `xion-ollama` bid | `429.375054 uact/block` (`rtx3090`) |
| Forwarded HTTPS base | `https://provider.pronto-ai.pp.ua:31503` |
| `send-manifest` to `ready_replicas` | `ready_replicas=1` observed by `provider-services lease-status --auth-type mtls`; exact wall-clock not captured |
| `ready_replicas` to `/health` 200 | `/health` 200 observed after the generation-ready Ollama startup gate settled |
| Ollama GPU detected in logs | CUDA backend loaded; `GPULayers:43[ID:GPU-ba251223-c268-a9a2-ed44-619a94cf01f1 Layers:43(0..42)]` |

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

   Use `forwarded_ports` (host + `externalPort`) with **`curl -k https://<host>:<externalPort>/health`** until `ready_replicas` catches up (image pull and the GPU-backed Ollama sidecar model pull can take several minutes). Record the accepted GPU bid, provider, dseq, forwarded base, and wall-clock timings in `docs/runbooks/POST_FUNDING_DEPLOY.md` before closing any `KW-` entry.
6. Inject only deployment secrets required for the Relay posture (optional overrides beyond the SDL `env` block).
7. Confirm `/health` returns OK over the lease endpoint (TLS uses the container entrypoint’s ephemeral cert unless you mount real `XION_TLS_*` material; use `curl -k` for quick checks).
8. Confirm the deployed open-weights floor is not the operator laptop:

   ```bash
   # The Relay env must point at the private sidecar:
   #   XION_OLLAMA_URL=http://xion-ollama:11434
   #   XION_OLLAMA_FLOOR_MODEL=gemma4:e4b-it-q4_K_M

   # From inside the lease/container shell if provider-services exposes one,
   # or from Relay startup logs:
   curl -sS http://xion-ollama:11434/api/tags
   ```

   Then stop or ignore the operator laptop's local Ollama daemon and run one
   `/chat` smoke turn against the Akash HTTPS base. If the deployment has no
   `XION_CHUTES_API_KEY`, the Genesis Default `hosted_api_first` router has no
   hosted provider to choose and the turn exercises the floor. If Chutes
   credentials are injected, do **not** prefix the client `curl` with
   `XION_INFERENCE_POLICY=open_weights_only` — that changes only the caller's
   shell. Instead, do a temporary manifest update with
   `XION_INFERENCE_POLICY=open_weights_only`, send the manifest, wait for the
   Relay to restart, run the smoke turn, then restore `hosted_api_first`.

   ```bash
   curl -k -sS -X POST https://<lease-host>:<externalPort>/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"deployed floor smoke: answer in one short sentence","max_tokens":1024}'
   ```

   `KW-FLOOR-DEPLOY-001` remains open until that turn succeeds with the
   laptop-local daemon out of the runtime path.
9. When **Chutes is the secondary** substrate in the current posture, record the dry-run against **Chutes** `/health` (Bearer from `chutes.env`, same as `scripts/verify-chute-cords.sh`):

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

10. Run `xion-verify substrate-portability`.
11. **Publish** the committed `ledgers/RELAY_REGISTRY.json` to Arweave (genesis snapshot). `relays[0]` **must** be the real Akash lease HTTPS base (not `…-pending.invalid`). Use `bash scripts/closeout-genesis-akash-primary-wsl.sh` with `XION_AKASH_HTTPS_BASE` first if the file still has a placeholder.
12. Run `xion-verify discovery` (expect **`OK`** once both relays carry real `ed25519:` public keys — use **`python scripts/gen-relay-registry-ed25519-pubkeys.py`** once, then retain **`secrets/relay_registry_ed25519.json`** only on operator hosts).

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

Arweave findings from the operator-track publish:

- The registry hash is computed over the document **without** `payload_sha256`, using sorted keys and minified separators. Recompute before publishing; `scripts/publish-relay-registry-arweave.py` refuses a mismatch.
- The published bytes are the full sorted/minified registry document **including** `payload_sha256`; the `payload_sha256` field is therefore a pre-publish content commitment, not a hash of the exact transaction bytes.
- Keep `ledgers/RELAY_REGISTRY_ARWEAVE_TX.txt` to a single latest tx id. Older txs remain permanent on Arweave and are recorded in the table below, but the file tracks the current registry anchor.
- A successful publish is not enough by itself: immediately rerun `xion-verify discovery` and `xion-verify substrate-portability` against the same working tree so the Arweave tx, local registry bytes, and verifier state are tied together in the closeout evidence.

| as_of (ledger) | payload_sha256 (first 16 hex) | Arweave tx id | Notes |
|----------------|------------------------------|---------------|--------|
| `1777352717050742000` | `f601a8b1b299ccd6` | **`n6OCNc5mfsgDBdBOUYJsS7tYo980lNQnWgzJzDYdyqE`** (2026-04-28, pubkey-bound) | Supersedes tx `vEvdNUQt…` after `gen-relay-registry-ed25519-pubkeys.py`. Gate: `https://arweave.net/tx/n6OCNc5mfsgDBdBOUYJsS7tYo980lNQnWgzJzDYdyqE` |
| `1777440937298896100` | `26c69c5f50bd9d8a` | **`KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs`** (2026-04-29, Akash GPU floor + Chutes d3-10 live) | Closes the operator-track registry publish after Akash `/chat` open-weights proof and `MODE=live bash scripts/verify-chute-cords.sh` returned all cords green. Gate: `https://arweave.net/tx/KXBVha3Qq4YEHlTXRVHdx7qz9UaJysmOgz_LeTfJLHs` |

The script uses the same JSON bytes as the on-disk registry (minified, sorted keys) so `payload_sha256` matches `xion-verify discovery` hashing.

### Steady-state (lease + drills)

- Re-run **`bash scripts/akash-lease-status.sh`** after any deploy or provider change; **`forwarded_ports`** (`host`, `externalPort`) move with the lease — refresh `relays[0].endpoint` and republish when they do (avoid blindly re-running `closeout` if you only need a registry hash bump without a new substrate dry-run row).
- **`curl -k https://<lease-base>/health`** on cadence you trust for your SLA.
- **`docs/runbooks/IMMORTALITY_DRILL.md`** — rehearse failover when you change registry posture or cord auth.

## Appendix — forwarded ingress TLS (`*.nip.io`) and PowerShell clients

Forwarded Akash ingress often presents a certificate whose **SAN does not include** the exact `provider.*.nip.io` hostname printed by `lease-status`. **`curl -k`** / **`curl --insecure`** remains the practical smoke posture (see changelog closeout examples). PowerShell 7+:

```powershell
Invoke-WebRequest -Uri "https://<host>:<port>/health" -SkipCertificateCheck
```

This addresses **operator ergonomics**, not Covenant transport semantics for eventual Genesis-hard ceremony URLs; pin real operator-controlled DNS names and matching certs when you need strict PKIX validation everywhere.

## Appendix — `arbiter_healthy` vs open-weights floor

`GET /health` exposes **`relay_healthy`**, **`arbiter_healthy`**, and related fields. **`arbiter_healthy: false`** means the Relay-side supervisor has not satisfied its Arbiter heartbeat contract within the doctrine grace window (`orchestrator/relay/relay.py`, `orchestrator/tests/test_relay_supervisor.py`). That posture is **orthogonal** to Inference Router **`open_weights_floor_unsatisfied`** on `POST /chat`. Treating Arbiter watchdog recovery as identical to **`KW-FLOOR-DEPLOY-001`** closure is incorrect — floor closure still requires the GPU SDL **with** **`xion-ollama`** and the external `/chat` proof in **Steps §8**.

## KW-FLOOR-DEPLOY-001 — operator closure checklist (GPU SDL only)

Closing **[`KW-FLOOR-DEPLOY-001`](../../KNOWN_WEAKNESSES.md)** requires **`infra/akash/relay-deployment.yaml`** (the GPU-backed **`xion-ollama`** topology), never the CPU-only relight YAML alone:

| Step | Action |
|------|--------|
| 1 | Build/push Relay image digest; GPU SDL **`placement`** / **`denom`** / cert / gas discipline per **Important findings**. |
| 2 | **`deployment create` → bid → lease → send-manifest`;** poll **`lease-status --auth-type mtls`**. |
| 3 | **`curl -k https://<host>:<externalPort>/health`** until **`ready_replicas`** and Gemma cold-start gate complete. |
| 4 | From a network **outside** laptop-local-only Ollama: **`POST /chat`** with **`max_tokens>=1024`**. For **`open_weights_only`** proof you must **`send-manifest`** the env onto the Relay (temporary flip), smoke, flip back (**§Important findings**, “read at process start”). |
| 5 | **`scripts/substrate-portability-dry-run.sh`** / evidence rows as posture requires; **`xion-verify substrate-portability`**. |
| 6 | Update **[`ledgers/RELAY_REGISTRY.json`](../../ledgers/RELAY_REGISTRY.json)** `relays[0]` (HTTPS base not placeholder, **`instance_class`** honesty for GPU+floor, **`payload_sha256`**, **`last_seen_utc_ns`**). **`bash scripts/publish-relay-registry-wsl.sh`**, refresh **`ledgers/RELAY_REGISTRY_ARWEAVE_TX.txt`**. |
| 7 | **`xion-verify discovery`** **`OK`;** amend **`KW-FLOOR-DEPLOY-001`** in **`KNOWN_WEAKNESSES.md`** only **after** the external smoke evidence exists. |

**Registry-only bumps** — If the forwarded URL **does not** change, you still re-hash and may republish, but **do not** declare **`KW-FLOOR-DEPLOY-001`** closed without the GPU-floor `/chat` evidence row.

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
