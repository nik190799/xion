# Xion AO Localnet (Phase 6.1.b)

A self-sufficient AO substrate for Xion's Phase 6.1 testnet seal, eliminating the upstream dependency on the legacy `https://mu.ao-testnet.xyz` MU (which has been HTTP 500-ing as of 2026-04-24, see `KW-AOCORE-004` in [KNOWN_WEAKNESSES.md](../../KNOWN_WEAKNESSES.md)).

## What this is

A thin wrapper around the upstream [`permaweb/ao-localnet`](https://github.com/permaweb/ao-localnet) Docker Compose stack — `arlocal` (Arweave gateway mock), `cu` (compute unit), `mu` (messenger unit), `su` (scheduler unit), `bundler` — pinned to a known commit SHA. Bring-up gives Xion a fully local AO substrate that:

- Has no upstream MU dependency.
- Is reproducible by any future operator (the pin is git-committed in [scripts/ao-localnet-up.sh](../../scripts/ao-localnet-up.sh)).
- Lets [`xion-verify ao-handlers`](../../xion-verify/src/xion_verify/commands/ao_handlers.py) target a local Compute Unit via `XION_AO_GATEWAY_URL=http://localhost:4004`.
- Can be torn down + reset between attempts with `docker compose down -v`.

## What this is NOT

- **Not public Arweave durability.** A `process_id` produced on this localnet is NOT queryable from the public AO mainnet GraphQL or the public CU at `https://cu.ao-testnet.xyz`. Public-Arweave durability is a Phase 6+ Tier-3 mainnet ceremony obligation, separately tracked.
- **Not Tier 1-supported by AO Forward Research.** Upstream `permaweb/ao-localnet` is explicitly self-described as "experimental … may become out-of-date and may not work out-of-the-box". Xion pins a commit SHA so the operator's experience is reproducible, but if the upstream's build dependencies have rotted (e.g. base images that have been deleted from upstream registries), the operator may need to fall back to a community fork — see [Fallback](#fallback-when-upstream-is-rotted) below.
- **Not a single Docker image.** The upstream stack uses `build: ./services/<unit>` for every service; there is no `permaweb/ao-localnet:<tag>` published on Docker Hub. Pinning is by git commit, not by image digest. This is the only honest pin available.

## Files

| Path | Purpose |
| --- | --- |
| `docker-compose.yaml` | Wrapper that `include:`s the upstream compose after `.upstream/` is cloned. |
| `.gitignore` | Excludes `.upstream/` (the cloned working copy) and `wallets/` (generated keys). |
| `README.md` | This file. |

The actual stack-bring-up logic lives in [`scripts/ao-localnet-up.sh`](../../scripts/ao-localnet-up.sh).

## Quick start (operator, in WSL2)

Prereqs: Docker Desktop (with WSL2 backend) on Windows, OR native Docker in your WSL2 Ubuntu. Confirm with `docker --version` and `docker compose version` (need Compose v2.20+ for `include:`).

```bash
cd /mnt/c/Users/16823/CursorProjects/xion-os
bash scripts/ao-localnet-up.sh
```

First-time run: ~10–15 minutes. Building from upstream sources for `arlocal`, `cu`, `mu`, `su`, `bundler` — and (depending on Docker layer cache) Postgres pulls. Subsequent runs are seconds.

When the script reports the stack healthy, point the verifier at it:

```bash
export XION_AO_GATEWAY_URL=http://localhost:4004
xion-verify ao-handlers
```

For the full Phase 6.1 deploy (spawning a process, loading the Lua, sending the first `commit-state`, capturing the receipt), follow the runbook at [docs/runbooks/AO_DEPLOY_LOCALNET.md](../../docs/runbooks/AO_DEPLOY_LOCALNET.md).

## Tear down

```bash
docker compose -f infra/ao-localnet/docker-compose.yaml down -v
```

`-v` drops the named volumes (`su` Postgres data, `turbo` Postgres data) so the next bring-up starts from a clean Arweave-mock slate.

## Pin discipline

The pinned commit SHA lives in `XION_AO_LOCALNET_COMMIT` at the top of [scripts/ao-localnet-up.sh](../../scripts/ao-localnet-up.sh). To change pin (e.g. to test a newer upstream commit, or a fork):

```bash
XION_AO_LOCALNET_COMMIT=<new-sha> bash scripts/ao-localnet-up.sh
```

If the new pin works for you, edit the default in the script and commit the change with a Phase-6.1.x commit message naming what improved.

## Fallback (when upstream is rotted)

The upstream `permaweb/ao-localnet@2f9f98e` was last touched 2024-04-10. If the build fails because (e.g.) a base image referenced in one of the upstream `Dockerfile`s has been deleted, or a `pnpm`/`npm` registry version it pins is gone, fall back to a community fork that has been actively maintained:

```bash
XION_AO_LOCALNET_UPSTREAM=https://github.com/weavedb/ao-localnet.git \
XION_AO_LOCALNET_BRANCH=hotfix \
XION_AO_LOCALNET_COMMIT=<inspect-the-fork-and-pin-a-sha> \
bash scripts/ao-localnet-up.sh
```

Document any such fallback in `KW-AOCORE-004` for the next operator. The doctrine in `docs/28-AO-CORE.md` § "Substrate amendment (Phase 6.1.b)" already accepts both upstream-permaweb and community-fork localnet stacks as long as the operator records which substrate produced the receipt and pins the commit SHA so a third-party verifier can reproduce the bring-up.

## Port map (after upstream `2f9f98e`)

| Port | Service | Verifier-relevant? |
| --- | --- | --- |
| 4000 | ArLocal (Arweave gateway/mock) | no |
| 4002 | `mu` (messenger unit) | no — `aos` uses this internally during deploy |
| 4003 | `su` (scheduler unit) | no |
| 4004 | `cu` (compute unit) | YES — `XION_AO_GATEWAY_URL=http://localhost:4004` |
| 4007 | bundler (Arweave bundle uploader) | no |

Optional profile-gated services (port 4001 ardrive-web, 4005 turbo, 4006 scar) are not enabled by default and not used by Xion. The bring-up script does not enable them.

## Doctrine cross-references

- [docs/28-AO-CORE.md](../../docs/28-AO-CORE.md) § "Substrate amendment (Phase 6.1.b, 2026-04-XX)"
- [docs/04-ARCHITECTURE.md](../../docs/04-ARCHITECTURE.md) § AO Core
- [docs/runbooks/AO_DEPLOY_LOCALNET.md](../../docs/runbooks/AO_DEPLOY_LOCALNET.md)
- [docs/runbooks/AO_DEPLOY_WSL2.md](../../docs/runbooks/AO_DEPLOY_WSL2.md) (sibling: legacynet path)
- [KNOWN_WEAKNESSES.md](../../KNOWN_WEAKNESSES.md) § `KW-AOCORE-004` (closure path #2 — this directory is the supporting artifact)
