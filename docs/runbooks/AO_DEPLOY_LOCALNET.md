# AO Core Deploy from a Local AO Stack (Phase 6.1.b Finalization Runbook)

> **Audience.** The Xion operator. Run this from a Windows + WSL2 workstation (or any host with Docker + bash + the `aos` CLI).
>
> **Property delivered.** A reproducible AO testnet deployment of [`ao/core/main.lua`](../../ao/core/main.lua) against a Xion-controlled local AO substrate (the [`infra/ao-localnet/`](../../infra/ao-localnet/) Docker stack), a verifiable [`genesis/AO_DEPLOY_RECEIPT.json`](../../genesis/AO_DEPLOY_RECEIPT.json) with `substrate: "localnet"`, a first `commit-state` message accepted by the AO process, and a seed row in [`ledgers/STATE_CHAIN_LEDGER.jsonl`](../../ledgers/STATE_CHAIN_LEDGER.jsonl). When this runbook completes, `xion-verify ao-handlers` flips from `NOT_YET_SEALED` to `OK` against `XION_AO_GATEWAY_URL=http://localhost:4004`.
>
> **Why this exists alongside [AO_DEPLOY_WSL2.md](AO_DEPLOY_WSL2.md).** The WSL2 runbook depends on the upstream legacy MU at `https://mu.ao-testnet.xyz`, which has been HTTP 500-ing across multiple spawn attempts (see [`KW-AOCORE-004`](../../KNOWN_WEAKNESSES.md)). Doctrine [`docs/28-AO-CORE.md` § "Substrate amendment (Phase 6.1.b)"](../28-AO-CORE.md) authorizes a Xion-local AO substrate as an equally-valid Phase 6.1 testnet seal target. This runbook is the operator path for that substrate.
>
> **Substrate scope (read this first).** A `process_id` produced on this localnet is reproducible by anyone with this repo + Docker, but is NOT queryable from the public AO mainnet GraphQL or the public CU. Public-Arweave durability is a separately-tracked Phase 6+ Tier-3 mainnet ceremony obligation. Phase 6.1's "testnet seal" bar is "the handler ABI works against a real AO compute unit + the receipt is reproducible by a third-party operator", which this localnet path satisfies.

---

## Prereqs (one-time)

### 1. WSL2 + Ubuntu (Windows operators only; macOS/Linux skip to step 2)

Same as [AO_DEPLOY_WSL2.md § Prereqs 1](AO_DEPLOY_WSL2.md). If WSL2 is not yet installed:

```powershell
wsl --install -d Ubuntu
```

Reboot when prompted. Open Ubuntu, set UNIX username + password.

### 2. Docker + Compose v2.20+

Inside WSL2 (or your shell of choice), confirm Docker is installed and the daemon is reachable:

```bash
docker --version
docker compose version
docker info >/dev/null && echo "daemon OK"
```

You need **Docker Compose v2.20 or newer** (released August 2023) because the wrapper at [`infra/ao-localnet/docker-compose.yaml`](../../infra/ao-localnet/docker-compose.yaml) uses the `include:` directive. If your `docker compose version` is older, install Docker Desktop's latest stable on Windows OR upgrade `docker-compose-plugin` on your distro.

If you do not have Docker installed: install Docker Desktop on Windows with the WSL2 backend enabled (recommended for this workstation per `KW-AOCORE-003`-era environment notes), or `apt-get install docker.io docker-compose-plugin` inside WSL2 Ubuntu and start the daemon.

### 3. `aos` CLI in WSL2 + Node 20 LTS

Same as [AO_DEPLOY_WSL2.md § Prereqs 2-3](AO_DEPLOY_WSL2.md). Brief recap:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
exec $SHELL -l
nvm install 20 && nvm use 20 && nvm alias default 20
npm i -g https://get_ao.arweave.net
aos --version
```

> **Critical (aos 2.0+).** `aos` 2.0 defaults to AO mainnet without `--legacy`. For Phase 6.1 you MUST always pass `--legacy` AND additionally point `--gateway-url`/`--cu-url`/`--mu-url` at the local stack so even an accidental missing `--legacy` cannot reach mainnet. Step 5 below pins the exact invocation.

### 4. Confirm repo path is reachable

WSL2 mounts the Windows filesystem at `/mnt/c/`. Confirm:

```bash
ls /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
sha256sum /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

Capture the `sha256sum` output — this is the `lua_source_sha256` receipt field.

---

## Bring up the localnet substrate

### 5. Run the bootstrap script

From the repo root, inside WSL2 (or your bash shell):

```bash
cd /mnt/c/Users/16823/CursorProjects/xion-os
bash scripts/ao-localnet-up.sh
```

The script:

1. Verifies Docker daemon and Compose v2 are available.
2. Clones [`permaweb/ao-localnet`](https://github.com/permaweb/ao-localnet) at the pinned commit (default `2f9f98ea2e7a7d77f1791df382afb3446edc044e`, 2024-04-10) into `infra/ao-localnet/.upstream/` (gitignored).
3. Runs the upstream's `wallets/generateAll.sh` to create localnet wallets (one-time).
4. Brings up the stack with `docker compose -f infra/ao-localnet/docker-compose.yaml up -d --wait`.
5. Polls `http://localhost:4004/state/<probe-pid>` until the CU responds with HTTP 200 or 404 (either means "CU is responding").

**First-time run: 10–15 minutes.** Most of that is `docker build` for `arlocal`, `cu`, `mu`, `su`, `bundler` from upstream sources. Subsequent runs are seconds (Docker layer cache).

When the script prints `[ao-localnet-up] OK. Localnet substrate is up.`, the substrate is ready.

> **If the build fails because an upstream base image or npm package has rotted** (the upstream repo was last touched 2024-04-10), follow the fallback in [`infra/ao-localnet/README.md`](../../infra/ao-localnet/README.md) § "Fallback (when upstream is rotted)" — point the script at the `weavedb/ao-localnet` community fork or another known-working pin via `XION_AO_LOCALNET_UPSTREAM` and `XION_AO_LOCALNET_COMMIT`. Record any deviation in `KW-AOCORE-004`.

### 6. Verify ports are exposed

```bash
curl -s http://localhost:4004/state/probe-pid -o /dev/null -w "cu:    %{http_code}\n"
curl -s http://localhost:4002/                  -o /dev/null -w "mu:    %{http_code}\n"
curl -s http://localhost:4003/                  -o /dev/null -w "su:    %{http_code}\n"
curl -s http://localhost:4000/info              -o /dev/null -w "arl:   %{http_code}\n"
```

Expected: each line shows a non-5xx HTTP code (404 is fine — the path is wrong but the service is responding).

---

## Deploy

### 7. Spawn an AO process targeting the localnet stack

The critical change versus [AO_DEPLOY_WSL2.md § 5](AO_DEPLOY_WSL2.md): every URL flag is pinned to `http://localhost:<port>`, so even if `--legacy` were silently dropped by some future `aos` upgrade, the connection would fail-closed (refuse to connect to mainnet) instead of silently spawning on mainnet.

```bash
aos xion-core-localnet --legacy \
  --gateway-url http://localhost:4000 \
  --cu-url      http://localhost:4004 \
  --mu-url      http://localhost:4002
```

The first launch prints something like:

```
Connected to xion-core-localnet <process-id>
xion-core-localnet@aos-2.0.x[Inbox:0]>
```

If `aos` cannot reach the local CU/MU, your stack is not actually up — go back to step 5 and inspect `docker compose -f infra/ao-localnet/docker-compose.yaml logs --tail=200`.

**Capture the four-and-a-half receipt fields.** Do not close the REPL until after step 9.

#### `process_id`

```lua
ao.id
```

#### `signer_address`

```lua
Owner
```

#### `lua_source_sha256`

You captured this in step 4. If you skipped, in a second WSL2 terminal:

```bash
sha256sum /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

#### `aos_version`

In a second WSL2 terminal:

```bash
aos --version
```

#### `substrate`

Hardcoded for this runbook: `localnet`. The verifier (after the Phase 6.1.b extension to [xion-verify/src/xion_verify/commands/ao_handlers.py](../../xion-verify/src/xion_verify/commands/ao_handlers.py)) requires this field on every non-placeholder receipt and rejects any value other than `localnet` or `legacynet`.

### 8. Load the Lua skeleton

Inside the REPL:

```
.load /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

Expected: a green confirmation that handlers `commit-state` and `attest` are registered. If you see a Lua syntax error, the source on disk has drifted from the spec — stop and report; do not edit inside the REPL.

Smoke-test:

```lua
Handlers.list
```

You should see `commit-state` and `attest` named in the printed list.

### 9. Send the first `commit-state` message

The handler reads `Tip-Height` and `State-Root-Sha256`. The first commit's `Tip-Height` must be `"1"`; the first `State-Root-Sha256` is the SHA-256 of the empty byte sequence:

```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Inside the REPL:

```lua
Send({
  Target = ao.id,
  Action = "Commit-State",
  Tags = {
    ["Tip-Height"] = "1",
    ["State-Root-Sha256"] = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  }
})
```

Then poll the inbox for the reply (the localnet's MU/SU loop is faster than upstream legacynet, but still takes 1-5 seconds):

```lua
Inbox[#Inbox]
```

Expect `Action = "State-Committed"`, `Height = "1"`, `Root` matching what you sent. Capture this message's `id` (the optional `first_commit_state_message_id`). Reasons for rejection (`Action = "State-Rejection"`) are the same as [AO_DEPLOY_WSL2.md § 7](AO_DEPLOY_WSL2.md) — same Lua, same handler.

### 10. Confirm `StateTip` advanced

```lua
StateTip
```

Expected: `{ height = 1, root = "e3b0c4...", prev = "0000...0000" }`. If `height` is still `0`, the message did not commit; recheck the inbox reply.

---

## Hand back to the agent

Paste the following into chat. **Do not paraphrase**; copy the exact strings from the REPL output:

```
process_id:                     <from step 7: ao.id>
signer_address:                 <from step 7: Owner>
lua_source_sha256:              <from step 4 or 7: sha256sum on main.lua>
aos_version:                    <from step 7: aos --version>
substrate:                      localnet
first_commit_state_message_id:  <from step 9: Inbox reply id>  (optional but useful)
upstream_pin:                   permaweb/ao-localnet@<git rev-parse HEAD inside infra/ao-localnet/.upstream/>
```

The agent will then:

1. Replace [`genesis/AO_DEPLOY_RECEIPT.json`](../../genesis/AO_DEPLOY_RECEIPT.json) with a real receipt: drop `"status": "placeholder"`, fill the four standard fields plus `"substrate": "localnet"` and `"upstream_pin"` (informational, not verifier-required), set `"status": "deployed"`, recompute `sha256(ao/core/main.lua)` and assert it matches `lua_source_sha256`.
2. Confirm or write the seed row to [`ledgers/STATE_CHAIN_LEDGER.jsonl`](../../ledgers/STATE_CHAIN_LEDGER.jsonl) using the [`StateChainRecord`](../../orchestrator/ao_core/ledger.py) writer.
3. Run `XION_AO_GATEWAY_URL=http://localhost:4004 xion-verify ao-handlers` and capture the `OK` line — note the substrate name now appears in the OK message after the Phase 6.1.b verifier extension.
4. Close [`KW-AOCORE-001`](../../KNOWN_WEAKNESSES.md), [`KW-AOCORE-003`](../../KNOWN_WEAKNESSES.md), and [`KW-AOCORE-004`](../../KNOWN_WEAKNESSES.md) (path #2 was elected and successfully exercised); update [`DEVELOPMENT_ROADMAP.md`](../../DEVELOPMENT_ROADMAP.md) Phase 6.1 header from "partial close" to "closed"; append a [`CHANGELOG.md`](../../CHANGELOG.md) paragraph naming the deploy `process_id` and the substrate.

---

## Tear down + reset

Between attempts, OR when you want a clean Arweave-mock slate:

```bash
docker compose -f infra/ao-localnet/docker-compose.yaml down -v
```

`-v` drops named volumes (`su` Postgres data, etc.), so the next bring-up restarts from a fresh `arlocal` and a fresh `su` ledger. The cloned `.upstream/` directory and the generated wallets stay (they are slow to recreate).

To completely reset (re-clone upstream, regenerate wallets):

```bash
docker compose -f infra/ao-localnet/docker-compose.yaml down -v
rm -rf infra/ao-localnet/.upstream
bash scripts/ao-localnet-up.sh
```

---

## Failure modes the runbook deliberately names

- **`docker compose version` reports 2.19 or older.** The wrapper compose uses `include:`, added in v2.20 (Aug 2023). Upgrade Docker Desktop on Windows, or `apt-get install --only-upgrade docker-compose-plugin` on Ubuntu.
- **Bootstrap script reports "docker daemon not running".** Start Docker Desktop on Windows; on native Linux `sudo systemctl start docker`. On WSL2, Docker Desktop must be started in Windows with WSL2 integration enabled for your Ubuntu distro.
- **First `docker compose up --wait` hangs at the `cu` build step.** The upstream `services/cu` Dockerfile pulls from npm; if your npm registry is slow or upstream packages have rotted, this stage takes long or fails. Inspect with `docker compose -f infra/ao-localnet/docker-compose.yaml logs cu --tail=200`.
- **Bootstrap reports "CU did not become ready within 180s".** The CU container started but is not answering HTTP. Most common cause: the wallets directory is empty (regenerate with `( cd infra/ao-localnet/.upstream/wallets && bash ./generateAll.sh )` then re-run the bootstrap). Second most common cause: another process is bound to port 4004 (`ss -tlnp | grep 4004` to identify, kill the squatter, retry).
- **`aos` accidentally connects to mainnet despite `--legacy`.** Should not happen if you ALSO pass the explicit `--gateway-url`/`--cu-url`/`--mu-url` to localhost ports per step 7. If the splash output reads `Network: Mainnet`, abort immediately, do not send any messages, and report — your `aos` install may have a regression.
- **`aos` connects to localnet but `commit-state` reply never arrives.** The localnet's MU/SU loop is fast but not instant; wait 5-15 seconds and re-poll `Inbox[#Inbox]`. If after 60 seconds there is still no reply, check `docker compose ... logs mu --tail=100` for errors — the local MU may be wedged. Restart the stack with `docker compose down && bash scripts/ao-localnet-up.sh` and retry from step 7.
- **`xion-verify ao-handlers` returns FAIL with "substrate: invalid value".** The receipt's `substrate` field is missing or set to something the verifier does not allow (only `localnet` or `legacynet` are accepted at this phase; mainnet is reserved for Phase 6+ Tier-3). Re-do the receipt with `substrate: "localnet"`.
- **Port collisions (4000/4002/4003/4004/4007).** Some other tool is bound to the port. Either stop it, or override the upstream's port mapping (requires editing `infra/ao-localnet/.upstream/docker-compose.yml` directly; document the override in `KW-AOCORE-004` so the next operator knows what changed).

---

## What this runbook deliberately does NOT do

- **Does not deploy to AO mainnet.** Localnet only. Mainnet is a Phase 6+ Tier-3 ceremony with cold-root cosigns per `docs/09-GOVERNANCE.md`.
- **Does not implement the other 17 handlers.** `treasury-spend`, `registry-update`, `spend`, `slash-imprint`, `rotate-authority`, `abdicate-tier`, `provision-{relay,inference,storage,bandwidth,witness}`, `route-slices`, `improvement-spend`, `reserve-draw`, `accept-donation`, `enter-hibernation`, `exit-hibernation` remain `doctrine_only` per their YAML schemas. They are tracked by [`KW-AOCORE-002`](../../KNOWN_WEAKNESSES.md) and ship in a follow-on plan that will use this same localnet substrate as the per-handler CI bring-up loop.
- **Does not produce a public-Arweave-durable receipt.** The `process_id` minted on this localnet exists only inside the bring-up's `arlocal` mock. That is fine for Phase 6.1's "testnet seal" bar; it is not fine for Phase 6+'s mainnet ceremony bar.
- **Does not stand up redundant CUs/MUs/SUs.** The upstream stack is single-instance per unit. Multi-instance redundancy is Phase 6 proper.

---

## Cross-references

- Doctrine: [`docs/28-AO-CORE.md`](../28-AO-CORE.md) § "Substrate amendment (Phase 6.1.b)", [`docs/04-ARCHITECTURE.md`](../04-ARCHITECTURE.md) § "AO Core (Phase 6.0)", [`docs/09-GOVERNANCE.md`](../09-GOVERNANCE.md) (mainnet ceremony / Tier-3 cosign rule).
- Handler ABIs: [`docs/schemas/ao-handler-commit-state.yaml`](../schemas/ao-handler-commit-state.yaml), [`docs/schemas/ao-handler-attest.yaml`](../schemas/ao-handler-attest.yaml).
- Verifier: [`xion-verify/src/xion_verify/commands/ao_handlers.py`](../../xion-verify/src/xion_verify/commands/ao_handlers.py).
- Local writer: [`orchestrator/ao_core/ledger.py`](../../orchestrator/ao_core/ledger.py) (`StateChainRecord`).
- Listener: [`orchestrator/ao_core/listener.py`](../../orchestrator/ao_core/listener.py).
- Sibling runbook (legacynet path): [`docs/runbooks/AO_DEPLOY_WSL2.md`](AO_DEPLOY_WSL2.md).
- Localnet wrapper: [`infra/ao-localnet/`](../../infra/ao-localnet/).
- Bootstrap script: [`scripts/ao-localnet-up.sh`](../../scripts/ao-localnet-up.sh).
- Known weaknesses: [`KW-AOCORE-001`](../../KNOWN_WEAKNESSES.md), [`KW-AOCORE-003`](../../KNOWN_WEAKNESSES.md), [`KW-AOCORE-004`](../../KNOWN_WEAKNESSES.md).
