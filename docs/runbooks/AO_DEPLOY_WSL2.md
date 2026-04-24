# AO Core Deploy from WSL2 (Phase 6.1 Finalization Runbook)

> **Audience.** The Xion operator. Run this from the Windows + WSL2 workstation.
>
> **Property delivered.** A real AO testnet deployment of [`ao/core/main.lua`](../../ao/core/main.lua), a verifiable [`genesis/AO_DEPLOY_RECEIPT.json`](../../genesis/AO_DEPLOY_RECEIPT.json), a first `commit-state` message accepted by the AO process, and a seed row in [`ledgers/STATE_CHAIN_LEDGER.jsonl`](../../ledgers/STATE_CHAIN_LEDGER.jsonl). When this runbook completes, `xion-verify ao-handlers` flips from `NOT_YET_SEALED` to `OK`.
>
> **Why WSL2.** [`KW-AOCORE-003`](../../KNOWN_WEAKNESSES.md) records that the `aos` CLI install path is broken on this Windows + Node 22 + nvm setup. WSL2 + Node 20 LTS is the operator path that works around the upstream bug without imposing a separate Linux box. The underlying npm-vs-Node-22 incompatibility is upstream and not "fixed" by running WSL2; the residual is now "operator runs WSL2," which is acceptable.

---

## Prereqs (one-time)

### 1. Confirm WSL2 is installed and Ubuntu is the default distro

From PowerShell as Administrator:

```powershell
wsl --version
wsl --list --verbose
```

If WSL is not installed or no Ubuntu distro is present:

```powershell
wsl --install -d Ubuntu
```

Reboot when prompted. After reboot, open the Ubuntu app from the Start menu, set the UNIX username + password, then re-open Ubuntu and run `whoami` to confirm you land in the WSL2 shell.

### 2. Install Node 20 LTS via nvm in the WSL2 shell

From the Ubuntu (WSL2) shell — **not** PowerShell:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
exec $SHELL -l               # or: source ~/.bashrc
nvm install 20
nvm use 20
nvm alias default 20
node --version               # expect v20.x
npm --version                # expect ≥ 10.x; if older, run: npm i -g npm@latest
```

**Do not install Node 22.** Per `KW-AOCORE-003`, the `aos` install fails on Node 22 with the npm-vs-Node-22 bug; Node 20 LTS is the working version.

### 3. Install the `aos` CLI

```bash
npm i -g https://get_ao.arweave.net
aos --version
```

> **Install URL note (2026-04-24).** The cookbook's `https://get_ao.g8way.io` is currently returning 404 from at least one ArNS gateway. `https://get_ao.arweave.net` resolves the same package and is what landed `aos` 2.0.11 on this workstation. If both fail, fall back to `npm i -g @permaweb/aos@latest` (the underlying npm package; older but install-equivalent for our purposes) and verify the binary exits cleanly on `aos --help`.

If `npm i -g` fails with EACCES, prefix with `sudo`. If `aos --version` reports it cannot reach the gateway, try a different gateway in step 5 below.

### 3a. Verify which `aos` major version you have, and what its default network is

```bash
aos --version
aos --help | grep -E 'mainnet|legacy'
```

> **Critical (aos 2.0+).** As of `aos` 2.0, the default network flipped from "legacynet/testnet" to "AO mainnet (HyperBEAM at `https://push.forward.computer`)". Without the `--legacy` flag, `aos <name>` will spawn a real on-chain process on **AO mainnet**. Per `docs/09-GOVERNANCE.md` and the doctrine pin in this runbook's "What this runbook deliberately does NOT do" section, mainnet deploy is a Phase 6+ Tier-3 ceremony with cold-root cosigns. Phase 6.1 (this runbook) is testnet-only. **Every `aos` invocation in steps 5–8 below MUST pass `--legacy`.** `KW-AOCORE-004` records the surprise mainnet spawns that happened during the agent-driven 2026-04-24 attempt before this warning was added.

### 4. Verify the repo is reachable from WSL2

WSL2 mounts the Windows filesystem at `/mnt/c/`. Confirm:

```bash
ls /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
sha256sum /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

Capture the SHA-256 — this is one of the four receipt fields you will hand back to the agent (`lua_source_sha256`).

---

## Deploy

### 5. Spawn a fresh AO process (testnet / legacynet)

```bash
aos xion-core --legacy
```

> **The `--legacy` flag is mandatory.** Without it, `aos` 2.0+ spawns on AO mainnet (see § 3a). The Phase 6.1 deploy is testnet-only.

This spawns a fresh AO process named `xion-core` on AO legacynet. The name is local; the on-chain identity is the `process_id` printed in the prompt header. The first launch may take 15–60 seconds while the legacynet CU/MU provision. If it hangs more than two minutes, abort with `Ctrl-C` and retry with explicit gateway/CU/MU URLs:

```bash
aos xion-core --legacy \
  --gateway-url https://arweave.net \
  --cu-url https://cu.ao-testnet.xyz \
  --mu-url https://mu.ao-testnet.xyz
```

> **Upstream blocker (as of 2026-04-24, recorded as `KW-AOCORE-004`).** Multiple consecutive `aos --legacy` spawn attempts from this workstation returned HTTP 500 from the legacy MU at `https://mu.ao-testnet.xyz`, body `{"error":"TypeError: Cannot read properties of null (reading 'toLowerCase')"}`. The error is server-side (the MU itself is 500-ing), not a client misconfiguration. If you reproduce this, the upstream legacy MU is degraded; your options are (a) wait and retry later (legacynet outages have historically been hours, not days), (b) escalate the runbook to use a local `permaweb/ao-localnet` Docker stack (which produces process IDs on a local arlocal mock — operator + cold-root must agree this satisfies Phase 6.1's "testnet seal" bar), or (c) defer Phase 6.1 finalization until upstream recovers. Do **not** silently switch to mainnet to "make it work"; that is a doctrine breach.

When the prompt comes up you will see something like:

```
Connected to xion-core <process-id>
xion-core@aos-2.0.6[Inbox:0]>
```

**Capture the four receipt fields now.** Do not close this terminal.

#### `process_id`

From inside the REPL:

```lua
ao.id
```

The printed string is the `process_id`. Also visible in the prompt header.

#### `signer_address`

From inside the REPL:

```lua
Owner
```

The printed string is the wallet address that owns this process — the `signer_address`.

#### `lua_source_sha256`

You captured this in step 4 (`sha256sum` on the host file). If you skipped it, open a second WSL2 terminal and run:

```bash
sha256sum /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

#### `aos_version`

Open a second WSL2 terminal:

```bash
aos --version
```

The reported version string is the `aos_version`.

### 6. Load the Lua skeleton

Inside the REPL:

```
.load /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua
```

Expected output: a green confirmation that handlers `commit-state` and `attest` are registered. If you see a Lua syntax error, the source on disk has drifted from the spec — stop and report; do not try to fix it inside the REPL.

Smoke-test that the handlers are wired:

```lua
Handlers.list
```

You should see `commit-state` and `attest` named in the printed list.

### 7. Send the first `commit-state` message

The handler reads two tags: `Tip-Height` and `State-Root-Sha256`. The first commit's `Tip-Height` must be `"1"` (the skeleton state ships with `height = 0`, and the handler asserts `tip_height == StateTip.height + 1`). The first `State-Root-Sha256` must be a 64-char lowercase-hex string; for the seed row, use the SHA-256 of the empty byte sequence:

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

Then poll the inbox for the reply:

```lua
Inbox[#Inbox]
```

You expect a message with `Action = "State-Committed"`, `Height = "1"`, and `Root` matching what you sent. Capture this message's `id` (this is the `first_commit_state_message_id` field). If you see `Action = "State-Rejection"` instead, the `Reason` tag tells you why; common ones:

| Reason | Diagnosis | Remediation |
| --- | --- | --- |
| `non_authorised_caller` | `msg.From` is not in `AuthorizedSigners` | The skeleton accepts `Owner` automatically. If this triggers, the Lua loaded from `.load` is from a stale path — rerun `.load` against the current source. |
| `missing_args` | `Tip-Height` or `State-Root-Sha256` tag is absent | Re-run the `Send` block above; the tag names are case-sensitive. |
| `tip_height_skip` | The handler expected `StateTip.height + 1`; you sent something else | Confirm `StateTip.height` is `0`; if it has drifted (because someone ran `commit-state` before in this process), use `StateTip.height + 1`. |

### 8. Confirm `StateTip` advanced

```lua
StateTip
```

Expected: `{ height = 1, root = "e3b0c4...", prev = "0000...0000" }`. If `height` is still `0`, the message did not commit; recheck the inbox reply.

---

## Hand back to the agent

Paste the following four field values into chat. **Do not paraphrase**; copy the exact strings from the REPL output:

```
process_id:                <from step 5: ao.id>
signer_address:            <from step 5: Owner>
lua_source_sha256:         <from step 4 or 5: sha256sum on main.lua>
aos_version:               <from step 5: aos --version>
first_commit_state_message_id (optional but useful): <from step 7: Inbox reply id>
```

The agent will then:

1. Replace [`genesis/AO_DEPLOY_RECEIPT.json`](../../genesis/AO_DEPLOY_RECEIPT.json) with a real receipt (drops `"status": "placeholder"`, fills the four fields, sets `"status": "deployed"`, computes the local SHA-256 of `ao/core/main.lua` and asserts it matches what you reported).
2. Confirm or write the seed row to [`ledgers/STATE_CHAIN_LEDGER.jsonl`](../../ledgers/STATE_CHAIN_LEDGER.jsonl) using the [`StateChainRecord`](../../orchestrator/ao_core/ledger.py) writer (Scenario A: orchestrator was running and already wrote the row; Scenario B: agent constructs and appends it).
3. Run `xion-verify ao-handlers` and capture the `OK` line.
4. Close [`KW-AOCORE-001`](../../KNOWN_WEAKNESSES.md) and [`KW-AOCORE-003`](../../KNOWN_WEAKNESSES.md), update [`DEVELOPMENT_ROADMAP.md`](../../DEVELOPMENT_ROADMAP.md) Phase 6.1 header from "partial close" to "closed", append a [`CHANGELOG.md`](../../CHANGELOG.md) paragraph naming the deploy `process_id`.

---

## Failure modes the runbook deliberately names

- **`aos` install fails because `npm` is too old.** Symptom: cryptic dependency-resolution errors during `npm i -g https://get_ao.arweave.net`. Remedy: `npm i -g npm@latest` then retry. (If the cookbook you are reading still names `https://get_ao.g8way.io`, that ArNS gateway was returning 404 as of 2026-04-24; use `get_ao.arweave.net` instead.)
- **`aos` REPL hangs on first connect.** Symptom: the prompt never appears after `aos xion-core --legacy`; CPU is idle. Remedy: `Ctrl-C` and retry with explicit URLs: `aos xion-core --legacy --gateway-url https://arweave.net --cu-url https://cu.ao-testnet.xyz --mu-url https://mu.ao-testnet.xyz`. If that also hangs or 500s, the legacy MU is down (this happened on 2026-04-24; see `KW-AOCORE-004`); check the AO ecosystem's current status channel and retry later.
- **`aos --legacy` returns "An Error occurred trying to contact your AOS process".** Symptom: spawn fails with that generic error. Re-run with `DEBUG=1 aos xion-core --legacy` to surface the underlying HTTP status. If the underlying error is `500: {"error":"TypeError: Cannot read properties of null (reading 'toLowerCase')"}`, it is the upstream legacy-MU regression tracked by `KW-AOCORE-004`; client-side retries will not help. See the recovery options listed in step 5.
- **`aos` accidentally spawned on mainnet.** Symptom: you forgot `--legacy` and the splash output reads `Network: Mainnet` (instead of `Legacynet`). Remedy: do not send any further messages to that process. The process_id is permanent on AO and cannot be deleted, but it can be abandoned (it will sit inert on chain forever). Document the orphan's process_id alongside the orphans already named in this runbook's "Lessons learned" section, then re-spawn with `aos xion-core --legacy` (the local name is per-network in `~/.aos-process-cache.json`, so reuse is safe; but the on-chain identity will differ). **Never** ratify the accidental mainnet spawn retroactively without operator + cold-root cosign per `docs/09-GOVERNANCE.md`.
- **`commit-state` reply times out.** Symptom: `Inbox[#Inbox]` returns the same message you just sent (your own outbound), not a reply. Remedy: wait 5–15 seconds (gateway round-trip) and re-poll. If after 60 seconds there is no reply, the `XION_AO_GATEWAY_URL` default in the verifier may be different from the gateway you connected through; the agent will need to pin a non-default gateway in the receipt.
- **WSL2 cannot see `/mnt/c/`.** Symptom: `ls /mnt/c/...` reports "no such file or directory". Remedy: confirm WSL2 (not WSL1) is the version of your distro: `wsl -l -v` should show `VERSION 2`. If it shows `1`, run `wsl --set-version Ubuntu 2`.
- **`AuthorizedSigners` rejects `Owner`.** Symptom: `commit-state` returns `non_authorised_caller`. Remedy: the Lua loaded into the REPL is stale; re-run `.load /mnt/c/Users/16823/CursorProjects/xion-os/ao/core/main.lua` and verify that line 15 includes `[Owner] = true`.

---

## What this runbook deliberately does NOT do

- **Does not deploy to AO mainnet.** Testnet only. Mainnet is a Phase 6+ Tier-3 ceremony with cold-root cosigns.
- **Does not implement the other 17 handlers.** `treasury-spend`, `registry-update`, `spend`, `slash-imprint`, `rotate-authority`, `abdicate-tier`, `provision-{relay,inference,storage,bandwidth,witness}`, `route-slices`, `improvement-spend`, `reserve-draw`, `accept-donation`, `enter-hibernation`, `exit-hibernation` remain `doctrine_only` per their YAML schemas and ship in Phase 6 proper. They are tracked by [`KW-AOCORE-002`](../../KNOWN_WEAKNESSES.md).
- **Does not stand up a second AO process for redundancy.** Single-process bootstrap; multi-process redundancy is Phase 6.

---

## Lessons learned (2026-04-24 attempt-2)

The first agent-driven run of this runbook (with the operator's explicit "you do all" delegation) discovered the `aos` 2.0 mainnet-default trap by spawning two AO mainnet processes by accident under the agent-generated WSL2 wallet `v8Fee96ZAGu1W5Ec5fj3EWc7fPvp3MSLbdKhDwjwfHY` (key location: `\\wsl.localhost\Ubuntu\root\.aos.json`):

- **Smoke-test orphan:** `-MlYwU1U_5tEjRFhIVQFncEroGFO4kFetIqByOgFnBE` — used to validate that the toolchain emits and receives non-interactively via `--run`. One eval message in its history. Abandoned.
- **Canonical-name orphan:** `PxTK8xPH4sRDCIRGl2sruE_OrRFcbW25Oz2NwiKzkKM` — spawned with the local name `xion-core` before the trap was discovered. The same invocation's `--load /mnt/c/.../ao/core/main.lua` and receipt-print `--run` failed mid-call with `sendMessageMainnet` errors (likely because the wallet has no AO mainnet topup), so this process is functionally empty: no Xion handlers ever attached, no `commit-state` history. Abandoned. **This is NOT Xion's canonical AO Core**; it is a name collision created by an undocumented default change. Operator + cold-root may verify this on AO mainnet GraphQL by querying the process's `Eval` history (it has none beyond the spawn) and the absence of any `Commit-State` or `State-Committed` messages.

The disposition (abandon both, redeploy on testnet) was operator-elected on 2026-04-24, recorded as Issue A in `KW-AOCORE-004`. The redeploy then immediately hit Issue B (upstream legacy MU 500), so Phase 6.1 finalization is now externally blocked. `KW-AOCORE-001` and `KW-AOCORE-003` remain open; `genesis/AO_DEPLOY_RECEIPT.json` remains `{status: "placeholder"}`.

Hardening that landed alongside this runbook amendment:

- `.gitignore` extended with `*.aos.json`, `**/.aos.json`, `*.jwk`, `*.jwk.json`, `**/*.jwk` patterns. Verified on 2026-04-24 that `genesis/.aos.json`, `wallet.jwk.json`, and `arweave-keyfile-x.jwk` are all auto-blocked from accidental commit.
- All four-receipt-fields capture commands in this runbook updated to require `--legacy`.
- Step 3 install URL updated from the dead `get_ao.g8way.io` to the live `get_ao.arweave.net`.

## Cross-references

- Doctrine: [`docs/28-AO-CORE.md`](../28-AO-CORE.md), [`docs/04-ARCHITECTURE.md`](../04-ARCHITECTURE.md) § "AO Core (Phase 6.0)", [`docs/09-GOVERNANCE.md`](../09-GOVERNANCE.md) (mainnet ceremony / Tier-3 cosign rule).
- Handler ABIs: [`docs/schemas/ao-handler-commit-state.yaml`](../schemas/ao-handler-commit-state.yaml), [`docs/schemas/ao-handler-attest.yaml`](../schemas/ao-handler-attest.yaml).
- Verifier: [`xion-verify/src/xion_verify/commands/ao_handlers.py`](../../xion-verify/src/xion_verify/commands/ao_handlers.py).
- Local writer: [`orchestrator/ao_core/ledger.py`](../../orchestrator/ao_core/ledger.py) (`StateChainRecord`).
- Listener: [`orchestrator/ao_core/listener.py`](../../orchestrator/ao_core/listener.py).
- Known weaknesses: [`KW-AOCORE-001`](../../KNOWN_WEAKNESSES.md), [`KW-AOCORE-003`](../../KNOWN_WEAKNESSES.md), [`KW-AOCORE-004`](../../KNOWN_WEAKNESSES.md).
