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

### 5b. Seed ArLocal (required before `aos` can spawn)

The upstream [permaweb/ao-localnet](https://github.com/permaweb/ao-localnet) README’s “Quick Start” includes **“Seed data onto the blockchain”** (download the `aos` module WASM, publish the scheduler-location and module, then **mine** blocks on the mock ArLocal). [`scripts/ao-localnet-up.sh`](../../scripts/ao-localnet-up.sh) starts Docker and wallets, but it does not run that seed. Do this **after** the bootstrap script succeeds, **once** per clean ArLocal (again after `docker compose ... down -v`):

```bash
bash scripts/ao-localnet-seed.sh
```

This also writes `infra/ao-localnet/localnet-aos.env` (gitignored) with:

- `export AOS_MODULE="<txid>"` — the **AOS Module transaction id you just published to ArLocal**. You must use that id for spawn: `@permaweb/aos`’s default (from its `package.json`) points at a **public testnet** module, not your local upload, and using the wrong module produces `Invalid Return 'undefined': Required` during **“Spawning New Process”** even after a successful seed.

- `export SCHEDULER="<arweave address>"` — the **Scheduler-Location publisher** wallet address printed during seeding (the wallet that signed the `Scheduler-Location` tag on ArLocal). The `aos` CLI uses the env var `SCHEDULER` when building spawn transactions (`@permaweb/aos` `src/services/connect.js`); if you omit it, `aos` falls back to the mainnet scheduler address, the MU cannot look up the chain’s `Scheduler-Location` for that tag, and you may get **`500: ... Cannot destructure property 'url' of 'undefined'`** on spawn or send.

Before any `aos …` against localnet, either `source infra/ao-localnet/localnet-aos.env` or rely on `scripts/ao-localnet-seal.sh`, which sources it automatically.

If you skip seed (or `AOS_MODULE`), `aos` frequently fails while **“Spawning New Process”** because the chain is missing the module/scheduler data **or** because the client is still using the default non-local module id.

- **`500: ... Cannot destructure property 'url' of 'undefined'`.** The messenger unit could not resolve a scheduler (usually because the on-chain `Scheduler-Location` `Url` is not reachable from the `mu` container — upstream used `http://host.docker.internal:4003`, which is unreliable on Linux/WSL). [`scripts/ao-localnet-seed.sh`](../../scripts/ao-localnet-seed.sh) rewrites the seed script to `http://su:80` (Compose service `su`) before publishing. You must **re-seed** so a new `Scheduler-Location` tx is posted: `docker compose -f infra/ao-localnet/docker-compose.yaml down -v`, then `bash scripts/ao-localnet-up.sh` and `bash scripts/ao-localnet-seed.sh`. If your Docker setup needs another hop, set `XION_LOCALNET_SU_URL` before seeding (e.g. `http://172.17.0.1:4003`).

- **`500: No Scheduler tag found on process …`**. (1) Fund the **bundler** wallet: [`scripts/ao-localnet-seed.sh`](../../scripts/ao-localnet-seed.sh) mints the upstream `wallets/bundler-wallet.json` on ArLocal so the bundler can post process txs. (2) Rebuild the **messenger** with the Xion **MU patch**: it fixes `getProcess()` so cached/SU-sourced process tags are merged from ArLocal GraphQL when the `Scheduler` tag is missing (upstream can cache incomplete tags). If you are not re-cloning, run `bash scripts/patch-ao-localnet-mu-graphql-fallback.sh`, then `docker compose -f infra/ao-localnet/docker-compose.yaml build mu` and `docker compose -f infra/ao-localnet/docker-compose.yaml up -d` (or run [`scripts/ao-localnet-up.sh`](../../scripts/ao-localnet-up.sh) after pulling — it runs the patch and rebuilds `mu` when the file changes).

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

**Also source `AOS_MODULE` from the seed step** (or pass `--module <txid>` with the `aos module: …` line from seed). Otherwise the CLI uses the default module in `@permaweb/aos` (public testnet), not the module you published to ArLocal.

```bash
set -a && . infra/ao-localnet/localnet-aos.env && set +a
aos xion-core-localnet --legacy \
  --gateway-url http://localhost:4000 \
  --cu-url      http://localhost:4004 \
  --mu-url      http://localhost:4002
```

Equivalent: add `--module <your local module txid>` and omit the `source` (see §5b).

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
- **CU is up but `aos` fails with "Could not connect to process" right after a process id is printed.** Check `docker compose -f infra/ao-localnet/docker-compose.yaml logs --tail=200 cu` for `Promise.withResolvers is not a function`. The upstream `services/cu/Dockerfile` pins `FROM node:20-alpine`, but the `ao/servers/cu` source (`main` branch) calls `Promise.withResolvers`, which only exists in Node 22+. Every `readResult` then crashes inside the CU; `aos` interprets the missing prompt as "could not connect" and bails. This is **not** a CU warm-up race. Fix: `bash scripts/patch-ao-localnet-cu-node22.sh && docker compose -f infra/ao-localnet/docker-compose.yaml build cu && docker compose -f infra/ao-localnet/docker-compose.yaml up -d cu`. The patch is also wired into `scripts/ao-localnet-up.sh` so a fresh bootstrap picks it up automatically. Verify: `docker exec ao-localnet-cu-1 node --version` should report `v22.x` or newer.
- **Bootstrap reports "CU did not become ready within 180s".** The CU container started but is not answering HTTP. Most common cause: the wallets directory is empty (regenerate with `( cd infra/ao-localnet/.upstream/wallets && bash ./generateAll.sh )` then re-run the bootstrap). Second most common cause: another process is bound to port 4004 (`ss -tlnp | grep 4004` to identify, kill the squatter, retry).
- **`aos` accidentally connects to mainnet despite `--legacy`.** Should not happen if you ALSO pass the explicit `--gateway-url`/`--cu-url`/`--mu-url` to localhost ports per step 7. If the splash output reads `Network: Mainnet`, abort immediately, do not send any messages, and report — your `aos` install may have a regression.
- **`aos` connects to localnet but `commit-state` reply never arrives.** The localnet's MU/SU loop is fast but not instant; wait 5-15 seconds and re-poll `Inbox[#Inbox]`. If after 60 seconds there is still no reply, check `docker compose ... logs mu --tail=100` for errors — the local MU may be wedged. Restart the stack with `docker compose down && bash scripts/ao-localnet-up.sh` and retry from step 7.
- **`xion-verify ao-handlers` returns FAIL with "substrate: invalid value".** The receipt's `substrate` field is missing or set to something the verifier does not allow (only `localnet` or `legacynet` are accepted at this phase; mainnet is reserved for Phase 6+ Tier-3). Re-do the receipt with `substrate: "localnet"`.
- **`Action = "State-Rejection", Reason = "non_authorised_caller"` after the first `commit-state`.** Sending `Send({Target=ao.id, Action='Commit-State', ...})` from inside an `aos --run` posts an outbox message *from the process itself* (`msg.From == ao.id`); the Phase 6.1 skeleton's commit-state handler authorizes only `[Owner]`, so a self-Send is silently rejected. Use [`scripts/ao-localnet-send-commit-state.cjs`](../../scripts/ao-localnet-send-commit-state.cjs) (which signs the message with `~/.aos.json` so `msg.From == Owner`) — `scripts/ao-localnet-seal.sh` invokes this helper automatically in step 2.
- **`xion-verify ao-handlers` returns NOT_YET_SEALED with "AO gateway response shape unrecognized".** The legacy AO CU's `/state/<pid>` endpoint serves a *binary* memory snapshot, not JSON. Older verifier builds queried that endpoint speculatively. The current verifier uses `POST /dry-run?process-id=<pid>` with a tiny Eval body that returns `json.encode({state_tip_height = StateTip.height, state_root_sha256 = StateTip.root})`. If you see this error, your `xion-verify` checkout pre-dates that change — pull latest. The dry-run round-trip is gas-free and side-effect-free, so a third-party reviewer with only the CU URL can independently re-run it.
- **Port collisions (4000/4002/4003/4004/4007).** Some other tool is bound to the port. Either stop it, or override the upstream's port mapping (requires editing `infra/ao-localnet/.upstream/docker-compose.yml` directly; document the override in `KW-AOCORE-004` so the next operator knows what changed).

---

## What this runbook deliberately does NOT do

- **Does not deploy to AO mainnet.** Localnet only. Mainnet is a Phase 6+ Tier-3 ceremony with cold-root cosigns per `docs/09-GOVERNANCE.md`.
- **Does not exercise every handler behavior end-to-end.** All 20 canonical AO Core handlers are implemented in [`ao/core/main.lua`](../../ao/core/main.lua), registered by schema, and checked by `xion-verify ao-handlers`. This localnet seal proves the substrate, receipt, and `commit-state`/`attest` path; broader per-handler behavioral dry-runs remain verifier/test-depth work, not missing handler implementation.
- **Does not produce a public-Arweave-durable receipt.** The `process_id` minted on this localnet exists only inside the bring-up's `arlocal` mock. That is fine for Phase 6.1's "testnet seal" bar; it is not fine for Phase 6+'s mainnet ceremony bar.
- **Does not stand up redundant CUs/MUs/SUs.** The upstream stack is single-instance per unit. Multi-instance redundancy is Phase 6 proper.

---

## Lessons learned (Phase 6.1.b finalization, 2026-04-25)

This appendix documents the six non-obvious traps the seal pipeline hit during finalization, in roughly the order they were discovered. Each entry names the **symptom** an operator would see, the **actual cause** (which is usually nothing like the symptom suggests), and the **fix lane** that's now in tree. If a future seal run fails with one of these symptoms, you're almost certainly hitting a regression of the corresponding fix — start with the named file rather than re-debugging from scratch.

### 1. CU server-side crashes on every `readResult`; symptom is "Could not connect to process"

**Symptom.** `aos --legacy` prints "Connecting to process..." then "Could not connect to process!" and exits non-zero. The CU container is up, ports are open, `curl http://localhost:4004/state/<probe>` returns 404 (which is the right answer for "no such process"). Looks like a transient network problem; isn't.

**Actual cause.** The upstream `permaweb/ao-localnet` `services/cu/Dockerfile` pins `FROM node:20-alpine`, but `ao/servers/cu`'s `main` branch calls `Promise.withResolvers` (Node 22+ only). Every `readResult` crashes server-side with `TypeError: Promise.withResolvers is not a function`; `aos` interprets the missing prompt as "could not connect" and bails. The CU logs have the truth: `docker compose -f infra/ao-localnet/docker-compose.yaml logs --tail=200 cu` shows the TypeError stack.

**Fix lane.** [`scripts/patch-ao-localnet-cu-node22.sh`](../../scripts/patch-ao-localnet-cu-node22.sh) rewrites the CU Dockerfile to `node:22-alpine`. [`scripts/ao-localnet-up.sh`](../../scripts/ao-localnet-up.sh) runs the patch and rebuilds `cu` automatically when the Dockerfile changes. [`scripts/ao-localnet-seal.sh`](../../scripts/ao-localnet-seal.sh) probes `docker exec ao-localnet-cu-1 node --version` at startup and warns if the running CU is still on Node 20. Verify a healthy CU with `docker exec ao-localnet-cu-1 node --version` → expect `v22.x` or newer.

### 2. `aoconnect` wipes `AO_URL` on import; `aos` silently routes through HyperBEAM

**Symptom.** `aos --legacy --gateway-url http://localhost:4000 --cu-url http://localhost:4004 --mu-url http://localhost:4002 ...` appears to honor the URL flags but in fact connects to mainnet. Spawned process IDs aren't queryable on the local CU but ARE queryable on AO mainnet's gateway.

**Actual cause.** `aos` 2.0 reads the *string* `'undefined'` from `process.env.AO_URL` as a sentinel meaning "stay on the legacy `readResult` codepath". `@permaweb/aoconnect`'s top-level module-init runs `process.env.AO_URL = void 0` on import, which evaluates to literal `undefined` and JavaScript stringifies that to `'undefined'`... except in some Node versions the assignment actually deletes the env var, breaking the sentinel. Result: `aos` flips to HyperBEAM mid-flight.

**Fix lane.** [`scripts/patch-npm-aoconnect-preserve-ao-url.sh`](../../scripts/patch-npm-aoconnect-preserve-ao-url.sh) is an idempotent patch that removes the clobber from the installed aoconnect's `dist/index.js`. [`scripts/ao-localnet-seal.sh`](../../scripts/ao-localnet-seal.sh) runs it on every invocation (the patch is a no-op if already applied) and exports `AO_URL=undefined` so the sentinel survives re-imports.

### 3. `aos --run "$(cat ao/core/main.lua)"` is parsed as a boolean; symptom is `Buffer.from(true)`

**Symptom.** Step 1 of the seal fails with `TypeError [ERR_INVALID_ARG_TYPE]: The first argument must be of type string or an instance of Buffer, ArrayBuffer, or Array or an Array-like Object. Received type boolean (true)` from somewhere deep inside `@permaweb/aoconnect/ar-data-create`. Looks like an aoconnect bug; isn't.

**Actual cause.** `aos` uses `minimist` to parse argv. Any `--run <value>` whose `<value>` starts with `-` is treated as a boolean flag (`{ run: true }`). `ao/core/main.lua`'s first line is `-- ao/core/main.lua` (a Lua line comment), so the entire Lua source is interpreted as a flag, `argv.run === true`, and that `true` is passed to `Buffer.from()` which explodes.

**Fix lane.** Prepend a single space to the Lua source before passing it to `--run`: `LUA_SRC=" $(cat "$LUA_RELP")"`. The leading space is invisible to Lua's parser (whitespace is skipped) and forces minimist to treat the value as the intended string. [`scripts/ao-localnet-seal.sh`](../../scripts/ao-localnet-seal.sh) does this with a multi-line comment explaining why; if you ever rewrite that step, preserve the leading space.

### 4. ArLocal indexes spawn DataItems lazily; back-to-back `aos $NAME` calls re-spawn

**Symptom.** Three sequential `aos xion-core-localnet --legacy ...` invocations (step 1: spawn + load Lua; step 2: send commit-state; step 3: read `ao.id` + `Owner`) end up writing a receipt naming a process whose `Inbox` is empty — because the commit-state went to a different process. Each `aos $NAME` call shows a *different* "Your AOS Process: <pid>" line.

**Actual cause.** `register(name)` in `@permaweb/aos` `src/register.js` queries gql for the *latest* process tagged with `name`. ArLocal indexes spawn DataItems lazily — the second `aos $NAME` call's gql query usually still sees no result and `register` falls through to the spawn path. Result: every back-to-back invocation makes a fresh process, and the receipt's `process_id` no longer corresponds to the process whose state was actually committed.

**Fix lane.** Extract the 43-char base64url pid from step 1's `Your AOS Process: <pid>` stdout line, then pass *that* pid (not the human-readable name) as the first argument to subsequent `aos` calls. `register()` treats anything matching `^[A-Za-z0-9_-]{43}$` as an address (`services/address.js#isAddress`) and short-circuits without re-spawning, even when gql can't find the tx (it returns `{ id: name, variant: null }` on any lookup failure — see `register.js` around L137). [`scripts/ao-localnet-seal.sh`](../../scripts/ao-localnet-seal.sh) does this; if you ever change the pid-extraction regex, preserve the ANSI-strip step (chalk wraps the pid in green escape codes that break naive `awk`).

### 5. `Send({Target=ao.id,...})` from inside an Eval has `msg.From == ao.id`, not `Owner`

**Symptom.** Step 9's `Send({ Target = ao.id, Action = "Commit-State", Tags = { ... } })` from inside the REPL appears to succeed (`Inbox[#Inbox]` shows a reply), but the reply is `Action = "State-Rejection", Reason = "non_authorised_caller"` and `StateTip` is still `{ height = 0, root = zeros }`. If the operator script uses the `Send`-from-Eval pattern and doesn't *check* the inbox reply for `State-Rejection`, the receipt gets written naming a process that never actually committed any state, and the verifier returns OK against a vacuously-uninitialized chain.

**Actual cause.** `msg.From` is the ID of whoever signed the inbound DataItem. When `Send` is invoked from inside an `aos --run` Eval, the outbox message is signed by the *process itself*, so `msg.From == ao.id` (NOT the owner address). [`ao/core/main.lua`](../../ao/core/main.lua)'s `is_authorized` check authorizes only `[Owner]` and `AuthorizedSigners`, so the self-Send is rejected. The rejection is silent from the REPL's perspective (no exception, just an inbox reply you have to explicitly read).

**Fix lane.** Send the message externally, signed by the owner's wallet (`~/.aos.json`). [`scripts/ao-localnet-send-commit-state.cjs`](../../scripts/ao-localnet-send-commit-state.cjs) is the template; [`scripts/ao-localnet-seal.sh`](../../scripts/ao-localnet-seal.sh) invokes it. The helper is `.cjs` (not `.mjs`) on purpose: Node's ESM loader does not honor `NODE_PATH` for `exports`-field resolution, but the only place `aoconnect` is installed in this environment is under `aos`'s own `node_modules`. CommonJS `require` handles `NODE_PATH` correctly, and `aoconnect`'s `package.json` ships an explicit `require: './dist/index.cjs'` entry for exactly this case. The helper also calls `process.exit(0)` after printing the message id so aoconnect's keep-alive sockets don't keep the event loop alive forever. [`ao/core/main.lua`](../../ao/core/main.lua) has a doc-string near `is_authorized` flagging this trap for future contract authors.

### 6. CU's `/state/<pid>` is binary; verifier needs `/dry-run` with the right `Owner`

**Symptom.** After a successful seal (receipt written, ledger row written), `xion-verify ao-handlers` returns `NOT_YET_SEALED` with a message like "AO gateway response shape unrecognized at http://localhost:4004/state/<pid>; expected JSON object containing `state_tip_height` ...". Or, after switching to `/dry-run`, you get `NOT_YET_SEALED` with "AO CU /dry-run inner Lua return is not JSON ... (got '\x1b[90mNew Message From ...')".

**Actual cause.** Two compounding issues. (a) The legacy AO CU exposes the process *memory* under `/state/<pid>` — a binary blob useful for snapshots, not for tip parity. The structured query surface is `POST /dry-run?process-id=<pid>`. (b) Once you switch to `/dry-run`, the dry-run request body's `Owner` field must equal the process's actual owner. AOS's default Eval handler only *executes* the message `Data` when `msg.From == Owner`; otherwise it returns the AOS-default banner-print string ("New Message From <pid>: Action = Eval ...") in `Output.data.output`. The CU populates `From` from the dry-run body's `Owner` field (no signature is required because dry-run is side-effect-free), so passing the owner is both necessary and sufficient.

**Fix lane.** [`xion-verify/src/xion_verify/commands/ao_handlers.py`](../../xion-verify/src/xion_verify/commands/ao_handlers.py)'s `_fetch_gateway_tip` POSTs to `/dry-run?process-id=<pid>` with a Lua body that returns `json.encode({state_tip_height = StateTip.height, state_root_sha256 = StateTip.root})`, and threads the receipt's `signer_address` as the dry-run body's `Owner`. The dry-run round-trip is gas-free and side-effect-free, so a third party with only the CU URL + the receipt can independently re-run the verification — preserving the trust model. The function's docstring documents both the binary-vs-JSON gotcha and the Owner requirement.

### Where this gets you

Running `bash scripts/ao-localnet-seal.sh` from a clean WSL2 + Node 20 + Docker session should now seal the localnet AO process end-to-end and exit 0 from the verifier, in ~2 minutes wall-clock (dominated by the 15s scheduler/CU settle wait). Reproducibility was confirmed by running the script twice back-to-back; each run produces a fresh process id, a fresh commit-state message id, a fresh ledger row, and a green verifier. If your run fails, work through the six traps above before opening a new issue.

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
