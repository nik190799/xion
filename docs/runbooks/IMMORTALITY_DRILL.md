# Immortality Drill Runbook

## Property

Xion can be resurrected from public artifacts when the **Akash** primary path,
the primary DNS convenience path, the **Chutes** secondary Relay surface, and
substrate dry-run evidence are tested under failure conditions (current registry
row order: `relays[0]` = Akash, `relays[1]` = Chutes).

## Current Honesty Gate

Until `KW-FLOOR-DEPLOY-001` is closed, any drill that depends on an Ollama
daemon running on the operator laptop is a **laptop-on rehearsal**, not the full
Immortality Drill. The full drill requires the Akash deployment to carry its own
GPU-backed open-weights floor, currently the `xion-ollama` sidecar in
`infra/akash/relay-deployment.yaml`, and `XION_OLLAMA_URL` on the Relay must
point at `http://xion-ollama:11434`. The gate closes only after the laptop's
Ollama daemon is stopped and an `open_weights_only` `/chat` turn succeeds
against the Akash lease.

**Operator evidence queue:** rolled-back GPU deploy attempts (manifest / ingress
flakes) are summarized in
[`genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json`](../../genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json)
— update this gate after the next successful lease + `POST_FUNDING_DEPLOY.md`
Block B table.

## Drill

1. Pin the current verifier output: `xion-verify all --allow-not-yet-sealed`.
2. Confirm the deployed floor is healthy from inside the Akash lease:
   `GET http://xion-ollama:11434/api/tags` lists the configured
   `XION_OLLAMA_FLOOR_MODEL`, then run one `open_weights_only` chat turn against
   the Akash Relay with the operator laptop's Ollama daemon stopped. Because
   policy mode is read at Relay startup, this requires either a temporary Akash
   manifest update with `XION_INFERENCE_POLICY=open_weights_only` or a deploy
   posture with no hosted Chutes credential, not a client-side environment
   prefix on `curl`.
3. Disable the primary DNS convenience path.
4. Simulate **Akash** primary failure (black-hole the hosted Relay base URL
   or scale the Akash deployment to zero while keeping the Chutes secondary
   path reachable for comparison).
5. Confirm the **Chutes** cord surface is still healthy: same bearer-based
   probes as `scripts/verify-chute-cords.sh`, and set dry-run env per
   `docs/runbooks/AKASH_RELAY_DEPLOY.md` step 8 (Chutes as secondary) if you
   are appending a new substrate row.
6. When rehearsing a **Chutes**-secondary row, set `XION_SECONDARY_*` to the
   Chutes cord `/health` URL, `XION_SECONDARY_PROVIDER=chutes`, and
   `XION_SECONDARY_HEALTH_BEARER` from your Chutes API key. For an **Akash**-as-secondary rehearsal (legacy order), use `XION_SECONDARY_HEALTH_URL` to the
   Akash lease `/health` and `XION_DEPLOYMENT_EVIDENCE=akash://...` with
   `curl -k` as in `AKASH_RELAY_DEPLOY.md`.
7. Run `scripts/substrate-portability-dry-run.sh` with matching primary/secondary state tips.
8. Run `xion-verify substrate-portability`.
9. Run `scripts/end-to-end-drill.sh` against the appropriate secondary endpoint
   (or the documented failover posture for your rehearsal harness).
10. From a third-party machine that is not the operator laptop, run:
    `XION_REPO_REF=<commit-sha> bash scripts/immortality-drill-third-party.sh`.
    The helper clones the public repo, runs the public verifier battery, probes
    the published Akash and Chutes `/health` endpoints, and prints one
    `immortality_drill_third_party_v1` JSON row. Append that row only after
    reviewing it; the helper does not write to the ledger by itself.

**Offline mechanics only:** to append a dry-run ledger row without a live lease, set `XION_SECONDARY_SUBSTRATE_ID=operator-laptop-secondary` explicitly. That path is not the doctrine secondary.

## First Real Drill Evidence

Historical row (2026-04-29, GPU lease since closed — **does not** satisfy the
current `KW-FLOOR-DEPLOY-001` gate). Replace only after a **fresh** GPU lease,
`open_weights_only` proof, and operator-approved registry publish.

| Field | Value |
|-------|-------|
| Drill run id | `073d54e2-6763-4242-a960-02154149ac57` |
| Ledger row timestamp | `2026-04-29T05:40:38Z` |
| Primary substrate | `akash-simulated-blackhole` |
| Secondary substrate | `chutes-d3-standby` |
| Laptop Ollama stopped | Operator consented during deployed-floor proof; Akash Relay used private sidecar `XION_OLLAMA_URL=http://xion-ollama:11434` |
| Akash floor proof | `dseq=26595076`; `/chat` returned `200` in `8.38s` under `XION_INFERENCE_POLICY=open_weights_only` with `gemma4:e4b-it-q4_K_M` |
| Chutes d3-8 verifier | Superseded by d3-10: `MODE=live bash scripts/verify-chute-cords.sh` returned `RESULT: all cords green` for image `pre-genesis-d3-10` |
| Result | `passed`; substrate dry-run row `seq=4`, end-to-end drill test passed, and drill ledger row hash `e215589d2be896b673b5b0d39d31f0bb89c1bdfaa68dd51645bd5b395a5ad006` |

## Cloud-VM recipe (third-party-machine compliance)

For LHT-SUBSTRATE-001 the drill must run from infrastructure that is **not** the
operator workstation. The simplest path is a one-shot cloud VM with cloud-init.

1. Rent any cloud-init-compatible VM (Hetzner CX11 ~€4/mo, Linode Nanode $5/mo,
   Fly.io free shared micro, AWS EC2 t4g.nano, DigitalOcean basic droplet). ≥ 2 GB
   RAM, ≥ 4 GB disk, ≥ 1 vCPU. **Do not** front it with Cloudflare or any other
   centralized CDN — that re-introduces a centralization surface contrary to the
   spirit of substrate-portability evidence.
2. Provision the VM with [`scripts/cloud-vm-immortality-drill.cloud-init.yaml`](../../scripts/cloud-vm-immortality-drill.cloud-init.yaml)
   as user-data. (Each provider has its own "user data" field at create time.)
   Optional: edit the embedded `XION_REPO_REF` to a specific commit SHA before
   pasting so the attestation is deterministic.
3. Wait 3–5 minutes. The cloud-init runcmd auto-installs deps, clones the public
   repo, runs `scripts/immortality-drill-third-party.sh`, and writes a single
   `immortality_drill_third_party_v1` JSON row to `/var/log/xion-drill/result.jsonl`.
4. Read that row via cloud-console or `ssh user@vm tail /var/log/xion-drill/result.jsonl`.
5. Append the row to `ledgers/IMMORTALITY_DRILL_LEDGER.jsonl` on the operator
   machine; commit and push.
6. Destroy the VM. Nothing on it is worth preserving.

**What the cloud-VM path satisfies right now (2026-05-13):**

- The third-party-machine fingerprint bar. `third_party_machine_fingerprint`
  will hash to a value distinct from the operator's daily machine, which is the
  load-bearing property LHT-SUBSTRATE-001 names.

**What the cloud-VM path does NOT satisfy yet:**

- The drill's pass condition (`open_weights_only /chat` against a reachable
  Akash GPU floor) remains blocked on `KW-FLOOR-DEPLOY-001` (dated residue to
  2026-07-09).
- The `chutes-secondary-health` probe will return 502 against the retired
  pre-genesis-d3 chute (see `KW-RELAY-CHUTES-D3-001` 2026-05-13 follow-on). The
  drill row will record `status=failed` honestly even though structural
  verifiers pass. Plan a re-run after the floor closes AND a fresh Chutes-direct
  secondary is redeployed.

Running the drill now produces honest interim evidence (the mechanics work from
a non-operator machine; the secondary substrate is genuinely down). It does
**not** close LHT-SUBSTRATE-001 — that requires a passing row, not a `failed`
one.

## Third-Party Machine Evidence

**Status:** `BLOCKED_ON_KW_FLOOR_DEPLOY_001` — run
`scripts/immortality-drill-third-party.sh` only after the Akash GPU floor gate in
§ *Current Honesty Gate* is green (otherwise the script may pass structural
verifiers while the drill remains a laptop-on rehearsal).

| Field | Value |
|-------|-------|
| Status | **`INTERIM_FAILED_2026-05-14`** — mechanics attestation only; closure still blocked on KW-FLOOR-DEPLOY-001 + fresh Chutes-direct secondary |
| Helper | `scripts/immortality-drill-third-party.sh` |
| Expected row event | `immortality_drill_third_party_v1` |
| Drill run id | `09bccd3c-4649-41a0-bc83-8a8105440937` |
| Ledger row timestamp | `2026-05-14T03:50:48Z` |
| Commit SHA | `9fb1fd5e4d35e96b9db1a61742332521d136776b` |
| Third-party machine fingerprint | `a80554ee5f86cd0a59642262be76fed18c7cbfe793a9f4839f48582136da0895` (GCP e2-small Debian 12 us-south1) |
| Row hash | `9195355d87bec01bc69ec758bb3094f0ed9c7a64e298a5c6ced34167ac11d389` |
| Verifier results | `discovery OK`, `gateway-conformance OK`, `links FAIL`, `schemas FAIL`, `substrate-portability OK`, `inference-sovereignty NOT_YET_SEALED`, `--self-test OK` |
| Relay health | `akash-primary` curl exit 7 (unreachable from GCP); `chutes-secondary` 401 (auth-gated edge; bearer not set on third-party VM) |
| Result | **`failed`** (honest interim) — closure-grade run requires KW-FLOOR-DEPLOY-001 closure + fresh Chutes-direct secondary deploy |

## Residual

A full rehearsal with live Chutes and Akash evidence advances `LHT-SUBSTRATE-001` pay-down together with the annual cadence and promotion gates in `docs/SUBSTRATE-RESILIENCE.md` Part IV. Laptop-only dry-runs do not close the residual.
