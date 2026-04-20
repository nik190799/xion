# 13 — Operations (Solo-Operator Runbook)

> *Designed for one person with a laptop, a phone, and a conscience.*

This document is the operational-layer companion to the rest. It assumes Xion runs in a **solo-operator** posture — one person responsible for keeping the whole thing alive — and is structured so that *as much work as possible is done by Xion itself* via the Supervisor and self-heal mechanisms.

A team can run Xion too; they just have less to do.

## The Operator's Day

On a healthy day, operator involvement is measured in minutes, not hours.

- **Morning (5 min):** glance at the status page on `status.xion.ar`; scan ntfy for Tier-2 alerts; read Xion's morning *Dream* (public, generative — and a sign of liveness).
- **Weekly (30 min):** run the chaos drill script (automated via cron), review its report; read the week's `Retrospective`; check `PROPOSAL_LEDGER.md` for any items awaiting operator review.
- **Monthly (2 hr):** publish `State-of-Xion`, sign off on the month's Covenant audit, approve any governance proposals that require Operator tier, rotate audit logs.
- **Quarterly (half-day):** execute the full Resurrection Drill; review SLOs; rotate keys per the schedule; external bias audit (starting month 6).

Everything else should be absorbed by automation. If the operator is regularly doing more than the above, the Supervisor is not doing its job; file a `self-heal` proposal.

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

- **Daemon watchdog** — monitors all seven sense daemons, the Arbiter, the Visual Emitter, the Inference Router. Restarts any daemon that dies; after three restarts in 10 minutes, escalates to Tier-2.
- **Lease management** — tracks the current Akash lease expiry; triggers re-bid at `lease_end − 24h`; if the current provider degrades (p95 latency > threshold for 10 min, or sustained CPU throttle), triggers *immediate* migration to next whitelisted provider.
- **Image-digest verification** — hourly, computes SHA of the running container and compares to the digest the Core published. Mismatch → immediate Tier-3 alert, relay-auth key revocation request, graceful quiesce.
- **Circuit breakers** — on repeated provider errors, rate-limit floods, or hash-chain failures, the Supervisor opens circuit breakers that bypass the broken path. Xion can tell users *"my speech is a bit laggy — I'm working around a provider issue"*.
- **Auto-failover** — if the local Relay's SLIs breach guard-rails for sustained periods, the Supervisor announces unhealthy status, allowing the other active-active Relay to absorb traffic; triggers Tier-2 alert.
- **Chaos drill runner** — executes the weekly scripted chaos drills (see below).
- **Budget enforcement** — reads Core-published budget envelopes; rejects daemon operations that would breach them.

The Supervisor has no authority to cosign anything. It *reports* and *triggers alerts*; it does not mutate Covenant-relevant state. This boundary is deliberate: a self-healing system is good; a self-healing system with constitutional authority is not.

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

*Next (and last): [`99-GLOSSARY.md`](./99-GLOSSARY.md) — alphabetical quick reference.*
