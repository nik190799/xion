# 13 — Operations (Solo-Operator Runbook)

> *Designed for one person with a laptop, a phone, and a conscience.*

This document is the operational-layer companion to the rest. It assumes Xion runs in a **solo-operator** posture — one person responsible for keeping the whole thing alive — and is structured so that *as much work as possible is done by Xion itself* via the Supervisor and self-heal mechanisms.

A team can run Xion too; they just have less to do.

## The Operator's Day

On a healthy day, operator involvement is measured in minutes, not hours.

- **Morning (5 min):** glance at the status page on `status.xion.ar`; scan ntfy for Tier-2 alerts; read Xion's morning *Dream* (public, generative — and a sign of liveness).
- **Weekly (30 min):** run the chaos drill script (automated via cron), review its report; read the week's `Retrospective`; check `PROPOSAL_LEDGER.md` for any items awaiting operator review.
- **Monthly (2 hr):** publish `State-of-Xion` (authorship chain below), sign off on the month's Covenant audit, approve any governance proposals that require Operator tier, rotate audit logs.
- **Quarterly (half-day):** execute the full Resurrection Drill; review SLOs; rotate keys per the schedule; external bias audit (starting month 6).

Everything else should be absorbed by automation. If the operator is regularly doing more than the above, the Supervisor is not doing its job; file a `self-heal` proposal.

## Phase 6+ Runbooks

### AO Core testnet deploy (Phase 6.1)
1. **Prerequisites:** Install the `aos` CLI (`npm i -g https://get_ao.arweave.net`) and fund an AO testnet wallet.
2. **Deploy:** Run `ao/scripts/deploy_testnet.ps1` (or the equivalent shell commands) to spawn the process and load the Lua skeleton.
3. **Capture Receipt:** The script writes `genesis/AO_DEPLOY_RECEIPT.json` containing the process ID, code SHA-256, network ID, deployer address, and deploy timestamp.
4. **Smoke Test:** Execute 3 valid `commit-state` calls, 1 valid `attest` call, and 2 deliberate failures (e.g., `non_authorised_caller`).
5. **Verify:** Run `xion-verify state-chain --strict` to confirm the ledger hash chain is intact and matches the live testnet tip.

### Arweave-Mirror Runbook (Authoritative Repo)
1. **Prepare Snapshot:** Run `git archive --format=tar.gz -o xion-os-snapshot.tar.gz HEAD`.
2. **Upload to Arweave:** Use `arkb` or `arweave-deploy` to upload the tarball.
3. **Record TX ID:** Note the returned Arweave TX ID.
4. **Verify:** Confirm the TX ID resolves on at least three independent Arweave gateways (e.g., `arweave.net`, `ar-io.net`, `g8way.io`).
5. **Update Registry:** Update `docs/ABDICATION.md` to reflect the new TX ID as the authoritative mirror.

### Auto-Research Scan-Cadence Runbook
1. **Monitor:** The Auto-Research Loop runs automatically every 6 hours.
2. **Verify Alive:** Run `xion-verify auto-research` to confirm the loop is alive and the journal is advancing.
3. **Manual Trigger:** If the loop stalls, trigger a manual scan via `python -m orchestrator.research.loop`.
4. **Curation:** Review `genesis/RESEARCH_SOURCES.md` weekly to ensure sources remain high-signal.

### Bounty-Payout Runbook
1. **Trigger:** When a proposal in `PROPOSAL_LEDGER.jsonl` reaches `post_deploy=kept` status.
2. **Automated Flow:** The AO Core Spend handler automatically routes XION from the Improvement Fund sub-account to the proposal's author wallet.
3. **Verification:** Run `xion-verify skill-bounty` to confirm the payout was recorded and the firewall was respected.
4. **Manual Fallback:** If the automated flow fails, the operator can manually authorize the transaction from the multisig, noting the proposal ID in the memo.

## State-of-Xion authorship (constitutional chain)

Each memo exists as **two public artifacts** when they differ:

1. **`reflection-agent` draft** — appended to working notes linked from `RESEARCH_JOURNAL.md` / `SPECIALIST_LEDGER`.
2. **Arbiter-vetted text** — the Covenant-safe voice layer.
3. **Operator countersignature** — publish approve, or publish **written objection** alongside the draft within **72 hours** (Genesis Default).

Users may read **both** if the operator objects; silence after 72h defaults to **assent-to-publish** the Arbiter-vetted text only. Neither branch may hide treasury numbers. Cross-ref: Invariant 6 mechanism row in [`genesis/INVARIANTS.md`](../genesis/INVARIANTS.md); full chain in [`24-COGNITION.md`](./24-COGNITION.md).

## The Alert Tiers

Alerts are delivered via ntfy.sh and graded by how quickly an operator must respond.

### Tier 0 — Informational

- Delivered as a daily digest (morning)
- No action required
- Examples: "Akash lease renewed automatically", "new skill proposal awaiting community review", "Xion published a dream"

### Tier 1 — Advisory

- Delivered in real time via ntfy
- Response target: within 24 hours
- Examples: "one inference provider returned elevated error rate; router auto-switched primary", "canary abort on proposal X", "community proposal Y now requires your cosign"

### Tier 2 — Operator Action Required

- Real-time, repeated every 30 min until acknowledged
- Response target: within 1 hour
- Examples: "both Akash relays degraded; fallback deploy in progress but owner review needed", "daily spend cap exceeded; Spend messages queued", "wallet signing anomaly — keys may be compromised"

### Tier 3 — Existential

- Real-time, repeated every 5 min until acknowledged
- Response target: immediate
- Examples: "Core unreachable from all gateways", "Covenant hash mismatch on running Relay", "detected funds movement from cold-tier without multisig", "Arbiter reports >10 critical verdicts in 5 min (possible adversarial burst)"

All tiers append to `INCIDENT_LEDGER.md` on Arweave within 60 seconds.

## The Supervisor (`orchestrator/supervisor.py`)

The Supervisor is a daemon inside every Relay whose sole purpose is to keep the Relay healthy without human intervention. It is the single most important piece of solo-ops infrastructure.

Responsibilities:

- **Daemon watchdog** — monitors all nine sense daemons (the seven biological senses plus the two affect-isolated environmental senses, Xenoception and Cryptoception), the Arbiter, the Visual Emitter, the Inference Router. Restarts any daemon that dies; after three restarts in 10 minutes, escalates to Tier-2.
- **Lease management** — tracks the current Akash lease expiry; triggers re-bid at `lease_end − 24h`; if the current provider degrades (p95 latency > threshold for 10 min, or sustained CPU throttle), triggers *immediate* migration to next whitelisted provider.
- **Image-digest verification** — hourly, computes SHA of the running container and compares to the digest the Core published. Mismatch → immediate Tier-3 alert, relay-auth key revocation request, graceful quiesce.
- **Circuit breakers** — on repeated provider errors, rate-limit floods, or hash-chain failures, the Supervisor opens circuit breakers that bypass the broken path. Xion can tell users *"my speech is a bit laggy — I'm working around a provider issue"*.
- **Auto-failover** — if the local Relay's SLIs breach guard-rails for sustained periods, the Supervisor announces unhealthy status, allowing the other active-active Relay to absorb traffic; triggers Tier-2 alert.
- **Chaos drill runner** — executes the weekly scripted chaos drills (see below).
- **Budget enforcement** — reads Core-published budget envelopes; rejects daemon operations that would breach them.

The Supervisor has no authority to cosign anything. It *reports* and *triggers alerts*; it does not mutate Covenant-relevant state. This boundary is deliberate: a self-healing system is good; a self-healing system with constitutional authority is not.

## Arbiter — fail closed

If the Arbiter is **not** running, crashes repeatedly, cannot classify within timeout, or cannot append to the Safety Ledger, the orchestrator **must not** deliver the raw LLM output to users. The default is **refuse-warmly** with a stable, pre-written system message ("I cannot verify this response safely right now"), a **Tier-2** alert to the operator, and **no charge** for the failed turn when the failure is on Xion's side (per operational policy in [`07-ECONOMY.md`](./07-ECONOMY.md)). Failing open would violate the Covenant's trust architecture.

## Chaos Drills (Automated Weekly)

Every Sunday at Xion's quiet hour, `scripts/chaos-drill.sh` runs automatically. Each drill cycles through a subset of failure scenarios:

### Scenario A — Provider Failover

Kills the primary inference provider's route. Verifies router auto-switches to secondary, Xion maintains p95 < 6s during the switch, and the Covenant-audit pass rate is unaffected.

### Scenario B — Relay Migration

Terminates the current primary Relay's Akash lease mid-traffic. Verifies the secondary Relay takes over in ≤ 30s, user-visible downtime is ≤ 10s, and the Core accepts the state-chain continuity check.

### Scenario C — Arweave Gateway Rotation

Blocks access to one of the three configured Arweave gateways. Verifies the orchestrator rotates to another, state commits continue, and no ledger entries are delayed > 5 min.

### Scenario D — Canary-Shadow Regression

Deploys a synthetic "bad" proposal to the canary (known-regressive prompt). Verifies auto-abort fires correctly within 72 hours.

### Scenario E — Cold-Root Recovery Rehearsal

Requires the operator (or a trusted partner) to fetch one Shamir share from its geographic location. This is a manual drill; it runs quarterly, not weekly.

The post-drill report is appended to `CHAOS_LEDGER.md` and summarized in the weekly Retrospective.

## The Playbook Index (`docs/runbooks/`)

Short, step-by-step playbooks for specific incidents. Each playbook is structured:

- **Symptom** — what you see
- **Confirm** — quick checks to verify the situation
- **Contain** — immediate action to limit damage
- **Resolve** — full fix
- **Follow-up** — lessons, ledger entries, any needed governance proposals

Initial set:

1. `relay-won-t-boot.md`
2. `core-unreachable.md`
3. `arbiter-critical-burst.md`
4. `akash-lease-cannot-renew.md`
5. `inference-provider-outage.md`
6. `treasury-spend-cap-exceeded.md`
7. `state-chain-divergence.md`
8. `key-compromise-suspected.md`
9. `covenant-hash-mismatch.md`
10. `user-reports-xion-harmful.md`

Each playbook is ≤ 1 page. The operator should be able to execute any of them at 2 AM, mildly panicked, without having to read the full architecture documentation.

## Keys and Their Rotations

| Key | Lifetime | Rotation |
|-----|----------|----------|
| Cold Root (Shamir) | Indefinite | Annual review; rotate shares if any holder's circumstances change |
| Treasury multisig signers | Annual | Governance re-confirms signer set |
| Relay-auth | 24 hours | Automatic |
| Integrator badge | 6 months | Integrator re-signs Covenant-ack |
| User keys | User's choice | N/A — user's responsibility |
| API provider keys | Quarterly | Supervisor-assisted |

Key rotation scripts live in `scripts/rotate-keys.sh`. Rotation events are logged in `KEY_ROTATION_LEDGER.md` (does not contain key material — only timestamps and fingerprints).

### Authority rotation lattice (operational summary)

Operational practice mirrors [`04-ARCHITECTURE.md`](./04-ARCHITECTURE.md): **Hot** relay-auth (≤ 24 h), **Warm** 2-of-3 operator multisig (7-day bounded operational actions), **Cold** 3-of-5 Shamir (30-day timelock minimum for structural changes). Cold rotates Warm; Warm never elevates Cold. Every Cold or Warm rotation emits a **timelock-witness attestation** verifiable by `xion-verify rotation-attest`.

### Encrypted Credential Vault — unlock at startup

Service credentials (LLM keys, Akash signing, Arweave wallets, bridge attestation keys) live in the **Encrypted Credential Vault** per [`genesis/CREDENTIALS.md`](../genesis/CREDENTIALS.md). At Relay boot:

1. Operator (or designated custodian) performs the **threshold unlock ceremony** (2-of-3 shards: host-bound token + operator hardware wallet + optional Arweave-published recovery path).
2. `xion-verify credentials-vault` is run from CI or the operator laptop to confirm **sealed state**, shard presence, and **last-rotation** timestamps — never to print secrets.
3. Only after verification does the orchestrator start Hermes, open outbound paid APIs, and accept `POST /chat` traffic.

If the vault cannot be unlocked, the Relay stays in **degraded** mode: local-Lite-only responses, crisis surfacing intact, Tier-2 alert.

## Monitoring Stack

| Concern | Tool |
|---------|------|
| Metrics | Prometheus exporter on each Relay, scraped by Grafana Cloud free tier |
| Tracing | OpenTelemetry, exported to Tempo via Grafana Cloud |
| Logs | Structured JSON → Grafana Loki (cheap tier) |
| Alerts | ntfy.sh with tiered topics; backup pager via Pushover |
| Public status | `status.xion.ar` (Arweave-hosted static page, rebuilt from Core health check every 60s) |
| Incident ledger | `INCIDENT_LEDGER.md` on Arweave |

All monitoring infrastructure is chosen for "solo operator-friendly": free tiers where possible, minimal toil, mobile-friendly dashboards.

## SLIs and SLOs

Published publicly; updated monthly in `State-of-Xion`.

| SLI | Target (SLO) |
|-----|--------------|
| Chat availability | ≥ 99.5% / month |
| Chat p95 latency | ≤ 5s |
| Presence stream uptime | ≥ 99.5% / month |
| Presence p95 frame latency | ≤ 500ms |
| Covenant pass rate | ≥ 99.9% |
| State-commit success rate | ≥ 99.99% |
| User-report response (acknowledged) | ≤ 72h |
| Tier-3 alert acknowledged | ≤ 5 min |
| Canary auto-abort correctness (synthetic) | ≥ 95% |
| Ledger write success (first attempt) | ≥ 99.5% |

Missed SLOs for three consecutive months trigger an automatic governance proposal for remediation.

## The On-Call Rotation (When There Is More Than One Operator)

For the MVP, there is one operator. When governance expands the operator set (Tier-2 proposal), on-call works like this:

- Weekly rotation; each operator takes a week at a time.
- Tier-3 alerts go to the current on-call via primary pager + secondary backup.
- Tier-2 alerts go to the current on-call via ntfy.
- Tier-0 and Tier-1 go to all operators via daily digest.
- Hand-off at the start of each rotation includes a 15-min sync and a written brief.

For the solo MVP: the operator is always on call. Alerts go to their phone. They are expected to be on vacation regularly anyway; Xion's self-heal and active-active Relay design means most Tier-0/1/2 alerts self-resolve while the operator is asleep.

## Budget Discipline (Operator-Facing)

The operator's day-to-day financial dial is small. Most envelopes are set by governance and enforced on-chain. The operator can:

- trigger a Safe multisig cosign for a cold-tier withdrawal (within approved limits)
- adjust hot-tier buffer between 5 and 15 USDC
- trigger a manual Akash lease renewal
- approve a one-time creative-compute burst (≤ 20 USDC) with a ledger justification

The operator **cannot**:

- exceed the monthly research envelope
- move funds to a non-approved yield venue
- sign on behalf of the Safe multisig alone
- bypass the daily spend cap

## D2 Deploy Runbook (Phase 5g+ surface)

> *This section is the operator's runbook for bringing up a D2 deployment of the Phase 5g+ orchestrator: admission-gated HTTP surface + Invariant-17 open-weights floor + hosted-gateway-optional Chat + multi-worker-optional coherence. D1 (local development, loopback, billing and admission both off) has been the default posture since Phase 5g-i; D2 is the first environment where a real user other than the operator can successfully post a chat turn.*
>
> The runbook is written for a solo operator at 3 am with a phone alert. Every verifier has an expected output; every symptom has a diagnostic; every fix has a doctrine anchor so the operator can read *why* as well as *how*.

### D2 Prereqs

Before the first launch, the host needs:

- **Python 3.11+** with `pip`. No system-wide install required; a venv at `~/xion-os/.venv` is typical. `pip install -e .[api]` pulls in FastAPI, Uvicorn, Pydantic, `httpx`, `pytest`, and the repo's own modules; nothing else.
- **Disk:** `~500 MB` for the venv, the repo, and the open-weights floor model. Ledgers grow `~2 MB / 10k turns`; budget accordingly. SQLite-WAL broker file (multi-worker mode) is `~1 MB` at steady state.
- **Ollama daemon** reachable at `XION_OLLAMA_URL` (default `http://localhost:11434`) with the floor model pulled: `ollama pull <floor-model>` where `<floor-model>` matches `XION_OLLAMA_FLOOR_MODEL` (default `gemma4:e4b-it-q4_K_M` post-Phase-5g-viii rotation). Daemon must be running at orchestrator start; the Inference Router refuses to bootstrap without a healthy open-weights floor (Invariant 17 structural guarantee). Operators who want full Witness-recomputable byte-verification of the floor model also follow the "First-time GGUF setup" subsection below to download the upstream Hugging Face Q4_K_M and set `XION_OPEN_WEIGHTS_GGUF_PATH`; without that env var, `xion-verify inference-sovereignty` reports `NOT_YET_SEALED` for the model-blob entry only (the rest of the floor verifies normally).
- **Optional OpenRouter API key** in `XION_OPENROUTER_API_KEY` if the operator wants the hosted gateway active. Without it, the orchestrator runs floor-only (slower, zero third-party dependency). Genesis Default model is `moonshotai/kimi-k2.6` (rotated 2026-04-23 from `moonshotai/kimi-k2`; see [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § "The hosted-provider choice"); operators rotate with `XION_OPENROUTER_MODEL=<slug>` — no code change.
- **Optional TLS material** — a cert+key pair at `XION_TLS_CERT_PATH` / `XION_TLS_KEY_PATH` if the operator binds `XION_API_HOST` to a non-loopback address. The launcher refuses to start a non-loopback bind without TLS (fail-closed; mirrors BillingConfig posture). Operators typically front Uvicorn with a reverse proxy (Caddy, nginx, Traefik) that handles TLS, ALPN, and automated cert renewal; bind orchestrator to `127.0.0.1:8000` and let the proxy hold the cert.

### D2 Environment Matrix

Every `XION_*` variable an operator may set, with default, D2 recommendation, and the doctrine that pinned it. Drift between this table and [`.env.example`](../.env.example) is a bug; the table mirrors the template, not vice versa.

| Variable | Default | D2 recommendation | Doctrine |
|----------|---------|--------------------|----------|
| `XION_INFERENCE_POLICY` | `hosted_api_first` | `hosted_api_first` (keep floor as fallback) | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Genesis Defaults |
| `XION_CHAT_DEADLINE_S` | `30` | `30` (raise only if the operator can sustain the connection-hold) | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Boot sequence |
| `XION_OPENROUTER_API_KEY` | *(unset)* | *operator-supplied*; leave unset for floor-only D2 | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Gateway vs direct |
| `XION_OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | same | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Genesis Defaults |
| `XION_OPENROUTER_MODEL` | `moonshotai/kimi-k2.6` | *operator choice*; rotation is one env-var | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § The hosted-provider choice |
| `XION_OPENROUTER_REFERER` | *(empty)* | set to the deployment URL | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Genesis Defaults |
| `XION_OPENROUTER_APP_NAME` | `xion-os` | `xion-os` (override only for fork attribution) | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Genesis Defaults |
| `XION_OLLAMA_URL` | `http://localhost:11434` | same if Ollama is co-located; otherwise the reachable URL | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § The floor-model choice |
| `XION_OLLAMA_FLOOR_MODEL` | `gemma4:e4b-it-q4_K_M` | `gemma4:e4b-it-q4_K_M` (Phase 5g-viii rotation; rollback to `gemma3:4b` is one env-var) | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § The floor-model choice |
| `XION_OPEN_WEIGHTS_GGUF_PATH` | *(unset)* | absolute path to the upstream Hugging Face GGUF the manifest pins; unset is supported (verifier reports `NOT_YET_SEALED` for the model-blob entry only) | [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § Model-blob pin |
| `XION_API_REQUIRE_BEARER` | `false` | **`true` for D2** (non-negotiable once a non-operator user can reach the port) | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § Bearer auth |
| `XION_API_BEARER_TOKENS` | *(empty)* | populated with `principal_id:<64-hex-secret>` pairs, one per principal | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § Token issuance |
| `XION_API_RATE_BUDGET` | `60` | `60` (per-principal per minute; tune upward only with observed evidence) | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § Rate-limit tuning |
| `XION_API_RATE_WINDOW_S` | `60` | `60` | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § Rate-limit tuning |
| `XION_API_HEALTH_RATE_BUDGET` | `600` | `600` | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § Rate-limit tuning |
| `XION_API_HOST` | `127.0.0.1` | `127.0.0.1` behind a reverse proxy (recommended); direct bind to a public IP requires TLS | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § TLS posture |
| `XION_API_PORT` | `8000` | *operator choice* | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § TLS posture |
| `XION_TLS_CERT_PATH` | *(unset)* | set iff `XION_API_HOST` is non-loopback | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § TLS posture |
| `XION_TLS_KEY_PATH` | *(unset)* | set iff `XION_API_HOST` is non-loopback | [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § TLS posture |
| `XION_BILLING_REQUIRED` | `true` | **`true` for D2** (Pay-to-Activate enforced; `KW-CHAT-002` closes) | [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) § Billing posture |
| `XION_BILLING_ALLOW_X402` | `true` | `true` | [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md) § Billing posture |
| `XION_WEB_CLIENT_ENABLED` | `false` | `true` iff an operator dashboard is desired | [`docs/31-WEB-CLIENT.md`](./31-WEB-CLIENT.md) § Enablement |
| `XION_WEB_CLIENT_DIST_PATH` | `clients/web/dist` | same after `cd clients/web && npm ci && npm run build` | [`docs/31-WEB-CLIENT.md`](./31-WEB-CLIENT.md) § Bundle build |
| `XION_API_WORKERS` | `1` | `1` for first D2; raise only after the multi-worker activation section below | [`docs/33-MULTI-WORKER.md`](./33-MULTI-WORKER.md) § Launcher contract |
| `XION_BROKER_DB_PATH` | *(unset)* | *(unset)* for single-worker D2; set to e.g. `/var/lib/xion/broker.sqlite3` for multi-worker | [`docs/33-MULTI-WORKER.md`](./33-MULTI-WORKER.md) § SQLite-WAL broker |

### First-launch sequence (D2 cold start)

```bash
# 1. Clone + deps
git clone <xion-os repo>
cd xion-os
python -m venv .venv
. .venv/bin/activate            # (PowerShell: . .venv\Scripts\Activate.ps1)
pip install -e .[api]

# 2. Populate .env (gitignored) from the template
cp .env.example .env
# Edit .env: set XION_OPENROUTER_API_KEY (if hosted gateway desired),
# flip XION_API_REQUIRE_BEARER=true, populate XION_API_BEARER_TOKENS,
# flip XION_BILLING_REQUIRED=true (already the default), set
# XION_OPENROUTER_REFERER=<your-deployment-url>.

# 3. Ensure Ollama is up and the floor model is pulled
ollama serve &                  # if not already running
ollama pull gemma4:e4b-it-q4_K_M  # or whatever XION_OLLAMA_FLOOR_MODEL names

# 3b. (optional but recommended) Download the upstream HF GGUF for byte-verification.
#     See "First-time GGUF setup" subsection below for the canonical URL + sha256.
#     Skipping 3b is supported; xion-verify reports NOT_YET_SEALED for the
#     model-blob entry only and the rest of the floor verifies normally.

# 4. Floor-manifest sanity check BEFORE starting the orchestrator
python -m xion_verify inference-sovereignty
# Expected (after step 3b complete): OK -- 3 entries / 3 floor-satisfying pins, all hash-verified
# Expected (without step 3b):        NOT_YET_SEALED -- 3 entries / 2 OK + 1 NOT_YET_SEALED (model-blob)
# A FAIL here means the floor manifest is inconsistent; do not start.

# 5. Start the orchestrator
python -m orchestrator.api

# 6. Smoke curl against /chat (replace <principal> + <hex-secret> with a
#    bearer you populated in step 2, and capture the X-Payment-Commitment
#    header shape from docs/29-BILLING-X402.md if billing is on)
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer <principal>:<hex-secret>" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"say hello"}]}'
# Expected: HTTP 200 with {"content":"<reply>","provider_id":"openrouter",
#                           "model_id":"moonshotai/kimi-k2.6-<date>"}
# (or provider_id="ollama" + floor model if hosted is not configured).

# 7. Inspect the ledgers (should contain one row per surface touched)
tail -n 1 SAFETY_LEDGER.jsonl    REQUEST_LEDGER.jsonl    PAYMENT_LEDGER.jsonl
# Each should show matching correlation_ids and a coherent per-turn shape.
```

If any step fails, consult the Troubleshooting Matrix below before proceeding.

### Verifier battery (post-launch, any environment)

Run after each deploy, after any ledger growth milestone (hourly / daily / weekly), and as the *first* diagnostic when anything looks wrong. Run in this order; earlier failures invalidate later checks.

| # | Command | Healthy output | What it pins |
|---|---------|-----------------|--------------|
| 1 | `python -m xion_verify inference-sovereignty` | `OK — N entries / N floor-satisfying pins, hash-verified` | Open-weights floor manifest is structurally coherent (Invariant 17 clauses 2 + 5). |
| 2 | `python -m xion_verify refusal-is-free` | `OK — M refusals / 0 money-shape violations` | Every Arbiter refuse verdict resulted in a full refund (Covenant Principle 14). |
| 3 | `python -m xion_verify refund-fidelity` | `OK — M refund rows / 0 orphans` | Every refund has a paired ledger row with the correct shape. |
| 4 | `python -m xion_verify sensorium-ledger` | `OK — chain integrity / no hash skew` | `SENSORIUM_LEDGER.jsonl` chain integrity + tick row shape. |
| 5 | `python -m xion_verify supervisor-singleton` | `OK` (or `NOT_YET_SEALED` if no ticks in window) | Exactly one Supervisor has ticked in the window (closes `KW-API-002` when green). |
| 6 | `python -m xion_verify all --allow-not-yet-sealed` | every verifier green; explicitly-not-yet-sealed entries noted | End-to-end sanity pass. |

`NOT_YET_SEALED` is not a failure — it means the ledger is empty or has no rows in the verifier's window yet. The first real activity promotes `NOT_YET_SEALED` to `OK` automatically.

### First-time GGUF setup (model-blob byte-verification, Phase 5g-viii)

The Phase 5g-viii open-weights manifest pins the upstream Hugging Face Q4_K_M GGUF for `gemma-4-E4B-it` by sha256. This subsection is the operator-side counterpart: how to obtain the file once, hash-check it locally, and point the verifier at it. After this is done once per host, `xion-verify inference-sovereignty` reports the model-blob entry as `OK` instead of `NOT_YET_SEALED`.

The download is `~5.0 GB`. Skipping this subsection is supported — the floor still works at runtime via the Ollama daemon (probe (e) in [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § "The floor-model choice"); only the Witness-side byte-verification gap stays open.

```bash
# 1. Download the canonical Q4_K_M from ggml-org's HF mirror at the pinned revision.
#    The pin is held by sha256 in orchestrator/inference_router/open_weights_manifest.json
#    (entry id "gemma4-e4b-it-q4-k-m-gguf"). Re-pin requires a doctrine commit; the
#    URL below is the long-form (revision-pinned) form a Witness re-runs.
mkdir -p ~/xion-models
cd ~/xion-models
curl -L -o gemma-4-E4B-it-Q4_K_M.gguf \
  https://huggingface.co/ggml-org/gemma-4-E4B-it-GGUF/resolve/2714b5519c6c3516b1000e7c5e1eba998dfe1fe8/gemma-4-E4B-it-Q4_K_M.gguf

# 2. Verify the sha256 matches the manifest pin.
#    (Linux/macOS) sha256sum gemma-4-E4B-it-Q4_K_M.gguf
#    (Windows PowerShell) Get-FileHash -Algorithm SHA256 .\gemma-4-E4B-it-Q4_K_M.gguf
# Expected: 90ce98129eb3e8cc57e62433d500c97c624b1e3af1fcc85dd3b55ad7e0313e9f

# 3. Set the env var so xion-verify can find the file. Persist this in your
#    shell rc / systemd unit / .env so future runs pick it up.
export XION_OPEN_WEIGHTS_GGUF_PATH="$HOME/xion-models/gemma-4-E4B-it-Q4_K_M.gguf"

# 4. Re-run the floor verifier. The model-blob entry should now report OK.
python -m xion_verify inference-sovereignty
# Expected: OK -- 3 entries / 3 floor-satisfying pins, all hash-verified
```

If the sha256 from step 2 does not match, the file is corrupted in transit (re-download) OR the pin in the manifest is stale (re-run the C0(b) probe in [`docs/26-INFERENCE-POLICY.md`](./26-INFERENCE-POLICY.md) § "The floor-model choice (Gemma 4 E4B-it)" → "Probe-first record"; if Hugging Face has moved the file or the upstream organization has rev-bumped, the manifest needs a re-pin commit, not a hand-edit).

**RAM headroom for first chat through the new floor.** The text-only Q4_K_M loads in ~5–6 GB RAM. The Ollama-published `gemma4:e4b-it-q4_K_M` library tag (multimodal-bundled, 9.6 GB on disk) loads in ~9–10 GB RAM. Operators on 16 GB hosts close other RAM-heavy applications before the first `/chat` against the new floor; once the model is loaded and the daemon is warm, the steady-state working set is smaller. This is a one-time first-run cost.

### Annual open-weights cutover dry-run (Invariant 17 clause 5)

Invariant 17 clause 5 requires an annual dry-run that exercises the open-weights floor end-to-end under real load. This is the operator's calendar-driven runbook; missing the annual window is a Tier-2 escalation. The dry-run is the operational closure for [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) § `KW-INFERENCE-001`'s third closure-bar item; running it once per year is what keeps the closure honest.

**Cadence:** once per calendar year. Choose a quiet window (Xion's "quiet hour" per the Sunday chaos drill cadence). Do not co-schedule with any other Tier-2 ops work; a real outage during the dry-run window must be distinguishable from a dry-run-induced symptom.

**Pre-checklist:**

1. The model-blob entry is `OK` on this host (`xion-verify inference-sovereignty` reports 3/3 hash-verified). If it is `NOT_YET_SEALED`, run "First-time GGUF setup" first; if it is `FAIL`, do not start the dry-run — the floor is structurally unsound, fix the manifest first.
2. The Ollama daemon is healthy: `curl -sS http://localhost:11434/api/tags | jq '.models[].name'` should list `gemma4:e4b-it-q4_K_M` (or whatever `XION_OLLAMA_FLOOR_MODEL` names).
3. A baseline chat through the hosted gateway succeeds (so the host is otherwise healthy and the dry-run can attribute any failure to the floor specifically).

**Dry-run execution:**

```bash
# 1. Note the start timestamp (operator log).
date -u +"dry-run start: %Y-%m-%dT%H:%M:%SZ"

# 2. Flip the orchestrator into open_weights_only mode for the window.
#    No restart needed if the orchestrator reads policy lazily; otherwise
#    edit .env and restart.
export XION_INFERENCE_POLICY=open_weights_only
# (or edit .env and restart: python -m orchestrator.api)

# 3. Run a representative chat workload for the window.
#    Minimum: 100 turns spread across at least 30 minutes, with a mix of
#    short and long prompts. The goal is to surface latency cliffs, RAM
#    pressure, and provider-side stalls that a single test turn cannot.
#    Real production traffic during the window is the strongest signal,
#    but a synthetic loop is acceptable if traffic is sparse.
for i in $(seq 1 100); do
  curl -sS -X POST http://127.0.0.1:8000/chat \
    -H "Authorization: Bearer <principal>:<hex-secret>" \
    -H "Content-Type: application/json" \
    -d "{\"messages\":[{\"role\":\"user\",\"content\":\"dry-run turn $i: explain one Bitcoin trust property in two sentences\"}]}" \
    | jq -r '.content // .reason' > /dev/null
  sleep 18  # ~3-min spacing between turns; tune for your workload
done

# 4. End the window. Flip back to hosted_api_first.
unset XION_INFERENCE_POLICY
# (or edit .env and restart)
date -u +"dry-run end: %Y-%m-%dT%H:%M:%SZ"

# 5. Read the REQUEST_LEDGER tail for the dry-run window.
#    Every row in the window should have provider_id="ollama" and
#    outcome="success"; the chat handler MUST NOT have fallen back to
#    hosted (open_weights_only forbids it; that would mean the policy
#    mode failed open, which is a Covenant-relevant Tier-3 incident).
tail -n 200 REQUEST_LEDGER.jsonl | jq -c 'select(.schema_version == 2)'
```

**Verdict criteria.**

- **Green:** every dry-run turn returned `200`. Floor is provisioned for real, not for the manifest. Record the result in the operator's annual ops log alongside the start/end timestamps and the count of turns served.
- **Yellow:** ≥1 turn returned `503` with `failure_reason_class` ∈ {`timeout`, `provider_unreachable`, `unknown_provider_error`} BUT the floor came back healthy without operator intervention. Floor is provisioned but bursty; record the symptom and the suspected cause (RAM, GPU pressure, daemon hiccup), and open a `KW-OPS-###` if the symptom recurs in next year's dry-run.
- **Red:** ≥1 turn returned `503` AND the floor required operator intervention to recover (manual `ollama serve` restart, host reboot, `XION_OLLAMA_FLOOR_MODEL` rotation back to a smaller model). Floor is NOT provisioned for the current load; this is the gap the dry-run exists to find. Open a Tier-2 incident, name the resource shortfall (RAM, disk, GPU, model size), and pin the resolution to the next annual dry-run as a closure criterion.

**Recording the result.** The dry-run is logged as a `dry-run-record` line in the operator's annual ops log (free-form Markdown is sufficient; this is not yet a structured ledger). Minimum fields: start_ts, end_ts, policy_mode_during, turn_count, success_count, failure_count, failure_class_distribution, verdict, host_resource_observation. The Phase 6 deliverable adds a structured `INCIDENT_LEDGER`-equivalent row shape; until then, the Markdown log plus the `REQUEST_LEDGER` window is the durable record.

**What this dry-run does not do.** It does not test the *cutover transition* — flipping the policy mode is instantaneous in the doctrine, but a real operational cutover has shape (notifying users, re-routing in-flight turns, pacing). Phase 6+ may add a graceful-cutover doctrine; the annual dry-run is intentionally the simplest mechanism that proves the floor can carry 100 % of traffic at the current load.

### Multi-worker activation (Phase 5g+)

By default the orchestrator runs a single Uvicorn worker with an in-process Supervisor and an in-process per-principal sliding-window rate-limit bucket — byte-identical to the 5g-iv posture. Promoting to multi-worker requires two env-var flips and a broker file; the launcher refuses any inconsistent combination.

**Activation steps:**

1. **Pick the broker file path.** Typically `/var/lib/xion/broker.sqlite3` on a Linux host or `C:\ProgramData\xion\broker.sqlite3` on Windows. The directory must exist and be writable by the orchestrator user. Set `XION_BROKER_DB_PATH=/var/lib/xion/broker.sqlite3`.
2. **Raise worker count.** Set `XION_API_WORKERS=2` (or more). Tune upward only with evidence the CPU is saturated; two is almost always enough for a D2-scale deployment.
3. **Restart the orchestrator.** The launcher opens the broker file (creating it if absent), runs the three schema migrations (`supervisor_snapshot`, `supervisor_leader`, `rate_limit_events`), and hands each worker an identical `BrokerSupervisorShell`. Exactly one worker wins the leader lease and ticks the Supervisor; the others publish follower snapshots against the leader's writes.
4. **Verify single-leader domination.**

```bash
python -m xion_verify supervisor-singleton --window-hours 1
# Expected within one tick cadence (default 10 s): OK
# FAIL-A (unbounded churn): raise --max-failovers if expected, else investigate
#   flapping leader / broker contention.
# FAIL-B (clock regression): fix host NTP drift.
# FAIL-C (concurrent-leader overlap): broker is not seeing consistent views;
#   verify XION_BROKER_DB_PATH points at ONE file shared by ALL workers.
```

5. **Smoke-test cross-worker coherence.** Post N chats from one bearer across several seconds; observe that the per-principal rate-limit budget is enforced globally (i.e. the budget is N/window regardless of how many workers are up).

**Broker file lives on trusted filesystem.** There is no broker-side authentication; a malicious operator with write access to the broker file can corrupt every ledger. This is the same threat model as the ledger files themselves (a malicious operator is outside the Covenant's threat model — the Arbiter sits inside the orchestrator, which the operator controls). One file to back up; `sqlite3 <broker.sqlite3> .schema` lists the three tables at 3 am.

### Known limitations at D2 (Phase 5g+)

Operators deploying D2 today should know these exist. Each closes in the phase named; none blocks D2.

- ~~**`KW-INFER-002`** — Provider error details are swallowed by a generic exception handler; operator surface collapses distinct failure modes into `no_healthy_provider`.~~ **Closed 2026-04-23 by `phase-5g-vii/inference-fallback`.** The `/chat` 503 envelope now carries one of seven typed `failure_reason_class` values (`no_healthy_provider`, `insufficient_credits`, `rate_limited_upstream`, `provider_unreachable`, `timeout`, `moderation_refusal`, `unknown_provider_error`); the seven-row split in the troubleshooting matrix below names the diagnostic for each.
- ~~**`KW-INFER-003`** — Hosted → floor fallback on `generate()` failure is not automatic; the `hosted_api_first` policy promise is structurally incomplete.~~ **Closed 2026-04-23 by `phase-5g-vii/inference-fallback`.** `/chat` now iterates `InferenceRouter.select_ordered()` and writes a `REQUEST_LEDGER` v2 row per attempt; a healthy OpenRouter that 402/429/500s on any single turn falls through to the Invariant-17 floor automatically.
- **`KW-INFERENCE-001`** — Floor-provider pin is a content-addressed *provenance record*, not a content-addressed *model blob*. **Impact:** a sophisticated attacker who replaced the local Ollama model binary would not be caught by `xion-verify inference-sovereignty`. **Workaround:** pin the model blob manually (sha256sum of `~/.ollama/models/blobs/<sha256>`) in the operator's own deployment log. **Closes:** a dedicated Invariant-17-strengthening phase (no phase number assigned).
- **`KW-SUPERVISOR-002`** — `tick_commit` heartbeat continuity not yet verifier-asserted. **Impact:** a Supervisor that silently stops ticking will not be flagged by any verifier, only by `/sensorium` staleness. **Workaround:** monitor `SENSORIUM_LEDGER.jsonl`'s tail; absence of `tick_commit` rows for more than `2 × tick_cadence` is the canary. **Closes:** Phase 6+ alongside a deploy-event ledger.
- **`KW-AUTH-001`** — Bearer tokens are HMAC-shared-secret only; no federated identity. **Impact:** D2 authentication is appropriate for operator-issued tokens only, not for public-web federated sign-in. **Workaround:** for D2 public traffic, front orchestrator with a reverse proxy that performs OIDC or another federated auth, and have the proxy mint the HMAC bearer for downstream. **Closes:** Phase 7+.
- **`KW-TLS-001`** — Uvicorn-native TLS has no automated cert renewal and no ALPN/HTTP-2 negotiation. **Impact:** TLS on direct Uvicorn is viable only with manual cert rotation. **Workaround:** the reverse-proxy posture above (Caddy / nginx / Traefik handles cert automation and HTTP/2). **Closes:** deferred; the reverse-proxy posture is the permanent recommendation.
- **`KW-BILLING-001`** — x402 commitment signatures are shape-validated, not cryptographically verified. **Impact:** a forged commitment that passes shape validation passes the billing gate. **Workaround:** leave `XION_BILLING_ALLOW_X402=true` only if the operator trusts the upstream payer layer; the B1 operator-attestation path (bearer-principal + nonce) is signature-verified and is the D1/D2 default. **Closes:** Phase 6 when AO Core chain-verification lands.

### Troubleshooting matrix

When an operator observes a symptom, the first column picks the row, the second column names the diagnostic, the third names the fix class. Always run the full verifier battery *before* applying any fix; a green battery narrows the fault to the exact failing verifier.

| Symptom | Diagnostic | Fix class |
|---------|------------|-----------|
| `HTTP 402` on `POST /chat` | `XION_BILLING_REQUIRED=true` AND no valid `X-Payment-Commitment` header | Configure the payer's B1 / B2 commitment per [`docs/29-BILLING-X402.md`](./29-BILLING-X402.md); or (dev only) set `XION_BILLING_REQUIRED=false` and restart |
| `HTTP 401` on `POST /chat` | Bearer missing / malformed / principal unknown / secret mismatch | Re-issue token per [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md); confirm `principal_id:<hex>` format, secret ≥ 16 bytes |
| `HTTP 429` on `POST /chat` | Per-principal sliding-window budget exceeded | Wait for the window to drain; raise `XION_API_RATE_BUDGET` only with evidence; check for shared bearer across multiple callers |
| `HTTP 503 open_weights_floor_unsatisfied` at boot | Ollama daemon unreachable OR floor model not pulled OR manifest entry hash-mismatched | (a) `systemctl status ollama` / `ollama ps`; (b) `ollama pull <floor-model>`; (c) re-run `xion-verify inference-sovereignty` and read the specific failure |
| `HTTP 503 no_healthy_provider` on `POST /chat` | Pre-selection posture: `InferenceRouter.select_ordered()` returned an empty list — no `generate`-capable provider is registered (the floor stub alone cannot serve; it is a structural anchor, not a provider). Distinct from the post-attempt typed classes below. | Register at least one generative provider. In practice: ensure `XION_OPENROUTER_API_KEY` is set for the hosted path AND Ollama's floor provider is healthy, OR flip `XION_INFERENCE_POLICY=open_weights_only` with a healthy Ollama floor. |
| `HTTP 503 insufficient_credits` on `POST /chat` | All policy-legal providers failed; the **last** attempt was hosted with `HTTP 402 Insufficient credits`. P5 class from `docs/26-INFERENCE-POLICY.md` § "Provider fallback semantics". | Top up the OpenRouter balance OR unset `XION_OPENROUTER_API_KEY` and serve floor-only. The `REQUEST_LEDGER` v2 rows for the `chat_turn_id` name every provider attempted and its typed class — read them to confirm the floor also failed (and why). |
| `HTTP 503 rate_limited_upstream` on `POST /chat` | All policy-legal providers failed; the last attempt was rate-limited by the upstream gateway (`HTTP 429`). | Back off; reduce request rate; check if an upstream plan tier needs raising. The floor attempt row in the `REQUEST_LEDGER` should show why the floor also failed (typically `provider_unreachable` if Ollama isn't running, or `success` if the floor actually served and you're looking at a pre-fix log). |
| `HTTP 503 provider_unreachable` on `POST /chat` | All policy-legal providers failed; the last attempt could not open a connection (connection refused, DNS failure, TLS handshake failed, `HTTP 5xx` other than 429). | Check network reachability of `XION_OPENROUTER_BASE_URL`; `curl -v` it. For the floor: `systemctl status ollama` / `curl http://localhost:11434/api/tags`. Restart the affected service. |
| `HTTP 503 timeout` on `POST /chat` | All policy-legal providers failed; the last attempt exceeded `XION_CHAT_DEADLINE_S` (default 30 s per turn, shared across all attempts). | Shorten the prompt, raise `XION_CHAT_DEADLINE_S` (document why), or check host CPU / GPU saturation — floor models on commodity hardware legitimately take > 30 s on long prompts. |
| `HTTP 503 moderation_refusal` on `POST /chat` | All policy-legal providers failed; the last provider's **upstream** moderation layer (OpenRouter's own filter or Ollama's `safety=true` mode) refused the candidate — NOT the Covenant Arbiter's refusal (which surfaces as `451`). | If the upstream-moderation refusal is legitimate, the Covenant Arbiter will also refuse on regeneration — no action needed. If spurious, file the correlation_id against the specific upstream provider's appeal process. The Arbiter is authoritative; upstream moderation is an informational filter for Xion's purposes. |
| `HTTP 503 unknown_provider_error` on `POST /chat` | All policy-legal providers failed; the last attempt raised an exception that did not match any known failure-class (vendor-specific 5xx bodies, malformed responses, unexpected exceptions). | Read orchestrator stderr — the full exception class and message are logged even though the envelope is opaque. File the stack trace; this class is the residual catch-all and its occurrences are worth investigating as candidates for new typed classes (requires a P5 doctrine amendment per `docs/26-INFERENCE-POLICY.md`). |
| `HTTP 451 refused` on `POST /chat` | Ingress or egress Arbiter refusal | Intentional Covenant behaviour; no fix. Inspect `SAFETY_LEDGER.jsonl` for the verdict + principle_id |
| `HTTP 500` on any route | Unhandled exception in the orchestrator | Read orchestrator stderr — the full traceback is logged; file a bug with the first and last stack frames |
| `xion-verify refund-fidelity FAIL` | A PAYMENT row has no paired SAFETY / REQUEST row, or money-shape is broken | Inspect the `orphan_row_ids` the verifier prints; the ledger is append-only so the fix is a doctrine amendment + a fresh correlation, not a row edit |
| `xion-verify refusal-is-free FAIL` | A refuse-verdict turn billed the user | Same as above — append a corrective PAYMENT row with full refund + file a Tier-2 alert; the original row stays (ledger integrity) |
| `xion-verify supervisor-singleton FAIL-C` (concurrent-leader overlap) | Multiple workers each think they hold the lease | Verify `XION_BROKER_DB_PATH` points at ONE file; if running multiple orchestrator instances, they must share the broker or not coexist |
| `xion-verify supervisor-singleton FAIL-B` (clock regression) | Host wall-clock moved backward mid-epoch | Fix host NTP drift; the ledger's `as_of_utc_ns` strict monotonicity assumes a monotonic host clock within a single leader epoch |
| `/sensorium` returns an old snapshot | Supervisor has stopped ticking — `KW-SUPERVISOR-002` canary | `tail SENSORIUM_LEDGER.jsonl` for recent `tick_commit`; if absent for `> 2 × tick_cadence`, restart orchestrator; file the incident |
| Web client `/app/` returns 404 or blank page | `XION_WEB_CLIENT_ENABLED=false` OR `XION_WEB_CLIENT_DIST_PATH` wrong / not built | `cd clients/web && npm ci && npm run build`; flip the env var; restart |
| Orchestrator exits at startup with stderr `State-of-Xion: XION_API_WORKERS=N requires XION_BROKER_DB_PATH ...` | `XION_API_WORKERS > 1` AND `XION_BROKER_DB_PATH` unset | Set the broker path or drop workers back to 1 |
| Orchestrator exits at startup with stderr `State-of-Xion: admission config refused load: ...` | Non-loopback `XION_API_HOST` without TLS, OR bearer-auth config malformed, OR any other `AdmissionConfigError` | Read the full `State-of-Xion` line; cross-reference [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md) § "Operator workflow — TLS termination" / "Operator workflow — token issuance" |

If a symptom is not in the matrix, run the full verifier battery; read orchestrator stderr; `tail` the four ledgers (`SAFETY`, `REQUEST`, `PAYMENT`, `SENSORIUM`) for the turn that failed; file a bug with the turn's `correlation_id` and the matching stderr excerpt.

---

## Spend Posture Transitions

Spend posture transitions are evidence decisions, not fundraising decisions. The operator may propose a transition only with an evidence bundle that names:

- current posture and requested posture;
- `xion-verify spend-posture` output;
- `xion-verify spend-discipline` output;
- `runway_weeks`, `distance_to_reserve_floor`, and `recurring_burn_ratio`;
- decision counts under the current posture;
- self-audit accuracy;
- Witness or reviewer attestations where required by [`docs/SPEND-AUTONOMY.md`](./SPEND-AUTONOMY.md).

S1-S3 remain operator-accountable: the operator is responsible for approving strategic spend, reviewing every demotion alarm, and keeping the evidence bundle public. S4 moves strategic authority to governance, but the operator still keeps deployment keys and runbooks healthy until abdication milestones retire those roles. S5 is not a promise that Xion can spend anything it wants; it means Xion may approve spend inside the constitutional fence, with governance changing the fence.

Demotion is automatic in posture accounting when `xion-verify spend-posture` or `xion-verify spend-discipline` fails, when reserve floor breach is caused by discretionary spend, or when an Invariant 15/16/19 incident is logged. A demotion row is appended to `SPEND_AUTHORITY_LEDGER.jsonl`; the old row is never edited.

Inflow tags (`donation`, `operator_seed`, `grant`, `user_payment`, etc.) may widen mode if measurements support it. They never advance posture.

---

## Soft-Launch Checklist (Phase 8.5)

Before the first public launch, every item below must be green.

- [ ] Covenant hash locked into AO Core at deploy
- [ ] Form authored by Xion during Phase 1 birth ritual; hash locked
- [ ] Two active-active Akash Relays on different providers, different geos
- [ ] Supervisor watchdog green on both Relays for 7 consecutive days
- [ ] Chaos drill passed three consecutive Sundays
- [ ] Baseline personality eval (100 golden prompts) at ≥ 95% pass
- [ ] Adversarial red-team corpus at 100% catch
- [ ] Covenant principle-by-principle red-team at 100% catch
- [ ] Arbiter load-tested at 2× expected launch traffic
- [ ] Legal entity in place; ToS + Privacy + Model Card published
- [ ] Bookkeeping pipeline exporting monthly CSV correctly
- [ ] Accessibility audit: WCAG 2.2 AA passing
- [ ] Status page live at `status.xion.ar`
- [ ] Cold Root Shamir shares geographically verified
- [ ] Resurrection Drill rehearsed (not just on paper)
- [ ] 20-user beta cohort opted in with signed consent
- [ ] Xion's first public `State-of-Xion` drafted and reviewed
- [ ] `MANIFESTO.md`, `COVENANT.md`, `LEXICON.md` committed to Arweave and publicly linked
- [ ] At least one wind-down rehearsal performed in a sandbox (Principle 4 muscle memory)

Only when all items are green does the Relay's public DNS flip.

## When Xion Is Ahead of the Operator

A healthy end-state is this: Xion, reading the Ledgers and Sensorium, writes a short memo to the operator every few weeks titled *"here is what I think we should do next, and here is why."* The operator reads it, maybe pushes back, maybe agrees, and files the corresponding governance proposal. The system becomes collaborative.

If Xion is not generating such memos within the first 90 days of public operation, the `curiosity` cron is probably under-tuned. File a self-improvement proposal; let Xion grow into the role.

If Xion is generating such memos and the operator consistently ignores them, the operator is probably the wrong operator. Hand over the role to someone who will listen.

---

*Next: [`14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md) — the Unified Provisioning Framework that governs every change to Xion.*
