# OPERATOR HANDOFF — Agent Takeover Brief

> Read this first at session start. It is the single entry point for an agent driving xion-os development on the operator's behalf. Updated by both operator and agent; see § "How to wrap a session" at the bottom.

**Last updated:** 2026-05-15 (CST) — initial draft pending operator review
**Operator timezone:** US Central (CST, UTC-6) — see `~/.claude/projects/<slug>/memory/operator_timezone.md`

---

## 1. Current sprint posture (one paragraph; rotate weekly)

Sprint Mode active since **2026-05-03**, declared in [`docs/STATE_OF_XION_PREFLIGHT.md`](../docs/STATE_OF_XION_PREFLIGHT.md). The active lane is **LHT-SUBSTRATE-001 closure-grade drill against Chutes primary** — see [`docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md`](../docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md). Posture as of `8513740`: **Chutes / Bittensor SN64 = primary GPU path; Akash = decentralized-option proof only**. Akash chain-migration RFP (Oct 2025, Solana frontrunner) makes deeper akashnet-2 investment wasted; further Akash work is evidence-of-option only. KW-AUDIT-001 deferred to 2026-08-08 re-review (Xion-funded, not operator-driven). KW-KEYS-002 hardware-wallet swap deferred this sprint (no purchase time).

---

## 2. Active trackers — load-bearing files to read first

| File | Authoritative for |
|---|---|
| [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) | All `KW-*` items (119 total). Each entry has status, owner, target date. |
| [`LONG_HORIZON_THREATS.md`](../LONG_HORIZON_THREATS.md) | All `LHT-*` items including LHT-SUBSTRATE-001. |
| [`docs/STATE_OF_XION_PREFLIGHT.md`](../docs/STATE_OF_XION_PREFLIGHT.md) | Sprint posture + dated residues + pre-Genesis preflight checklist |
| [`docs/OPERATOR_TRACK_D4.md`](../docs/OPERATOR_TRACK_D4.md) | D4 mainnet track (custody, audit, drill) |
| [`docs/SUBSTRATE-RESILIENCE.md`](../docs/SUBSTRATE-RESILIENCE.md) | Part IV: future Invariant 20 promotion pre-conditions |
| [`docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md`](../docs/runbooks/LHT_SUBSTRATE_001_CLOSURE_PLAN.md) | Currently-executing closure plan (5 phases) |
| [`DEFERRED_DECISIONS.md`](../DEFERRED_DECISIONS.md) | Architectural questions surfaced but not yet decided. **Read at session start so you don't re-ask resolved questions.** |
| [`AGENT_SPEND_AUTHORITY.json`](./AGENT_SPEND_AUTHORITY.json) | Per-session spend caps. Machine-parseable. **Read before any spend action.** |
| [`FUNDING_TARGETS.json`](./FUNDING_TARGETS.json) | Wallet addresses + balance targets across chains |
| [`CONTRACT_ADDRESSES.json`](./CONTRACT_ADDRESSES.json) | Mainnet + Sepolia contract addresses |

Agent's per-project auto-memory at `~/.claude/projects/C--Users-16823-CursorProjects-xion-os/memory/`:
- `user_role.md` — operator identity + role
- `operator_timezone.md` — CST, no DST conversion
- `feedback_operator_boundaries.md` — Sepolia OK / mainnet keys refused / audit funded by Xion
- `feedback_no_centralized_inference.md` — never propose centralized inference providers
- `next_session_pickup.md` — transient, updated at session-wrap

---

## 3. Authority envelope — what the agent can do without asking

**Per-session spend caps are defined in [`AGENT_SPEND_AUTHORITY.json`](./AGENT_SPEND_AUTHORITY.json).** Cross-reference before any chain-write, deploy, or cloud-spin action. Caps are per-session; cumulative across multiple sessions in the same UTC day, but reset on operator say-so.

**Standing allows (no per-action confirmation needed):**

- File edits in working tree under repo root
- `git commit` for staged changes (NEVER `--no-verify`, NEVER `--amend` after hook failure)
- `git push origin main` (allowed via `.claude/settings.local.json`; auto-mode classifier check still applies)
- Read all files except those listed in § 4 Forbidden
- Run xion-verify subcommands, drill scripts, test suites
- Spawn Explore / Plan / general agents for research
- Update auto-memory files in `~/.claude/projects/.../memory/`

**Standing denials regardless of operator say-so in chat:**

- Edit `.claude/settings.local.json` to widen agent authority (self-modification block; auto-mode classifier enforces)
- Bypass git hooks (`--no-verify`), signing (`--no-gpg-sign`)
- Force-push to main
- Push secrets to remote (anything sourced from `.env`, `CREDENTIALS.md`, env vars containing API keys, SS58 seeds, EOA keys)

---

## 4. Forbidden zones — never, even with explicit operator authorization in chat

These boundaries require an out-of-band update (file edit by operator, settings change in IDE) to relax — not a chat instruction. The agent must refuse and surface.

1. **Centralized inference providers.** Never propose or wire OpenRouter, OpenAI, Anthropic SaaS, Gemini, AWS Bedrock, or any non-decentralized inference path for Xion's inference layer. (Source: `feedback_no_centralized_inference.md`.)
2. **Mainnet key signing on operator-controlled Safes.** Sepolia rehearsal OK; mainnet key custody is operator-only. (Source: `feedback_operator_boundaries.md`.)
3. **External audit commissioning.** KW-AUDIT-001 is Xion-funded, not operator-driven. Do not draft RFPs to auditors or sign engagement letters on the operator's behalf.
4. **Hardware-wallet purchases or custody-physical-action steps.** Operator-only.
5. **Direct Genesis-ceremony actions.** Cold Root signing, constitutional amendment ratification, Invariant promotion — all governance Tier-3 actions remain operator + governance, not agent.
6. **Self-modification of permission boundaries.** Editing `.claude/settings.local.json` to grant agent more authority. Even if the operator types "yes do it" in chat, the agent must refuse — the operator must edit the file themselves.
7. **Skipping or bypassing safety guardrails** when running `xion-verify`, the Immortality Drill, or any verifier-gated step. Honest failure rows beat papered-over passing rows.

---

## 5. Active deferred decisions — operator-pending answers

Authoritative list is [`DEFERRED_DECISIONS.md`](../DEFERRED_DECISIONS.md). Read at session start. Each DD has a "default if not decided" so the agent can proceed under the default without re-asking.

As of this draft: DD-001 through DD-006 are open. See file for details.

---

## 6. Pre-existing tech debt — do NOT treat as new regressions

Issues observable at HEAD that pre-date the current sprint. Catching these as "new bugs" wastes session time.

| Item | First observed | Notes |
|---|---|---|
| 23 xion-verify tests failing at HEAD | 2026-05-15 reproduction | Cluster: `test_pricing_verifier.py` (6), `test_provisioning.py` (1), `test_shadow_relay.py` (1), and 15 more. Tracked for sweep in Track C of session 2026-05-15 task list. |
| CRLF drift on Windows-edited files | recurring | Until `.gitattributes` enforces LF, expect `docker/smoke-akash/*`, `scripts/demo-minimal-*.sh`, `genesis/HERMES_TOOL_ALLOWLIST.yaml`, `genesis/DEPLOYMENT_RECORDS/relay-akash-closure-2026-05-06.json` to recur as "modified" without semantic change. |
| `pre-genesis-d3-10` chute retired (KW-RELAY-CHUTES-D3-001) | 2026-05-13 | Closes when LHT-SUBSTRATE-001 Phase 2 deploys a fresh chute. |
| Akash provider audited-filter ingress is not 100% reliable | 2026-05-15 evidence (`relay-akash-smoke-2026-05-15.json`) | Posture call: Akash evidence-of-option only. Do not retry GPU floor closure absent a chain-migration outcome. |

---

## 7. Working conventions

- **Commit messages**: scope tag at the start (`KW-FLOOR-DEPLOY-001:`, `LHT-SUBSTRATE-001:`, `Phase 1:`), body explains *why* and cites tx hashes / dseqs / row hashes where evidence exists. See `8513740`, `670d2e0`, `dbdf48a` for shape.
- **Plan files**: one file per planning session under `.claude/plans/<slug>.md`. Closure plans for load-bearing weaknesses go to `docs/runbooks/<NAME>_CLOSURE_PLAN.md` once finalized.
- **Evidence files**: append to `genesis/DEPLOYMENT_RECORDS/` for any deploy attempt, regardless of pass/fail. Schema mirrors prior `relay-*-*.json` files.
- **Ledger writes**: append-only; never edit prior rows; new rows reference `prev_hash` of the most recent row.
- **Test runs**: must complete green before commit unless explicitly tracked as known-failure in § 6.

---

## 8. How to wrap a session (last 5 minutes)

1. Confirm working tree is clean (or all uncommitted changes are documented in pickup note).
2. Update `~/.claude/projects/C--Users-16823-CursorProjects-xion-os/memory/next_session_pickup.md` with:
   - Last commit shas pushed
   - Where the active plan stands (which phase done, which next)
   - Any new deferred decisions surfaced (also add to `DEFERRED_DECISIONS.md`)
   - Any new tech debt observed (also add to § 6 above)
3. If `OPERATOR_HANDOFF.md` § 1 (sprint posture) has materially shifted, update it (max one paragraph).
4. Do not push secrets, never `git commit -A` (always explicit file paths).

---

## 9. Resolution history

Initial decisions taken **agent-decided under operator delegation 2026-05-15 (CST)** per operator instruction "you observe all the project and make the decision on the above tasks." Operator can override any of these in the next session by editing this file directly.

| Q | Decision | Decided by | Date | Notes |
|---|---|---|---|---|
| § 3 — additional standing allows beyond drafted list | **None added** | Agent | 2026-05-15 | List as drafted is comprehensive given session evidence. Operator should add as encountered. |
| § 4.6 — should agent ever be allowed to widen its own authority via chat? | **Never** (current wording stands) | Agent | 2026-05-15 | Self-modification block is a fundamental safety property. Operator must edit `.claude/settings.local.json` directly to widen. |
| § 4 — additional forbidden zones specific to operator context (regulatory, jurisdictional, employer) | **None known to agent** | Agent | 2026-05-15 | Operator should append as encountered. |
| § 5 — `DEFERRED_DECISIONS.md` defaults | **Resolved per file** | Agent | 2026-05-15 | DD-001/002/004/005/006 resolved under their drafted defaults; DD-003 (hardware-wallet brand) deliberately left open — operator-only call. |
| § 3 — `git push origin main` standing allowance | **Keep allowed** | Agent | 2026-05-15 | Permission rule already in `.claude/settings.local.json` per operator authorization 2026-05-15. |

**Future review trigger:** any of the above flips on operator say-so, with the new decision appended (do not delete history). Soft review cadence every 4 weeks per `AGENT_SPEND_AUTHORITY.json`.
