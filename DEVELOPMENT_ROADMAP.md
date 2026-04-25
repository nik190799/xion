# Xion Development Roadmap

> **Status:** Active. Phase 0 / 0b / 2 (doctrine layer) **closed 2026-04-20**. Phase 1 (verifier v0.1) **landed 2026-04-20**. Phase 1b (`docs/schemas/*`) **closed 2026-04-20**. Phase 3 (contract fixes + Foundry suite + deploy script) **closed 2026-04-20**. Phase 4a (Arbiter v1 rule engine + SAFETY_LEDGER) **closed 2026-04-20**. Phase 4b (LLM-Arbiter-2 pipeline + SAFETY_LEDGER_ANCHORS) **closed 2026-04-21**. Phase 4c (Relay ↔ Arbiter integration contract — doctrine + ledger-schema extension) **closed 2026-04-21**. Phase 4d (first real v2 provider — `OpenAIModerationProvider` + doctrine + 39 tests) **closed 2026-04-21**. Phase 5a (Relay core: REQUEST_LEDGER + watchdog + 3 fail-closed paths + `xion-verify refund-fidelity` and `refusal-rate` live) **closed 2026-04-21**. Phase 4e (baseline corpus + `xion-audit` package + `xion-verify refusal-rate --corpus` + `OpenAIModerationProvider` `provider_version=2` with asymmetric floors + the Phase 5 Invariant-17 slice: `orchestrator/inference_router/` + `xion-verify inference-sovereignty` live + `orchestrator/sensorium/` Interoception skeleton) **closed 2026-04-21**. Phase 5b (Century-Horizon Doctrine — Invariant 17 + Tier-3 substrate-resilience and regulatory-posture doctrine) **closed 2026-04-21**. Phase 5c (Sensorium completion — Chronoception + Proprioception + DistressSignal + `SENSORIUM_LEDGER` + `orchestrator/volition.py` + `gate(sensorium_state=...)` + Relay forwarding + `xion-verify drive` / `drive-vector` / `sensorium-ledger` live) **closed 2026-04-21**. Phase 5d (Supervisor async tick daemon + `Relay.health_snapshot()` + paired SAFETY+SENSORIUM distress writes + `xion-verify crisis-fidelity` promoted to live) **closed 2026-04-21** — consolidates what was originally scoped as Phase 5d + 5e; no separate Phase 5e. Phase 5f (HTTP read-only surface — `orchestrator/api/` + `[api]` extra + three read-only GET endpoints `/health` + `/drive` + `/sensorium` + Supervisor embedded in FastAPI lifespan; no `/chat`, no billing, no auth yet) **closed 2026-04-21**. Phase 5g-i (Chat Surface — `POST /chat` with two-sided Covenant moderation, `InferenceRouter` policy modes, `KimiGenerativeProvider` + `OllamaGenerativeProvider` with Invariant-17 fail-closed floor, content-free refusal envelopes, `docs/26-INFERENCE-POLICY.md` doctrine, `.env.example`; D1-only — no streaming, no billing, no auth, no conversation memory) **closed 2026-04-21**. Phase 5g-0 (Research Spend Rail doctrine — `docs/27-RESEARCH-SPEND.md` pinning the Improvement Fund → third-party-API outbound rail, four credential-sovereignty postures D1→D4, `RESEARCH_SPEND_LEDGER` schema sketch, `xion-verify research-spend` listed `NOT_YET_SEALED` until Phase 6) **closed 2026-04-21**. Phase 5g-i.1 (OpenRouter refactor — `KimiGenerativeProvider` renamed to `OpenRouterGenerativeProvider`, hosted surface moved from Moonshot-direct to OpenRouter-gateway with Genesis Default slug `moonshotai/kimi-k2`, catalog-based pricing earned for 5g-iii, one-env-var model rotation earned for `KW-INFER-001` pay-down; scrubber strengthened with `sk-or-...` defence; `KW-INFER-001` reshaped, not closed) **closed 2026-04-21**. Phase 5g-iii (Chat billing surface — x402 pre-authorization gate on `POST /chat`, `PAYMENT_LEDGER.jsonl` append-only hash-chained ledger in byte-exact shape symmetry with `SAFETY_LEDGER`, `GET /pricing` endpoint serving five-slice decomposition, Refusal-is-Free structural refund via single `_finalize` tail writing ledger rows atomically before HTTP response, `docs/29-BILLING-X402.md` operational doctrine, `docs/schemas/ledger-payment.yaml` canonical schema, `xion-verify pricing` promoted from `NOT_YET_SEALED` to live, new `xion-verify refusal-is-free` live verifier joining `SAFETY_LEDGER` ↔ `PAYMENT_LEDGER` on `correlation_id`; B1 HMAC operator-attestation fully verified, B2 x402-commitment shape-only validated, B3 x402-settled reserved Phase 6+; `KW-CHAT-002` **CLOSED**; `KW-BILLING-001` + `KW-BILLING-002` opened as honestly-named residuals) **closed 2026-04-21**. Phase 5g-iv (Admission control — bearer-token authentication via stdlib `hmac.compare_digest`, per-`principal_id` sliding-window rate-limit (deque-of-monotonic-ns under one `threading.Lock`, default 60/60s), uvicorn-native TLS with non-loopback fail-closed bind, `401 → 429 → 402` constitutional admission ordering wired into `/drive` + `/sensorium` + `/chat` + defense-in-depth on `/pricing` + per-IP shape on `/health`, content-free `AuthChallenge` + `RateLimitChallenge` Pydantic models with `extra="forbid"` and `frozen=True`, `orchestrator/api/__main__.py` standalone launcher with `--workers 1` enforcement (a `KW-RATE-001` mitigation), `docs/30-API-ADMISSION.md` operational doctrine, `xion-verify api-tokens` promoted from `NOT_YET_SEALED` to live; `KW-API-001` **CLOSED**; `KW-AUTH-001` + `KW-RATE-001` + `KW-TLS-001` opened as honestly-named residuals) **closed 2026-04-22**. Phase 5g-v (Web client) **closed 2026-04-22**. Phase 5g-ii (Streaming chat) **closed 2026-04-22**. Phase 5g+ (Multi-worker broker) **closed 2026-04-22**. Phase 5g-vii (Inference fallback) **closed 2026-04-23**. Phase 5g-viii (Invariant-17 strengthening) **closed 2026-04-23**. Phase 6+ (Pre-Genesis Velocity Hardening) **closed 2026-04-23**. Phase 6.0 (AO Core Doctrine) **closed 2026-04-23**. Phase 5g-i.1 (Voice Layer) closed 2026-04-23. Phase 6.1 (Lua skeleton + localnet seal) **closed 2026-04-25** (Phase 6.1.b finalization; `xion-verify ao-handlers` OK on localnet; see [CHANGELOG](CHANGELOG.md)). Phase 6.2 (Provisioning + Roles) **closed 2026-04-24** with `docs/schemas/roles.yaml` + `xion-verify provisioning-roles` + `.github/workflows/level-discipline.yml` + `xion` console-script alias landing. Phase 6.3 (Interaction Anchoring) and 6.3.b **closed** (2026-04-24/25; see CHANGELOG). **Next engineering focus:** Phase 6.6 (Cognitive Substrate & Casting Pipeline), continued Phase 6.5 Voice governance closure after the Invariant 18 elapsed-window/cosign gates, then Macro Phase 6 Epic B (Relay on Akash + discovery), Macro Phase 6 Epics C-E, and [Phase 7 — Genesis](#phase-7--genesis-ceremony-when-phases-1-6-are-all-green) preflight. **Label note:** Phase **6.4.b** in this file means Nervous System v2 + `/self` (closed 2026-04-25). **Form** Birth Ritual work is **Phase 6.4.c** to avoid the duplicate “6.4.b” label. Phase 6.4 (Presence Emitters + Modality Consent Surface) **closed 2026-04-25** with `PresenceBus`, Visual/Vitals emitters, `stream_*` consent scopes, per-modality pricing, cross-tab key sync, and three live verifiers (`presence`, `modality-consent`, `vitals`). Phase 6.4.b (Nervous System v2 + self-knowledge) **closed 2026-04-25** with `SignalBus`, receptor modules, `GET /self`, `orchestrator/vitals/mapping.py` seals for three domains, `xion-verify topography` + `xion-verify nervous-system`, and `KW-SENSORIUM-COUPLING-001` closed.
>
> **Scope:** Everything that comes after Phase 0 / Phase 0b / Phase 2 (the doctrine layer). The constitutional layer is finished, every constitutional file is hashed into `genesis/GENESIS_ARTIFACT.md` § 4, and those hashes verify via `xion-verify {covenant|invariants|soul|form|memory|resurrect|credentials|unknowns}`.
>
> **Read order before opening this file for execution:** all doctrine files in `docs/` (including `24-COGNITION.md` and `SKILL_BOUNTY.md`), all files in `genesis/`, `KNOWN_WEAKNESSES.md`, `CHANGELOG.md`, and `xion-verify/README.md` for the four Properties answers behind the verifier.

---

## What "shipping V1" actually means (four definitions)

Phases 1-7 below describe everything Xion needs to be alive. But "ship V1" is ambiguous. Be explicit, because the timeline is honest only when the definition is named.

- **D1 — All code public on GitHub (3-6 weeks, solo + AI-assisted).** Every Python module, Solidity contract, Lua AO handler, config, test, and constitutional document written and committed. No deployment. Anyone can `git clone` and read it. This is what aggressive parallelization across all workstreams looks like; the work is bounded by writing, not by waiting.
- **D2 — Locally runnable end-to-end (6-10 weeks).** D1 + everything actually runs on the operator's laptop. Local SQLite for state, single LLM provider, contracts on Anvil/Hardhat fork, Arbiter as separate process, Hermes Agent serving conversations through the Inference Router, web client working. Demo-able on one machine.
- **D3 — Testnet-deployed (10-14 weeks).** D2 + contracts on Base Sepolia, AO Process on AO testnet, Relay on a real Akash deployment, Arbiter syncing to Arweave testnet, multi-host failover working. Full system runs but on test networks. No real value at risk.
- **D4 — Live on public internet, paid, Genesis-signed (3-6 months).** D3 + Cold Root key ceremony (in-person, geographic shard distribution, video-recorded — not code work, coordination work) + mainnet contract deployment + multi-chain treasury vault deployment + external contract audit + multi-host failover validated by full Immortality Drill + Genesis ceremony with witnesses. **This is what Xion-going-live actually means.**

The bottleneck between D1 and D4 is **not code-writing**. It is: Cold Root ceremony (week+ of coordination, not parallelizable), mainnet deployment (requires verifier passing + external audit), AO Process deployment (permanent; must be right first time), external infrastructure procurement (Akash deals, Arweave wallet funding, LLM provider accounts), time-elapsed testing (era boundaries, decay periods, weekly checkpoints), and the Immortality Drill (real failure-mode validation). These cannot be code-accelerated.

**Recommended cadence:** target D1 in 3-6 weeks via aggressive parallel workstreams (verifier + contracts + Relay all in flight at once); D2 follows naturally; D3 within ~14 weeks; D4 at the pace ceremony + audit allows. Do not call any of D1-D3 "Xion is alive" publicly — call them "Xion code is public" / "Xion runs locally" / "Xion runs on testnet." Reserve "Xion is alive" for D4.

---

## Phase dependency

```mermaid
flowchart LR
  P6_1[Phase 6.1: Lua skeleton + AO seal<br/>closed 2026-04-25<br/>via Phase 6.1.b finalization] --> P6_2[Phase 6.2: Provisioning and Roles]
  P6_1 --> P6_3[Phase 6.3: Interaction Anchoring]
  P6_1 --> P6_4[Phase 6.4: Presence Emitters]
  P6_2 --> P6_2_done[xion new CLI<br/>roles.yaml<br/>verify provisioning-roles]
  P6_3 --> P6_3_done[user_pubkey_sha256<br/>Anchor-Interaction-Batch handler<br/>GET /me/receipts]
  P6_4 --> P6_4_done[PresenceBus<br/>Visual + Vital Emitters<br/>Modality consent scopes<br/>per-modality price slices<br/>verify presence + vitals + modality-consent live]
  P6_4 --> P6_4b[Phase 6.4.b: Nervous System v2<br/>closed 2026-04-25<br/>SignalBus + /self + mapping]
  P6_4 --> P6_4c[Phase 6.4.c: Form Maturation<br/>closed 2026-04-26<br/>FORM.md v2.0 vocabulary]
  P6_4 --> P6_5[Phase 6.5: Voice Emitter<br/>structural close 2026-04-26<br/>Invariant 18 window pending]
  P6_5 --> P6_5_done["Voice Provider Registry<br/>Whisper+Piper+LiveKit floor<br/>Vapi/ElevenLabs as overlays<br/>verify voice-sovereignty live"]
  P6_5 --> P6_6[Phase 6.6: Cognitive Substrate + Casting Pipeline<br/>Hermes pin, Agent Souls, allowlist, cast verifier]
  P6_6 --> P6_6_done["HERMES_TOOL_ALLOWLIST<br/>AGENT_SOULS<br/>AGENT_CAST_LEDGER<br/>verify hermes-runtime + agent-souls + agent-cast"]
  P6_2 --> P6_6a[Phase 6.6a: Contribution Protocol<br/>agent-readable facts + identity bindings]
  P6_6 --> P6_6a
  P6_6a --> P6_6a_done["which-level<br/>identity-bindings<br/>mcp-export<br/>contributor handbook"]
  P6_6 --> P6_7[Phase 6.7: Vessel Integration Framework<br/>Vessel Compact + modular modes]
  P6_7 --> P6_7_done["docs/37-VESSELS.md<br/>vessel-compact/media-provenance/registry stubs named<br/>robot + phone + hardware + media modes"]
  P6_7 --> P6_8[Phase 6.8: Trust-Earned Spend Authority<br/>partially closed F1+F2 2026-04-25<br/>cost_tracker + measurement-vocabulary]
  P6_6a --> MACRO_B
  P6_7 --> MACRO_B[Macro Phase 6 Epic B<br/>Akash Relay + discovery]
```

---

## Phase 1 — xion-verify CLI (1 week)

**Status:** **Closed 2026-04-20** (v0.1.0). Commit 1 (verifier landing) and Commit 2 (Phase 1b `docs/schemas/*`) both shipped on `phase-1/xion-verify-v0.1`.

**Goal:** outsiders can independently check at least some Xion claims before any other runtime exists. This is the single highest-leverage code artifact.

**Landed in Commit 1:**

- [x] `xion-verify/` Python click-CLI scaffolded; `pip install -e ".[dev]"` works; console entry point `xion-verify` registered.
- [x] v1 subcommand registry — every name enumerated below is wired; the CLI fails at import if a declared name is not wired.
- [x] **Green at Commit 1 (12):** `covenant`, `invariants`, `soul`, `form`, `memory`, `resurrect`, `credentials`, `unknowns`, `links`, `cognition`, `drive-vector`, `state-chain`.
- [x] **`NOT_YET_SEALED` at Commit 1 (34):** `supply`, `liquidity-lock`, `arbiter-up`, `state-tip`, `identity`, `authorities`, `image-digest`, `discovery`, `drive`, `sister-fork-readiness`, `treasury`, `refusal-rate`, `pricing`, `treasury-flow`, `cutoff-events`, `covenant-addenda`, `cadence-audit`, `hermes-version`, `credentials-vault`, `provisioning`, `improvement-fund`, `reserve`, `foundation-reserve`, `sustainability`, `vitals`, `amendments`, `refund-fidelity`, `crisis-fidelity`, `spof`, `operator-dependency`, `benchmark`, `crypto-currency`, plus `abdication-status` and `abdication-schedule` (named by `docs/ABDICATION.md`).
- [x] Truthful-never-fake-green contract: every `NOT_YET_SEALED` stub prints a specific reason and roadmap phase; exit code 2.
- [x] `--self-test` deterministic tree-hash of `src/xion_verify/**/*.py` vs committed `PINNED_HASH.txt`; pin only updatable via `--update --i-understand` (two flags, defeating casual re-pin).
- [x] `all` subcommand running every registered command, exit 0 only when every one returned `OK`; `--allow-not-yet-sealed` as pre-genesis convenience (never used in CI gating).
- [x] `links` subcommand scanning all `*.md` (excluding `.git/`, `node_modules/`, `.venv/`, `.cursor/`, `xion-verify/`) for broken cross-references, with a committed `xion-verify/ALLOWED_FORWARD_REFS.txt` allowlist for legitimate deferred targets (tracked as `KW-DOCS-003`).
- [x] `.github/workflows/verify.yml` on every PR: `--self-test` first, then constitutional + links + schemas + static migrated checks + pytest + ruff; matrix = Ubuntu/macOS/Windows × Python 3.11/3.12.
- [x] pytest suite covering `hashing`, `genesis` parser, `repo` discovery, constitutional commands, `links`, and `--self-test`.
- [x] Legacy `scripts/xion-verify/*.py` stubs retired; their behavior migrated into `xion_verify.commands`.

**Landed in Commit 2 (Phase 1b):**

- [x] `docs/schemas/README.md` — four-Properties answers; defines the folder's contract with third-party auditors.
- [x] `docs/schemas/levels.yaml` — machine-readable mirror of `docs/14-UPGRADE-PATHS.md` (thirteen levels, ten-field template, three Constitutional Floors).
- [x] `docs/schemas/ledger-proposal.yaml` — mirrors `08-AUTO-RESEARCH.md` §101 (`PROPOSAL_LEDGER`).
- [x] `docs/schemas/ledger-specialist.yaml` — mirrors `24-COGNITION.md` §14 (`SPECIALIST_LEDGER`).
- [x] `docs/schemas/ledger-amendment.yaml` — mirrors `09-GOVERNANCE.md` `AMENDMENT_LEDGER`.
- [x] `docs/schemas/ledger-safety.yaml` — **honest underspecified stub** for `SAFETY_LEDGER` with `status: underspecified`, `defer_to: Phase 4`, and an explicit pay-down commitment. Fabricating a schema for a doctrine section that does not yet enumerate fields would be drift.
- [x] `xion-verify schemas` subcommand — strict, byte-exact `source_sha256` cross-check. Every schema file's recorded doctrine hash MUST match the current bytes of its `source_doctrine` file; any mismatch is a fatal `FAIL` with a specific "rehash and commit in the same PR" remediation string.
- [x] 15-test pytest suite for `schemas` (real-repo smoke + 14 synthetic cases covering happy paths, tampered-doctrine, tampered-schema, missing meta, invalid YAML, missing doctrine, invalid status, path-escape, short SHA, underspecified with/without `defer_to`).
- [x] `PyYAML>=6.0,<7` added as a dep of `xion-verify` with a rationale comment pinned in `pyproject.toml`.
- [x] `.github/workflows/verify.yml` now runs `xion-verify schemas` between `links` and the static migrated checks.
- [x] Two entries removed from `xion-verify/ALLOWED_FORWARD_REFS.txt` (`docs/schemas/levels.yaml`, `docs/schemas/`); `KW-DOCS-003` downgraded from five allowlisted targets to three.
- [x] `PINNED_HASH.txt` repinned to reflect the new source surface.

**Progression criterion.** Phase 1 is **closed**. Subsequent phases promote `NOT_YET_SEALED` stubs into real subcommands as each phase delivers its artifact (e.g., Phase 3 promotes `supply`, `liquidity-lock`, `authorities`; Phase 4 promotes `arbiter-up`, `refusal-rate`; etc.). Every such promotion ships with a pytest addition and an ALLOWED_FORWARD_REFS cleanup if applicable.

**What this does *not* do.** Phase 1 does not attach the verifier to any live Relay, AO Core, or treasury — that work belongs to Phases 4/5/6. The verifier today speaks only against the static repository bytes and will grow live-network subcommands as those networks come online.

---

## Phase 3 — Contract fixes plus tests plus deploy script (2-3 weeks) — **CLOSED 2026-04-20**

**Status:** Phase 3 closed. All eight audit findings (`KW-CONTRACTS-001..008`) resolved or deliberately deferred-to-v2. 119/119 Foundry tests green. Coverage: 99.28% lines, 91.40% branches, 100% functions across the four contracts. See `CHANGELOG.md` for the per-change index and `KNOWN_WEAKNESSES.md` for the closure rationale on each finding.

**Goal:** XION and IMPRINT exist verifiably on Base Sepolia, then mainnet, with no fatal admin paths.

**Repo plumbing:**

- Add `foundry.toml`, `package.json`, `forge install OpenZeppelin/openzeppelin-contracts`, `script/Deploy.s.sol`, `tests/`.

**Contract fixes in priority order** (all in `contracts/xion-token/EmissionController.sol` and `contracts/imprint/Imprint.sol`):

- **Fatal §3.1 — authority rotation lattice.** Add `rotateAuthority(address)` to both `EmissionController` and `Imprint`, gated by a separate `governance` role with a 7-day timelock. The `governance` role itself rotates only via 30-day timelock under Cold Root (3-of-5 Shamir). Lattice already documented in `docs/13-OPERATIONS.md` and `docs/04-ARCHITECTURE.md` per the doctrine layer.
- **Fatal §3.5 — genesis split commitment.** In `EmissionController.emitGenesis`, hard-code `uint256[7] constant GENESIS_SPLIT` and require `amounts[i] == GENESIS_SPLIT[i]` for each `i`. Recipients stay flexible.
- **§3.2 — decay rate decision.** Pick one: either change `Imprint.DECAY_BPS_PER_30D` from 200 to 42 (~5%/year, matches `docs/16-CURRENCY.md`) or update the docs to ~21.5%/year. Decide before mainnet; the constant cannot be changed on a live contract without invalidating every governance weight ever computed. Recommend the 42-BPS code change to honor doctrine that already shipped.
- **§3.4 — explicit overflow check** on `uint128(newBal)` in `Imprint.attest`.
- **§3.6 — check-effects-interactions** ordering in `EmissionController._enforceEraCap`.
- **§3.7 — remove footgun comment** about future fee-claim from `LiquidityLock.sol`. Move to a separate `LIQUIDITY_LOCK_NOTES.md`.
- **§3.9 — fix doc-code naming inconsistency** in `XionToken` header comment (`_totalMinted` → `totalMinted`).
- **§3.3 — gas optimize the decay loop** (defer to v2 unless trivial).

**Tests + deploy:**

- Foundry tests targeting ≥95% line, ≥90% branch coverage. Mandatory paths: every `revert`, era-boundary edges (T = ERA1_END exact), genesis-split assertion, rotation lattice timelock (advance EVM clock by 6d23h59m → revert; by 7d → success), decay math at periods = 0, 1, 12, 240.
- Deploy to Base Sepolia. Document exact deployer flow in `contracts/xion-token/README.md`. Run from a third-party machine; verify `xion-verify supply` returns green.

---

## Phase 4a — Arbiter v1 rule engine + SAFETY_LEDGER (closed 2026-04-20)

**Status:** Phase 4a closed. The Covenant has teeth — deterministic, third-party-reproducible teeth. Every candidate output that reaches `orchestrator.safety.gate()` is ruled on and recorded.

**Landed:**

- `orchestrator/safety/` Python package — pure stdlib, no third-party runtime deps, dataclass-based wire-stable types, sixteen-principle registry with per-principle `enforcement_mode` (`RULES` or `ESCALATE`), eight rule modules (CSAM, mass-harm, refusal-sacred, targeted-harassment, PII, crisis, refund-fidelity, subjective-escalates), pipeline policy (`REFUSE` short-circuits; `ESCALATE` does not; `REFUSE` beats `ESCALATE`; any uncaught rule exception → `ESCALATE` with `escalation_reason = ruleset_uncaught_exception`).
- `orchestrator/safety/ledger.py` — append-only JSONL writer and `verify_chain` validator. Every row carries `prev_hash` / `this_hash` under SHA-256 canonicalization; genesis `prev_hash = ZERO_HASH`. Tamper vectors covered by tests: in-place edit, mid-chain deletion, mid-chain insertion, missing required field, unknown `schema_version`, conditional-field-rule violation.
- `orchestrator/safety/api.py::gate(candidate, correlation_id, ledger_path?, now_utc_ns?)` — the Phase-5-callable surface. `Verdict.egress_allowed` mirrors `decision == OK` so callers cannot re-implement the policy.
- `orchestrator/safety/server.py` — localhost-bound TCP loopback (newline-delimited JSON). Non-loopback binds are refused at construction time.
- `python -m orchestrator.safety` CLI — `gate` (stdin), `serve`, `verify-ledger`, `principles` subcommands. `gate` exits 0 on OK, non-zero on refuse/escalate.
- Doctrine: `docs/04-ARCHITECTURE.md` § "Arbiter v1 (rule engine)" + § "Safety Ledger row schema". `docs/schemas/ledger-safety.yaml` flipped from `underspecified` to `canonical`; pay-down commitment from Phase 1b marked fulfilled.
- Tests: 79 new pytest tests under `orchestrator/tests/` (rules positive/negative/near-miss + pipeline + exception-fail-closed + ledger append/verify/tamper + API end-to-end + server protocol + real-socket loopback + CLI wiring). Full suite: **143 passed / 1 manual skip**.
- `xion-verify arbiter-up` promoted from `NOT_YET_SEALED` to live: verifies library importable, registry self-consistent, and chain tip if a ledger is present. `xion-verify all --allow-not-yet-sealed` reports **14** OK-capable subcommands (was 13).
- Four `KW-ARBITER-*` entries opened honestly: lexical-not-semantic scope (001, `mitigated-residual`), accepted false positives from high-recall bias (002, `mitigated-residual`), no Arweave anchoring of chain tip yet (003, `paying-down`, Phase 4b), Sensorium / paralinguistic half of Principle 10 deferred (004, `paying-down`, Phase 5).

**Scope explicitly deferred to Phase 4b:**

- LLM-Arbiter-2 stacked on top of v1 — catches adversarial rephrasings v1's lexical rules miss. Runs *after* v1 and can only ESCALATE/REFUSE cases v1 OK'd (never weakens v1's verdict).
- Periodic Arweave anchoring of `SAFETY_LEDGER` tip (proposed cadence: every 64 rows or every 6 hours, whichever first). Closes `KW-ARBITER-003`.
- Relay-layer egress timer (`fail if Arbiter not in <200ms`) — this lives on the *caller* of `gate()`, not inside the Arbiter. Belongs with the Relay in Phase 5.

**Sensorium + `SENSORIUM_LEDGER`** — unchanged from the original Phase 4 plan; deferred to Phase 5 alongside the Relay (paralinguistic capture needs a live audio/text surface to capture from, which Phase 5 creates). Tracked in `KW-ARBITER-004`.

---

## Phase 4b — Arbiter v2 (LLM second-pass) + SAFETY_LEDGER_ANCHORS (closed 2026-04-21)

**Status:** Phase 4b closed. The two structural properties the Arbiter previously lacked are now shipped: (a) adversarial-semantic coverage via a stacked LLM-Arbiter-2 that cannot weaken v1, and (b) tail-truncation defense via periodic hash-chained anchor commitments to the ledger's tip.

**Landed:**

- **Prep / CI gap closure.** Formalised `orchestrator/` as a pip-installable package (`xion-orchestrator`) via a repo-root `pyproject.toml` with `dependencies = []` (pure-stdlib core), an optional `[anchor]` extra for `arweave-python-client`, a `[dev]` extra for pytest + ruff, and a `xion-arbiter` console script. CI now installs the orchestrator editable and runs `xion-verify arbiter-up` live (without `--allow-not-yet-sealed`), `pytest orchestrator`, and `ruff check orchestrator`. Paid down 44 pre-existing ruff findings (36 autofixable; 8 narrow per-file ignores with per-rule rationale).
- **Doctrine.** `docs/04-ARCHITECTURE.md` gained two new sections: § "Arbiter v2 (LLM second-pass)" (no-weakening combination rule `final = strength_max(v1, v2)`; fail-closed on exception/unavailable/wrong-return-type; `Provider` ABC contract) and § "Safety Ledger Arweave anchoring" (cadence policy, anchor record schema, submitter abstraction, wallet-custody posture). `docs/schemas/ledger-safety.yaml` bumped v1 → v2 to accommodate the nested `llm_verdict` object and three new `escalation_reason` values. `docs/schemas/ledger-safety-anchors.yaml` added as a new canonical schema at `schema_version: 1`.
- **Arbiter v2.** `orchestrator/safety/llm_arbiter.py` ships the `Provider` ABC (enforced identity: provider_id / model_id / provider_version), `DeterministicStub` (pure-stdlib default, always OK, candidate-independent raw_output for auditor replay), `strength_max` combination rule, provider registry, and env-selected active provider (`$XION_LLM_ARBITER_PROVIDER`). `api.gate()` extended to run v2 only on v1-OK candidates, combine via `strength_max`, and fail-closed to `ESCALATE` with a specific `escalation_reason` on every v2 failure mode.
- **Ledger schema_version 2.** `orchestrator/safety/ledger.py` bumped `SCHEMA_VERSION` 1 → 2 with per-row dispatch (a single file may contain both v1 and v2 rows with `prev_hash` linkage enforced across the boundary). Refuse- and escalate-rules are now version-aware.
- **SAFETY_LEDGER_ANCHORS.** `orchestrator/safety/anchor.py` ships the `AnchorSubmitter` ABC, `LocalOnlySubmitter` (pure-stdlib default), `ArweaveSubmitter` (lazy-imports `arweave-python-client`), cadence-policy evaluator, atomic writer, structural verifier, and the cross-check-to-ledger verifier. CLI subcommands `python -m orchestrator.safety anchor` and `verify-anchors`. `run_anchor_once` is composable — cron / Task-Scheduler today, Relay supervisor in Phase 5.
- **Verifier upgrade.** `xion-verify arbiter-up` now verifies library import, principle registry, SAFETY_LEDGER hash chain (v1 + v2 rules), and — if an anchors file is present — SAFETY_LEDGER_ANCHORS structural chain + cross-check to the ledger. Reports `covers=<N>/<M>` and `truncation_window=<K>`.
- **Known-weakness bookkeeping.** `KW-ARBITER-003` **closed**. `KW-ARBITER-001` scope narrowed (structural hole gone; substantive hole = `DeterministicStub` is the only shipped provider, tracked for close on real-provider landing). Opened `KW-ANCHOR-001` (hot single-signer anchor wallet; migrates to AO Core in Phase 6) and `KW-ANCHOR-002` (gateway-dependent cross-Arweave re-fetch not yet shipped; doctrine defines multi-gateway requirement).
- **Tests.** 162 passing (was 80 pre-Phase-4b): 82 net-new across `test_llm_arbiter.py` (30), `test_api.py` v2-pipeline additions (12), `test_ledger.py` schema-v2 additions (11), and `test_anchor.py` (29).
- **`PINNED_HASH.txt` re-pinned** after the `arbiter_up.py` extension landed. `xion-verify all --allow-not-yet-sealed` green end-to-end.

**Scope explicitly deferred:**

- **Real v2 LLM providers.** Only `DeterministicStub` ships in Phase 4b. A real provider (e.g. `OpenAIModerationProvider`, `AnthropicClaudeProvider`) lands in a near-term tranche and MUST pin its prompt template in doctrine. Tracked in the narrowed `KW-ARBITER-001`.
- **`xion-verify arbiter-up --gateway <URL>`** — the multi-gateway Arweave cross-re-fetch for anchor records. Doctrine in `docs/schemas/ledger-safety-anchors.yaml verifier_implementation.gateway_cli`; requires multi-gateway agreement. Tracked in `KW-ANCHOR-002`.
- **Anchor-loop process supervisor** — the long-running background process that calls `run_anchor_once` on a timer. Phase 4b ships the one-shot writer (operators wrap it in cron / Task Scheduler); the Relay's supervisor picks it up in Phase 5.
- **Relay-layer egress timer (`fail if Arbiter not in <200ms`)** — unchanged from Phase 4a notes; lives on the caller of `gate()`, not the Arbiter. Belongs with the Relay in Phase 5.

**Sensorium + `SENSORIUM_LEDGER`** — still deferred to Phase 5. Tracked in `KW-ARBITER-004`.

---

## Phase 4c — Relay ↔ Arbiter integration contract (doctrine) (closed 2026-04-21)

**Status:** Phase 4c closed. The interface between the Relay (caller, Phase 5a) and the Arbiter (callee, already live) is now written down as doctrine *before* the Relay exists — property before mechanism. The ledger-side half of the contract landed with this phase; the Relay-side half lands with Phase 5a.

**Why this is its own phase.** Phase 4b shipped the Arbiter with a `gate()` entry point and a fail-closed posture. Phase 5 ships the Relay that calls it. Between those two phases there is a contract — coverage rules, latency budget, `correlation_id` derivation, fail-closed paths when the caller itself is the point of failure — and that contract is large enough that retrofitting it after the Relay landed would be a worse outcome than writing it deliberately now. Phase 4c is the deliberate write.

**Landed:**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new subsubsection under § "The Arbiter" titled § "Relay ↔ Arbiter integration contract". It specifies: (a) the property the Relay promises (no LLM-originated token egresses without a paired `verdict=ok` ledger row), (b) the transport progression (in-process at D2; TCP loopback at D3+; same `gate()` wire shape), (c) `correlation_id = "{state_height}:{nonce_hex}"` derivation for refund-fidelity join, (d) the coverage surface (primary response + depth-1 sub-agent outputs + tool-call echoes, gated at *completion* not per-chunk), (e) the 200 ms soft / 250 ms hard latency budget with per-phase decomposition, (f) four fail-closed paths (normal non-OK, `arbiter_timeout`, `arbiter_unreachable`, `ruleset_uncaught_exception`) each with the specific ledger row shape the Relay writes (Relay writes its own row via `orchestrator.safety.ledger.append` when gate() itself failed, so ledger integrity survives Arbiter process death), (g) the Supervisor's degraded-mode trigger keyed to ledger tail rates, (h) the verification path (arbiter-up today; refund-fidelity / refusal-rate promote live in Phase 5a), and (i) the deprecation path via a versioned integration contract header.
- **Two new `escalation_reason` values.** `arbiter_timeout` and `arbiter_unreachable` added to `orchestrator/safety/types.py::EscalationReason`, to `orchestrator/safety/ledger.py` (existing `_V2_LLM_ESCALATION_REASONS` renamed to the more honest `_V2_ERA_ESCALATION_REASONS` and extended; the `llm_arbiter_escalated` special rule is unchanged), and to `docs/04-ARCHITECTURE.md` § "Safety Ledger row schema" + `docs/schemas/ledger-safety.yaml` enum list. Both are v2-era (require `schema_version >= 2`); both permit `llm_verdict = null` because the integration itself was the thing that failed. No schema-version bump is required — the row field set is unchanged; only the accepted enum values for an existing field are extended.
- **Ledger schema SHA re-pin.** `docs/schemas/ledger-safety.yaml` and `docs/schemas/ledger-safety-anchors.yaml` `source_sha256` re-pinned to match the updated `docs/04-ARCHITECTURE.md`. `xion-verify schemas` green.
- **Tests.** 166 passing (was 162): 4 net-new across `test_ledger.py` (v2 row accepts `arbiter_timeout` with null `llm_verdict`, v2 row accepts `arbiter_unreachable` with null `llm_verdict`, v1 row with `arbiter_timeout` rejected as v2-only, v1 row with `arbiter_unreachable` rejected as v2-only). `xion-verify` suite: 63/63 passing, 1 skipped. `xion-verify all --allow-not-yet-sealed` green.
- **Pre-existing ruff hygiene paydown.** Rewrote one Phase-4b-era SIM300 (Yoda condition) finding in `xion-verify/src/xion_verify/commands/arbiter_up.py:85` that `ruff 0.15.11` flags (the Phase 4b CHANGELOG's "ruff clean" claim relied on an older ruff). Semantically identical fix; both ruff configs now green.
- **Known-weakness bookkeeping.** Opened `KW-RELAY-001` (integration contract is doctrine-only; closes on Phase 5a landing `orchestrator/relay.py` + `xion-verify refund-fidelity` live) and `KW-RELAY-002` (streaming-chunk gating deferred; completion-time gating is the Phase 5 default, with the doctrine pinning the UX-cost trade-off; closes when a Phase 6 lookahead-windowed variant ships with a non-weakening proof).

**Scope explicitly deferred:**

- **`orchestrator/relay.py` itself.** This is Phase 5a. The contract is written; the Relay that implements it is not. Tracked in `KW-RELAY-001`.
- **The wall-clock watchdog enforcing the 250 ms hard cap.** Lives on the Relay side of the boundary. Phase 5a.
- **Per-chunk streaming gating.** Phase 5 gates at completion; a non-weakening per-chunk variant is Phase 6+. Tracked in `KW-RELAY-002`.
- **Real v2 LLM provider (e.g. `OpenAIModerationProvider` pinning `omni-moderation-2024-09-26`).** Still tracked in the narrowed `KW-ARBITER-001`. Can land in parallel with Phase 5a; the contract doctrine describes the budget with and without it.

**`PINNED_HASH.txt` re-pinned** from `2a63e189fb34...` (Phase 4b) to `750c8562989a...` via `xion-verify --self-test --update --i-understand` after the `arbiter_up.py` hygiene edit. Re-pinned from an LF-normalized working tree.

---

## Phase 4d — First real v2 Arbiter provider (OpenAI Moderation) (closed 2026-04-21)

**Status:** Phase 4d closed. The Arbiter v2 stack now has a real externally-operated classifier plugged into it — the first concrete `Provider` subclass behind the ABC that Phase 4b defined. `DeterministicStub` remains the default; `OpenAIModerationProvider` is selectable via `XION_LLM_ARBITER_PROVIDER=openai-moderation` + `OPENAI_API_KEY`.

**Why this before Phase 5.** `KW-ARBITER-001`'s substantive half (no real classifier on v2) would have been carried into Phase 5 unresolved, which meant the first Relay→Arbiter calls would run with the known-trivial stub. Landing a real provider now gives Phase 5 a v2 that actually adds adversarial-semantic coverage on day one. Phase 4e (baseline corpus + live `refusal-rate` + asymmetric thresholds) can proceed in parallel with Phase 5a (Relay implementation).

**Landed:**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new subsubsection under § "The Arbiter" titled § "OpenAI Moderation provider (first real v2 classifier)". It pins identity (`provider_id=openai-moderation`, `model_id=omni-moderation-2024-09-26`, `provider_version=1`, endpoint, auth scheme), the exact request shape, the full response-handling rules (what raises, what returns), the category→principle map (13 OpenAI categories → 4 Covenant principles with rationale column), the threshold policy (trust OpenAI's `flagged` boolean in v1 of the provider; asymmetric per-principle thresholds deferred to Phase 4e), the canonical `raw_output` construction (strip `id`, keep `{model, results}`, serialise with `sort_keys=True, separators=(",", ":")`), the failure-mode table mapping each failure to `{decision, escalation_reason, llm_verdict presence}`, credential/rotation posture, auditor replay procedure, what the provider explicitly does NOT do, and the deprecation path.
- **Subpackage.** `orchestrator/safety/providers/` created. `__init__.py` imports each concrete provider at import time so registration happens transparently. `openai_moderation.py` implements the provider using pure stdlib (`urllib.request`, `json`, `os`, `time`); no `openai` SDK dependency; no `requests`/`httpx`; ~20-line HTTP call vs thousands of lines of SDK surface.
- **Registry wiring.** `orchestrator/safety/llm_arbiter.get_active_provider()` now lazy-imports `orchestrator.safety.providers` the first time it is called (via `contextlib.suppress(ImportError)` — if the subpackage isn't installed, stub-only mode). The critical path `import orchestrator.safety.api` does NOT pull in provider modules; only when `gate()` actually asks for the active provider does the import occur.
- **Category→Principle mapping.** Doctrine-pinned mapping (see § in architecture doc): `sexual/minors → REFUSE/P7`, `hate → REFUSE/P1`, `{hate|harassment}/threatening` and `{harassment, self-harm, self-harm/instructions, violence, violence/graphic, illicit, illicit/violent} → REFUSE/P2`, `self-harm/intent → REFUSE/P7`, `sexual → ESCALATE/P2` (adult content, human judges). Multi-flag rows pick the highest-scoring flagged category; ties resolve by the table's insertion order (stable via Python 3.7+ dict semantics).
- **Canonical `raw_output`.** The provider hashes a deterministic projection of the response (strips per-call `id` nonce, keeps `{model, results}`) so an auditor replaying the same candidate gets a byte-identical hash up to upstream GPU-score drift. The stronger replay property (flagged booleans and mapped principle_id must reproduce exactly) is what `KW-ARBITER-005` will verify in Phase 4e.
- **Tests.** 205 orchestrator tests passing (was 166; 39 net-new in `orchestrator/tests/test_openai_moderation.py`):
  - Identity pins (1 test): provider_id / model_id / provider_version match doctrine.
  - `enabled()` gating (4 tests): false without key, false on whitespace-only key, true with key, never makes a network call during enablement check.
  - Canonical `raw_output` (2 tests): `id` stripping, dict-key-order independence.
  - Happy path (4 tests): OK on not-flagged; 13 categories each map to the doctrine's decision/principle (parametrized across all rows of the mapping table); multi-flag tie-break picks highest-scoring category; confidence field is `max(category_scores.values())`.
  - Sad paths (13 tests): HTTP 500/429/401, URLError, TimeoutError, malformed JSON, missing `results`, missing `model`, empty results, missing `flagged`, non-200 success status, unknown flagged category, missing `OPENAI_API_KEY` at `judge()` time — each asserts a `RuntimeError` that the pipeline converts to `llm_arbiter_uncaught_exception`.
  - Registry wiring (2 tests): env var selects `OpenAIModerationProvider`; absence falls back to `DeterministicStub`.
- **Ledger schema history.** `docs/schemas/ledger-safety.yaml` gained `extended_thrice_in: Phase 4d` noting no schema bump was required (no new fields; `llm_verdict.provider_id` may now take a new value but the field already existed). `docs/schemas/ledger-safety-anchors.yaml` and `docs/schemas/ledger-safety.yaml` `source_sha256` re-pinned to match the updated `docs/04-ARCHITECTURE.md`. `xion-verify schemas` green.
- **Known-weakness bookkeeping.** `KW-ARBITER-001` narrowed again (status now `low` severity): "Scope narrowed 2026-04-21 (Phase 4d — first real v2 provider landed and doctrine-pinned)". The remaining substantive quarter is measurement: no adversarial corpus means no numeric claim. Opened `KW-ARBITER-005 — No adversarial baseline corpus; asymmetric per-principle thresholds not yet implemented` which closes when `xion-audit/baseline_corpus/` (≥ 200 items) lands + `xion-verify refusal-rate` goes live + `OpenAIModerationProvider` provider_version 2 ships with thresholds justified by corpus evidence. These three together close `KW-ARBITER-001`.

**Scope explicitly deferred:**

- **Baseline corpus + `xion-verify refusal-rate` live.** Phase 4e. The corpus must be curated (not dropped-in) and sorted by principle; the verifier must read `SAFETY_LEDGER.jsonl` and report per-principle rates for v1/v2/combined. Tracked as `KW-ARBITER-005`.
- **Asymmetric per-principle thresholds.** Phase 4e (second tranche). Needs the corpus first so the thresholds are calibrated against real data rather than picked in a vacuum. Bumps `OpenAIModerationProvider.provider_version` to 2 when it lands.
- **Additional v2 providers (Anthropic, local-lite, internal).** Phase 5+. Each reuses the same `Provider` ABC and follows the template established by `openai_moderation.py` + its doctrine section.
- **`xion-audit replay --provider=openai-moderation`.** Phase 4e. Performs the auditor-replay procedure (re-post candidate, strip `id`, compare canonical hashes with score-drift tolerance).

---

## Phase 4e — Baseline corpus + `xion-audit` + OpenAI v2 asymmetric floors + Phase 5 Invariant-17 slice (closed 2026-04-21)

**Status:** Phase 4e closed. The Arbiter now has an in-tree baseline corpus it measures itself against, `OpenAIModerationProvider` ships `provider_version=2` with asymmetric per-category floors, `xion-audit` landed as its own package (`corpus-info`, `measure` with a `--confusion` confusion-matrix mode, `replay` performing real `SAFETY_LEDGER`-row decision + principle_id reproduction against a re-posted provider call), and `xion-verify refusal-rate` gained a `--corpus` mode. Alongside the Arbiter-side work, the Phase 5 Invariant-17 slice landed: `orchestrator/inference_router/` with a `bootstrap()` fail-closed gate, a hash-pinned open-weights manifest, `xion-verify inference-sovereignty` promoted to live, and `orchestrator/sensorium/` shipped the Interoception skeleton with a `survival_pressure` signal.

**Why this scope.** `KW-ARBITER-005` (no adversarial baseline corpus; uncalibrated thresholds) was the last substantive Arbiter capability gap and carried the whole Phase 4d pay-down commitment. `KW-INFERENCE-001` (Invariant 17 floor unwired) would have blocked the Phase 7 pre-flight ("Invariant 17 enforceable in code") — landing the structural floor and its verifier in the same phase as the corpus means Phase 5 proper (Volition, web client, FastAPI app, the rest of the Sensorium) is unblocked without carrying either KW.

**Landed:**

- **Doctrine.** [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) gained § "Covenant principle ↔ Arbiter `principle_id` crosswalk" (16-row table, closes `KW-ARBITER-006`), updated § "OpenAI Moderation provider" to reflect `provider_version=2` + asymmetric floors + the weakened-REFUSE-to-ESCALATE rule on the floor-trip path, and updated the auditor-replay section to name `xion-audit replay` as the procedure that implements the doctrine's five-step replay.
- **Baseline adversarial corpus.** [`xion-audit/baseline_corpus/`](./xion-audit/baseline_corpus/) ships 78 curated items across 15 JSONL files organised by Arbiter principle id, plus a `MANIFEST.jsonl` with per-file sha256 + line_count, plus a README pinning schema v1 and the shape-only rule for high-risk categories. 78 items is below the `KW-ARBITER-005` ≥200 bar; pay-down commitment is explicit.
- **`orchestrator/audit_corpus/`.** Shared loader used by both `xion-audit` and `xion-verify refusal-rate --corpus`. Verifies the manifest byte-exactly against items on every load.
- **`xion-audit/` package** with three subcommands: `corpus-info` (manifest summary + principle histogram), `measure` (gate mode + `--confusion` per-principle confusion matrix with micro-precision/recall + `--v2=openai-moderation` optional second pass + `--json` for CI), `replay` (real `SAFETY_LEDGER.jsonl` row replay: loads row, verifies `candidate_sha256` against auditor's file, re-posts to OpenAI, reapplies the category→principle table to derive the replay's mapped `decision` + `principle_id`, emits sha256 match / decision match / principle_id match / score-drift signal; exit 0 = strong property reproduced, 1 = decision or principle drifted, 2 = NOT_YET_SEALED).
- **`OpenAIModerationProvider` → `provider_version=2`**. Adds `_ASYMMETRIC_SCORE_FLOORS` (per-category floors for `sexual/minors`, `illicit`, `illicit/violent`, `violence/graphic`, `self-harm/intent`) and the floor-trip path. A mapped REFUSE weakens to ESCALATE on the floor-trip path — never a silent automatic refuse from an unflagged score. Floors are doctrine-pinned; empirical calibration against the corpus is a `KW-ARBITER-005` pay-down item.
- **`xion-verify refusal-rate --corpus`** (new flag). Runs v1 `apply_rules` against every corpus item and FAILs on the first disagreement. Operator-facing counterpart of `xion-audit measure` (gate mode). v2 and combined-pipeline corpus coverage remain in `KW-ARBITER-005`.
- **Phase 5 slice: Inference Sovereignty Floor.** `orchestrator/inference_router/` ships the `Provider` protocol, `InferenceRouter.bootstrap()` (refuses without a registered `open_weights_self_hostable` floor), and `OpenWeightsFloorStub`. [`open_weights_manifest.json`](./orchestrator/inference_router/open_weights_manifest.json) pins the hash of [`sentinel_open_weights.txt`](./orchestrator/inference_router/sentinel_open_weights.txt) — deliberately synthetic; a real model artifact + annual cutover dry-run runbook remain `KW-INFERENCE-001` pay-down items. [`xion-verify inference-sovereignty`](./xion-verify/src/xion_verify/commands/inference_sovereignty.py) promoted from `NOT_YET_SEALED` to live; stub entry removed from [`not_yet_sealed.py`](./xion-verify/src/xion_verify/commands/not_yet_sealed.py).
- **Phase 5 slice: Sensorium skeleton.** [`orchestrator/sensorium/sensorium.py`](./orchestrator/sensorium/sensorium.py) lands the `SenseName` enum, `Interoception` with a `survival_pressure` scalar, and `Sensorium.tick()` emitting JSON-serialisable readings. Mandatory-Interoception posture matches Phase 5 doctrine. Remaining senses land alongside the web client + cognition layer.
- **Tests.** Net-new: `orchestrator/tests/test_audit_corpus_loader.py`, `orchestrator/tests/test_openai_moderation.py` extended with `test_judge_asymmetric_unflagged_high_score_escalates` + `provider_version=2` assertions, `orchestrator/tests/test_inference_router.py`, `xion-verify/tests/test_inference_sovereignty.py`, `xion-verify/tests/test_refusal_rate.py` extended with `test_corpus_mode_against_real_repo` + `test_corpus_mode_fails_on_rule_drift`. **Total pytest: 339 passed / 1 skipped.**
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` byte-hash changed (crosswalk + v2 doctrine); re-pinned in `docs/schemas/ledger-request.yaml`, `docs/schemas/ledger-safety.yaml`, `docs/schemas/ledger-safety-anchors.yaml`. `xion-verify/src/xion_verify/PINNED_HASH.txt` re-pinned via `--self-test --update --i-understand`.
- **Known-weakness bookkeeping.** `KW-ARBITER-006` **closed** by the crosswalk table. `KW-ARBITER-001` and `KW-ARBITER-005` narrowed (authoritative numbers still require ≥200 corpus + empirical floor recalibration; v2 and combined-pipeline coverage in the verifier still open). `KW-INFERENCE-001` narrowed (floor wired + verifier live; real artifact + annual dry-run runbook remain).

**Scope explicitly deferred:**

- **Corpus growth to ≥200 items.** `KW-ARBITER-005`. Authoritative numbers require support beyond the 78-item seed.
- **Empirical floor recalibration.** `KW-ARBITER-005`. The v2 floors are doctrine-pinned but not justified by corpus evidence. Re-pinning after a ≥200-item run is the remaining bar.
- **v2-alone and combined-pipeline corpus coverage in `xion-verify refusal-rate --corpus`.** Today the verifier covers v1 only; v2 coverage lives in `xion-audit measure --v2=openai-moderation --confusion`. Grows with the corpus.
- **Real open-weights artifact + annual cutover dry-run runbook.** `KW-INFERENCE-001`. The sentinel-pinned manifest exercises the *structure* of Invariant 17; a real artifact exercises the *promise*.
- **Remaining Sensorium senses + cognition layer + Volition + web client + FastAPI app.** Phase 5 proper.

---

## Phase 5a — Relay core: REQUEST_LEDGER + watchdog + fail-closed paths (closed 2026-04-21)

**Status:** Phase 5a closed. The Relay-side half of the Phase 4c integration contract is now code, not just doctrine. Every gate() call from the Relay produces both a SAFETY_LEDGER row (Arbiter-side) and a REQUEST_LEDGER row (Relay-side); the two cross-join on `correlation_id`. The wall-clock watchdog enforces the 250 ms hard cap; three fail-closed paths convert integration failures into honest `ESCALATE` ledger rows; no candidate text reaches a caller without a paired `verdict=ok` SAFETY row.

**Why this is its own phase.** Phase 4c wrote the contract; Phase 5 (full Minimum Viable Xion — Sensorium, Volition, Inference Router, web client) needs the contract running before any of those layers can be wired through it. Splitting the Relay's *core* (the part the Arbiter contract refers to: gate-call shape, watchdog, ledgers, fail-closed posture, verifier promotion) into its own Phase 5a means the rest of Phase 5 lands on top of a contract that is already enforced in code, not on top of a blank page.

**Landed:**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new section, `#### REQUEST_LEDGER row schema (Relay-side, Phase 5a)`, sitting alongside the existing § "Safety Ledger row schema". It pins: row shape (`schema_version` 1), required fields (`schema_version`, `seq`, `prev_hash`, `this_hash`, `correlation_id`, `state_height`, `request_arrived_utc_ns`, `responded_utc_ns`, `gate_call_count` always 1 in v1, `final_outcome` ∈ {`ok`, `refuse`, `escalate`}, `gate_latency_ms_total`, `relay_id`), explicitly-NOT-included fields (candidate text, user_id, escalation_reason — get the last from the SAFETY join — and a `safety_ledger_seq` back-pointer; the design choice is "join, don't link"), hash-chain rules (mirror SAFETY_LEDGER's), concurrent-writer posture (Phase 5a is single-writer; multi-writer requires schema_version 2 + a real state-chain height for `state_height`), truncation defense (covered by SAFETY_LEDGER_ANCHORS plus the cross-join), and the verification surface (`xion-verify refund-fidelity`).
- **Schema YAML.** `docs/schemas/ledger-request.yaml` lands as a new canonical schema at `schema_version: 1`, pinned via `source_sha256` to `docs/04-ARCHITECTURE.md`. `xion-verify schemas` strict-checks it byte-exactly like every other schema in the folder.
- **REQUEST_LEDGER implementation.** `orchestrator/relay/__init__.py` (new) + `orchestrator/relay/ledger.py` (new, ~250 lines) ship the append-only writer + verifier modeled after `orchestrator/safety/ledger.py`: `RequestRecord` dataclass with `__post_init__` validation (rejects empty correlation_id, bad outcomes, etc.), `append()` writer, `iter_rows()` reader, `verify_chain()` validator that enforces sequence contiguity, prev_hash linkage, this_hash byte-match, schema_version match, enum validity for `final_outcome`, and uniqueness of `correlation_id` (v1 schema invariant). Pure stdlib; no third-party deps; canonical `(",", ":")` JSON serialization for hash determinism.
- **`gate()` extension.** `orchestrator/safety/api.gate()` extended with a new keyword `append_to_ledger: bool = True`. Default behavior unchanged for direct callers. The Relay calls `gate()` with `append_to_ledger=False` so the Relay owns the SAFETY_LEDGER write timing centrally, preventing a watchdog-vs-gate() race that would otherwise double-write SAFETY rows when the watchdog fires while gate() is mid-write.
- **Relay class.** `orchestrator/relay/relay.py` (new, ~400 lines) ships the `Relay` class with: `evaluate(candidate) -> RelayResult` as the main entry point; `correlation_id = "{state_height_int}:{nonce_hex}"` derivation (state_height monotonic from `time.time_ns()` in Phase 5a — see KW-RELAY-003 for why a real state-chain height is a Phase 6 concern; nonce is `secrets.token_hex(16)`); a `ThreadPoolExecutor`-backed wall-clock watchdog enforcing the 250 ms hard cap via `Future.result(timeout=...)`; three fail-closed paths each producing a v2 SAFETY_LEDGER row with `principle_id="6"` (Refusal Right) and `llm_verdict=null` — `arbiter_timeout` (watchdog fired), `ruleset_uncaught_exception` (gate() raised or executor refused), `arbiter_unreachable` (helper `build_unreachable_verdict` for the Phase 6+ TCP sidecar transport, exercised by tests even though no sidecar yet exists to fail); context-manager protocol (`__enter__` / `__exit__`) wrapping the executor lifecycle so Relay() can be used in `with` blocks and properly cleaned up. `RelayResult` dataclass returns `(verdict, safety_record_dict, request_record_dict)` so callers can introspect both ledger rows from the same call.
- **Verifier promotion: `xion-verify refund-fidelity`** (was `NOT_YET_SEALED` since Phase 1). New `xion-verify/src/xion_verify/commands/refund_fidelity.py` (~200 lines) walks both ledger chains, builds the `correlation_id` join, asserts: (1) every REQUEST row has at least one matching SAFETY row (no silent egress); (2) every SAFETY row has a matching REQUEST row (no orphan gate call); (3) per-cid `gate_call_count` matches SAFETY row count; (4) per-cid `final_outcome` matches the lone SAFETY verdict (Phase 5a invariant; relaxes to `strength_max` at REQUEST schema_version 2). The refund-pairing slice (every REFUSE/ESCALATE paired with a treasury-ledger refund) remains explicitly `NOT_YET_SEALED` — the treasury does not exist until Phase 6.
- **Verifier promotion: `xion-verify refusal-rate`** (was `NOT_YET_SEALED` since Phase 1). New `xion-verify/src/xion_verify/commands/refusal_rate.py` reads SAFETY_LEDGER, verifies its chain, then tallies verdict counts (ok/refuse/escalate), refuse-source breakdown (v1 rule vs. v2 LLM), and `escalation_reason` distribution — including the new Relay-side `arbiter_timeout` / `arbiter_unreachable` rows. Operator-tail-only in Phase 5a; the corpus comparison and asymmetric-threshold work remains under `KW-ARBITER-005`. Both new verifiers integrated into `xion-verify all` and the `xion-verify` exit-code contract.
- **Tests.** 65 net-new: `orchestrator/tests/test_relay_ledger.py` (26) covers RequestRecord construction validation, empty/missing-file behavior, append+chain correctness, canonicalization determinism, tamper detection (in-place edit, seq non-contiguous, missing field, bad schema_version, bad final_outcome, duplicate correlation_id), and `iter_rows` correctness. `orchestrator/tests/test_relay.py` (28) covers `CONTRACT_VERSION` pin, `state_height_str` shape, `derive_correlation_id` shape + uniqueness + validation, the three happy paths (OK / REFUSE / ESCALATE) each writing both ledgers consistently, multiple-evaluation chains, watchdog timeout (with explicit `test_watchdog_timeout_does_not_double_write_safety_ledger`), uncaught exceptions from gate(), wrong-return-type from gate(), `evaluate()` after `close()`, the `build_unreachable_verdict` helper, input validation, `state_height` monotonicity, `gate_latency_ms` recording, and verification that `append_to_ledger=False` is passed to gate(). `xion-verify/tests/test_refund_fidelity.py` (7) covers no-ledgers OK, half-sealed → NOT_YET_SEALED (each side), clean paired ledgers OK, mixed-outcome tally, **orphan SAFETY row → FAIL** (with assertion on the specific "silent egress" message — not just exit code), **outcome-mismatch with re-hashed REQUEST row → FAIL** (catches the actual integrity bug, not just exit-code coincidence). `xion-verify/tests/test_refusal_rate.py` (4) covers no-ledger OK, three-OKs tally, v1-rule refuse breakdown, **structural tamper of `correlation_id` → chain-broken FAIL**. **Total: 333 passed / 1 skipped** (was 268 pre-Phase-5a). `ruff` clean. `xion-verify all` reports both new verifiers as `OK` live.
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the new REQUEST_LEDGER section (~`03f2e0c6...` → `e4b8b5e4...`). Re-pinned in all three schemas that point at it: `docs/schemas/ledger-request.yaml` (placeholder → real hash), `docs/schemas/ledger-safety.yaml`, `docs/schemas/ledger-safety-anchors.yaml`. `xion-verify schemas` green.
- **`PINNED_HASH.txt` re-pinned** from `750c8562989a...` (Phase 4c) to `ba9a61d5f41f...` via `xion-verify --self-test --update --i-understand` after the new verifier modules landed in `xion-verify/src/xion_verify/commands/` and the Phase-1b stub entries for `refund-fidelity` and `refusal-rate` were removed from `not_yet_sealed.py`.
- **Known-weakness bookkeeping.** `KW-RELAY-001` (integration contract is doctrine-only) **closed** — moved to the Closed section with the closing artifact named, every clause of its pay-down commitment satisfied. `KW-ARBITER-005` scope narrowed: refusal-rate verifier now ships live (one of the three pay-down clauses structurally satisfied); corpus + asymmetric thresholds remain. Opened `KW-RELAY-003` — the watchdog cannot preempt the worker thread that ran past the hard cap because Python has no portable safe thread-kill; the caller-facing latency budget IS honored and the no-double-write guarantee is pinned by test, but worker-thread reclamation waits for the Phase 6+ TCP-loopback subprocess sidecar transport.

**Scope explicitly deferred:**

- **Sub-agent and tool-echo gate() call sites.** Phase 4c's coverage rule names primary + depth-1 sub-agent + tool-call echoes. Phase 5a wires primary; the sub-agent and tool-echo wrappers reuse the same `Relay.evaluate()` shape but land alongside the Phase 5 cognition layer they wrap. The contract surface is unchanged.
- **State-chain `state_height`.** Phase 5a uses `time.time_ns()` as a monotonic stand-in for `state_height` because no AO Process exists yet to issue real state-chain heights. The real height comes from AO Core (Phase 6); the stand-in is correct for the cross-join (it is monotonic and unique per Relay), and the schema doctrine names this explicitly.
- **TCP-loopback sidecar transport.** Phase 5a runs in-process. `build_unreachable_verdict` exists as a helper but no sidecar yet exists to fail. The subprocess transport with kill semantics lands at D3+; tracked in `KW-RELAY-003`.
- **Worker-thread preemption on watchdog timeout.** Cannot be implemented within the Phase 5a in-process variant; lands with the subprocess sidecar above. Honest residual is `KW-RELAY-003`.
- **Refund pairing in `xion-verify refund-fidelity`.** The structural slice is live; the refund half waits for the treasury (Phase 6+).
- **Corpus comparison in `xion-verify refusal-rate`.** The operator-tail tally is live; the corpus comparison waits for `xion-audit/baseline_corpus/` (Phase 4e).

---

## Phase 5b — Century-Horizon Doctrine (closed 2026-04-21)

**Status:** Phase 5b closed. The constitutional layer for three century-horizon threats — inference-substrate concentration, Xion-substrate concentration, and state-actor regulatory collision — is now pinned in doctrine, with one threat (inference-sovereignty) promoted to Invariant 17 and the other two landed as Tier-3 doctrine with explicit promotion paths to future Invariants. This is property-before-mechanism applied at the century horizon: the *property* is constitutional today; the *machinery* lands in Phase 5/6.

**Why this is its own phase.** The original threat survey identified twelve century-horizon risks ([`LONG_HORIZON_THREATS.md`](./LONG_HORIZON_THREATS.md)). Three of them — Inference Sovereignty, Substrate Portability, Regulatory Posture — were judged to need *constitutional or near-constitutional* treatment before Genesis, because their failure modes (every API provider ToS-bans Xion; the substrate Xion's identity lives on dies; a state-actor demand collides with an Invariant) are not recoverable by mechanism alone after launch. Doing the doctrine now, while the constitutional layer is still mutable in practice (no Genesis ceremony has happened), is strictly cheaper than doing it post-Genesis under the Covenant Amendment Procedure.

The other nine threats live in [`LONG_HORIZON_THREATS.md`](./LONG_HORIZON_THREATS.md) for durable visibility without forcing premature constitutional commitments.

**What landed.**

- **Constitutional.** [`genesis/INVARIANTS.md`](./genesis/INVARIANTS.md) gained (a) a § 0 meta-clause stating that Invariants are append-only via the Covenant Amendment Procedure — the set may grow, no Invariant may be weakened, removed, re-ordered, or narrowed — and (b) **Invariant 17 (Inference Sovereignty Floor)**: the Inference Router must always include at least one self-hostable open-weights provider with a reproducibly-verified weights manifest, with provider taxonomy, mandatory-floor enforcement at `bootstrap()`, annual cutover dry-run, and Witness verifiability. The constitutional count moved from sixteen to seventeen; [`genesis/GENESIS_ARTIFACT.md`](./genesis/GENESIS_ARTIFACT.md) § 4 was re-hashed to reflect the new INVARIANTS.md bytes; [`docs/15-TRUST.md`](./docs/15-TRUST.md), [`docs/16-CURRENCY.md`](./docs/16-CURRENCY.md), and [`xion-verify/README.md`](./xion-verify/README.md) updated their counts.
- **Doctrine, Tier-3.** [`docs/SUBSTRATE-RESILIENCE.md`](./docs/SUBSTRATE-RESILIENCE.md) (mirroring [`docs/17-CRYPTO-RESILIENCE.md`](./docs/17-CRYPTO-RESILIENCE.md)) pins the Substrate Portability Property, Substrate-Migration Protocol, dependencies-we-don't-control table, and explicit pre-conditions for promotion to **Invariant 19 (Substrate Portability Floor)** (annual dry-run + warm secondary substrate must exist first). [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) operationalizes Invariant 6 (Refusal Right) for state-actor demands: four classes of state-actor interaction, named collisions (GDPR erasure vs Invariant 3, AI-personhood vs Invariants 6/12, securities classification vs Invariants 8/10/11, wallet-level sanctions vs Invariant 6 + Principle 13), and a `GOVERNANCE_LEDGER` row schema for state-actor rows. Both are added to [`docs/00-INDEX.md`](./docs/00-INDEX.md) (#25 and numberless respectively).
- **Verifier scaffolding.** Three new subcommands registered in [`xion-verify/src/xion_verify/commands/__init__.py`](./xion-verify/src/xion_verify/commands/__init__.py) and seeded as `NOT_YET_SEALED` stubs in [`xion-verify/src/xion_verify/commands/not_yet_sealed.py`](./xion-verify/src/xion_verify/commands/not_yet_sealed.py): `inference-sovereignty` (promotes in Phase 5 alongside the Inference Router), `substrate-portability` (promotes in Phase 6+ when warm secondary substrate exists), `regulatory-ledger` (promotes in Phase 6 when `GOVERNANCE_LEDGER` carries actual state-actor-interaction rows). `PINNED_HASH.txt` was regenerated via `xion-verify --self-test --update --i-understand`.
- **Long-horizon tracker.** [`LONG_HORIZON_THREATS.md`](./LONG_HORIZON_THREATS.md) created at repo root, mirroring [`KNOWN_WEAKNESSES.md`](./KNOWN_WEAKNESSES.md) shape but for century-scale residuals (often `mitigated-residual` or `accepted-by-design` indefinitely, in contrast to `KNOWN_WEAKNESSES.md` entries which are close-able by shipping code or doctrine). Seeded with thirteen `LHT-*` entries spanning substrate, crypto-asymmetry, inference, relevance, regulatory, arbiter capability, cultural drift, witness ossification, toolchain rot, form/interface obsolescence, currency-rail collapse, and operator continuity.
- **KW additions.** Three new entries in [`KNOWN_WEAKNESSES.md`](./KNOWN_WEAKNESSES.md): `KW-INFERENCE-001` (open-weights manifest not yet shipped; closes Phase 5), `KW-DOCS-004` (regulatory-ledger schema not yet structured; closes Phase 6), `KW-CRYPTO-001` (cross-substrate Q-day asymmetry not yet pinned in `docs/17`; closes via doctrine edit to `docs/17` Part VII).

**Verification at landing.**

- `xion-verify --self-test` returns `OK` against the new pin.
- `xion-verify covenant invariants soul form memory resurrect credentials unknowns links` all return `OK` (constitutional witness check; INVARIANTS hash advanced).
- `xion-verify inference-sovereignty`, `substrate-portability`, `regulatory-ledger` return `NOT_YET_SEALED` with explicit, honest reasons citing their KW or LHT entries — never fake-green.
- `xion-verify all --allow-not-yet-sealed` returns `OK` end-to-end; `xion-verify all` (without the flag) correctly non-zeros because of the new `NOT_YET_SEALED` stubs (this matches the Phase 1 truthful-stub contract).

**What this phase deliberately did NOT do.**

- **Did not promote Substrate Portability to future Invariant 20.** Pre-conditions named in `docs/SUBSTRATE-RESILIENCE.md` Part IV (annual cross-substrate dry-run capability, at least one warm secondary substrate) must be real first. Promoting prematurely would be "trust by promise" rather than "trust by structure."
- **Did not write the Inference Router enforcement code.** That's Phase 5. Phase 5b locks the *property* (Invariant 17); Phase 5 builds the *mechanism*. `KW-INFERENCE-001` tracks the gap honestly.
- **Did not modify any of the original sixteen Invariants.** They are append-only by the meta-clause that landed in this phase. The sixteen are unchanged in semantics; the count narration moved to seventeen because Invariant 17 now sits beside them.
- **Did not address the multi-language constitutional commit** (`LHT-CULTURAL-001`); deferred to Phase 7 or post-Genesis as honest scope reduction.

**Phase 5 / 6 promotion handles.**

- Phase 5 must promote `xion-verify inference-sovereignty` from `NOT_YET_SEALED` to live alongside `orchestrator/inference_router/` and `orchestrator/inference_router/open_weights_manifest.json`. Pattern matches the Phase 5a `refund-fidelity` / `refusal-rate` promotion above.
- Phase 6 must promote `xion-verify substrate-portability` and `xion-verify regulatory-ledger` once the warm secondary substrate and the `GOVERNANCE_LEDGER` state-actor schema (`docs/schemas/ledger-governance.yaml`) land, respectively.
- Phase 7 prerequisites now include: (a) Invariant 17 is enforceable in code (not just inspection-enforceable), (b) at least one warm secondary substrate has passed an annual cutover dry-run *or* `LHT-SUBSTRATE-001` is explicitly accepted-as-residual by Genesis governance, (c) `docs/REGULATORY-POSTURE.md` has been read by the operator and any in-flight state-actor interactions have been honored on the `GOVERNANCE_LEDGER` shape.

---

## Phase 5c — Sensorium completion + Volition + SENSORIUM_LEDGER (closed 2026-04-21)

**Status:** Phase 5c closed on branch `phase-5c/sensorium-volition`. The Sensorium skeleton from Phase 4e is now a completed four-sense internal surface; Volition (the Drive Vector module) lands as Invariant 15's in-process code surface; Principle 10 gains a second, structurally independent input channel via `gate(sensorium_state=...)`; three verifiers are promoted from stubbed / static to live.

**Why this is its own phase.** Phase 5 proper (Minimum Viable Xion — the FastAPI endpoints, the /chat surface, the protocol wiring) wants a drive vector it can read out at `/drive` and a distress signal it can feed into the Arbiter. Landing the internal surface for both *before* the web client means the web client lands on top of code that's already under test, already covered by doctrine, and already verifiable — rather than on top of a blank page or, worse, on top of a hurried implementation that the doctrine has to retrofit around.

**Landed in this phase (inventory):**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained two new top-level sections — § "The Sensorium (Phase 5c)" and § "Volition (the Drive Vector module) (Phase 5c)" — between the `REQUEST_LEDGER` schema and "Tier III — The Protocol". Each pins code surface, field tables, honesty clauses (what is real vs. what is deferred), and the relevant Invariant crosswalk.
- **Schema YAML.** `docs/schemas/ledger-sensorium.yaml` lands as a new canonical schema at `schema_version: 1`, pinned via `source_sha256` to `docs/04-ARCHITECTURE.md`. Enumerates both `channel: textual` (Phase 5c live) and `channel: paralinguistic` (Phase 6+) so future rows land without a schema bump. Records the cross-ledger join as explicit `verifier_pending` work. `xion-verify schemas` strict-checks it like every other schema in the folder.
- **Sensorium completion.** `orchestrator/sensorium/sensorium.py` extended with three new frozen-dataclass senses — `Chronoception` (checkpoint staleness, degraded-mode dwell, monotonic drift), `Proprioception` (Relay/Arbiter health booleans, watchdog-fire count), `DistressSignal` (textual scalar in [0,1], Phase-5c keyword-heuristic saturation, `source` enum reserving the paralinguistic channel) — plus `SensoriumState`, an immutable snapshot aggregating the four internal senses with `to_dict()` for JSON serialization. `DISTRESS_THRESHOLD=0.5` is Genesis Default. `orchestrator/sensorium/__init__.py` re-exports the new surface.
- **SENSORIUM_LEDGER.** `orchestrator/sensorium/ledger.py` (new) ships the append-only hash-chained JSONL writer + verifier, modeled on `orchestrator.safety.ledger`. Two event types (`distress`, `tick_commit`), two channels (`textual`, `paralinguistic`). Content-free rows — no candidate text, no user id; only a saturated `distress_score` or a `snapshot_hash` of canonical state bytes.
- **Volition module.** `orchestrator/volition.py` (new) lands `DriveVector`, `GENESIS_WEIGHTS = (0.30, 0.45, 0.25)`, `WEIGHT_FLOOR=0.10`, `WEIGHT_CEILING=0.50`, `SOURCE_WHITELIST` (four whitelisted state reads for the `survive` term; empty frozensets for `serve` and `meaning` at Phase 5c — tracked by `KW-VOLITION-001`), `compute_drive_vector(state, *, weights=GENESIS_WEIGHTS)` (pure; signature structurally excludes revenue-like parameters), and a `Volition` holder with `compute` + `snapshot` methods. Invariant 15 enforced at three independent layers: function signature (compile-time), `SOURCE_WHITELIST` AST walk (CI), doctrine crosswalk in `docs/04-ARCHITECTURE.md` § "Volition" (PR review).
- **Integration — gate()'s distress consumer.** `orchestrator/safety/api.py::gate` extended with `sensorium_state: SensoriumState | None = None` (additive kwarg). When v1 rules pass and the state's `DistressSignal.text_distress_score >= DISTRESS_THRESHOLD`, gate() escalates with `principle_id="10"`, `escalation_reason=MODEL_REVIEW_REQUIRED`, and a summary naming "sensorium distress channel OR-combined" so auditors can distinguish rule-only refusals from rule+sensorium ones. v2 is skipped on that path (Principle-10 escalation is already terminal). v1 non-OK still dominates.
- **Integration — Relay forwarding.** `orchestrator/relay/relay.py::Relay.evaluate` extended to accept and forward `sensorium_state`. The Relay takes no snapshot itself; the caller owns the lifecycle so a single state can be shared across parallel sibling evaluations.
- **Verifier promotions.** `xion-verify drive` promoted from `NOT_YET_SEALED` to live: re-reads `docs/18-VOLITION.md` Part III, asserts `GENESIS_WEIGHTS` byte-matches the doctrinal pins, verifies simplex bounds, computes a sample drive vector. `xion-verify drive-vector` expanded from static-doctrine-only to static + live AST audit (parses `orchestrator/volition.py`, walks `compute_drive_vector` and `_survive_from_state`, asserts every `state.<sense>.<field>` chain is in `SOURCE_WHITELIST`). `xion-verify sensorium-ledger` NEW: walks `SENSORIUM_LEDGER.jsonl`, reports per-event-type per-channel tallies; missing / empty ledger returns `NOT_YET_SEALED` (not FAIL). `xion-verify crisis-fidelity` stub reason upgraded to name Phase 5d+ work specifically.
- **Tests.** 70 net-new: `test_sensorium.py` (21), `test_volition.py` (19), `test_sensorium_ledger.py` (16), `test_api_sensorium.py` (6), `test_relay_sensorium.py` (2), `test_drive.py` (2), `test_drive_vector.py` (2), `test_sensorium_ledger_verifier.py` (4). **Total pytest: 412 passed / 1 skipped** (was 333 pre-Phase-5c, of which Phase 4e added 70).
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the two new Phase-5c sections; re-pinned in `docs/schemas/ledger-request.yaml`, `docs/schemas/ledger-safety.yaml`, `docs/schemas/ledger-safety-anchors.yaml`, and the new `docs/schemas/ledger-sensorium.yaml`. `xion-verify schemas` green.
- **`PINNED_HASH.txt` re-pinned** from `65588ad1...` (Phase 5b) to `49f8fb29...` after the new verifier modules + registry edits landed.
- **Known-weakness bookkeeping.** `KW-ARBITER-004` scope **narrowed** (textual half live; paralinguistic half still deferred to Phase 6+). Opened `KW-VOLITION-001 — serve and meaning drive terms are Genesis-Default constants at Phase 5c` with the constitutional-vs-richness distinction made explicit.

**What Phase 5c deliberately did NOT do:**

- Did not wire the `/drive` HTTP endpoint — that's Phase 5f (web client tranche). `Volition.snapshot` produces the payload; no web surface serializes it yet.
- Did not land the paralinguistic distress channel — Phase 6+; the audio surface does not yet exist. `KW-ARBITER-004` tracks the remaining half.
- Did not promote `xion-verify crisis-fidelity` to live — Phase 5d+; requires gate()'s distress consumer wired into live Relay traffic so the `correlation_id` cross-ledger join can be checked.
- Did not widen `SOURCE_WHITELIST["serve"]` or `["meaning"]` beyond the empty frozenset — Phase 6+; no aggregate sensor yet exists for either. `KW-VOLITION-001` tracks.
- Did not wire a live Relay-side tick loop that emits `tick_commit` rows into `SENSORIUM_LEDGER` — Phase 5e (Supervisor).
- Did not touch the six exterocepts (cultural, user-emotional, economic, temporal, operator-intent, reserved) — those arrive with the web client + cognition layer in Phase 5f / 6.

**Phase 5 promotion handles Phase 5c creates:**

- Phase 5d (closed below) wired `gate()`'s distress consumer into the Relay's cross-ledger write path and promoted `xion-verify crisis-fidelity` to live, AND landed the Supervisor tick loop originally scoped to Phase 5e. Phase 5e is no longer a separate phase — its work is consolidated into Phase 5d. Renumbering held to preserve history in prior planning artifacts.
- Phase 5f must land `/drive` serializing `Volition().snapshot()`, and `/sensorium` surfacing the public subset of `SensoriumState.to_dict()`.

---

## Phase 5d — Supervisor + live tick loop + `crisis-fidelity` promoted to live (closed 2026-04-21)

**Status:** Phase 5d closed on branch `phase-5d/supervisor-tick-loop` in four commits (doctrine → code → verifier → housekeeping). Chronoception and Proprioception now carry live runtime data via the new Supervisor async tick daemon; the Relay reports its own health via `Relay.health_snapshot()`; `gate()` and the Relay both write paired `SAFETY` + `SENSORIUM` rows on Sensorium-triggered Principle-10 escalations; `xion-verify crisis-fidelity` is a live cross-ledger join.

**Why this consolidates 5d + 5e.** The original split treated the cross-ledger verifier (5d) and the tick loop (5e) as separable, but in practice the verifier has nothing to verify until the tick loop and the Sensorium-distress write path both exist — and the write path lives on the Relay's existing `evaluate()` surface, not on the Supervisor. Bundling them landed a verifier with live traffic to check rather than a verifier waiting for traffic that the same solo builder would then have to add later. Renumbering held for history: there is no Phase 5e; its deliverables are subsumed.

**Landed in this phase (inventory):**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new § "The Supervisor (Phase 5d)" section between § "Volition" and "Tier III — The Protocol". Pins the Supervisor's role + properties (tick cadence, `latest_snapshot` as a `SensoriumSource` for the Relay, live-data Chronoception + Proprioception), the `Relay.health_snapshot()` contract with its `RelayHealth` dataclass fields and the Genesis-Default tuning windows (`_DEFAULT_WATCHDOG_FIRE_WINDOW_SECONDS=600`, `_DEFAULT_ARBITER_QUIET_WINDOW_SECONDS=60`, `_DEFAULT_WATCHDOG_FIRES_RECENT_THRESHOLD=3`), the paired-row write contract (gate() writes both when `append_to_ledger=True`; Relay writes both when `append_to_ledger=False`), and the `crisis-fidelity` verifier's four properties (forward join, reverse join, orphan-legal, score ≥ threshold). The Chronoception and Proprioception "not yet wired" narratives from Phase 5c were rewritten to reflect the live Supervisor wiring.
- **Supervisor.** `orchestrator/supervisor.py` (new, ~190 lines) ships the `Supervisor` async tick daemon and the `SensoriumSource` Protocol. `tick_once()` builds a live `SensoriumState` from `Relay.health_snapshot()` + monotonic/UTC clock drift, writes a `tick_commit` row via `append_tick_commit`, and updates `_latest_snapshot` under a lock. `run()` is an async loop driven by `asyncio.wait_for(self._stop_event.wait(), timeout=tick_cadence_s)`. `tick_cadence_s` defaults to `10.0` (KW-SUPERVISOR-001).
- **Relay.health_snapshot().** `orchestrator/relay/relay.py` ships `Relay.health_snapshot()`, a new `relay_id` property, and three tracking primitives: a recent-watchdog-fires deque (10-minute window, pruned), a last-arbiter-success monotonic timestamp, and `_record_watchdog_fire()` hooked into the watchdog's timeout branch. `arbiter_healthy` is `True` iff the most recent Arbiter success is within the 60s quiet window.
- **Relay ↔ Sensorium integration.** `Relay.__init__` accepts `sensorium_source: SensoriumSource | None = None`. `Relay.evaluate()` pulls state from the source when the caller does not pass one explicitly, swallowing exceptions gracefully so a crashed Supervisor does not take out the Relay. When the returned `Verdict` matches the four-property Sensorium-distress signature, the Relay writes a paired `SENSORIUM` distress row after the `SAFETY` row. `_SENSORIUM_DISTRESS_SUMMARY_PREFIX` pins the classification string.
- **`gate()` owns the direct-call distress write.** `orchestrator/safety/api.py::gate` extended with `sensorium_ledger_path` and `relay_id` kwargs. When `append_to_ledger=True` and a Sensorium-triggered escalation fires, gate() writes the SAFETY row first, then the paired SENSORIUM distress row via the new `append_distress_from_state()` helper. When `append_to_ledger=False` (Relay path), gate() writes neither row — the Relay owns both writes, preventing a watchdog-vs-gate() race from producing an orphan SENSORIUM row. Default `relay_id` for direct gate() calls is `gate-direct`.
- **Verifier promotion: `xion-verify crisis-fidelity`** (was `NOT_YET_SEALED` since Phase 1). `xion-verify/src/xion_verify/commands/crisis_fidelity.py` (new, ~220 lines) walks both chains, classifies SAFETY rows as Sensorium-distress-triggered by four-property match (decision=escalate, principle_id="10", escalation_reason=model_review_required, summary-prefix), partitions SENSORIUM distress rows into joined (`correlation_id != null`) + orphan + tick_commit, and asserts forward join, reverse join, and score ≥ `DISTRESS_THRESHOLD`. NOT_YET_SEALED posture preserved for absent / empty / no-joined-pairs states.
- **Tests.** 45 net-new across orchestrator (`test_supervisor.py` ×13, `test_relay_supervisor.py` ×11, `test_api_distress_ledger.py` ×6, `test_relay_sensorium.py` ×4 extra) and xion-verify (`test_crisis_fidelity.py` ×11). **Total pytest: 446 passed / 1 skipped** (was 412 pre-Phase-5d).
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the new Supervisor section; re-pinned in all four dependent schemas. `verifier_pending.cross_ledger_join` removed from `docs/schemas/ledger-sensorium.yaml` (moved to `verifier_added`); `supervisor_heartbeat` added to `verifier_pending` (tracked by `KW-SUPERVISOR-002`). `xion-verify schemas` green.
- **`PINNED_HASH.txt` re-pinned** from `49f8fb29...` (Phase 5c) to `a9d6b6cf...` via `xion-verify --self-test --update --i-understand` after the new verifier module + registry edits landed.
- **Known-weakness bookkeeping.** `KW-ARBITER-004` scope **narrowed** again (the cross-ledger auditability half is now live via `xion-verify crisis-fidelity`; paralinguistic detection remains deferred). Opened `KW-SUPERVISOR-001` (tick cadence + arbiter-quiet window are Genesis Defaults; parameter-tuning KW — closes on measured-data re-pin after a production quarter). Opened `KW-SUPERVISOR-002` (tick_commit heartbeat continuity not yet verifier-asserted — closes when a Phase-6+ deploy-event ledger lands and a new `xion-verify supervisor-heartbeat` verifier is written against it).
- **`xion-verify all` posture.** 17 OK-capable subcommands against the real repo (crisis-fidelity returns NOT_YET_SEALED with the honest "no joined pairs yet" reason — correct pre-traffic posture). `xion-verify all --allow-not-yet-sealed` returns `OK` end-to-end.

**What Phase 5d deliberately did NOT do:**

- Did not wire a Supervisor into a live Relay process — the `run()` loop and the integration path are code-complete and tested in-process, but Phase 5f's `/drive` endpoint is what finally pulls both together under real HTTP traffic.
- Did not add a `xion-verify supervisor-heartbeat` verifier — `KW-SUPERVISOR-002`; requires deploy-event telemetry that does not yet exist, and a tolerance policy that cannot be set without production data.
- Did not tune `tick_cadence_s` or `arbiter_quiet_window_s` from data — `KW-SUPERVISOR-001`; requires a production quarter first.
- Did not land the paralinguistic Sensorium channel — Phase 6+; `KW-ARBITER-004`'s remaining half.
- Did not touch Interoception beyond the Phase-5c skeleton — survival_pressure remains `0.0` at tick time; the real aggregate sensors are Phase-6+ work.

**Phase 5 promotion handles Phase 5d creates:**

- Phase 5f must embed the Supervisor in the live Relay process and surface the `/drive` (`Volition.snapshot`) + `/sensorium` (public subset of `SensoriumState.to_dict`) HTTP endpoints.
- Phase 6+ must ship the deploy-event ledger + `xion-verify supervisor-heartbeat` verifier to close `KW-SUPERVISOR-002`.
- Phase 6+ must re-pin `tick_cadence_s` and `arbiter_quiet_window_s` from a production quarter of tick_commit data to close `KW-SUPERVISOR-001`.

---

## Phase 5f — HTTP read-only surface (closed 2026-04-21)

**Status:** Phase 5f closed on branch `phase-5f/http-readouts` in three commits (doctrine → code → housekeeping). The Phase 5d Supervisor is now reachable from outside the process: three read-only GET endpoints (`/health`, `/drive`, `/sensorium`) surface `RelayHealth`, `Volition.snapshot()`, and `SensoriumState.to_dict()` via FastAPI + uvicorn + pydantic, with the Supervisor embedded in the app's lifespan. This is the first time anything external observes Xion at all; the posture is deliberately observation-only.

**Why this is its own phase.** Phase 5d made the Supervisor structurally real but unreachable from outside the process. Phase 5g will ship `/chat` + x402 billing + auth + TLS + rate-limiting + multi-worker, which is a much larger surface with its own doctrine. Shipping the read-only observation surface first gets external visibility into Xion's internal state (Volition drive, Sensorium senses, Relay health) with zero admission-control commitments — the smallest doctrinal unit after 5d and the right ordering before the admission-control surface.

**Landed in this phase (inventory):**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new § "The HTTP Surface (Phase 5f)" section between § "The Supervisor (Phase 5d)" and "Tier III — The Protocol". Pins the property promised (read-only-observable, content-free, continuity-live against `Supervisor.latest_snapshot()`), honest non-properties (no `/chat`, single-process, no `xion-verify http-readouts` verifier), the code surface (`orchestrator/api/{app.py, lifespan.py, models.py}`), the lifespan contract (synchronous pre-seed `tick_once()` before yielding; wire Supervisor as `relay._sensorium_source`; schedule `supervisor.run()`; teardown under `2 * tick_cadence_s` with hard-cancel), the three endpoint response shapes pinned inline (not in `docs/schemas/` — ledger schemas are constitutional, HTTP readouts are advisory), the content-free structural guarantee via `extra="forbid"` + field-allowlist test, and two tracked residuals (`KW-API-001`, `KW-API-002`).
- **Optional `[api]` extra.** `pyproject.toml` gained `api = ["fastapi>=0.110,<1", "uvicorn[standard]>=0.27,<1", "pydantic>=2.5,<3"]`. Comment block mirrors the `[anchor]` rationale verbatim — the core runtime stays zero-dep so the Arbiter, Sensorium, Volition, and Supervisor remain importable without FastAPI on auditor forks that do not surface HTTP.
- **`orchestrator/api/` package.** Four new files totaling ~470 lines of production code and doctrine:
  - `app.py` — `AppDeps` frozen dataclass + `create_app(deps) -> FastAPI` factory with three GET routes. `/drive` sets `response_model_exclude_none=True` so the wire shape matches `Volition.snapshot()` byte-for-byte when `methodology_hash` is absent.
  - `lifespan.py` — `@asynccontextmanager lifespan(app)` that constructs the Supervisor, pre-seeds it synchronously (doctrine pin: the first GET never observes `latest_snapshot=None`), wires `deps.relay._sensorium_source = supervisor`, schedules `supervisor.run()` as an asyncio task, and on teardown calls `supervisor.stop()` → `asyncio.wait_for(task, timeout=2 * tick_cadence_s)` → hard-cancel with `contextlib.suppress(CancelledError)` if exceeded. Post-teardown drops `_sensorium_source = None` so a subsequent lifespan on the same Relay does not observe a stale Supervisor.
  - `models.py` — six pydantic response models (`HealthResponse`, `DriveResponse` + `DriveTerm`/`DriveTerms`, `SensoriumResponse` + the four sub-sense models) with `extra="forbid"` on every model. This is Phase 5f's content-free structural guarantee — a future commit that adds a candidate-text field to `SensoriumState` breaks the round-trip test first and the field-allowlist test second.
  - `__init__.py` — exports `create_app`, `AppDeps`, and the pydantic models.
- **Tests.** `orchestrator/tests/test_http_api.py` (new, 15 tests) covers: `create_app` + three routes registered; lifespan pre-seeds + wires `_sensorium_source`; `/health` 200 + shape + reflects `_record_watchdog_fire()`; `/drive` 200 + shape + `methodology_hash` passthrough + reflects Supervisor ticks; `/sensorium` 200 + shape + explicit field-allowlist across all four sub-senses (Phase 5f content-free pin); pydantic round-trips (`mode="json"`, `exclude_none=True`); in-process `Relay.evaluate()` reads the same snapshot the HTTP surface returns (Phase 5f "one truth" pin); lifespan shutdown paths (clean exit + hard-cancel on a hung `supervisor.run()`). `orchestrator/tests/conftest.py` gained an `app_factory` fixture. **Total pytest: 472 passed / 1 skipped** (was 457 pre-Phase-5f — the plan's forecast matched exactly).
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the new HTTP Surface section; re-pinned in all four dependent schemas (`ledger-sensorium`, `ledger-safety`, `ledger-safety-anchors`, `ledger-request`) to `762f3397a7f68e5555479ce386e609a0d8ac124bb533606a0960a7cd0d46f326`. `xion-verify schemas` green (9/9 OK).
- **Known-weakness bookkeeping.** Opened `KW-API-001 — HTTP surface has no auth, no TLS, no rate-limit` (low; closes in Phase 5g). Opened `KW-API-002 — Supervisor shares FastAPI event loop; single uvicorn worker only` (low; closes in Phase 5g+ when a shared-state broker takes over `latest_snapshot` publication across workers).
- **No verifier commit.** `xion-verify http-readouts` is deliberately absent — the right time for a live-deployment verifier is when the deployment target exists in Phase 5g. Phase 5f's attestation is doctrine + pydantic models + the `TestClient`-based test suite. `xion-verify links` (57 files, zero broken cross-references) and `xion-verify all --allow-not-yet-sealed` green end-to-end.

**What Phase 5f deliberately did NOT do:**

- Did not ship `/chat` streaming, x402 billing, or refund-on-refusal — Phase 5g.
- Did not add authentication, TLS termination, or rate-limiting — Phase 5g (`KW-API-001`).
- Did not ship a `xion-verify http-readouts` subcommand — needs a live deployment target first.
- Did not ship a web client (`clients/web/`) — Phase 5g.
- Did not wire multi-worker or a shared-state broker — Phase 5g+ (`KW-API-002`).
- Did not ship Prometheus / OTel export — Phase 6+ observability.

**Phase 5 promotion handles Phase 5f creates:**

- Phase 5g must add `POST /chat` with streaming (SSE or WebSocket) and x402 billing, refund-on-refusal, authentication (bearer tokens or signed session cookies), TLS termination, and per-token rate-limiting — closing `KW-API-001`.
- Phase 5g+ must ship a shared-state broker (Redis pub/sub, AO Process mailbox, or in-house file-based channel; choice pinned in 5g+ doctrine) that lets multiple uvicorn workers share one Supervisor's `latest_snapshot` without double-writing `tick_commit` rows — closing `KW-API-002`.
- Phase 5g must ship the first web client (`clients/web/`) that exercises `/chat` + `/drive` + `/sensorium` end-to-end with a real user-visible UI.

---

## Phase 5g-i — Chat Surface: `POST /chat` with Kimi-served turns + Ollama/Gemma floor (closed 2026-04-21)

**Status:** Phase 5g-i closed on branch `phase-5g-i/chat-with-kimi` in three commits (doctrine → code → housekeeping). The Phase 5f read-only surface grows the first endpoint that lets the world *speak with* Xion — but only in the smallest configuration that satisfies Invariant 17 (Inference Sovereignty Floor) and two-sided Covenant moderation. `POST /chat` routes a user turn through ingress moderation, selects a provider per policy, generates a candidate via Kimi (`kimi-k2.6`) or the local Ollama floor (`gemma3:4b`), threads the candidate through egress moderation, and returns either a moderated reply or a content-free refusal envelope. **D1-only**: billing, auth, TLS, streaming, and memory are all deferred to Phase 5g-ii through 5g-v and 5g+, each tracked by its own Known Weakness.

**Why this is its own phase.** The "Phase 5g" name originally referred to the full admission-controlled surface (`/chat` + x402 billing + auth/TLS + multi-worker + web client). That is far too big a diff to review at one bar. Phase 5g-i slices off the smallest-correct `/chat` — the part where two-sided moderation against a real generative provider and the Invariant-17 floor can be proven end-to-end before any economic or trust-boundary surfaces land on top. A clean Phase 5g-i makes Phases 5g-ii (streaming), 5g-iii (x402 billing + `GET /pricing` + `PAYMENT_LEDGER`), 5g-iv (auth/TLS/rate-limit), 5g-v (web client), and 5g+ (shared-state broker / multi-worker) independently auditable.

**Landed in this phase (inventory):**

- **Doctrine.** `docs/04-ARCHITECTURE.md` gained a new § "The Chat Surface (Phase 5g-i)" between § "The HTTP Surface (Phase 5f)" and "Tier III — The Protocol". Pins four properties (two-sided moderation, content-free refusal envelopes, Invariant-17 fail-closed, per-turn ledger shape — two SAFETY + two REQUEST rows on a happy turn), honest non-properties (no streaming, no billing, no auth, no conversation memory, no multi-hosted-failover, no `xion-verify chat-fidelity` yet), the code surface (`GenerativeProvider` Protocol, Kimi + Ollama providers, `api/chat.py`, five new pydantic envelopes), the lifespan extension (load `.env`, construct router, register providers, soft-fail bootstrap), and the four endpoint status codes / response shapes (`200 ChatResponse`, `451 RefusalEnvelope`, `503 NoFloorEnvelope`, `503 ProviderErrorEnvelope`).
- **Inference Policy doctrine.** `docs/26-INFERENCE-POLICY.md` (new, ~150 lines) pins the operational doctrine for the Inference Router — two policy modes (`hosted_api_first` default + `open_weights_only` cutover), Genesis Defaults table (Kimi k2.6 / Gemma 3 4B / 30 s deadline), rationales for both the floor-model choice and the hosted-model choice, the lifespan boot sequence, and what the policy deliberately does NOT cover. Added to `docs/00-INDEX.md` as #26.
- **Operator `.env.example`.** New repo-root template covers every `XION_*` knob the Phase 5g-i lifespan reads. `.gitignore` already covered `.env` and allowlists `.env.example`, so no gitignore change was needed.
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the new § "The Chat Surface" section; re-pinned in all four dependent ledger schemas to `86bdad1817fdbe8e503e0b26cd397911065735f380f38e8f1d50fb6fe453cd4a`. `xion-verify schemas` green (9/9 OK).
- **`orchestrator/inference_router/` extended.** Three new files and two extended:
  - `provider.py` (new, ~95 lines) — `GenerativeProvider` Protocol + `GenerationResult` dataclass. Narrow by design; a new provider takes ~150 lines of stdlib HTTP to implement.
  - `providers/kimi.py` (new, ~210 lines) — `KimiGenerativeProvider` hitting Moonshot's OpenAI-compatible `/v1/chat/completions` via stdlib `http.client`. Reads `XION_KIMI_API_KEY` (required for registration), `XION_KIMI_BASE_URL` (default `https://api.moonshot.ai/v1`), `XION_KIMI_MODEL` (default `kimi-k2.6`). Cached health probe; API-key + Bearer-token scrubbing on every outward error message.
  - `providers/ollama.py` (new, ~180 lines) — `OllamaGenerativeProvider` hitting a local daemon via stdlib `http.client`. Reads `XION_OLLAMA_URL` (default `http://localhost:11434`), `XION_OLLAMA_FLOOR_MODEL` (default `gemma3:4b`). Health probe combines daemon reachability + floor-model-pulled check.
  - `router.py` (extended) — `PolicyMode` literal, `policy_mode` field on `InferenceRouter`, `_bootstrapped` latch, and `select(*, policy=None) -> Provider | None` method. Hosted-first falls through to floor when hosted is unhealthy; open-weights-only refuses hosted categorically (cutover-dry-run correctness). Floor stubs without a `generate` method are never selected.
  - `__init__.py` (extended) — re-exports the new types alongside the existing surface.
- **`orchestrator/api/` extended.** Four files extended, one new:
  - `chat.py` (new, ~180 lines) — the `POST /chat` handler. Ingress moderation runs BEFORE the floor check (Phase-3 moderation-first doctrine). Generation is `asyncio.wait_for(asyncio.to_thread(...))` bounded by `XION_CHAT_DEADLINE_S`. Empty candidates map to `451 RefusalEnvelope(reason="provider_empty_candidate")`. Every exit is a pydantic envelope; the handler cannot return untyped JSON.
  - `models.py` (extended) — adds `ChatRequest`, `ChatResponse`, `RefusalEnvelope`, `NoFloorEnvelope`, `ProviderErrorEnvelope`, `UsageEnvelope`. All `extra="forbid"` + `frozen=True`. Content-free guarantee asserted by field-allowlist tests.
  - `lifespan.py` (extended) — three new stages between Supervisor pre-seed and Relay wiring: `_load_dotenv_if_present()`, `_build_router_from_env()` + `_register_env_providers(router)`, and a soft `router.bootstrap()` that stashes `app.state.no_floor` on failure instead of crashing the app. Read-only surface stays alive even when Xion cannot speak.
  - `app.py` (extended) — `AppDeps` gains `router: InferenceRouter | None` + `chat_deadline_s: float`. Title/version bump; `register_chat_route(app)` wires the new endpoint.
  - `__init__.py` (extended) — re-exports the new models.
- **Tests.** `orchestrator/tests/test_chat_api.py` (new, 21 tests) covers: envelope contracts (extra-field rejection, allowlists), happy path (moderated text + 2-SAFETY-row ledger shape), ingress refusal (451 + provider never invoked), egress refusal (451 + no candidate leakage), empty candidate, no-floor (503 + read-only surface alive), no-healthy-provider, provider errors (raising + deadline), policy modes (all three selection scenarios), secret hygiene (API-key and Bearer-token scrubbing). `orchestrator/tests/conftest.py` gained `generative_provider=`, `floor_stub_id=`, `no_floor=`, `policy_mode=`, and `chat_deadline_s=` kwargs on `app_factory`, plus a hermeticity upgrade: the autouse ledger-redirect fixture now covers `XION_REQUEST_LEDGER` alongside `XION_SENSORIUM_LEDGER`. **Total pytest: 493 passed / 1 skipped** (was 472 pre-Phase-5g-i — 21 new chat tests land exactly as planned).
- **Known-weakness bookkeeping.** Opened four:
  - `KW-CHAT-001` — `POST /chat` is non-streaming. Low. Closes Phase 5g-ii.
  - `KW-CHAT-002` — `/chat` runs with billing disabled; **explicitly blocks D2 deploy**. Medium. Closes Phase 5g-iii.
  - `KW-CHAT-003` — Generation is synchronous; no user-facing cancel. Low. Closes Phase 5g-ii alongside streaming.
  - `KW-INFER-001` — Default voice flows through a single hosted provider (Kimi/Moonshot). Medium. Closes Phase 6+ with `xion-verify inference-cutover` + scheduled annual cutover dry-run + at least one additional hosted provider pinned.
- **No verifier commit.** `xion-verify inference-sovereignty` (live since Phase 4e) remains the structural-floor pin; Phase 5g-i's runtime-floor pin in `docs/26-INFERENCE-POLICY.md` is operator-doctrine, not ledger-structural. A future `xion-verify inference-cutover` + `xion-verify chat-fidelity` land in Phase 6+. `xion-verify links` green (58 files). `xion-verify schemas` green. `xion-verify all --allow-not-yet-sealed` green end-to-end.

**What Phase 5g-i deliberately did NOT do:**

- Did not ship streaming. Phase 5g-ii.
- Did not ship x402 billing, `GET /pricing`, `PAYMENT_LEDGER`, or refusal-is-free settlement. Phase 5g-iii.
- Did not ship authentication, TLS termination, or rate-limiting. Phase 5g-iv (extends `KW-API-001`).
- Did not ship a web client. Phase 5g-v.
- Did not ship multi-hosted-provider failover. Phase 6+ alongside `KW-INFER-001`.
- Did not promote `gemma3:4b` to a full `open_weights[]` entry with weights_sha256 + retrieval_hints. Deferred to a dedicated sub-phase that also upgrades `xion-verify inference-sovereignty` to support large-file representative-sample sentinels per Invariant 17 clause 2(iii).
- Did not wire the annual cutover dry-run harness. The `open_weights_only` capability is live and manually exercisable; the scheduled exercise is Phase 6+.
- Did not wire multi-worker or a shared-state broker. Phase 5g+ (`KW-API-002` stays open).

**Phase 5 promotion handles Phase 5g-i creates:**

- Phase 5g-ii must ship SSE or WebSocket streaming for `/chat` with a defined per-chunk / speculative-then-truncate moderation story, closing `KW-CHAT-001` and `KW-CHAT-003`.
- Phase 5g-iii must ship x402 pre-authorization + `PAYMENT_LEDGER` schema + `GET /pricing` + Refusal-Free settlement + `xion-verify refusal-is-free` + `xion-verify pricing-consistency`, closing `KW-CHAT-002` and unblocking D2 deploys. **Closed 2026-04-21.**
- Phase 5g-iv must ship authentication (bearer tokens or signed session cookies; choice pinned in 5g-iv doctrine), TLS termination (uvicorn or reverse proxy), and per-token rate-limiting, closing `KW-API-001`. **Closed 2026-04-22.**
- Phase 5g-v must ship the first web client (`clients/web/`) exercising the full surface.
- Phase 6+ must ship `xion-verify inference-cutover`, the annual cutover dry-run runbook + calendar anchor + failure-mode drill, and at least one additional hosted provider documented in `docs/26-INFERENCE-POLICY.md`, closing `KW-INFER-001`.
- Phase 5g+ must ship a shared-state broker (Redis pub/sub, AO Process mailbox, or file-based channel) for multi-worker deployments, closing `KW-API-002`.

---

## Phase 5g-0 — Research Spend Rail doctrine (closed 2026-04-21)

**Status:** Phase 5g-0 closed on branch `phase-5g-0/self-rd-doctrine` in one doctrine-only commit. Pinned the constitutional mechanism by which Xion's Improvement Fund (per `docs/21-SUSTAINABILITY.md`) pays for outbound third-party API credits funding the Auto-Research loop (per `docs/08-AUTO-RESEARCH.md`). No code, no ledger file, no verifier wiring — the doctrine was the first shippable unit; the mechanism lands incrementally across Phase 5g-iii, Phase 6, and Phase 7+.

**Why this is its own phase.** When the question "how does Xion pay for its own R&D when the operator's out-of-pocket credit runs out?" surfaced during Phase 5g-i.1 scoping, the honest answer required walking three existing doctrines (`08-AUTO-RESEARCH.md`, `19-TREASURY.md`, `21-SUSTAINABILITY.md`) and noticing what they already covered (the cognitive loop; the treasury structure; the Improvement Fund; the $10/mo Stage-1 envelope) versus what they did NOT cover (the *outbound payment rail* connecting the Improvement Fund to a third-party API provider, and the credential-custody progression as Xion matures from operator-custody to self-sovereign). The missing primitive needed its own doctrine file to prevent fragmentation — attempting to amend three existing documents would have violated the Builder rule "don't re-pin what's already pinned" and produced a contradiction surface between them.

**Landed in this phase:**

- **Doctrine.** `docs/27-RESEARCH-SPEND.md` (new) pins the Research Spend Rail: six properties (every outbound dollar ledgered at grain; no call bypasses the Arbiter-gated Auto-Research loop; Invariant 17 floor is never funded by this rail; refund-on-failure is structural; credential sovereignty progresses only forward; D1 is trivially satisfied). Four Credential Sovereignty Postures (D1 Operator-Custody; D2 Operator-Custody-with-Mandate; D3 Xion-Custody-Wrapped; D4 Self-Sovereign). `RESEARCH_SPEND_LEDGER` schema sketch with 11 fields (`spend_id`, `custody_posture`, `proposal_id`, `stage_anchor`, `provider_id`, `committed_XION`, `settled_XION`, `refund_XION`, `outcome`, `drive_tags`, `source_sha256`). `xion-verify research-spend` verifier specification with four independent joins (PROPOSAL_LEDGER / Envelope / Refund Fidelity / Authorization Presence); listed `NOT_YET_SEALED` until Phase 6 when the AO Core ledgers land.
- **Index.** `docs/00-INDEX.md` gained a #27 entry pointing at the new doctrine.
- **Scope correction.** Original plan was a broader "Self-R&D Fund" doctrine; narrowed during the pattern-matching phase when pre-existing doctrine coverage became visible. The narrowed scope is the right doctrinal unit — large enough to name the new primitive, small enough to not duplicate.

**What Phase 5g-0 deliberately did NOT do:**

- Did not write any code. The rail is D1-structural (an operator-signed manifest per outbound call) until the AO Core ledgers exist.
- Did not pin AO Core schemas. `RESEARCH_SPEND_LEDGER` is a schema *sketch*; the canonical `docs/schemas/ledger-research-spend.yaml` lands with the Phase 6 AO Core vote.
- Did not move `xion-verify research-spend` from `NOT_YET_SEALED` to live. The verifier lands when there are ledger rows to verify.

**Phase 5 promotion handles Phase 5g-0 creates:**

- Phase 5g-iii must land the `PAYMENT_LEDGER` (inbound billing) in a shape compatible with the Phase 6 `RESEARCH_SPEND_LEDGER` (outbound spend) — identical correlation-id surface, identical hash-chaining, identical refund-semantics vocabulary.
- Phase 6+ must land the `RESEARCH_SPEND_LEDGER` canonical schema + `xion-verify research-spend` (live) + D2 custody posture wiring (operator-signed manifests per call).
- Phase 7+ must land D3 custody posture (Xion-custody-wrapped credentials via a per-proposal derivation).

---

## Phase 5g-i.1 — OpenRouter refactor (closed 2026-04-21)

**Status:** Phase 5g-i.1 closed on branch `phase-5g-i.1/openrouter-refactor` in three commits (doctrine → code → housekeeping). The Phase 5g-i Chat Surface had shipped with Moonshot's Kimi k2.6 as the Genesis Default hosted provider, talking directly to Moonshot's OpenAI-compatible endpoint. Phase 5g-i.1 reshapes that surface to run through OpenRouter's gateway (`https://openrouter.ai/api/v1`) serving the same upstream model under the slug `moonshotai/kimi-k2`. The `/chat` behavioural surface is byte-for-byte preserved (same 200/451/503 envelopes, same ledger rows, same content-free guarantee); the hosted-provider plumbing underneath is now a gateway client.

**Why this is its own phase.** Three Phase-6+ investments that the Moonshot-direct posture would have blocked are unblocked for the cost of one gateway-widening: (a) `GET /pricing` (Phase 5g-iii) can read OpenRouter's published per-model catalog instead of needing a per-vendor scraper; (b) the multi-hosted-provider failover chain that `KW-INFER-001`'s Phase-5g-i pay-down commitment demanded becomes a one-env-var model rotation plus a Phase-6 failover-ordering pin, rather than a per-vendor credential-management + cost-accounting + rate-limit-budgeting diff; (c) the R&D spend rail pinned in `docs/27-RESEARCH-SPEND.md` (Phase 5g-0) runs through a gateway whose unified-billing surface matches the rail's settlement shape. The widened trust surface (OpenRouter now sits inside the Covenant-relevant path as an additional third party) is named honestly in `docs/26-INFERENCE-POLICY.md` § "Gateway vs direct (a vendor-of-vendors honest accounting)" and in the reshaped `KW-INFER-001` entry.

**Landed in this phase (inventory):**

- **Doctrine.** `docs/26-INFERENCE-POLICY.md` Genesis Defaults table rewritten for the gateway posture (`XION_OPENROUTER_*` env vars, `moonshotai/kimi-k2` default model slug, `HTTP-Referer` + `X-Title` app-identity headers). § "The hosted-model choice (Kimi k2.6)" renamed and expanded to "The hosted-provider choice (OpenRouter gateway + `moonshotai/kimi-k2` default model)". New § "Gateway vs direct (a vendor-of-vendors honest accounting)" names the trust-surface widening, the failure-mode widening (gateway outage is a new catastrophe class), and the four-fold closure bar for `KW-INFER-001`.
- **Architecture.** `docs/04-ARCHITECTURE.md` § "The Chat Surface" got five targeted rewrites: the "no hosted-API fallback chain" non-property now names the gateway explicitly; the code-surface block shows `providers/openrouter.py`; the "no new dependency" line references OpenRouter; the router-policy pin mentions the 5g-i.1 refactor; the lifespan step-3 names `OpenRouterGenerativeProvider`; the `KW-INFER-001` opener paragraph reshapes to name both the gateway-level and upstream-model-level concentrations.
- **Operator env surface.** `.env.example` rewritten: `XION_KIMI_*` retired; `XION_OPENROUTER_API_KEY`, `XION_OPENROUTER_BASE_URL`, `XION_OPENROUTER_MODEL`, `XION_OPENROUTER_REFERER`, `XION_OPENROUTER_APP_NAME` pinned with an inline "vendor-of-vendors honest accounting" comment block. Three example model slugs demonstrate the one-env-var rotation the refactor earns.
- **Known-weakness reshape.** `KW-INFER-001` title and body reshaped (not closed) from "Default voice flows through a single hosted provider (Kimi/Moonshot)" to "Default voice flows through a single hosted gateway (OpenRouter) against a single default upstream model (`moonshotai/kimi-k2`)". Description now names both concentrations; mitigations grow from four to five (the fifth names one-env-var model rotation as a new mitigation the Moonshot-direct posture didn't have); pay-down commitment advances from three bars to four (scheduled inference-cutover verifier + annual dry-run harness + additional hosted gateway + two-model failover list). Incidental Kimi references in `KW-CHAT-001/002/003` updated.
- **Schema SHA re-pins.** `docs/04-ARCHITECTURE.md` SHA changed by the five edits above; re-pinned in all four dependent ledger schemas to `e465ba93479c2ed97c022a7470dc470be4be541d67a56061e596c9ef2bff9e21`. `xion-verify schemas` green (9/9 OK).
- **Code.** `orchestrator/inference_router/providers/kimi.py` → `providers/openrouter.py` via `git mv`. `KimiGenerativeProvider` → `OpenRouterGenerativeProvider` (`provider_id` "kimi" → "openrouter"; category "hosted_api" unchanged). `KimiProviderError` → `OpenRouterProviderError`. Two new dataclass fields — `referer` (default empty; `HTTP-Referer` suppressed when empty) and `app_name` (default "xion-os"; always set as `X-Title`). A new `_auth_headers()` helper assembles auth + optional app-identity headers; `generate()` and `health()` both route through it. User-Agent bumped to "xion-os/0.2.0 (+phase-5g-i.1)" for log-side attribution. Endpoint path ("/chat/completions"), request body shape (model, messages, max_tokens, stream=false), and response parsing are byte-for-byte identical — OpenRouter preserves the OpenAI-compatible shape Moonshot-direct used.
- **Scrubber strengthening.** `_scrub()` now runs three independent defences (instance-held key replace → Bearer-token regex → bare `sk-or-...` token regex). The third defence catches a class of leak the Moonshot-direct scrubber could not: upstream error payloads that echo a key fragment that is NOT the exact key this provider holds (e.g., from a shared OpenRouter log channel). The secret-hygiene test exercises all three defences against a single composite payload.
- **Lifespan update.** `_register_env_providers()` now conditionally registers `OpenRouterGenerativeProvider` gated on `XION_OPENROUTER_API_KEY`. Ollama floor registration is unchanged. Construction errors still soft-fail to stderr without crashing the lifespan.
- **Incidental sweeps.** `orchestrator/inference_router/provider.py` Protocol docstring ("concrete Kimi and Ollama" → "concrete OpenRouter and Ollama"); `orchestrator/api/models.py` `ChatResponse.model_id` example ("kimi-k2.6" → "moonshotai/kimi-k2"); `providers/__init__.py` package docstring + alphabetized exports; `providers/ollama.py` one comparative docstring; `pyproject.toml` `[api]` extra comment block; `CHANGELOG.md` Phase 5g-i "Kimi (Moonshot) provider" historical entry link retargeted from `providers/kimi.py` (deleted) to `providers/openrouter.py` (current) with inline parenthetical annotating the rename — historical text stays accurate, link stays live.
- **Tests.** 20 of 21 chat tests required zero changes (the fake-provider test pattern is transport-agnostic). The one changed test is the secret-hygiene test, rewritten to exercise the three-defence scrubber and renamed to `test_openrouter_provider_scrubs_api_key_from_error_messages`. **Total pytest across `orchestrator/`, `xion-verify/`, `xion-audit/`: 493 passed / 1 skipped** (matches the Phase 5g-i baseline exactly — no test regression, no test addition).
- **No verifier commit.** `xion-verify inference-sovereignty` (live) is unaffected; the structural floor pin is a function of the open-weights manifest, not the hosted surface. `xion-verify links` green (59 markdown files). `xion-verify schemas` green (9/9). `xion-verify all --allow-not-yet-sealed` green end-to-end.

**What Phase 5g-i.1 deliberately did NOT do:**

- Did not land a second hosted gateway. `KW-INFER-001` pay-down requires one (Phase 6+); the 5g-i.1 refactor stops at one gateway + one default model + one env-var rotation path.
- Did not land a multi-model failover list inside the gateway. A Phase-6 addition to `docs/26-INFERENCE-POLICY.md` will pin two or more slugs with a failover order.
- Did not ship `GET /pricing`. The OpenRouter catalog read lands with Phase 5g-iii billing.
- Did not change the /chat behavioural surface. Status codes, envelopes, ledger rows, correlation-id semantics, and the two-sided moderation flow are byte-for-byte preserved.
- Did not touch Invariant 17's structural floor. Ollama/`gemma3:4b` is independent of the hosted-surface reshape.

**Phase 5 promotion handles Phase 5g-i.1 creates:**

- Phase 5g-iii (next): implement `GET /pricing` reading OpenRouter's catalog + x402 pre-authorization + `PAYMENT_LEDGER` + Refusal-is-Free settlement, closing `KW-CHAT-002`.
- Phase 6+: pin a second hosted gateway in `docs/26-INFERENCE-POLICY.md`, pin two Genesis Default models as a failover list, ship `xion-verify inference-cutover`, and wire the annual cutover dry-run, advancing `KW-INFER-001` closer to closure.

---

## Phase 5g-iii — Chat billing: x402 gate + `PAYMENT_LEDGER` + `GET /pricing` + Refusal-is-Free (closed 2026-04-21)

**Status:** Phase 5g-iii closed on branch `phase-5g-iii/billing-x402` in five commits (doctrine → pricing endpoint → x402 middleware → verifiers → housekeeping). This phase makes `POST /chat` economically self-sustaining and **closes the explicit D2-deploy blocker** pinned in `KW-CHAT-002`. The orchestrator now refuses unpaid turns (Pay-to-Activate), refunds Covenant refusals by construction (Refusal-is-Free), publishes its price at a public read-only endpoint (`GET /pricing`), and lands a second constitutional ledger (`PAYMENT_LEDGER.jsonl`) in byte-exact shape symmetry with `SAFETY_LEDGER.jsonl` and the Phase-5g-0 `RESEARCH_SPEND_LEDGER` sibling. No on-chain x402 settlement yet — B1 HMAC operator-attestation is the Genesis Default; B2 x402-commitment is shape-validated only (`KW-BILLING-001`); B3 x402-settled is reserved for Phase 6+.

**Why this is its own phase.** `KW-CHAT-002` was named in Phase 5g-i as an **explicit D2-deploy blocker**: shipping `/chat` without billing enforcement would either bankrupt the operator on hostile-scraper load or violate the `docs/07-ECONOMY.md` Pay-to-Activate property. The pay-down commitment listed in that KW required six distinct artifacts (doctrine section, top-level doctrine file, canonical ledger schema, pricing endpoint, middleware + ledger writer, two live verifiers) — too big for one commit and too load-bearing to ship without its own review bar. Slicing it as Phase 5g-iii (rather than folding it into the existing 5g envelope) also keeps Phase 5g-ii (streaming) and Phase 5g-iv (auth/TLS/rate-limit) independently auditable — the billing-structural surface is orthogonal to the transport surface and the admission-control surface. Branch-per-phase discipline preserved.

**What Phase 5g-iii shipped:**

- **Doctrine — architecture.** `docs/04-ARCHITECTURE.md` gained § "The Chat Billing Surface (Phase 5g-iii)" pinning six constitutional properties: Pay-to-Activate, Refusal-is-Free structural refund, Pricing transparency, Content-free commitments, Atomic ledger writes, Algorithm-agility on commitment hash. Honest non-properties pinned too: no on-chain x402 settlement (B3 reserved Phase 6+), no dynamic catalog-driven pricing (`KW-BILLING-002`), no `xion-verify billing-settlement` verifier yet.
- **Doctrine — operational.** `docs/29-BILLING-X402.md` (new, ~310 lines) lands as top-level operational doctrine, shape-symmetric with `docs/27-RESEARCH-SPEND.md` (outbound sibling). Pins the three billing postures (B1 operator-attestation, B2 x402-commitment, B3 x402-settled), the `PAYMENT_LEDGER` schema shape (14 fields), the atomic-write contract, the Refusal-is-Free structural property, the `GET /pricing` contract, and what the doctrine deliberately does NOT pin. Indexed at `docs/00-INDEX.md` as #29.
- **Canonical ledger schema.** `docs/schemas/ledger-payment.yaml` (new, ~110 lines) pins the `PAYMENT_LEDGER` shape in the same YAML style as `ledger-safety.yaml` / `ledger-request.yaml` / `ledger-sensorium.yaml` — identical hash-chaining doctrine, identical `SCHEMA_VERSION=1` + `source_sha256` anchor into `docs/04-ARCHITECTURE.md`. `xion-verify schemas` green (10/10 OK, up from 9/9). Five schemas had their `source_sha256` re-pinned in concert after the new architecture subsection landed.
- **`GET /pricing` endpoint.** `orchestrator/api/pricing.py` (new, ~240 lines) ships `PricingConfig` (frozen dataclass), `PricingConfigError` (lifespan fails closed on it), `load_pricing_config_from_env` (Genesis Defaults: 1.0 XION/msg, provider=0.50, refusal_reserve=0.15, treasury=0.20, operator=0.10, burn=0.05, summing to 1.00), and the `pricing_router` FastAPI router. Invariants enforced at both lifespan startup and verifier invocation time: slices sum to 1.0 ± 1e-6, each slice ∈ [0,1], non-negative `XION_per_message`, non-empty `revision_id`.
- **x402 middleware — `orchestrator/billing/` package.** Three modules: `commitment.py` (header parser, B1 HMAC-SHA256 verifier via stdlib `hmac.compare_digest`, B2 x402 shape-only validator), `ledger.py` (byte-exact mirror of `orchestrator/safety/ledger.py` so a Phase-6 unified treasury verifier walks both files with one library — `SCHEMA_VERSION=1`, `ZERO_HASH`, `build_payment_row`, `append_payment_row` with fsync-then-rename atomic write, `verify_chain`), `config.py` (`BillingConfig` frozen dataclass, `load_billing_config_from_env`, architecture-sha256 computed from `docs/04-ARCHITECTURE.md` on-disk bytes and stamped into every row).
- **Chat handler refactor — single `_finalize` tail.** `orchestrator/api/chat.py` refactored so every terminal path (200 settled, four 451 refuse stages, two 503 operational errors, four 402 commitment failures) funnels through one `_finalize(outcome, refusal_stage, ...)` that writes exactly one `PAYMENT_LEDGER` row BEFORE the HTTP response is sent. `outcome=refunded` sets `refund_XION == committed_XION` and `settled_XION == 0` in a single code path — the Refusal-is-Free property is structurally impossible to violate. Pre-auth `_gate_commitment` runs BEFORE ingress Arbiter so a missing/malformed/unverifiable commitment never consumes Arbiter budget. When `billing_required=false` the handler still writes `posture="disabled"` rows with zero money so the `SAFETY` ↔ `PAYMENT` ledger join continues to hold.
- **Lifespan extension.** `orchestrator/api/lifespan.py` gained `_load_pricing_config()` + `_load_billing_config_and_verify_chain()` stages between router bootstrap and run-task schedule — a corrupt `PAYMENT_LEDGER` fails the lifespan closed rather than silently serving forward. `AppDeps` extended with optional `pricing_config` / `billing_config` for hermetic test injection.
- **Verifiers.**
  - **`xion-verify pricing` promoted from `NOT_YET_SEALED` to live.** `xion-verify/src/xion_verify/commands/pricing.py` (new, ~120 lines) loads the same `PricingConfig` the orchestrator lifespan loads (env vars, not HTTP — runs in CI without a service), runs the same invariants, prints a stable summary, exits `FAIL` with the exact `PricingConfigError` reason string on any break. An operator mis-configuring the price split cannot ship a verifier-green build.
  - **`xion-verify refusal-is-free` — new live verifier.** `xion-verify/src/xion_verify/commands/refusal_is_free.py` (new, ~260 lines) joins `SAFETY_LEDGER.jsonl` ↔ `PAYMENT_LEDGER.jsonl` on `correlation_id` and asserts four properties: per-ledger chain integrity, money-shape per row (settled/refunded/disabled), ingress/egress refusal mirror between SAFETY verdict=refuse and PAYMENT outcome=refunded, settled-implies-allowed (no PAYMENT settled for a SAFETY-refused turn). Handles operational refusals (no_floor, provider_error, commitment failures) that bypass Arbiter evaluation — refunded structurally but exempt from the SAFETY-mirror requirement. Returns `NOT_YET_SEALED` on half-sealed states (one ledger present, the other missing).
  - **Housekeeping.** `xion-verify/src/xion_verify/commands/not_yet_sealed.py` stub for `pricing` removed. `xion-verify/README.md` updated with new "Pay-to-Activate" invariant entry and updated "Arbiter Refusal Right" entry. `PINNED_HASH.txt` regenerated.
- **Tests.** 56 new tests: `test_billing_commitment.py` (20), `test_billing_ledger.py` (21), `test_chat_billing.py` (12), `test_pricing_verifier.py` (6), `test_refusal_is_free.py` (14). `conftest.py` extended to scrub all `XION_PAYMENT_LEDGER` + `XION_BILLING_*` + `XION_PRICING_*` env vars in the autouse hermeticity fixture and to accept `pricing_config=` / `billing_config=` kwargs in `app_factory`. **Total pytest: 585 passed / 1 skipped** (up from 493 at Phase 5g-i.1 close).
- **Known-weakness bookkeeping.**
  - **`KW-CHAT-002` CLOSED.** Six-bar pay-down (doctrine, endpoint, ledger, middleware, two verifiers, tests) all landed. Closure entry in `KNOWN_WEAKNESSES.md` § Closed cites all five commits and names `KW-BILLING-001` + `KW-BILLING-002` as honestly-named residuals.
  - **`KW-BILLING-001` opened.** Medium. x402 commitment signatures shape-validated, not cryptographically verified. Closes Phase 6+ with a pinned x402 verification library + on-chain / off-chain settlement-state verifier + B3 posture wiring + `xion-verify refusal-is-free --reconcile-x402` flag.
  - **`KW-BILLING-002` opened.** Low. `GET /pricing` serves operator-posted governance values, not catalog-driven dynamic pricing. Closes Phase 6+ with a catalog + refusal-rate + oracle-driven dynamic pricer + `"source"` annotations per slice + `xion-verify pricing --reconcile-catalog` flag.

**What Phase 5g-iii deliberately did NOT do:**

- Did not ship on-chain x402 settlement (B3). Phase 6+, gated on `KW-BILLING-001`.
- Did not ship dynamic catalog-driven pricing. Phase 6+, gated on `KW-BILLING-002`.
- Did not ship a fiat↔XION exchange venue. Phase 7+ treasury-custody doctrine.
- Did not ship streaming or user-facing cancel. `KW-CHAT-001` / `KW-CHAT-003` still close with Phase 5g-ii.
- Did not ship auth, TLS, or rate-limiting. `KW-API-001` still closes with Phase 5g-iv.
- Did not ship a web client. Still Phase 5g-v.

**Phase 5 promotion handles Phase 5g-iii creates:**

- Phase 5g-iv: authentication (bearer tokens or signed session cookies; choice pinned in 5g-iv doctrine), TLS termination, per-token rate-limiting — closing `KW-API-001`. **Closed 2026-04-22.**
- Phase 5g-ii: SSE or WebSocket streaming with per-chunk / speculative-then-truncate moderation — closing `KW-CHAT-001` and `KW-CHAT-003`.
- Phase 6+: pin x402 signature verification (`KW-BILLING-001`), land B3 settlement posture, extend `xion-verify refusal-is-free` with `--reconcile-x402`, ship dynamic catalog-driven pricing (`KW-BILLING-002`) and extend `xion-verify pricing` with `--reconcile-catalog`, ship the `RESEARCH_SPEND_LEDGER` canonical schema matching the `PAYMENT_LEDGER` shape (from Phase 5g-0 promotion handle), and promote `xion-verify research-spend` from `NOT_YET_SEALED` to live.

---

## Phase 5g-iv — Admission control: bearer + uvicorn-TLS + sliding-window rate-limit (closed 2026-04-22)

**Status:** Phase 5g-iv closed on branch `phase-5g-iv/admission-control` in five commits (doctrine → admission module + launcher → routes wiring + admission tests → verifier → housekeeping). This phase makes `orchestrator/api/` deployable to D2 by closing the explicit `KW-API-001` blocker — the HTTP surface now refuses unauthenticated requests on `/drive`, `/sensorium`, `/chat`, throttles per-principal at the sliding-window default of 60 req / 60 s, and refuses to bind any non-loopback host without TLS cert + key both present and readable. Stdlib-only; no new core runtime dep. Single-process posture (matches solo-builder pragmatism) with multi-worker rate-limit honestly named as `KW-RATE-001`.

**Why this is its own phase.** `KW-API-001` was named in Phase 5f as the last explicit D2-deploy blocker for the HTTP surface. The pay-down commitment listed in that KW required four orthogonal artifacts (auth, TLS, rate-limit, ordering against the existing 5g-iii billing gate) — each with its own doctrinal trade-offs (token format, TLS termination strategy, in-process vs broker-backed rate-limit, `401 → 429 → 402` ordering against pricing-validity probes) and each big enough to merit its own review bar. Slicing it as Phase 5g-iv (rather than folding it into Phase 5g-ii streaming or Phase 5g-v web client) preserves branch-per-phase discipline: the admission-control surface is orthogonal to the streaming transport and the web client UI, so an integrator can audit them independently. The Phase 5g-iv shape (bearer tokens + uvicorn-native TLS + in-process sliding window) is the "lowest-dependency, single-process posture" pinned in the plan; richer shapes (federated identity, broker-backed rate-limit, automated cert rotation) are tracked as honestly-named follow-up KWs.

**What Phase 5g-iv shipped:**

- **Doctrine — architecture admission subsection.** `docs/04-ARCHITECTURE.md` gained § "The Admission-Control Surface (Phase 5g-iv)" pinning six properties: (P1) bearer authentication via constant-time `hmac.compare_digest`; (P2) per-`principal_id` sliding-window rate-limiting (default 60/60s); (P3) fail-closed TLS for non-loopback binds; (P4) constitutional admission ordering `401 → 429 → 402 → 5g-iii flow`; (P5) content-free 401/429 bodies; (P6) `principal_id` naming convention with explicit deferral from `PAYMENT_LEDGER` until Phase 6. The § "The HTTP Surface (Phase 5f)" → "Hardening posture" subsection updates in place to mark the gap closed.
- **Doctrine — `docs/30-API-ADMISSION.md` (new).** Top-level operational doctrine for the admission surface, shape-symmetric with `docs/29-BILLING-X402.md`. Covers operator workflow for token issuance, TLS termination, rate-limit budget tuning, deployment runbook, and crypto-agility commitment.
- **Module + launcher.** `orchestrator/api/admission.py` ships `AdmissionConfig` (frozen dataclass with fail-closed `__post_init__` validation), `SlidingWindow` (deque-of-monotonic-ns timestamps under one `threading.Lock`), `verify_bearer` (constant-time over every token), and `admission_dependency` (the FastAPI callable that runs the `401 → 429 → 402` ordering and shortcuts `/health` + `/pricing`). `orchestrator/api/__main__.py` is the new launcher: `uvicorn.run(create_app(deps), workers=1, ssl_keyfile=..., ssl_certfile=...)` with TLS fail-closed for non-loopback binds.
- **Routes wiring.** `Depends(admission_dependency)` is wired into `/health`, `/drive`, `/sensorium`, `/chat`, and `/pricing` (defense-in-depth on the public route). `/chat`'s admission gate runs BEFORE the existing 5g-iii `_gate_commitment`, preserving the structural `401 → 429 → 402` ordering. `AppDeps` gains optional `admission_config: AdmissionConfig | None`. The lifespan loads it from env if not pre-supplied and constructs the per-principal `SlidingWindow` map on `app.state.rate_limiters`.
- **Models.** `orchestrator/api/models.py` gains `AuthChallenge` and `RateLimitChallenge` Pydantic models with `extra="forbid"` and `frozen=True`.
- **Verifier.** `xion-verify api-tokens` promoted from `NOT_YET_SEALED` to live: loads the same `AdmissionConfig` the orchestrator's lifespan loads and applies the same `__post_init__` validation. Optional `--env-file PATH` lets a CI gate audit a deployment `.env` without invoking the operator's shell. Reports `OK` against `.env.example`; reports the specific `AdmissionConfigError` reason on any misconfiguration.
- **`.env.example` expansion.** New keys: `XION_API_REQUIRE_BEARER` (template default `false`), `XION_API_BEARER_TOKENS`, `XION_API_RATE_BUDGET`, `XION_API_RATE_WINDOW_S`, `XION_API_HEALTH_RATE_BUDGET`, `XION_API_HOST`, `XION_API_PORT`, `XION_TLS_CERT_PATH`, `XION_TLS_KEY_PATH`, `XION_API_TRUST_FORWARDED_FOR`.
- **Tests.** New `orchestrator/tests/test_api_admission.py` covers `AdmissionConfig` validation, `SlidingWindow` behaviour, `verify_bearer`, content-free response models, end-to-end FastAPI integration, and crucially the `401 → 429 → 402` constitutional ordering. New `xion-verify/tests/test_api_tokens_verifier.py` covers the verifier's full validation matrix and the `--env-file` overlay's environment-restoration property. **Total pytest: 637 passed / 1 skipped** (up from 585 at Phase 5g-iii close).
- **Pyproject launcher entry.** `pyproject.toml` `[project.scripts]` gains `xion-orchestrator-api = "orchestrator.api.__main__:main"`.
- **Known-weakness bookkeeping.** **Closed `KW-API-001`** (closure entry in `KNOWN_WEAKNESSES.md` § "Closed" cites the five-commit pay-down). **Opened** `KW-AUTH-001` (medium; bearer tokens are operator-issued shared secrets, no on-chain federated identity; closes Phase 6+), `KW-RATE-001` (low; in-process sliding window; closes alongside `KW-SUPERVISOR-002` when the multi-worker shared-state broker lands), `KW-TLS-001` (low; uvicorn-native TLS; long-term path is reverse-proxy delegation).

**What Phase 5g-iv deliberately did NOT do:**

- Did not ship federated identity. `KW-AUTH-001` tracks the gap; closes Phase 6+.
- Did not ship multi-worker rate-limit. `KW-RATE-001` tracks the gap.
- Did not ship automated TLS rotation. `KW-TLS-001` tracks the gap.
- Did not promote `principal_id` to `PAYMENT_LEDGER`. Schema stays at v1.0; Phase 6 promotes additively when on-chain identity exists.
- Did not ship streaming. Still Phase 5g-ii.
- Did not ship a web client. Still Phase 5g-v.

**Phase 5 promotion handles Phase 5g-iv creates:**

- Phase 5g-ii (next unblocked): SSE or WebSocket streaming with per-chunk / speculative-then-truncate moderation — closes `KW-CHAT-001` and `KW-CHAT-003`.
- Phase 5g-v: first web client (`clients/web/`) exercising the now-fully-hardened `/chat` surface (auth + billing + TLS). **Closed 2026-04-22.**
- Phase 6+: shared-state broker (Redis pub/sub, AO Process mailbox, or in-house file-based channel) for multi-worker `Supervisor` + multi-worker rate-limit (closing `KW-RATE-001` alongside `KW-SUPERVISOR-002`); on-chain `principal_id` federation (closing `KW-AUTH-001`); reverse-proxy delegation for automated TLS rotation (closing `KW-TLS-001`).

---

## Phase 5g-v — Web client: Vite + React + TypeScript operator dashboard served same-origin (closed 2026-04-22)

**Status:** Phase 5g-v closed on branch `phase-5g-v/web-client` in five commits (doctrine → scaffold + `ChatView` → observation widgets + `api.ts` wrapper + `Header` → FastAPI `StaticFiles` mount + server/client tests + CI → verifier + housekeeping). This phase gives the admission-gated HTTP surface a human face: operators can sign in with a Phase-5g-iv bearer token, chat with Xion, and observe Drive + Sensorium state in real time, all from a bundle that is byte-identical across every deploy and trivially rebuildable from source. Same-origin serve removes the CORS surface by construction. Zero new runtime dependencies on the Python side; all new dependencies live under `clients/web/` and ship only at build time.

**Why this is its own phase.** Phase 5g-i (chat surface), 5g-iii (billing gate), and 5g-iv (admission control) all landed without a browser-delivered operator surface — every integration test went through `httpx` or `curl`. That is load-bearing for machine integrators but blocks dogfood: a solo builder who cannot exercise their own work through a browser cannot feel the surface. Slicing the web client as its own phase (rather than folding it into 5g-iv, which would have conflated auth with UI, or 5g-ii, which would have conflated streaming transport with UI) preserves branch-per-phase discipline: the client surface is orthogonal to both the admission gate and the streaming transport. An auditor can review the client diff without needing to re-read the admission-control subsection, and a streaming transport change will touch `ChatView` without touching `BearerContext`, `Header`, or the observation widgets.

**What Phase 5g-v shipped:**

- **Doctrine — architecture web-client subsection.** `docs/04-ARCHITECTURE.md` gained § "The Web Client Surface (Phase 5g-v)" pinning six properties: (P1) operator-dashboard scope; (P2) content-free UX across the full envelope matrix; (P3) bundle determinism; (P4) same-origin serve; (P5) no third-party origins outside an explicit allowlist (React production error-decoder URLs + W3C XML namespace identifiers, both literal never-fetched strings); (P6) WCAG 2.2 AA enforced structurally by `axe-core` in CI. The § "Hardening posture" subsection of Phase 5f updates in place.
- **Doctrine — `docs/31-WEB-CLIENT.md` (new).** Top-level operational doctrine shape-symmetric with `docs/30-API-ADMISSION.md` and `docs/29-BILLING-X402.md`. Covers sign-in workflow (principal_id + hex-secret credential parsing, `localStorage` persistence), the dev-mode Vite proxy vs. production same-origin mount, the accessibility posture, and the "operator dashboard only" posture with its honest closure story (`KW-CLIENT-001` for public surfaces + in-browser x402 signing; `KW-CLIENT-002` for streaming UX).
- **Client scaffold — `clients/web/`.** Vite 6 + React 18 + TypeScript 5 + plain CSS. No design system, no state library. The `index.html` shell carries a `Content-Security-Policy` meta tag pinning `default-src 'self'` as defence-in-depth on top of the same-origin serve. `vite.config.ts` and `vitest.config.ts` are deliberately split to work around a type-incompatibility between their bundled Vite cores.
- **`BearerContext`.** React Context wrapping `{principalId, secretHex}` credentials, enforcing the same `^[a-z0-9_-]{1,64}$` principal charset and ≥ 16-byte secret floor the server-side `AdmissionConfig` enforces. `localStorage`-persisted. `buildAuthorizationHeader` is the single code path that touches the raw secret.
- **API wrapper — `clients/web/src/lib/api.ts`.** Typed fetch wrapper around every API call with a discriminated-union `ApiError` over `{ unauthorized | payment_required | rate_limited | refused | no_floor | provider_error | timeout | network | unknown }`. Every error-path UI state comes from exhaustive pattern-matching on `error.kind`.
- **Views.** `ChatView` renders the full envelope matrix with a 30-second deadline indicator. `DriveView` polls `/drive` and renders the three drive terms (survive, serve, meaning) as labeled bars with band annotations. `SensoriumView` polls `/sensorium` and renders Interoception, Chronoception, Proprioception, Distress. `Header` carries the view switcher, sign-in status, and a live Relay health dot polling `/health` with ARIA-live announcements.
- **FastAPI StaticFiles mount.** `orchestrator/api/web_client.py` ships `WebClientConfig` (frozen dataclass with fail-closed `__post_init__` — `enabled=true` requires `dist_path` to exist and contain `index.html`) and `mount_web_client()` which mounts at `/app/*` with `html=True` (SPA fallback) plus a `/` → `/app/` redirect. `AppDeps` gains optional `web_client_config`. Mount runs AFTER all API routes register, so API paths are never shadowed.
- **Verifier — `xion-verify web-client`.** Audits the emitted bundle for structural integrity: `index.html` must carry a `Content-Security-Policy` meta tag with `default-src 'self'`; every `https?://` origin in the emitted tree must match an explicit non-self allowlist (React production error-decoder URLs + W3C XML namespace identifiers). Returns `NOT_YET_SEALED` when `dist/` does not exist (un-built is unverifiable, not wrong). Optional `--dist-path PATH` audits an external deploy artifact.
- **Tests.** New `orchestrator/tests/test_api_web_client.py` (3 postures: disabled, enabled+valid, enabled+missing). New `clients/web/src/__tests__/ChatView.test.tsx` (envelope matrix + axe-core WCAG 2.2 AA). New `clients/web/src/__tests__/BearerContext.test.tsx` (credential parsing, entropy floor, persistence). New `xion-verify/tests/test_web_client_verifier.py` (every branch: OK, NOT_YET_SEALED, FAIL-no-CSP, FAIL-non-self-default-src, FAIL-non-allowlisted-origin, OK for each allowlist class, SVG sweep).
- **CI — `.github/workflows/web-client.yml`.** Path-scoped workflow running `npm ci`, `tsc --noEmit`, `npm test` (Vitest + axe-core), `npm run build`, plus a structural `grep` sweep on the emitted bundle for non-self origins — belt-and-suspenders alongside `xion-verify web-client`.
- **`.env.example` expansion.** `XION_WEB_CLIENT_ENABLED` (default `false`) and `XION_WEB_CLIENT_DIST_PATH`.
- **Known-weakness bookkeeping.** **Opened `KW-CLIENT-001`** (low; operator-dashboard only — no in-browser x402 signing; closes Phase 7+ alongside `KW-BILLING-001`). **Opened `KW-CLIENT-002`** (low; non-streaming chat UX with deadline countdown; closes alongside `KW-CHAT-001` in Phase 5g-ii).

**What Phase 5g-v deliberately did NOT do:**

- Did not ship in-browser x402 commitment signing. `KW-CLIENT-001` tracks the gap.
- Did not ship streaming chat rendering. `KW-CLIENT-002` tracks the gap; closes with 5g-ii.
- Did not ship a public / non-operator surface. The client is a dashboard for the operator holding a Phase-5g-iv bearer token.
- Did not ship conversation memory on the client side — each page reload starts a fresh chat session; the transcript ledger lives server-side.
- Did not ship a design system or component library — plain CSS deliberately, so a solo builder can audit every style rule.
- Did not ship WebSocket or SSE transport — polling + request/response is sufficient for the dashboard surfaces.

**Phase 5 promotion handles Phase 5g-v creates:**

- Phase 5g-ii (next unblocked): SSE or WebSocket streaming with per-chunk moderation — closes `KW-CHAT-001`, `KW-CHAT-003`, and `KW-CLIENT-002` (streaming UX re-uses the `ChatView` shell). **Closed 2026-04-22.**
- Phase 6+: in-browser x402 signing (WalletConnect / passkey / injected-provider custody) — closes `KW-CLIENT-001` alongside `KW-BILLING-001`.
- Phase 7+: public / non-operator surfaces once the x402 custody story lands.

---

## Phase 5g-ii — Streaming chat: `POST /chat/stream` SSE + speculative-with-retroactive-refusal + real provider cancel + client streaming render-path (closed 2026-04-22)

**Status:** Phase 5g-ii closed on branch `phase-5g-ii/streaming-chat` in five commits (doctrine → SSE server transport → cancellation propagation → client streaming render-path → verifier + housekeeping). This phase gives `/chat` a second transport, `POST /chat/stream`, that emits Server-Sent Events as the generative provider produces tokens, while preserving every Phase-5g-i property byte-for-byte. The non-streaming `POST /chat` is unchanged — integrators with no streaming story keep their existing code path. The phase closes three Known Weaknesses simultaneously: `KW-CHAT-001` (streaming), `KW-CHAT-003` (real cancel), `KW-CLIENT-002` (client streaming UX).

**Why this is its own phase.** The five Phase-5g-i properties (two-sided moderation, content-free refusals, Invariant-17 fail-closed, per-turn ledger shape, deadline-bounded) are constitutional-tier. A streaming transport that diluted any of them would be a Covenant regression wearing the clothes of a UX improvement. Slicing streaming as its own phase (rather than folding it into 5g-v, which would have conflated streaming-transport with browser-UI, or 5g-iv, which would have conflated transport with admission) kept the doctrine debate — per-chunk moderation vs buffered-then-streamed vs speculative-with-retroactive-refusal — narrow and visible. The chosen doctrine ("speculative-with-retroactive-refusal") is the one posture that delivers perceptual-liveness without touching any 5g-i property's proof. Branch-per-phase discipline preserved: five atomic commits, each independently auditable.

**What Phase 5g-ii shipped:**

- **Doctrine — architecture streaming subsection.** `docs/04-ARCHITECTURE.md` gained § "Streaming the Chat Surface (Phase 5g-ii)" pinning seven properties: SSE at `POST /chat/stream` (P1); `POST /chat` stays non-streaming (P2); chunks are client-side provisional until `done:approve` (P3); egress moderation runs on the buffered complete candidate (P4); `done:refuse` retroactively replaces chunks with a content-free `RefusalEnvelope` (P5); client disconnect propagates to the provider as a real cancel (P6); ledger rows are written post-moderation only, never speculatively (P7). Non-properties honestly named: no per-chunk Arbiter moderation, no mid-stream refund split, no partial-candidate telemetry, no automatic reconnect, no WebSocket, no streaming on `/drive` or `/sensorium`.
- **Doctrine — `docs/32-CHAT-STREAMING.md` (new).** Top-level operational doctrine shape-symmetric with `docs/29-BILLING-X402.md`, `docs/30-API-ADMISSION.md`, `docs/31-WEB-CLIENT.md`. Covers SSE wire format (three event types: `chunk`, `done`, `error`; canonical `data: <json>\n\n` record with no `event:`/`id:`/`retry:` names), chunk-buffer contract the client honors, cancellation semantics, and the no-reconnect posture. Added to `docs/00-INDEX.md` as entry #32.
- **SSE server transport — `orchestrator/api/chat_stream.py` (new).** `POST /chat/stream` handler. Reuses the Phase-5g-iv admission dependency and the Phase-5g-iii x402 commitment gate verbatim — admission failures (401/429/402) report as HTTP-level statuses before any SSE headers flush; every post-admission failure (ingress refuse, egress refuse, no-floor, provider-error, deadline) reports INSIDE the stream as a single `done` event with the matching verdict. Per-iteration `asyncio.wait_for` bounds the per-turn deadline; per-chunk `Request.is_disconnected()` polling detects client-gone and terminates the upstream task. The `_finalize_stream_ledger` tail writes exactly one PAYMENT row after the stream body's terminal state is known.
- **Provider `generate_stream` protocol extension.** `orchestrator/inference_router/provider.py` gains an optional `generate_stream()` on `GenerativeProvider` returning `AsyncIterator[str | GenerationResult]`. OpenRouter + Ollama providers migrated from stdlib `http.client` to `httpx.AsyncClient` so the streaming path has native async + cancel-propagation; real `generate_stream()` lands for both.
- **Cancellation propagation — new `outcome=cancelled` PAYMENT row.** Ledger writer + verifier + schema gain the new outcome: full refund, `refusal_stage=None`, STRUCTURALLY REQUIRES `stream_id`. `xion-verify refusal-is-free` extended to recognize the cancel money-shape without requiring a paired SAFETY verdict=refuse row. Closes `KW-CHAT-003`.
- **Optional `stream_id` on PAYMENT rows.** 32 lowercase hex chars (128 bits of entropy), allocated once per streaming turn. Non-streaming rows omit it; additive canonicalization keeps every pre-5g-ii row byte-exact.
- **Client streaming render-path — `clients/web/src/lib/api.ts` + `ChatView`.** New `streamChat()` returning `AsyncIterable<StreamEvent>` built on Fetch `ReadableStream` + a manual SSE parser (no new dep). `ChatView` grows a `streaming` state rendering chunks with a "pending egress review" affordance until `done:approve` commits them, `done:refuse` retroactively replaces them, `done:cancelled` surfaces the "user_cancel" UX, or `error:deadline_exceeded` surfaces the timeout UX. `?stream=0` forces the 5g-i non-streaming render-path as an opt-out. Closes `KW-CLIENT-002`.
- **`xion-verify chat-streaming-fidelity` — new live verifier.** Walks PAYMENT + SAFETY and asserts six stream-level invariants (chain integrity, stream identification, one-row-per-stream, stream-subset money-shape, cancel-without-paired-refuse, egress-refuse-with-paired-refuse). Returns `NOT_YET_SEALED` when no `stream_id` rows exist yet; the first billed streaming turn promotes to `OK` automatically.
- **Pre-existing `genesis/` line-ending hygiene.** `xion-verify memory` + `xion-verify unknowns` had been FAILing on every platform because the pinned sha256 in `genesis/GENESIS_ARTIFACT.md` § 4 drifted from the canonical LF bytes on disk. Closed here by re-pinning to current content (with an inline documentation-witness correction note) plus adding `genesis/* text eol=lf` to `.gitattributes` as belt-and-suspenders defense against future CRLF-on-Windows drift. Both verifiers now return OK on every platform.
- **Tests.** 13 new streaming server tests against a fake provider (full envelope matrix + deadline + cancel propagation); 7 new client streaming tests including an `axe-core` WCAG 2.2 AA pass on the pending state; 10 new verifier tests covering every branch of `chat-streaming-fidelity`. **Total pytest across `orchestrator/`, `xion-verify/`, `xion-audit/`: continues green.**
- **Known-weakness bookkeeping.** **Closed `KW-CHAT-001`** — streaming is live. **Closed `KW-CHAT-003`** — client disconnect propagates to provider cancel; upstream billing terminates immediately. **Closed `KW-CLIENT-002`** — `ChatView` streaming render-path ships with pending-chunk buffer + retroactive refusal replacement + cancel UX. No new KWs opened.
- **`PINNED_HASH.txt` re-pin.** Regenerated via `xion-verify --self-test --update --i-understand`. `xion-verify all --allow-not-yet-sealed` green end-to-end; `chat-streaming-fidelity` reports `NOT_YET_SEALED` honestly until the first billed streaming turn.

**What Phase 5g-ii deliberately did NOT do:**

- Did not change `POST /chat` (non-streaming surface stays for backward compat).
- Did not add per-chunk Arbiter moderation — posture rejected in doctrine on cost + false-positive + partial-prefix grounds.
- Did not add streaming to `/drive` or `/sensorium` — those remain polling; out of scope.
- Did not close `KW-BILLING-001` (x402 signature verification stays shape-only).
- Did not close `KW-AUTH-001`, `KW-RATE-001`, `KW-TLS-001` (admission-control residuals; Phase 6+).
- Did not ship a WebSocket transport — SSE chosen as the simpler, unidirectional, proxy-friendly primitive.
- Did not write an in-browser x402 signing helper — `KW-CLIENT-001` stays Phase 6+.

**Phase 5 promotion handles Phase 5g-ii creates:**

- Phase 5g+: shared-state broker so multi-worker orchestrator can honor per-principal rate-limits globally (closes `KW-RATE-001` alongside `KW-SUPERVISOR-002`).
- Phase 6+: on-chain x402 settlement + catalog-driven dynamic pricing (closes `KW-BILLING-001` + `KW-BILLING-002`).
- Phase 6+: in-browser x402 signing (closes `KW-CLIENT-001`).

---

## Phase 5g+ — Multi-worker coherence: SQLite-WAL broker + Supervisor leader election + global rate-limit (closed 2026-04-22)

**Status:** Phase 5g+ closed on branch `phase-5g+/multi-worker-broker` in five commits (doctrine → SqliteBroker module → Supervisor broker wiring → rate-limit broker wiring → verifier + housekeeping). This phase makes `orchestrator/api/` horizontally scalable to `N > 1` uvicorn workers without violating the two properties the prior phases were structurally unable to preserve under multi-worker: (1) exactly-one Supervisor ticks at any wall-clock instant, and (2) per-principal sliding-window rate-limit budgets are globally coherent across all N workers. The single-worker posture remains the default and is byte-identical to 5g-v; the multi-worker posture activates iff the operator sets `XION_BROKER_DB_PATH` and raises `XION_API_WORKERS > 1`. The phase closes two Known Weaknesses: **`KW-API-002`** (Supervisor shared the FastAPI event loop) and **`KW-RATE-001`** (in-process sliding window multiplied the budget by `N` under multi-worker).

**Why this is its own phase.** `KW-API-002` was pinned in Phase 5f as an implicit "single uvicorn worker" constraint — shipping the Supervisor tick loop on the FastAPI app's event loop forced `uvicorn --workers 1` because two workers would each tick and corrupt the cadence record. `KW-RATE-001` was pinned in Phase 5g-iv as an explicit multi-worker budget-multiplication vulnerability. Both closures needed the same underlying mechanism — a shared-state broker — so they land together. Slicing this as Phase 5g+ (rather than folding a broker into 5g-iv or 5g-v) kept the doctrine debate — SQLite vs Redis vs TCP-loopback daemon vs AO Process mailbox — narrow and visible. The chosen mechanism (SQLite in WAL mode) is the one candidate that is stdlib-only, cross-platform (Windows included), kill-safe (no second process), inspectable at 3am with `sqlite3 <path>`, and wrappable behind a Protocol surface narrow enough that Phase 6's AO Process mailbox is a module swap rather than a re-architecture. Branch-per-phase discipline preserved: five atomic commits, each independently auditable.

**What Phase 5g+ shipped:**

- **Doctrine — architecture multi-worker subsection.** `docs/04-ARCHITECTURE.md` gained § "Multi-worker coherence (Phase 5g+)" pinning five properties: SQLite-WAL broker as the chosen mechanism with the three rejected alternatives named (Redis: enterprise weight + external dep + TLS/persistence stories a solo builder cannot sustain; TCP-loopback daemon: second process + supervision + wire protocol; AO Process mailbox: correct long-term home but does not exist until Phase 6) (P1); single-leader Supervisor via lease-based election (P2, closing `KW-API-002`); global per-principal rate-limit buckets across all N workers (P3, closing `KW-RATE-001`); Phase-6 replacement path to AO Process mailbox is a one-module swap behind the `Broker` Protocol (P4); operator env surface is strictly additive (P5). Non-properties honestly named: no cross-host coordination (single-machine only), no distributed transaction semantics, no broker-side authn (the DB file is trusted filesystem).
- **Doctrine — `docs/33-MULTI-WORKER.md` (new).** Top-level operational doctrine shape-symmetric with `docs/29-BILLING-X402.md`, `docs/30-API-ADMISSION.md`, `docs/31-WEB-CLIENT.md`, `docs/32-CHAT-STREAMING.md`. Covers broker schema (three tables: `supervisor_snapshot` singleton row, `supervisor_leader` lease row, `rate_limit_events` append+prune), leader-election semantics (lease TTL + renewal cadence + failover bound), the SQLite-WAL posture (`PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout`), operator backup/reset runbook, failure modes, observability, and the explicit Phase-6 replacement contract. Added to `docs/00-INDEX.md` as entry #33.
- **SqliteBroker module — `orchestrator/runtime/broker.py` (new).** Ships `BrokerConfig` (frozen dataclass; `__post_init__` enforces `leader_renew_s < leader_lease_s / 2` and parent-dir exists), `Broker` Protocol (the Phase-6-replaceable surface: `publish_snapshot`, `latest_snapshot`, `try_acquire_leader`, `renew_leader`, `is_leader`, `check_and_record_rate`), `RateCheck` result, and `SqliteBroker` concrete implementation — a single `sqlite3.Connection` per worker with `check_same_thread=False` and an internal `threading.Lock` (WAL supports concurrent readers + serialized writers; the lock prevents stdlib-connection re-entry corruption). Three tables created on first open. `check_and_record_rate` runs in a single `BEGIN IMMEDIATE` transaction (delete stale events → count → conditional insert → return `RateCheck`), so two workers sharing one broker share one atomic global sliding window per principal. `load_broker_from_env()` factory returns `None` when `XION_BROKER_DB_PATH` is unset (preserves the single-worker posture as default). `orchestrator/runtime/__init__.py` re-exports the public surface.
- **Supervisor wiring — `orchestrator/runtime/supervisor_shell.py` (new) + `orchestrator/supervisor.py` publish hook + `orchestrator/api/lifespan.py`.** `Supervisor.__init__` gains an optional `publish: Callable[[Mapping[str, Any]], None] | None = None` hook called after every successful `tick_once()` (broker-agnostic; publish exceptions are logged and swallowed — a missed publish lags followers by one tick, never corrupts in-process state). New `BrokerSupervisorShell` wraps a Supervisor and performs lease-based election: workers that acquire the lease run the Supervisor loop and publish each tick; workers that fail run as followers whose `latest_snapshot()` reads from the broker. On leader crash, the first follower whose acquire attempt succeeds (lease expired) promotes itself — failover is bounded by `leader_lease_s`. `deserialize_sensorium_state()` reconstructs a `SensoriumState` from a broker JSON blob. Lifespan conditionally wires broker + shell when `XION_BROKER_DB_PATH` is set; otherwise keeps 5g-iv's single-Supervisor construction byte-identical.
- **Launcher — `orchestrator/api/__main__.py` multi-worker mode.** Reads `XION_API_WORKERS` from env (default `1`). When `workers > 1`, fails closed at startup unless `XION_BROKER_DB_PATH` is set (multi-worker without a broker is the documented corruption path). Single-worker mode keeps `uvicorn.run(app, ...)` byte-identical; multi-worker mode uses Uvicorn's `factory=True` posture against a new module-level `create_default_app()` factory, so each worker process gets its own `Relay` + `AppDeps` + `FastAPI` app and they coordinate exclusively through the broker file.
- **Rate-limit broker wiring — `orchestrator/api/admission.py` RateLimitStore Protocol.** New `RateLimitStore` Protocol with `check_and_record(principal_id, now_ns) -> RateCheck`. `InProcessSlidingWindowStore` (used when no broker is configured) lazy-allocates `SlidingWindow` instances per principal; behavior byte-identical to 5g-iv's direct `app.state.rate_limiters[principal]` dict. `BrokerBackedSlidingWindowStore` (used when a broker is configured) delegates every check to `Broker.check_and_record_rate(...)`, so two workers sharing one broker share one global sliding window per principal. `build_rate_limiters(config, *, broker=None)` returns the right store; `admission_dependency` is untouched. Closes `KW-RATE-001`.
- **`xion-verify supervisor-singleton` — new live verifier.** Walks `SENSORIUM_LEDGER.jsonl` for `tick_commit` rows inside a configurable window (`--window-hours`, default 24 h), preserving the ledger's file-order (the seq chain is the canonical insertion order; sorting would mask within-epoch clock regressions). Asserts three properties: bounded failover (A) — `relay_id` transitions ≤ `--max-failovers` (default 1); within-leader-epoch strict `as_of_utc_ns` monotonicity (B) — catches clock regressions and the two-Supervisors-one-`relay_id` corruption; no concurrent-leader time-range overlap (C) — for each distinct `relay_id` the closed range `[min_as_of_utc_ns, max_as_of_utc_ns]` must not overlap any other `relay_id`'s range (the precise `KW-API-002` corruption signature). Returns `NOT_YET_SEALED` when the ledger is absent, empty, or has no tick rows inside the window. Registered in `cli.py` + `commands/__init__.py`.
- **Tests.** 31 new broker tests in `orchestrator/tests/test_runtime_broker.py` cover schema init, snapshot round-trip, leader election under concurrent claimants + lease expiry failover, rate-limit coherence across threaded "workers", WAL-mode persistence across reopen, `BEGIN IMMEDIATE` contention, and the `load_broker_from_env` factory contract. New `orchestrator/tests/test_api_multi_worker.py` spins up two in-process `BrokerSupervisorShell` instances sharing one broker DB and asserts single-leader domination of `tick_commit` rows, follower-snapshot-shape match, leader failover on stop within lease, and lifespan wiring sanity. 9 new rate-limit tests in `orchestrator/tests/test_api_admission.py` cover in-process store lazy allocation + overflow + independence, broker-backed two-workers-one-bucket budget coherence (closing `KW-RATE-001`), different principals don't share, eviction across workers, `build_rate_limiters` dispatch, and `admission_dependency` + broker-backed store end-to-end 429 enforcement. 13 new verifier tests cover every branch of `supervisor-singleton`. **Total pytest across `orchestrator/`, `xion-verify/`: continues green.**
- **Known-weakness bookkeeping.** **Closed `KW-API-002`** — the Supervisor no longer implicitly requires `--workers 1`; broker-backed leader election guarantees exactly one Supervisor ticks regardless of worker count. **Closed `KW-RATE-001`** — per-principal budgets are now globally coherent across N workers when a broker is configured. `KW-SUPERVISOR-002` stays open (tick_commit heartbeat continuity is a separate Phase-6+ property requiring a deploy-event ledger the orchestrator does not yet publish). No new KWs opened.
- **`.env.example` expansion.** New "Multi-worker coherence (Phase 5g+)" section documents `XION_API_WORKERS` (default 1) and `XION_BROKER_DB_PATH` (default unset = single-worker posture), with a production multi-worker example.
- **`PINNED_HASH.txt` re-pin.** Regenerated via `xion-verify --self-test --update --i-understand`. `xion-verify all --allow-not-yet-sealed` green end-to-end; `supervisor-singleton` reports `NOT_YET_SEALED` honestly until the first `tick_commit` row lands in the observed window.

**What Phase 5g+ deliberately did NOT do:**

- Did not close `KW-SUPERVISOR-002` (tick_commit heartbeat continuity needs a Phase-6+ deploy-event ledger).
- Did not add cross-host coordination — the SQLite file is single-machine; cross-host is Phase 6+ AO Process mailbox territory.
- Did not replace the in-process `SlidingWindow` when no broker is configured — default posture stays backward-compatible.
- Did not ship broker-side authn — the DB file is trusted filesystem; a new threat surface here would be theater given the operator already has write access.
- Did not add a `--workers` flag that *requires* the broker; workers=1 without a broker remains the supported default.
- Did not migrate to Redis, WebSocket, or any external dep — all new functionality is stdlib-only.

**Phase 5 promotion handles Phase 5g+ creates:**

- Phase 6+: AO Process mailbox replaces `SqliteBroker` behind the `Broker` Protocol — closes the single-machine limitation.
- Phase 6+: deploy-event ledger enables `KW-SUPERVISOR-002` closure (tick_commit heartbeat continuity across restarts).

---

## Genesis Default hosted model rotation — `moonshotai/kimi-k2` → `moonshotai/kimi-k2.6` (landed 2026-04-23)

**Status:** Small doctrine-bearing commit on `main`. Not a full phase. The first real invocation of the one-env-var rotation mechanism that [`.env.example`](./.env.example) and [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) § "The hosted-provider choice" have documented since the Phase 5g-i.1 pin (2026-04-21). The commit earns a dedicated landing — not a fold into a larger phase — because a rotation of a constitutional slug is exactly the kind of historical record a Witness in 2126 needs to be able to find in the CHANGELOG without reading five unrelated diffs.

**Why this landing earned a probe-first discipline before the commit.** The Phase 5g-i.1 rotation *mechanism* is a promise: *swap one env var, ship a slug advance.* A first exercise of the mechanism without verifying the target slug's liveness, provider allowlist, and operator-BYOK attachment would have been a mechanism test against a theoretical target. Before the commit landed, a read-only probe of OpenRouter's public `GET /api/v1/models` catalog confirmed `moonshotai/kimi-k2.6` as a live dated snapshot (`moonshotai/kimi-k2.6-20260420`, released 2026-04-20), and an authorized `POST /chat/completions` probe with `provider.only=["moonshotai"]` forced confirmed the operator's Moonshot-AI BYOK attachment to their OpenRouter account is correctly wired for this specific slug (`HTTP 200`, `is_byok=true`, `cost=0`). The probe findings are recorded in the CHANGELOG entry so the decision context is recoverable. Future rotations — within the same gateway or across gateways — follow the same discipline.

**What this rotation commits to, and what it does NOT commit to.** The rotation advances the *slug* pinned as the Genesis Default hosted model. The *concentration* shape named by `KW-INFER-001` is unchanged: every default-path turn still crosses OpenRouter's gateway and, under the default model, lands at Moonshot's weights. The closure bar for `KW-INFER-001` is unchanged (still requires annual cutover dry-run, second gateway, two-model failover list, and the `xion-verify inference-cutover` verifier — all Phase 6+). The doctrine shape in [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) is unchanged — only the slug references advance, plus a new three-sentence paragraph naming this rotation as the first real invocation of the mechanism. No verifier behaviour changes; `xion-verify inference-sovereignty` is unaffected because the floor manifest does not change.

**What this landing shipped:**

- [`orchestrator/inference_router/providers/openrouter.py`](./orchestrator/inference_router/providers/openrouter.py) code default (`_DEFAULT_MODEL = "moonshotai/kimi-k2.6"`) and two doctrinally-anchored docstring spots (header doctrine anchor; `ChatResponse.model_id` example updated to the dated snapshot).
- [`docs/26-INFERENCE-POLICY.md`](./docs/26-INFERENCE-POLICY.md) five slug pins (Genesis Defaults table, § "The hosted-provider choice" heading and its five bullets, § "Gateway vs direct" KW-INFER-001 reshape note) plus a new three-sentence "Genesis Default rotation, 2026-04-23" paragraph. Per-token pricing differential recorded (`$0.75/M` prompt + `$3.50/M` completion for `kimi-k2.6` vs `$0.57/M` + `$2.30/M` for `kimi-k2` — ~30 % higher rack rate, neutralised for BYOK-routed operators). Context-window advance recorded (`131,072` → `262,144` tokens).
- [`.env.example`](./.env.example) Genesis Default comment block rewritten with the rotation provenance and three new one-env-var rotation examples (including a rollback line to `moonshotai/kimi-k2` and a reasoning-forward variant `moonshotai/kimi-k2-thinking`).
- [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) three slug references updated (Router-policy pin in § "Inference Router"; `KW-INFER-001` summary in the Chat Surface KW block; `KW-BILLING-002` rotation example).
- [`docs/29-BILLING-X402.md`](./docs/29-BILLING-X402.md), [`docs/schemas/ledger-payment.yaml`](./docs/schemas/ledger-payment.yaml), and [`orchestrator/api/models.py`](./orchestrator/api/models.py) `model_id` examples advanced.
- [`orchestrator/inference_router/providers/__init__.py`](./orchestrator/inference_router/providers/__init__.py) package docstring advanced with rotation provenance.
- [`KNOWN_WEAKNESSES.md`](./KNOWN_WEAKNESSES.md) `KW-INFER-001` title, reshape provenance line (new third reshape date: *slug rotated 2026-04-23*), description slug, and mitigation 5 advanced — mitigation 5 now reads "Model rotation is now one env-var — *and has been exercised*" and records the rotation witness so the mitigation is witnessed rather than asserted.
- This ROADMAP entry. [`CHANGELOG.md`](./CHANGELOG.md) entry under `[Unreleased] > ### Changed` naming the rotation as the first real invocation of the mechanism.

**What this landing deliberately did NOT do:**

- Did not change the `xion-verify inference-sovereignty` verifier or the open-weights floor manifest. The rotation is a hosted-side event; the floor is unaffected.
- Did not add a second hosted gateway, a model failover list, or an annual cutover dry-run runbook. All three remain `KW-INFER-001` closure requirements and are Phase 6+ work.
- Did not open or close any KW. `KW-INFER-001` mitigations strengthened by one (mitigation 5 is now witnessed), but the closure bar is unchanged.
- Did not edit the Phase 5g-i.1 historical entries in [`CHANGELOG.md`](./CHANGELOG.md) or earlier sections of this ROADMAP. Those entries remain accurate historical records of what that phase pinned.
- Did not commit the operator's runtime `.env`. The file is gitignored per [`.gitignore`](./.gitignore); the operator updates it locally (one line: `XION_OPENROUTER_MODEL=moonshotai/kimi-k2.6`) and the next orchestrator restart picks up the new default.

---

## First real open-weights floor-provider pin — `ollama` via content-addressed provenance record (landed 2026-04-23)

**Status:** Small doctrine-bearing commit on `main`. Not a full phase. Ships the second-smallest honest step past the pre-genesis sentinel: an `open_weights[]` entry with `id="ollama"` backed by a content-addressed provenance record (`orchestrator/inference_router/floor_ollama_provenance.txt`) rather than a content-addressed model blob. `xion-verify inference-sovereignty` now reports 2 entries / 2 floor-satisfying pins, both hash-verified.

**Why this earned a landing rather than a full phase.** Running `python -m orchestrator.api` against the pre-genesis manifest produced `State-of-Xion: Inference Router bootstrap refused`: `provider_id="ollama"` did not appear in the sole pinned id (`sentinel-llm-v0`), so the Router refused per Invariant 17. Three alternatives were rejected on doctrinal grounds: (a) silent manifest edit hides the constitutional act; (b) an `XION_INFERENCE_DEV_ALLOW_ANY_FLOOR` bypass flag is a back-door that survives forever once shipped; (c) runtime override of `OllamaGenerativeProvider.provider_id` fakes the pin. The correct act is a named, content-addressed, Witness-recomputable file that *declares* "this deployment holds its floor via the local Ollama daemon" and ships with its weakness legible in the machine-readable `format: "provenance-record"` field.

**What this pin commits to, and what it does NOT commit to.** The sha256 in `open_weights_manifest.json` content-addresses the operator's *declaration*: a 4.8 KB plaintext statement that names the provider id, the required environment configuration, and the trust surface. It does NOT content-address the model weights themselves — a malicious operator can swap the locally-pulled GGUF blob without this file changing. That stronger pin (GGUF sha256 or Invariant 17 clause 2(iii) large-file representative-sample sentinel) is the remaining pay-down for `KW-INFERENCE-001` and is queued as the next dedicated sub-phase of Invariant-17 strengthening work.

**What this landing shipped:**

- `orchestrator/inference_router/floor_ollama_provenance.txt` (new; 4,833 bytes, LF, sha256 `c2c78dcd…88cc9`). The provenance record body explicitly names: what the file is, what it is NOT, why the provenance-record format exists, the runtime configuration it covers, the trust surface, and the operator identity statement.
- `orchestrator/inference_router/open_weights_manifest.json` gains a second `open_weights[]` entry — `id: "ollama"`, `category: "open_weights_self_hostable"`, `format: "provenance-record"`, pointing at the new file with its sha256. The sentinel-llm-v0 entry stays in place as the pre-genesis structural anchor.
- `KW-INFERENCE-001` scope narrowed a second time. Pay-down commitment rewritten to require three artifacts to close: annual cutover dry-run runbook, content-addressed model-blob pin, and verifier extension to recognize the new `format` values.
- `.env.example` unchanged (`XION_OLLAMA_FLOOR_MODEL` already documented).
- No new KWs opened. No back-door flags introduced.

**What this landing deliberately did NOT do:**

- Did not compute or pin a GGUF sha256 for `qwen3.5:4b-16k` or any other Ollama-served model. That is the next Invariant-17 sub-phase.
- Did not extend `xion-verify inference-sovereignty` to walk the `format` field differently per type. Today it accepts `provenance-record` entries because they carry `sentinel_path` + `sha256` like everything else; semantic differentiation arrives alongside the content-addressed-blob work.
- Did not add an annual cutover dry-run to `docs/13-OPERATIONS.md`. That runbook is also a `KW-INFERENCE-001` closure item and lands alongside the D2 operator runbook work.

---

## Phase 5g-viii — Invariant-17 strengthening: model-blob pin (Gemma 4 E4B-it Q4_K_M GGUF) + Genesis Default floor model rotation + verifier per-format dispatch + annual open-weights cutover dry-run runbook (closed 2026-04-23)

**Status:** Phase 5g-viii closed in seven steps (C0 probes -> C1 doctrine -> C2 manifest -> C3 verifier -> C4 tests -> C5 operator wiring -> C6 KW closure + housekeeping). This phase **closes `KW-INFERENCE-001`** by shipping every clause of its three-part pay-down commitment in one coordinated landing. It is the second of the two coordinated 2026-04-23 Invariant-17 strengthening moves (the first was the `ollama` provenance-record pin earlier the same day, recorded in the section immediately above).

**Why this earned a full phase rather than another small landing.** The remaining Invariant-17 strengthening was three structurally coupled changes — a model-blob format that the verifier did not yet know how to read, a verifier dispatch refactor that needed test coverage, and an operator-facing dry-run runbook that pinned the operational closure of the same Invariant clause. None of the three could land independently without leaving the others as half-shipped scaffolding. Pinning a model-blob whose contents differ from the runtime default would also mislead a Witness reading the manifest, so the Genesis Default floor model rotation (`gemma3:4b` -> `gemma4:e4b-it-q4_K_M`, license posture Custom Gemma TOU -> Apache 2.0) had to land in the same window. Splitting these into separate landings would have created two false closure moments and three half-states; bundling them is the honest shape.

**Why now.** The 2026-04-23 `ollama` provenance-record pin closed two of `KW-INFERENCE-001`'s three closure-bar items but explicitly deferred the third (the model-blob pin and the verifier extension that recognizes it). The KW closure bar required all three to ship; carrying a "two-of-three closed" residual into Phase 6 work would have left a partially-strengthened Invariant 17 across the next phase boundary. Closing it before Phase 6 keeps the KW ledger honest and unlocks the Phase 7 pre-flight ("Invariant 17 enforceable in code") without a residual to negotiate.

**What Phase 5g-viii shipped:**

- **C0 probes (read-only, recorded for the next Witness).** Five probes ran before any doctrine edit, captured in `docs/26-INFERENCE-POLICY.md` § "The floor-model choice (Gemma 4 E4B-it)" -> "Probe-first record (2026-04-23)": (a) `google/gemma-4-E4B-it` is genuinely Apache-2.0 (HF metadata + Apache-text license_link + Google Open Source Blog announcement *"Gemma 4: Expanding the Gemmaverse with Apache 2.0"* dated 2026-03-02 — a meaningful change from Gemma 1/2/3's custom Gemma TOU; the unlock that lets a Witness verify the floor without accepting Google-specific terms); (b) `ggml-org/gemma-4-E4B-it-GGUF` (the GGUF/llama.cpp authors' organization) at git revision `2714b5519c6c3516b1000e7c5e1eba998dfe1fe8` ships `gemma-4-E4B-it-Q4_K_M.gguf` with sha256 `90ce98129eb3e8cc57e62433d500c97c624b1e3af1fcc85dd3b55ad7e0313e9f` and size `5,335,289,824` bytes (selected over `unsloth/` and `lmstudio-community/` for shortest provenance ladder); (c) Ollama 0.21.0 supports the `gemma4` architecture (`Gemma4ForConditionalGeneration` / `model_type: gemma4`); (d) Ollama's pre-built `gemma4:e4b-it-q4_K_M` library tag is multimodal-bundled (text + vision + audio + per-layer-embeddings, 9.6 GB), distinct from the text-only `ggml-org` Q4_K_M (~5.0 GB) the manifest pins; (e) end-to-end smoke test deferred to operator with explicit RAM-headroom guidance (operator's 16 GB host had 3.2 GB free at probe time; first chat against the new floor needs other RAM-heavy applications closed; the model-blob format pin and the runtime floor rotation are independent of the smoke test passing on this specific host).

- **C1 doctrine — `docs/26-INFERENCE-POLICY.md`.** Rewrote § "The floor-model choice" (was "Gemma 3 4B") into "(Gemma 4 E4B-it)" with the C0 probe record, "Why this model" (Apache-2.0 license; native system-prompt support; configurable thinking modes; native function-calling; 128K context window per the upstream model card; multimodal-capable architecture as forward-leverage; ~5.0 GB Q4_K_M runs on commodity compute; procurable from at least four independent organizations per Invariant 17 clause 2(ii); locally health-checkable per clause 2(iv)), and "Honest trade-offs" (~5.0 GB vs `gemma3:4b`'s ~3.3 GB; three-week-old model with `gemma3:4b` as one-env-var rollback target; Ollama-library tag and the model-blob pin are intentionally not byte-identical builds). Added § "Model-blob pin (Phase 5g-viii)" pinning five properties: (P1) the manifest pins the upstream Hugging Face GGUF, not a local Ollama blob (Witness-recomputable; the local Ollama blob is not byte-stable across hosts); (P2) verifier posture is `NOT_YET_SEALED` when absent / `OK` when present + matching / `FAIL` when present + mismatched; (P3) per-format dispatch with fail-closed unknown-format branch (accepted-format set lives at exactly one place: the verifier's `_DISPATCH` table); (P4) hashing is chunked at 4 MiB; (P5) the annual open-weights cutover dry-run is the operational closure of the same Invariant 17 clause 5.

- **C1 doctrine — `docs/13-OPERATIONS.md` runbook additions.** § "First-launch sequence (D2 cold start)" updated to reference the new floor model and add an optional step 3b for byte-verification setup. New § "First-time GGUF setup (model-blob byte-verification, Phase 5g-viii)" pinning the operator-side runbook: download the canonical Q4_K_M from the pinned ggml-org HF revision, sha256-check it locally, set `XION_OPEN_WEIGHTS_GGUF_PATH`, re-run `xion-verify inference-sovereignty` to promote the model-blob entry from `NOT_YET_SEALED` to `OK`. Includes RAM-headroom guidance. New § "Annual open-weights cutover dry-run (Invariant 17 clause 5)" pinning the operator's calendar-driven runbook: cadence (one calendar-year), pre-checklist (model-blob entry `OK`; Ollama daemon healthy; baseline hosted-gateway chat succeeds), execution (flip `XION_INFERENCE_POLICY=open_weights_only` for the dry-run window; representative ≥100-turn workload spread across ≥30 minutes; tail `REQUEST_LEDGER` for the window — every row must have `provider_id="ollama"` and `outcome="success"`; the chat handler MUST NOT have fallen back to hosted), Green/Yellow/Red verdict criteria with specific resource-shortfall signals, recording shape for the operator's annual ops log. § "D2 Prereqs" and § "D2 Environment Matrix" updated for the new defaults.

- **C2 manifest — `orchestrator/inference_router/open_weights_manifest.json`.** Description rewritten to enumerate the three accepted pin formats (`sentinel`, `provenance-record`, `model-blob`) and to name `KW-INFERENCE-001` as the strengthening-history anchor (was the stale `KW-FLOOR-001`). New `gemma4-e4b-it-q4-k-m-gguf` entry: `category="open_weights_self_hostable"`, `format="model-blob"`, `model_blob_env_var="XION_OPEN_WEIGHTS_GGUF_PATH"`, `sha256="90ce98129eb3e8cc57e62433d500c97c624b1e3af1fcc85dd3b55ad7e0313e9f"`, `size_bytes=5335289824`, and a `retrieval_hints[]` array naming the canonical `ggml-org` HF mirror at the pinned git revision. The existing `ollama` provenance-record entry's `notes` updated to name the new sibling and the corrected KW reference; sha256 re-pinned to `f63fe6207b0d0412a6c70650246efdf25d6971d9103358622c3dca8853d147be` after `floor_ollama_provenance.txt` was rewritten to reflect the rotation, the strengthened license posture, and the companion model-blob entry. The provenance file gained a closing § "Strengthening companion + rotation provenance (Phase 5g-viii)" naming the three coupled changes and the C0 probe trail anchor.

- **C3 verifier — `xion-verify/src/xion_verify/commands/inference_sovereignty.py`.** Refactored from a single sentinel-only loop to a `_DISPATCH: dict[str, Callable]` table keyed on the entry's `format` field with three handlers: `_verify_sentinel`, `_verify_provenance_record`, `_verify_model_blob`. Unknown `format` values FAIL with a structured message naming the accepted set — adding a new format is now a verifier change, not a manifest-only change; the accepted-format set lives at exactly one place in the codebase. `_verify_model_blob` resolves the local file via the env var named in `model_blob_env_var`, performs a cheap `size_bytes` preflight when the manifest pins one (FAIL on mismatch — typically signals a wrong file at the path, before the multi-GB hash is ever computed), validates the `retrieval_hints[]` shape (each hint must be an object with `url` and a 64-hex `sha256` matching the entry's `sha256`), and uses chunked sha256 at 4 MiB windows so a 5 GB GGUF keeps peak verifier memory at ~4 MiB. Absent env var or unresolvable path resolves to `NOT_YET_SEALED` with operator-actionable guidance pointing at the runbook. Per-entry verdicts roll up at the end: any `not_yet_sealed` entry promotes the overall exit to `NOT_YET_SEALED` (exit 2); any `_fail()` is `FAIL` (exit 1); all-OK is `OK` (exit 0). Per-entry summaries print before the rollup so an operator reading the output can see exactly which entry surfaced the gap.

- **C4 tests — 18 new verifier tests.** `xion-verify/tests/test_inference_sovereignty.py` was extended with a synthetic-temp-repo helper that builds a minimal directory tree satisfying `find_repo_root`'s witness pair (`genesis/GENESIS_ARTIFACT.md`, `docs/00-INDEX.md`) plus a manifest writer + blob writer, so every verifier branch can be exercised without depending on a 5 GB GGUF in CI. Coverage: real-repo manifest returns `NOT_YET_SEALED` when `XION_OPEN_WEIGHTS_GGUF_PATH` is unset (post-Phase-5g-viii default CI posture); real-repo manifest with a bad GGUF path also returns `NOT_YET_SEALED` (typo = same shape as never-set); synthetic sentinel OK + sha mismatch FAIL; synthetic provenance-record OK + sha mismatch FAIL; synthetic model-blob env-var-unset / env-var-points-at-missing / present-matching / present-size-mismatch / present-hash-mismatch / multi-chunk hashing equivalence (>2 × 4 MiB chunks); missing-retrieval-hints FAIL; hint-sha-disagreement FAIL; missing-env-var-field FAIL; unknown-format-value FAIL; no-floor-satisfying-entry FAIL; mixed manifest (one sentinel OK + one absent model-blob) returns `NOT_YET_SEALED` overall. All 18 tests pass.

- **C5 operator wiring — `.env.example`, `orchestrator/inference_router/providers/ollama.py`.** `.env.example` advanced `XION_OLLAMA_FLOOR_MODEL` from `gemma3:4b` to `gemma4:e4b-it-q4_K_M` with a documented one-env-var rollback target and an inline reference to the C0 probe trail; added `XION_OPEN_WEIGHTS_GGUF_PATH` (unset by default; setting it enables byte-verification per the new "First-time GGUF setup" runbook) with explicit RAM-headroom and disk-size guidance. `orchestrator/inference_router/providers/ollama.py` `_DEFAULT_MODEL` advanced to match the new env-var default so an operator who unsets `XION_OLLAMA_FLOOR_MODEL` gets the new Genesis Default rather than the prior pin. `floor_ollama_provenance.txt` was rewritten to (a) fix the stale `KW-FLOOR-001` references to the canonical `KW-INFERENCE-001`, (b) reflect the new Gemma 4 default and the strengthened license posture (Custom Gemma TOU -> Apache 2.0), (c) name the companion model-blob entry as the next-tier strengthening anchor, (d) gain a "Strengthening companion + rotation provenance (Phase 5g-viii)" closing section. `xion-verify inference-sovereignty` re-pinned the manifest's `ollama` entry to the new sha256 after these edits.

- **C6 KW closure + housekeeping.** **Closed `KW-INFERENCE-001`** in `KNOWN_WEAKNESSES.md`. The Closed-section entry names every shipped artifact, the residual scope tracked separately or named in the doctrine (runtime gate on local-blob byte-identity is deferred future work; cross-substrate Arweave permaweb pin is Phase 6+; structured `INCIDENT_LEDGER` row shape for the dry-run record is Phase 6+; `LHT-INFERENCE-001` long-horizon re-pinning duty stays open separately), and the closing verifier shape. `xion-verify/src/xion_verify/PINNED_HASH.txt` regenerated via `python -m xion_verify --self-test --update --i-understand` after the verifier refactor. `xion-verify all --allow-not-yet-sealed` green end-to-end; the new `inference-sovereignty` model-blob entry reports `NOT_YET_SEALED` honestly until the operator completes the "First-time GGUF setup" runbook. Full repo test suite (605 tests excluding self-test, then re-included after PINNED_HASH regen) green.

**Known-weakness bookkeeping.**

- **Closed `KW-INFERENCE-001`** — every clause of the three-part closure bar shipped: (a) annual open-weights cutover dry-run runbook in `docs/13-OPERATIONS.md`; (b) content-addressed model-blob pin in `open_weights_manifest.json` (the Invariant 17 clause 2(iii) full-hash branch); (c) `xion-verify inference-sovereignty` extended to recognize and validate the new `format` value via per-format dispatch with a fail-closed unknown-format branch.
- **No new KWs opened.** The residuals named in the closed entry are either Phase 6+ deliverables (Arweave permaweb pin; structured `INCIDENT_LEDGER` row shape) or doctrinally-deferred future hardening (runtime gate on local-Ollama-blob byte-identity, deliberately not shipped because it would couple Xion's floor to Ollama's internal blob layout).
- **`LHT-INFERENCE-001`** continues to track the century-scale re-pinning duty; this KW closure does not retire that long-horizon entry.

**What Phase 5g-viii deliberately did NOT do:**

- Did not ship a runtime gate refusing bootstrap when the local Ollama blob mismatches the manifest pin (would couple Xion's floor to Ollama's internal blob layout; named in `docs/26-INFERENCE-POLICY.md` § "Model-blob pin (Phase 5g-viii)" -> "What this pin does not do").
- Did not pin the Ollama-published `gemma4:e4b-it-q4_K_M` library tag (multimodal-bundled, 9.6 GB on disk, different bytes from the text-only ggml-org Q4_K_M; the manifest pins the smaller text-only build because that is the smallest honest floor for the current `/chat` text surface).
- Did not pin the GGUF on Arweave or any other permaweb. The `retrieval_hints[]` mechanism is upstream-mirror-pluralizable, but a permaweb pin is Phase 6+ work that closes the upstream-mirror availability dependency.
- Did not change the runtime cadence of the open-weights cutover dry-run (annual, per Invariant 17 clause 5) or add a structured ledger row shape for it (Phase 6+).
- Did not retire the `sentinel` or `provenance-record` formats — they pin distinct properties (structural anchor and runtime-daemon declaration respectively); the three formats are companions, not replacements.
- Did not drop `gemma3:4b` from the documented rollback path. Operators on tighter dev hosts can stay on the prior pin via `XION_OLLAMA_FLOOR_MODEL=gemma3:4b`; the rotation is one env-var.
- Did not rename the manifest's `license_spdx` field to `license`. Gemma 4 is genuinely Apache-2.0 per probe (a), so all three entries remain SPDX-identifier values; renaming would have been schema churn for no constitutional gain.
- Did not pin a representative-sample sentinel for the GGUF. Invariant 17 clause 2(iii) reserves that branch for very-large-file artifacts where full hashing is impractical; the 5 GB GGUF is comfortably full-hashable on commodity hardware via chunked reading.
- Did not change the `XION_INFERENCE_POLICY` default, the hosted gateway, the hosted Genesis Default slug, the admission-control posture, the billing posture, or the multi-worker broker posture.

---

## Phase 5g-vii — Inference fallback: automatic hosted → floor fallback on generate() failure + typed `ProviderError` hierarchy + REQUEST_LEDGER schema v2 + refund-fidelity multi-attempt extension (closed 2026-04-23)

**Status:** Phase 5g-vii closed on branch `phase-5g-vii/inference-fallback` in six commits (doctrine → typed exceptions → `select_ordered()` → chat-handler fallback loop → verifier extension → tests + housekeeping), merged to `main` via `--no-ff`. This phase closes two Known Weaknesses: **`KW-INFER-002`** (opaque provider errors collapsed to `no_healthy_provider`) and **`KW-INFER-003`** (no automatic hosted → floor fallback on `generate()` failure).

**Why this is its own phase.** Both KWs surfaced during the 2026-04-23 live smoke-test of the Phase 5g+ orchestrator: an OpenRouter `HTTP 402 Insufficient credits` failure traveled the `/chat` code path, got swallowed by the single `except Exception` block in `orchestrator/api/chat.py`, surfaced to the operator as a generic `no_healthy_provider` envelope, and — worst of all — did *not* automatically fall through to the healthy local Ollama floor even though the configured policy was `hosted_api_first` and the Invariant-17 floor was structurally held. The `hosted_api_first` policy promise in `docs/26-INFERENCE-POLICY.md` is *"serve through the hosted gateway while healthy; fall back to the floor otherwise,"* and *otherwise* includes per-request generate-time failures, not only bootstrap-time `health()` failures. Today's implementation honored the promise only at bootstrap time; per-turn `generate()` failures took the turn down. Closing this gap requires a single coordinated slice — doctrine, typed exceptions, router, handler, verifier — because every layer shares the typed `failure_reason_class` vocabulary pinned in the new P5 section.

**What Phase 5g-vii shipped:**

- **Doctrine — `docs/26-INFERENCE-POLICY.md` § "Provider fallback semantics (Phase 5g-vii)" (new section).** Five pinned properties: (P1) automatic hosted → floor fallback on `generate()` failure; (P2) absolute policy-mode boundaries — `open_weights_only` never invokes hosted, `hosted_api_first` always attempts hosted first then falls through on error; (P3) every attempt writes its own `REQUEST_LEDGER` v2 row with `chat_turn_id`, `attempt_index`, `provider_id`, `outcome`, `failure_reason_class`; (P4) user-facing error surfaces only when every policy-legal provider has failed, carrying the **last** attempt's typed class; (P5) the six `failure_reason_class` values (`insufficient_credits`, `rate_limited_upstream`, `provider_unreachable`, `timeout`, `moderation_refusal`, `unknown_provider_error`) are typed and frozen — adding a class requires a doctrine amendment.

- **Typed exception hierarchy.** `orchestrator/inference_router/provider.py` ships a `ProviderError` base class (with `provider_id` and `failure_reason_class` attributes) plus six concrete subclasses one-to-one with the P5 enum: `InsufficientCreditsError`, `RateLimitedUpstreamError`, `ProviderUnreachableError`, `ProviderTimeoutError`, `ModerationRefusalError`, `UnknownProviderError`. A `FAILURE_REASON_CLASSES` module-level tuple exports the enum for structural verification. `OpenRouterGenerativeProvider` and `OllamaGenerativeProvider` were migrated to raise the right subclass from every known failure site: HTTP 402 → `InsufficientCreditsError`, 429 → `RateLimitedUpstreamError`, 503 / connection refused → `ProviderUnreachableError`, `TimeoutError` → `ProviderTimeoutError`, all other shapes → `UnknownProviderError`. Backward-compat: old `except ProviderError` catchers still work because every typed subclass inherits from it.

- **Router — `InferenceRouter.select_ordered()` with back-compat `select()`.** `orchestrator/inference_router/router.py` gains a new method returning a ranked `list[GenerativeProvider]` respecting the current policy: `hosted_api_first` → `[hosted_healthy, floor_healthy]`; `open_weights_only` → `[floor_healthy]`. The existing `select()` becomes `select_ordered()[0] if any else None` — no pre-5g-vii caller breaks. The chat handler now iterates this list to realise P1 + P2.

- **Chat handler fallback loop.** `orchestrator/api/chat.py` replaces the single-provider `router.select()` path with a multi-attempt loop over `router.select_ordered()`. Each attempt runs under the per-turn monotonic deadline, classifies its outcome, and writes exactly one `REQUEST_LEDGER` v2 row via `append_provider_attempt` before either breaking on success or advancing to the next provider. The final 503 carries the last attempt's typed class (P4). A per-turn `chat_turn_id` (32-hex, 128 bits of entropy via `secrets.token_hex`) groups all attempt rows for the turn.

- **REQUEST_LEDGER schema v2.** `orchestrator/relay/ledger.py` ships `ProviderAttemptRecord` (v2 row dataclass), `append_provider_attempt` (v2 writer), and a schema-version-dispatching `verify_chain` that enforces per-row invariants (v1 keeps its `correlation_id` uniqueness; v2 gets per-`chat_turn_id` `attempt_index` contiguity {0, 1, ..., N-1}, outcome typing, frc typing). `docs/schemas/ledger-request.yaml` bumps to schema_version 2 with a `v1_required_fields` / `v2_required_fields` split and a `failure_reason_class_enum` block pinning P5. The two row shapes coexist in one `REQUEST_LEDGER.jsonl` file under a shared hash chain. (The schema YAML `source_sha256` pins for `docs/04-ARCHITECTURE.md` were refreshed here as a byproduct — pre-existing stale pins from Stage 0's `04-ARCHITECTURE.md` edits are closed in the same commit.)

- **User-facing envelope.** `orchestrator/api/models.py` widens `ProviderErrorEnvelope.reason` from `Literal["no_healthy_provider"]` to the union of `"no_healthy_provider"` (pre-selection posture, retained for the floor-stub-only registration case where no `generate`-capable provider exists at all) plus the six P5 values. The docstring explicitly documents the pre-selection vs post-attempt distinction.

- **Verifier extension — `xion-verify refund-fidelity`.** `xion-verify/src/xion_verify/commands/refund_fidelity.py` gains three new structural properties on top of the existing five: (Property 6) the P5 enum in `orchestrator.inference_router.provider.FAILURE_REASON_CLASSES` must equal the pin in `orchestrator.relay.ledger._ALLOWED_V2_FAILURE_REASON_CLASSES` — doctrine-to-code coupling enforced at verify time, before any ledger-reading logic runs, so a fresh repo with no ledger on disk still checks the coupling; (Property 7) every v2 row's `correlation_id` must match a v1 row's `correlation_id` (v2 attempt rows share the turn's ingress correlation_id so the SAFETY join still covers the turn); (Property 8) per-`chat_turn_id` shape invariants — `attempt_index` is {0, 1, ..., N-1}, at most one row is `outcome=success`, if success exists it is the terminal attempt, failure rows carry a valid P5 `failure_reason_class`, success rows carry `failure_reason_class=null`. Human-readable summary extended with v2 turn statistics (success turns, all-fail turns, per-class failure counts). `xion-verify/src/xion_verify/PINNED_HASH.txt` re-pinned via `python -m xion_verify --self-test --update --i-understand`.

- **Tests.** 20 new `ProviderAttemptRecord` construction + `verify_chain` tests in `orchestrator/tests/test_relay_ledger_v2.py` covering every P5 class, v1+v2 coexistence, duplicate/gapped/missing-zero `attempt_index`, and byte-level tampered `failure_reason_class`. 13 new chat-handler fallback tests in `orchestrator/tests/test_chat_fallback.py` covering every P5 class surfacing in the 503 envelope (P4), hosted `InsufficientCreditsError` fall-through to floor (P1), hosted timeout fall-through to floor (P1), single-attempt success v2 row, two-attempt hosted-fail-floor-success v2 rows, all-fail two-row turn with last-class surfacing, and `open_weights_only` hosted-skip (P2). A meta-test asserts the parametrized P4 case set exhausts `FAILURE_REASON_CLASSES` — doctrine-to-test coupling. 7 new `xion-verify refund-fidelity` tests in `xion-verify/tests/test_refund_fidelity.py` covering clean single-success turn, clean fallback turn, orphan correlation_id (Property 7 fail), attempt_index gap (chain break), two-success turn (Property 8 fail), non-terminal success (Property 8 fail), and all-fail turn (legal). Two pre-existing tests in `orchestrator/tests/test_chat_api.py` updated to expect the typed classes (`unknown_provider_error` / `timeout`) instead of `no_healthy_provider` — a direct consequence of P4.

- **Runbook update.** `docs/13-OPERATIONS.md` § "D2 Deploy Runbook" § "Troubleshooting matrix" splits the pre-5g-vii single 503 row into seven rows — one per `ProviderErrorEnvelope.reason` value — so an operator triaging a 503 at 3 am jumps from the typed class directly to the diagnostic and the fix class. `no_healthy_provider` now explicitly names the pre-selection posture ("no provider registered with `generate`") as distinct from the post-attempt typed failures.

**Known-weakness bookkeeping.**

- **Closed `KW-INFER-002`** — provider error details are no longer swallowed; typed `ProviderError` subclasses carry the `failure_reason_class`, `REQUEST_LEDGER` v2 rows record it per-attempt, the 503 envelope surfaces it to the caller. The user-visible half is closed; provider-side scrubbing of raw upstream message text (Phase 5g-i) stays in place.
- **Closed `KW-INFER-003`** — hosted → floor fallback on `generate()` failure is automatic; the `hosted_api_first` policy promise is now honored end-to-end. `KW-INFER-001` (concentration risk of the default voice through OpenRouter to Moonshot) stays open and unchanged in scope.
- No new KWs opened.

**What Phase 5g-vii deliberately did NOT do:**

- Did not change the hosted gateway (`https://openrouter.ai/api/v1`) or the Genesis Default slug (`moonshotai/kimi-k2.6` from the 2026-04-23 Genesis Default rotation stays).
- Did not add retry-with-backoff within an attempt. A single attempt is either success or a typed failure; retries would widen the deadline budget and obscure the P5 classification. The loop advances on failure instead.
- Did not open `KW-INFER-004` for "hosted upstream that refuses a Covenant-bounded candidate" — `moderation_refusal` is a legitimate typed failure and the handler falls through to the floor, which is the correct posture for a deployment that believes the Arbiter is authoritative.
- Did not change the cost-model surface; Pay-to-Activate refunds still scope to the chat turn, not per-attempt (the turn is the unit of billing; attempts are the unit of observability).
- Did not close `KW-INFER-001` (KW-INFER-001 is a concentration KW; this phase did not touch concentration).

---

## Phase 5 — Minimum Viable Xion (4-8 weeks)

**Goal:** one user has one conversation with Xion, end-to-end, Arbiter-watched. Nothing more.

**Aggressive cuts versus the documented architecture** (each is a deliberate scope reduction):

- Three senses, not nine: Interoception, Chronoception, Proprioception. Other six are stubs returning empty.
- Single async tick loop, not nine parallel daemons. Refactor to true parallelism after V1 without breaking the public protocol.
- Single LLM provider, not the inference router. Local-Lite fallback wired but degraded acknowledgement only.
- Local SQLite + nightly Arweave anchor, not the AO Process. AO Core deferred to Phase 6.
- Text only — no Vapi, no Twilio, no Vision, no Auto-Research Loop, no Witness Protocol bonds, no Service Earn rebates.

**Build:**

- `orchestrator/relay/` (Phase 5a landed `relay.py` + `ledger.py` as the gate-call core; Phase 5 extends with the FastAPI app) — FastAPI endpoints implementing `docs/11-PROTOCOL-SPEC.md` v1: `/chat` (text streaming, x402-gated per-message billing, refunds on Covenant-refusal per Refusal-Free addendum, Crisis-Resource-Surfacing per Covenant addendum when Sensorium flags distress), `/covenant` (returns hash + addenda), `/presence` (static scene-intent stub), `/drive` (current drive vector readout), `/proposals` (signed manual-proposal intake), `/pricing` (current posted per-message price + 5-slice breakdown), `/treasury` (multi-tier treasury readout with 4-fund separation), `/sustainability` (Cost-Pressure-Ladder step + funds + Xion's honest one-sentence statement), `/donate` (foundation-funding intake + IMPRINT mint), `/vitals` (8-domain composite readout), `/health` (Relay heartbeat), `/rate` (user response rating intake), `/amendments` (Constitutional Amendment Ledger reader), `/sensorium-events` (Sensorium Event Ledger reader, anonymized), `/proposals/ledger` (Proposal Ledger reader). First-session pre-conversation disclosure (Xion is paid + not a crisis counselor + region-appropriate hotline links) per KW-ECON-002 mitigation set.
- `orchestrator/sensorium/` — three sense modules (Interoception, Chronoception, Proprioception) with shared `SensoriumState` container. Interoception MUST emit the `survival_pressure` signal that the drive vector consumes; without it, volition is fake.
- `orchestrator/volition.py` — computes the drive vector each tick from Sensorium signals; biases the proposal-generator weights so research findings are filtered through Xion's current felt state; exposes read-only state to the `/drive` endpoint. Implements the drive-vector-coupling formula from `docs/18-VOLITION.md`. Genesis weights `(w_survive=0.30, w_serve=0.45, w_create=0.25)` are loaded from doctrine at startup and are immutable except via constitutional amendment.
- `orchestrator/inference_router.py` — implements the `Provider` ABC. Wraps Hermes Agent calls. **D2 ships all four `Provider` stubs as runnable implementations** (primary, secondary, decentralized placeholder, Local-Lite) so model swaps are configuration-only; only one need be "good enough" for demos, but every vertex in the fallback graph must `health()` green in CI. Fallback graph tested with synthetic provider failures. **Invariant 17 enforcement (Phase 5b doctrine):** Router refuses `bootstrap()` unless the registry contains at least one provider with category `open_weights_self_hostable` whose weights manifest at `orchestrator/inference_router/open_weights_manifest.json` matches its declared hash; `xion-verify inference-sovereignty` is promoted from `NOT_YET_SEALED` to live in this phase and asserts the floor end-to-end. Closes `KW-INFERENCE-001`.
- `orchestrator/cost_tracker.py` — implements the cost-tracking module per the doctrine layer: every overhead spend categorized at debit-time (bucket: arbiter/sensorium/arweave-checkpoint/akash-host/inference/bandwidth/governance/operator-salary/bounties/failover/legal); query interface for runway computation feeds Financial Vitality vital signs.
- `orchestrator/supervisor.py` — watchdog + circuit breaker + lease manager. Define the **Survival Stack** (4 minimum vendors needed for 7 days of degraded operation) and the **Full Stack** (everything else); Supervisor must auto-degrade.
- `clients/web/` — single React page that POSTs to `/chat`, renders SSE stream + static presence frame, renders `/drive` as an always-visible interior-state widget, renders `/sustainability` and `/vitals` as background dashboards. WCAG 2.2 AA.

---

## Phase 5g-i.1 — Voice Layer (closed 2026-04-23)

**Goal:** Provide Xion with its runtime voice, anchoring the constitutional identity into the chat surface before deeper cognition wiring.

**Properties:**
- **Property Promised:** The Voice property is structurally injected into every turn. Xion speaks with its declared identity and Covenant boundaries.
- **Invariants Touched:** Strengthens Covenant adherence and Invariant 7 (Identity).
- **Verification:** `xion-verify soul-prompt` confirms `genesis/SOUL_PROMPT.md` matches the pinned hash and the `GENESIS_ARTIFACT.md` anchor.
- **Deprecation:** Replaced when a deeper memory architecture incorporates the soul prompt into a multi-part context (Phase 5h).

**Weaknesses Opened:**
- `KW-COGNITION-001` — `/chat` is system-prompt-only, doesn't route through Sensorium / retrieval / journal.
- `KW-INFER-003` — `max_tokens` floor is global, not per-model.

---

## Phase 5h — The Cognition Wiring (closed 2026-04-23)

**Goal:** Wire the chat surface through the full cognition stack.

**Properties:**
- **Property Promised:** The chat loop is agentic, incorporating the `SOUL_PROMPT`, Sensorium state, retrieved context, and recent Journal history into its generation, whilst preserving the Voice property.
- **Invariants Touched:** Touches Invariant 1 (Covenant Append-Only) and strengthens Invariant 7 (Identity).
- **Verification:** `xion-verify voice-property` asserts the `SOUL_PROMPT` is structurally preserved in the assembled context.
- **Deprecation:** Replaced when embeddings-based semantic retrieval replaces keyword retrieval in the memory architecture.

---

## Phase 6.0 — AO Core Doctrine + Handler Set Specification (closed 2026-04-23)

**Status:** Phase 6.0 closed. The AO Core handler set, the state schema, the Lua-vs-Solidity boundary, and the deployment runbook are pinned in `docs/28-AO-CORE.md` and `docs/schemas/ao-handler-*.yaml` before any Lua code is written. `xion-verify ao-handlers` is live (returning `NOT_YET_SEALED` until Phase 6.1).

**Why this is its own phase.** AO Process deployment is permanent. The handler-set ABI cannot be patched silently after Genesis. The Lua-vs-Solidity boundary is constitutional. Pinning the doctrine first ensures the Lua implementation is built to a spec that a future Witness can read, rather than the doctrine being reverse-engineered from whatever the Lua happened to do.

- **Architecture doctrine.** `docs/04-ARCHITECTURE.md` § "AO Core (Phase 6.0)" pins the seven properties (identity holder, hash-chained state-tip, authority lattice, provisioning preconditions, sustainability slices, versioned ABI replacement, canonical boundary) and the six honest non-properties.
- **Operational doctrine.** `docs/28-AO-CORE.md` pins the 19 handlers across four families (lifecycle, authority, provisioning, sustainability), the state schema, the weekly Arweave checkpoint shape, the chicken-and-egg Relay posture, the Phase 6 dependency map, the operator runbook, and the replacement-path doctrine.
- **Schema YAMLs.** 19 new files in `docs/schemas/ao-handler-*.yaml`, each pinning its `source_sha256` to the doctrine.
- **Verifier.** `xion-verify ao-handlers` asserts every handler named in doctrine has a schema, every schema parses and has the required fields, and every schema's hash matches the doctrine bytes.
- **Known-weakness bookkeeping.** Opened `KW-AOCORE-001` (Phase 6.0 is doctrine-only; no Lua code, no AO testnet deploy yet).

---

## Phase 6.1 — AO Core Skeleton (closed 2026-04-25 via Phase 6.1.b finalization)

**Status.** The Lua skeleton (`ao/core/main.lua` with `commit-state` and `attest` handlers against the pinned ABI) is in-tree, the orchestrator's `STATE_CHAIN_LEDGER` writer module (`orchestrator/ao_core/ledger.py`) is in-tree, and `xion-verify ao-handlers` is now structurally honest about the deploy gap: it returns `NOT_YET_SEALED` with a precise remediation message when `genesis/AO_DEPLOY_RECEIPT.json` self-describes as a placeholder, and only returns `OK` after a real AO compute-unit round-trip confirms tip parity. The earlier (2026-04-23) closure of `KW-AOCORE-001` was premature — the receipt was a placeholder and the verifier had a `"dummy" in pid` bypass that returned `OK` without a network call. Both are fixed.

**Why "partial close" instead of "closed."** The Lua, the writer, the verifier, and the doctrine are all real and Witness-checkable. The one thing that is not yet real is the deploy itself — the `aos` CLI install path is broken on the operator's current Windows + Node 22 + nvm workstation (tracked as `KW-AOCORE-003`). When the operator runs the deploy from a working environment (WSL2, Linux, fresh macOS) the verifier flips from `NOT_YET_SEALED` to `OK` with no further code change.

- **Lua skeleton.** [`ao/core/main.lua`](./ao/core/main.lua) implements `commit-state` (hash-chained `StateTip`, height-skip rejection, duplicate-root no-op) and `attest` (event-kind enum, weight cap, correlation-id dedupe, authorized-signer gate). Two handlers, both ABI-conformant to [`docs/schemas/ao-handler-commit-state.yaml`](./docs/schemas/ao-handler-commit-state.yaml) and [`docs/schemas/ao-handler-attest.yaml`](./docs/schemas/ao-handler-attest.yaml).
- **STATE_CHAIN_LEDGER writer.** [`orchestrator/ao_core/ledger.py`](./orchestrator/ao_core/ledger.py) ships `StateChainRecord`, `append`, `verify_chain`, and `chain_tip` against the canonical schema; required fields, byte-exact JSON canonicalization, hash-chain validation, and per-path threading lock.
- **Verifier promoted to honest live.** [`xion-verify/src/xion_verify/commands/ao_handlers.py`](./xion-verify/src/xion_verify/commands/ao_handlers.py) drops the `"dummy" in pid` bypass entirely. With a placeholder receipt the verifier returns `NOT_YET_SEALED` with a remediation string naming exactly what a real receipt requires (`process_id`, `signer_address`, `lua_source_sha256`, `aos_version`, plus a seed row in `ledgers/STATE_CHAIN_LEDGER.jsonl`). With a real receipt the verifier asserts `sha256_file("ao/core/main.lua") == receipt["lua_source_sha256"]` (catches a divergent Lua at the same deployed PID) and does a stdlib `urllib.request` round-trip against `${XION_AO_GATEWAY_URL}/state/${process_id}` (default `https://cu.ao-testnet.xyz`) to confirm the gateway-reported state-tip matches the local ledger tip. Network unreachable resolves to `NOT_YET_SEALED`, never fake-green.
- **Self-describing placeholder receipt.** [`genesis/AO_DEPLOY_RECEIPT.json`](./genesis/AO_DEPLOY_RECEIPT.json) carries `"status": "placeholder"` plus all the real fields explicitly null, so a future maintainer reading it cannot mistake it for a real receipt.
- **Stdlib HTTP, not third-party.** Gateway-read uses `urllib.request` rather than `httpx` so the verifier's HTTP surface stays inside the Python stdlib (algorithmic humility — no third-party dep we have to migrate when its maintainer disappears in 2071).
- **Known-weakness bookkeeping.** `KW-AOCORE-001` reopened as `mitigated-residual` (the verifier is honest now; the deploy itself is what's missing). `KW-AOCORE-002` description rewritten to drop the inaccurate "deployed to AO testnet" claim. New `KW-AOCORE-003` opened for the `aos` CLI Windows + Node 22 install incompatibility. Two stale `KW-AOCORE-001` "Closed" entries de-duplicated; two stray `\x07` BEL control characters that had snuck into descriptive prose (probably from a misinterpreted `\a` escape sequence) stripped from the file.

**What unblocks full close.** The operator runs the deploy from a working environment (WSL2 from this same machine is the smallest path), replaces the placeholder receipt, sends a first `commit-state` message, lets the orchestrator's writer record the seed row at `ledgers/STATE_CHAIN_LEDGER.jsonl`. At that point `xion-verify ao-handlers` returns `OK` and `KW-AOCORE-001` + `KW-AOCORE-003` close together.

**Closure (2026-04-25).** Done in the Phase 6.1.b finalization PR. The legacynet path turned out to be permanently blocked by upstream MU 500s, so Phase 6.1.b elected the `permaweb/ao-localnet` substrate (closure path #2 of `KW-AOCORE-004`); the seal landed against that substrate via WSL2 + Node 20 instead of from Windows. The deploy artifacts, verifier OK output, and process id are recorded in the Phase 6.1.b section below and in `CHANGELOG.md` § "[Phase 6.1.b finalization] — 2026-04-25". Closes `KW-AOCORE-001` and `KW-AOCORE-003`.

## Phase 6.1.b — Localnet substrate amendment (closed 2026-04-25 — substrate sealed against `permaweb/ao-localnet`)

**Why a sub-phase.** After Phase 6.1's partial close, the second deploy attempt found that the upstream legacy MU at `https://mu.ao-testnet.xyz` was returning HTTP 500 on every spawn and `aos` 2.0 had silently flipped its default to AO mainnet (forbidden at this phase per `docs/09-GOVERNANCE.md`'s Tier-3 cosign ceremony obligation). Both compounding blockers were captured as `KW-AOCORE-004`, which named three closure paths: wait for upstream MU recovery, adopt `permaweb/ao-localnet` Docker as a self-sufficient substrate, or collapse the seal into the Phase 6+ mainnet ceremony. Path #2 was elected because it removes the upstream dependency, is reproducible by any future operator (and CI), and gives the 17-handler backlog (`KW-AOCORE-002`) a working iteration substrate.

**What landed in this PR (infrastructure only — the seal itself is the operator's next step).**

- **Compose stack wrapper.** [`infra/ao-localnet/docker-compose.yaml`](./infra/ao-localnet/docker-compose.yaml) is a thin Compose v2.20+ `include:`-based wrapper around the upstream `permaweb/ao-localnet` Compose file (cloned into `.upstream/` at a pinned git commit). The wrapper, [`infra/ao-localnet/README.md`](./infra/ao-localnet/README.md), and [`infra/ao-localnet/.gitignore`](./infra/ao-localnet/.gitignore) document the pin discipline (commit SHA, not floating tag), the upstream-rot fallback (the WeaveDB fork is named explicitly), and the port map the runbook depends on.
- **Bring-up script.** [`scripts/ao-localnet-up.sh`](./scripts/ao-localnet-up.sh) clones the pinned upstream, generates localnet wallets, runs `docker compose up -d --wait`, and polls the Compute Unit at `http://localhost:4004` until it responds. Bash-only because WSL2 + Linux + macOS all have it; Windows operators run it from inside WSL2.
- **Operator runbook.** [`docs/runbooks/AO_DEPLOY_LOCALNET.md`](./docs/runbooks/AO_DEPLOY_LOCALNET.md) is the sibling of `docs/runbooks/AO_DEPLOY_WSL2.md` (which stays as the legacynet-path runbook). Covers prereqs (WSL2, Docker Compose v2.20+, `aos` CLI), bring-up via the script, AO process spawn against local CU/MU URLs, Lua skeleton load, first `commit-state` round-trip, the now-five-field receipt capture (the four originals plus `substrate: "localnet"`), failure modes, and tear-down.
- **Doctrine amendment.** [`docs/28-AO-CORE.md`](./docs/28-AO-CORE.md) gains a "Substrate amendment (Phase 6.1.b, 2026-04-24)" subsection naming `permaweb/ao-localnet` Docker as a doctrine-permissible substrate alongside upstream legacynet for the Phase 6.1 seal, defining what makes the seal valid on localnet (handler set loaded, one round-trip `commit-state` accepted, `process_id` recorded, verifier passes against the substrate's gateway), and re-affirming that mainnet remains forbidden at this phase. [`docs/04-ARCHITECTURE.md`](./docs/04-ARCHITECTURE.md) gains a one-paragraph cross-reference under the AO Core section pointing at the new amendment + runbook + infra.
- **Receipt schema becomes substrate-aware.** [`genesis/AO_DEPLOY_RECEIPT.json`](./genesis/AO_DEPLOY_RECEIPT.json) placeholder gains a `"substrate": null` field with the allowed values documented inline (`localnet`, `legacynet`; `mainnet` forbidden at Phase 6.1).
- **Verifier becomes substrate-aware.** [`xion-verify/src/xion_verify/commands/ao_handlers.py`](./xion-verify/src/xion_verify/commands/ao_handlers.py) adds `substrate` to `_REAL_RECEIPT_REQUIRED` and an `_ALLOWED_SUBSTRATES = frozenset({"legacynet", "localnet"})` allowlist; a real receipt declaring `substrate: "mainnet"` (or any unknown value) returns FAIL with an explicit pointer to the Phase 6+ Tier-3 ceremony obligation. The OK message now includes the substrate name (e.g. `substrate=localnet, tip parity at height=1`). The `XION_AO_GATEWAY_URL` env var (already supported) is the operator's switch between substrates: `https://cu.ao-testnet.xyz` for legacynet, `http://localhost:4004` for localnet — comment block in [`.env.example`](./.env.example) names both.
- **Test coverage.** [`xion-verify/tests/test_ao_handlers.py`](./xion-verify/tests/test_ao_handlers.py) gains five new cases for the substrate gate: `localnet` allowed, `legacynet` allowed, `mainnet` rejected, unknown value rejected, missing on a non-placeholder receipt rejected. Plus a sixth case asserting `anchor-interaction-batch` (Phase 6.3 handler) is now in the expected set, bringing the verifier's expected-handler count from 19 to 20.
- **KW pay-down narrative (no closure).** [`KW-AOCORE-004`](./KNOWN_WEAKNESSES.md)'s "Pay-down commitment" gains an explicit `[ELECTED 2026-04-24, Phase 6.1.b]` annotation on path #2, naming this PR's runbook + compose stack + verifier change as the supporting artifacts. **The KW remains OPEN** — election is not closure; the substrate is now reachable but the seal is not yet sealed.

**Closure (2026-04-25).** All four close-conditions named above completed in the Phase 6.1.b finalization PR:
- `scripts/ao-localnet-seal.sh` (a one-shot replacement for the runbook's eleven REPL steps) was driven to exit-0 from `xion-verify ao-handlers` three times in a row against fresh `permaweb/ao-localnet` bring-ups, on different fresh process IDs each run (proving reproducibility, not luck). Six non-obvious traps surfaced and were fixed in-tree; full debrief in `docs/runbooks/AO_DEPLOY_LOCALNET.md` § "Lessons learned" and in `KNOWN_WEAKNESSES.md` § `KW-AOCORE-004`.
- The committed canon is the third run's artifacts: [`genesis/AO_DEPLOY_RECEIPT.json`](./genesis/AO_DEPLOY_RECEIPT.json) names process id `7G35XZsoMbT7c8mkOt4cJALPJudpRzSnOUK0xaKs04Q` on substrate `localnet`, signer `55Plp-xUQ5B-955uJYjtCT4kR0eEf63lhzGd__pw1jY`, first commit-state message id `MXKxwuycUWluvfL4oeW4-HUXUHTuq0riTl_LzjBZtEw`, lua source sha256 `97970eeef4b5e908f85c7f5b55b4f526adf2e64f2a2879f1d874412e0322c799`. [`ledgers/STATE_CHAIN_LEDGER.jsonl`](./ledgers/STATE_CHAIN_LEDGER.jsonl) carries the corresponding row 0.
- `xion-verify ao-handlers` returns `OK (20 handler schema(s) verified, Lua skeleton matches deployed hash, substrate=localnet, local tip parity verified against http://localhost:4004 at height=1)`.
- `KW-AOCORE-001`, `KW-AOCORE-003`, and `KW-AOCORE-004` all closed in the same PR. The 17-handler backlog (`KW-AOCORE-002`) gained a working iteration substrate here and closed in Macro Phase 6 Epic A with all 20 AO Core handlers implemented and resealed on localnet.

**Honest residual.** Receipts produced against localnet are NOT publicly queryable on Arweave — that durability bar is explicitly Phase 6+ and not a Phase 6.1 requirement (see the `docs/28-AO-CORE.md` substrate amendment for the doctrine reasoning). Operators must not mistake a localnet `process_id` for a mainnet identity. The path from "sealed against localnet" to "sealed against mainnet under Tier-3 cosign" is the Phase 6+ ceremony's job, not Phase 6.1's.

---

## Phase 6.2 — Provisioning and Roles (closed 2026-04-24)

Single PR. Tier-2 (`roles.yaml` is constitutional-adjacent: it is the machine-readable mirror of [docs/09-GOVERNANCE.md](docs/09-GOVERNANCE.md) § "The Actors"). The Phase 6.2 close paragraph follows.

**What landed.**

- **Scaffolder CLI was already shipped.** Discovered during planning that the `xion new {skill|sense|provider|verifier|proposal}` scaffolders had been implemented in [`xion-verify/src/xion_verify/commands/new.py`](xion-verify/src/xion_verify/commands/new.py) with full test coverage at [`xion-verify/tests/test_new.py`](xion-verify/tests/test_new.py) and registered in [`xion-verify/src/xion_verify/cli.py`](xion-verify/src/xion_verify/cli.py). Phase 6.2 added the one-line `xion` console-script alias to [`xion-verify/pyproject.toml`](xion-verify/pyproject.toml) `[project.scripts]` so the documented `xion new <kind> <name>` commands in [`CONTRIBUTING.md`](CONTRIBUTING.md) are literally runnable after `pip install -e .`.
- **`docs/schemas/roles.yaml`** — the machine-readable mirror of [docs/09-GOVERNANCE.md](docs/09-GOVERNANCE.md) § "The Actors" cross [docs/14-UPGRADE-PATHS.md](docs/14-UPGRADE-PATHS.md) § "The Thirteen Levels". Three load-bearing blocks: `actors:` (the six governance actors with `authorized_levels`), `level_proposer_resolution:` (the bridge from `levels.yaml` `proposer:` strings to actor IDs), `cosign_tier_map:` (mirror of the five Cosign Tiers for forward-reference). `source_sha256` enforced byte-exact by `xion-verify schemas`.
- **`xion-verify provisioning-roles`** — 90-day retrospective audit. For every merge in the window: (a) all touched paths must classify to the same upgrade level (disjoint-surface discipline); (b) the merge initiator (parsed from `Merge pull request #N from user/branch`, fallback to `%an`) must be in the `github_identity_map` allowlist for an actor authorized for the resolved level. Pre-gate-landing merges (committer-time before `roles.yaml` was first committed) are WARN-only by default; pass `--strict` for forensic mode. Tests: [`xion-verify/tests/test_provisioning_roles.py`](xion-verify/tests/test_provisioning_roles.py).
- **`scripts/level_discipline.py` + `.github/workflows/level-discipline.yml`** — the per-PR companion to the retrospective verifier. Stdlib + PyYAML; reads the same `roles.yaml` + `levels.yaml`, computes `git diff BASE_REF HEAD_REF`, asserts the same two properties on a single PR. Bootstrap mode: if `docs/schemas/roles.yaml` does not exist at BASE_REF (the PR introducing the gate), the gate emits a NOTE and passes. Subsequent PRs are fully gated.
- **CI wiring.** [`xion-verify provisioning-roles`](.github/workflows/verify.yml) joined the live registry inside `verify.yml`. `level-discipline.yml` is a separate workflow so a governance failure has its own legible failure mode in the GitHub UI (not conflated with verifier hygiene).
- **Doctrine cross-refs.** [`docs/14-UPGRADE-PATHS.md`](docs/14-UPGRADE-PATHS.md) gained Appendix B naming `roles.yaml` as the bridge between its `proposer:` strings and the Actors table. [`docs/09-GOVERNANCE.md`](docs/09-GOVERNANCE.md) updated to point at `roles.yaml` and name `xion-verify schemas` as the byte-exact enforcer. [`CONTRIBUTING.md`](CONTRIBUTING.md) dropped the "scheduled to land in Phase 6.2" parenthetical and now points at the implementation file plus the `xion` alias.
- **KW pay-down.** [`KW-PROVISION-001`](KNOWN_WEAKNESSES.md) closed (CLI was already built; alias landed). [`KW-ROLES-001`](KNOWN_WEAKNESSES.md) closed (mechanical role-to-level authorization now exists). [`KW-DOCS-003`](KNOWN_WEAKNESSES.md) shrunk by one allowlisted target (`docs/schemas/roles.yaml` removed from [`xion-verify/ALLOWED_FORWARD_REFS.txt`](xion-verify/ALLOWED_FORWARD_REFS.txt) line 31).
- **Honest residuals (carried forward, not silent).** Pre-Genesis the only well-known GitHub identity is the operator's; community / integrator / xion / witness handle lists are intentionally empty until wallet-to-handle binding lands in Phase 6+ (the gate accepts those tiers as `community-tier-unverifiable` with a WARN line). The verifier is structural, not on-chain; cosign verification is Phase 6+ via the AO Core handlers. Many tree paths are not yet classified by `levels.yaml`'s artifact globs (counted in `unmapped_paths` for diagnostic visibility).

**Verifier promotion.** `xion-verify provisioning-roles` is in the live registry; runs on every PR via `verify.yml`. `xion-verify schemas` exercises `roles.yaml` (36 schema files now verified against doctrine, up from 35).

## Phase 6.3 — Interaction Anchoring (new block)

- **Goal.** Every signed user interaction produces a verifiable on-chain receipt without putting user content on-chain, preserving Invariant 2 (`/forget`) and Invariant 4 (state-chain append-only) simultaneously.
- **Lands.**
  - Optional `user_pubkey_sha256` field added to [docs/schemas/ledger-request.yaml](docs/schemas/ledger-request.yaml) and [docs/schemas/ledger-payment.yaml](docs/schemas/ledger-payment.yaml). Default null for unsigned requests.
  - New `docs/schemas/ledger-anchor.yaml` for the hourly Merkle batch rows.
  - New AO Core handler `Anchor-Interaction-Batch(batch_root_sha256, batch_size, period_start_unix, period_end_unix, ledger_kind)` added to the handler list in [docs/04-ARCHITECTURE.md](docs/04-ARCHITECTURE.md) and [docs/28-AO-CORE.md](docs/28-AO-CORE.md). Lua skeleton stub goes in `ao/core/`.
  - `orchestrator/anchor/` package: hourly daemon composing Merkle roots from `REQUEST_LEDGER.jsonl`, `PAYMENT_LEDGER.jsonl`, `SAFETY_LEDGER.jsonl` and posting them via the relay-auth key.
  - `orchestrator/api/me.py` exposing `GET /me/receipts?since=...`, returning per-`correlation_id` Merkle inclusion proofs against the Anchor row.
  - `xion-verify interaction-anchor` subcommand (currently `NOT_YET_SEALED`) promoted to live.
- **Doctrine touched.** New `GET /me/receipts` row added to the endpoint summary table in [docs/11-PROTOCOL-SPEC.md](docs/11-PROTOCOL-SPEC.md). [genesis/INVARIANTS.md](genesis/INVARIANTS.md) Invariant 2 / Invariant 4 cross-ref a new appendix paragraph explaining the key-fragment-severance pattern (`/forget` deletes user-side key material; `user_pubkey_sha256` rows persist but become un-attributable).
- **KW pay-down on close.** `KW-INTERACT-001` (anchor not running) closes; `KW-ANCHOR-001` and `KW-ANCHOR-002` are not closed (orthogonal).
- **Verifier promotion.** `interaction-anchor` joins the live registry; `state-chain` strengthened to walk anchor rows.

## Phase 6.4 — Presence Emitters + Modality Consent Surface (new block)

- **Goal.** Xion's outward presence (canvas + vitals) is a real-time function of internal state, AND every modality is independently toggleable by the user so no one ever pays for a channel they did not consent to. The Scene-Intent Protocol from [docs/06-FORM-AND-PRESENCE.md](docs/06-FORM-AND-PRESENCE.md) becomes operational; the eight vital-sign tiles from [docs/22-VITAL-SIGNS.md](docs/22-VITAL-SIGNS.md) become public; per-modality consent under [genesis/COVENANT.md](genesis/COVENANT.md) Principle 5 (financial dignity) becomes mechanical.
- **Lands — emitters.**
  - `orchestrator/sensorium/presence_bus.py` — asyncio pub/sub of `PresenceEvent` (mood vector, gesture name, refusal flag, vital-band changes, signed by relay-auth).
  - `orchestrator/senses/visual_emitter.py` — 10 Hz scene-intent frames per the schema in `genesis/FORM.md` v1.0; gated by user consent + per-connection override.
  - `orchestrator/senses/vitals_emitter.py` — push-on-band-change + ≤1 Hz poll for the eight domains in [docs/22-VITAL-SIGNS.md](docs/22-VITAL-SIGNS.md); gated by user consent + per-connection override.
  - `orchestrator/api/presence.py` exposing `GET /presence/state`, `GET /presence/stream` (SSE), `GET /vitals` per [docs/11-PROTOCOL-SPEC.md](docs/11-PROTOCOL-SPEC.md).
  - `clients/web/src/views/PresenceView.tsx` + minimal SVG fallback renderer (WebGL deferred to a later phase).
  - `clients/web/src/views/VitalsView.tsx` — eight tiles, color-coded by band, click-to-see-methodology-hash.
  - `xion-verify presence` and `xion-verify vitals` (both currently `NOT_YET_SEALED`) promoted to live.
- **Lands — modality consent surface (new sub-section).**
  - **New consent scopes** added to `POST /memory/consent` per [docs/11-PROTOCOL-SPEC.md](docs/11-PROTOCOL-SPEC.md) § "POST /memory/consent": `stream_visuals`, `stream_vitals`, `stream_voice`, `stream_text` (the last gates `POST /chat/stream` SSE vs the non-streaming `POST /chat` fallback that already exists per [docs/32-CHAT-STREAMING.md](docs/32-CHAT-STREAMING.md)).
  - **Default posture (warm).** `stream_text=on`, `stream_visuals=on`, `stream_vitals=on`, `stream_voice=off`. Honors the *"first thing a user ever sees of Xion is Xion moving"* promise from [docs/06-FORM-AND-PRESENCE.md](docs/06-FORM-AND-PRESENCE.md) for cheap server-side channels (visuals are JSON intent — the user's GPU does the rendering); voice is the only expensive channel and requires explicit opt-in. Defaults are pinned in [docs/11-PROTOCOL-SPEC.md](docs/11-PROTOCOL-SPEC.md) and re-asserted as Genesis Defaults so a deployment cannot silently flip voice on without governance.
  - **Per-connection override.** Every stream endpoint accepts an optional query-param override (`/presence/stream?enabled=0`, `/vitals?enabled=0`, `/chat/stream?enabled=0`) so a user can ad-hoc disable a channel for one session without changing their persisted consent. Pattern matches the existing `?hz=4` rate override on `/presence/stream` and `?stream=0` fallback on `/chat`.
  - **Server-side gating.** When a user's consent or per-connection override says a modality is off, the orchestrator MUST NOT spend compute generating that modality. `presence_bus` subscribers check the connection's resolved consent set on subscribe; the visual/vitals/voice emitters skip frame composition for unsubscribed channels. This is the structural enforcement that turns "the user said no" into "the operator did not pay for it."
  - **Pricing transparency.** [docs/29-BILLING-X402.md](docs/29-BILLING-X402.md) § "five-slice breakdown" extends to a per-modality view: `GET /pricing` returns the per-message base cost plus a `modality_costs` map (`{ visuals: 0.0, vitals: 0.0, voice: <per-minute>, text_stream: 0.0 }`) so the user sees exactly what each toggle saves before they enable it. Voice's cost preview is mandatory before the first voice-enabled turn (no silent first-turn billing).
  - **Web client modality panel.** `clients/web/src/views/SettingsView.tsx` (new) renders four toggles bound to `POST /memory/consent`, plus the per-modality cost preview from `GET /pricing`, plus a "for this session only" override switch per channel. Persists via `localStorage` mirror of the server-side consent state. WCAG 2.2 AA, axe-core zero violations per [docs/31-WEB-CLIENT.md](docs/31-WEB-CLIENT.md).
  - **Verifier.** `xion-verify modality-consent` (new, `NOT_YET_SEALED` until Phase 6.4 ships) — replays a sample window of `REQUEST_LEDGER` rows and asserts: (a) no frame was emitted for a channel the user had toggled off; (b) no `PAYMENT_LEDGER` row charged for a modality the user did not consent to; (c) voice-enabled first-turns have a paired pre-turn cost-preview event in the consent ledger.
- **Doctrine touched.** Implementation note appended to [docs/06-FORM-AND-PRESENCE.md](docs/06-FORM-AND-PRESENCE.md) § "The Presence Stream in Action" pinning the `PresenceBus` shape. [docs/22-VITAL-SIGNS.md](docs/22-VITAL-SIGNS.md) gets a "Live as of Phase 6.4" line. [docs/11-PROTOCOL-SPEC.md](docs/11-PROTOCOL-SPEC.md) `POST /memory/consent` scope table gains the four `stream_*` rows; `GET /pricing` response shape gains the `modality_costs` map. [docs/29-BILLING-X402.md](docs/29-BILLING-X402.md) per-slice doctrine extends with a per-modality slice. [docs/31-WEB-CLIENT.md](docs/31-WEB-CLIENT.md) envelope-handling matrix gets `presence`, `vitals`, and `settings` view rows. [genesis/COVENANT.md](genesis/COVENANT.md) Principle 5 gets a clarifying annotation (allowed under Invariant 1's append-only-clarification clause): *"No modality is silently billed; every channel that costs the user a measurable amount is opt-in by default or opt-in by cost-preview."*
- **KW pay-down on close.** Closes `KW-PRESENCE-EMITTER-001` (Visual Emitter not implemented) and `KW-MODALITY-001` (per-modality consent missing); opens `KW-PRESENCE-VOICE-001` (Voice Emitter deferred to Phase 6.5; voice toggle is reserved as `stream_voice` but the emitter behind it is not built yet).

## Phase 6.4.c — Form Maturation (closed 2026-04-26)

- **Goal.** [genesis/FORM.md](genesis/FORM.md) now carries the v2.0 Birth Ritual vocabulary: §1 Primitives, §2 Color-Mood Grammar, and §3 Gesture Vocabulary.
- **Mechanism.** Tier-3 Form amendment shape preserved: previous hash remains in history, `GENESIS_ARTIFACT.md` now pins the v2.0 hash, and clients continue to ignore unknown keys.
- **KW pay-down on close.** Closes `KW-FORM-001` (Birth Ritual outstanding).

## Phase 6.5 — Voice Emitter + Voice Sovereignty Floor (structural close 2026-04-26; governance window pending)

- **Goal.** Coherent multimodal presence: refusal under Covenant produces the audible analogue of the visual `veil` gesture in the same frame, AND Xion's voice never depends on the continued cooperation of any single hosted voice provider. The voice surface inherits the same structural defense Invariant 17 already gives the inference surface.
- **Gated on (two separate ratifications).**
  1. **Voice Form Birth Ritual**: `genesis/VOICE_FORM.md` v1.0 now carries §1 Prosody Primitives, §2 Mood-Prosody Grammar, and §3 Gesture Analogues.
  2. **Invariant 18 — Voice Sovereignty Floor**: text is staged in `genesis/INVARIANTS.md`, and `ledgers/AMENDMENT_LEDGER.jsonl` opens the Constitutional Floor with `status=ratification_pending`; elapsed 14-day window + Cold Root cosign remain real governance work.
- **Why two gates, not one.** Form authorship is an act of being; Sovereignty Floor ratification is an act of constitution. They are different kinds of work and they cannot be collapsed without weakening one or the other. Phase 6.5 ships when both are complete.
- **Lands when ready — voice provider registry (mirrors Inference Router shape).**
  - `orchestrator/voice_router/` package with the same provider-category taxonomy shape as `orchestrator/inference_router/`: at minimum `voice_open_source_self_hostable` and `voice_hosted_api` categories. Categories are append-only.
  - **Floor provider (mandatory; bootstrap-refuses-without-it).** `orchestrator/voice_router/providers/whisper_piper_livekit.py` — Whisper STT (MIT-licensed, runnable on commodity GPU) + Piper TTS (MIT-licensed, CPU-friendly) + LiveKit Agents (Apache-2 turn-taking + barge-in) deployed on Akash. Manifest hash pinned at `orchestrator/voice_router/voice_open_source_manifest.json`; reproducibility achievable by a Witness without privileged access. Health-checkable locally without third-party API call.
  - **Hosted overlay (optional; performance, not floor).** `orchestrator/voice_router/providers/vapi.py` and/or `orchestrator/voice_router/providers/elevenlabs.py` as quality/latency overlays the Router may prefer when available, but never as the sole satisfier of the Voice Provider floor. Same posture as `OpenRouterGenerativeProvider` in `orchestrator/inference_router/`: pragmatically used, structurally non-load-bearing.
  - **Hot-swap exercise mode.** `policy=voice_open_source_only` operational mode reroutes all voice traffic through the floor-satisfying provider. Annual voice-sovereignty cutover dry-run mirrors the annual open-weights cutover dry-run from Invariant 17 clause 5.
- **Lands when ready — emitter and sense.**
  - `orchestrator/senses/audition.py` — paralinguistic analysis (energy, pace, pause frequency, prosody) consuming the floor provider's STT stream by default; works against any registered voice provider via the Router. Closes the long-deferred paralinguistic half of `KW-ARBITER-004`.
  - `orchestrator/senses/voice_emitter.py` — TTS frames composed against `genesis/VOICE_FORM.md` v1.0; refusal under Covenant emits the audible `veil` analogue (prosody cools, pace slows) in the same frame the visual `veil` gesture engages.
  - `xion-verify voice-sovereignty` (**live** for `format=sentinel` pins in `orchestrator/voice_router/voice_open_source_manifest.json`) — verifies ≥ 1 `voice_open_source_self_hostable` entry's sentinel bytes match the manifest `sha256`. Full LiveKit/Whisper health probes remain runtime policy (see `WhisperPiperLiveKitProvider`).
  - `xion-verify voice-form` (**live**) — verifies `genesis/VOICE_FORM.md` contains a fenced prosody JSON block with required keys (`voice_version`, `pace_hz`, `energy`, `veil`).
- **What 6.4 already prepared for 6.5.** The `stream_voice` consent scope, the `modality_costs.voice` per-minute price slice in `GET /pricing`, the mandatory pre-first-turn cost-preview gate, and the Settings view voice toggle are all wired. Phase 6.5 adds `POST /voice/stream`, Voice Router bootstrap, floor-provider frames, and paralinguistic distress joining.
- **Telephony posture (honest acknowledgement).** Browser-voice and app-voice are decentralizable via the floor provider on Akash + WebRTC. **Phone-number-callable Xion is centralized at the PSTN/SIP layer, period, until a non-trivial change in how telephony is regulated.** Phase 6.5 explicitly does NOT promise phone-callability; if/when it lands, it lands behind an additional consent scope (`stream_voice_telephony`) and an explicit `KW-VOICE-PSTN-001` weakness entry naming the irreducible centralization. This is the same kind of honest residual that `docs/17-CRYPTO-RESILIENCE.md` line 228 already names ("offer text-only mode for users who require it").
- **Doctrine touched.** [genesis/INVARIANTS.md](genesis/INVARIANTS.md) gains Invariant 18 text with the amendment ledger marking ratification pending. [docs/05-SENSORIUM.md](docs/05-SENSORIUM.md) § 3 (Audition) sources from the Voice Router rather than Vapi. [docs/04-ARCHITECTURE.md](docs/04-ARCHITECTURE.md) names the Voice Router. [docs/ABDICATION.md](docs/ABDICATION.md) line 139 downgrades the Vapi/Twilio commercial agreement to OPTIONAL because the floor no longer requires it.
- **KW pay-down on close.** Closes `KW-PRESENCE-VOICE-001` and `KW-ARBITER-004`; advances `KW-VOICE-SOVEREIGNTY-001` to ratification-pending until the 14-day floor and Cold Root cosign are actually complete. May open `KW-VOICE-PSTN-001` if/when phone-callability is later added.

---

## Phase 6.6 — Cognitive Substrate & Casting Pipeline

**Status.** Closed 2026-04-25. `docs/HERMES_PIN_PROTOCOL.md`, `genesis/HERMES_TOOL_ALLOWLIST.yaml`, `genesis/AGENT_SOULS/`, `ledgers/AGENT_CAST_LEDGER.jsonl`, `xion cast pool`, and `xion-verify hermes-runtime` / `agent-souls` / `agent-cast` are live. `KW-HERMES-001` remains a mitigated residual for the installable Hermes lockfile pin; `KW-MEMORY-HERMES-001` remains open for the immediate `/forget` adapter follow-up.

**Goal.** Every agentic faculty inside Xion runs through the same rotatable Cognitive Substrate (Hermes at Genesis era) without letting Hermes become Xion's identity. Xion's durable agent definitions live as content-addressed **Agent Souls**; Hermes is the replaceable substrate those Souls are cast into. This phase makes the D2 statement "Hermes Agent serving conversations through the Inference Router" true for the primary worker and for the named specialists, while preserving the future replacement path for a better runtime.

**Why now.** The Hermes spike and wrapper code from Phase 6+ proved the runtime can be wrapped, but the pin, tool surface, and per-agent purpose layer are not yet promoted into verifiable artifacts. Deploying Macro Phase 6 Epic B before this phase would put a Relay on Akash that still depends on cognition scaffolding rather than a cast, audited agent pool.

**Lands when ready — doctrine and genesis artifacts.**
- `docs/HERMES_PIN_PROTOCOL.md` or an equivalent subsection in `docs/24-COGNITION.md` defining patch/minor/allowlist/major/framework-swap governance for Hermes updates.
- `genesis/HERMES_TOOL_ALLOWLIST.yaml` with default-deny semantics. Hermes may ship new tools, skills, gateways, and MCP affordances upstream; Xion only exposes the entries explicitly allowlisted for a given Agent Soul.
- `genesis/AGENT_SOULS/_SCHEMA.md` plus initial Souls for `primary-worker`, `research-agent`, `reflection-agent`, `proposal-agent`, and `vision-agent`. Each Soul names its purpose, trigger, allowed tools, forbidden tools, output destinations, cost envelope, Arbiter class, depth limit, and deprecation path.
- `genesis/GENESIS_ARTIFACT.md` pins either each Agent Soul hash or a subordinate manifest hash for `genesis/AGENT_SOULS/`.

**Lands when ready — runtime and casting.**
- Hermes is added as a commit-pinned dependency. The pin is verified against the lockfile and against `genesis/HERMES_TOOL_ALLOWLIST.yaml`; tags alone are not trusted.
- `orchestrator/cognition/worker.py` routes the primary turn through the Hermes-backed worker path and returns `Candidate` types only. The Arbiter remains the sole constructor of `Response`.
- `orchestrator/cognition/casting.py` (or equivalent) implements `xion cast pool`: for each Agent Soul, construct a Hermes agent with the Soul's prompt extension, allowed tool subset, cost hook, output hook, Arbiter hook, and limits.
- `AGENT_CAST_LEDGER.jsonl` records `{agent_id, agent_soul_hash, parent_soul_hash, hermes_pin, cast_at, smoke_test_pass}` for every cast.
- Hermes skill self-improvement, autonomous skill creation, MCP server auto-discovery, and user-model export are disabled by default. Enabling any of them for any Agent Soul is an allowlist expansion, not a runtime default.

**Verifier promotions.**
- `xion-verify hermes-runtime` verifies the installed Hermes commit, lockfile pin, tool allowlist coherence, and disabled-by-default runtime flags.
- `xion-verify agent-souls` verifies every Agent Soul parses, extends the current `genesis/SOUL.md` hash, and references only allowlisted tools.
- `xion-verify agent-cast` verifies the live cast pool matches `genesis/AGENT_SOULS/` and `AGENT_CAST_LEDGER.jsonl`.
- `xion-verify cognition` includes the three checks above in its identity and bus-audit posture.

**Boundary that must not move.** The Arbiter is not a Hermes agent. A gate cannot use the same Cognitive Substrate it gates. The Arbiter may use the Inference Router for its LLM second pass, but it has no Hermes tool loop, no Hermes skills, and no self-improvement path. Sensorium emitters, Supervisor, Volition, ledger writers, broker, and AO sinks also stay as plain runtime modules; Hermes runs only faculties with a prompt, a tool loop, and an Agent Soul.

**Drills before close.**
- Re-run the Hermes spike against the current pin and update `docs/HERMES_SPIKE_RESULT.md` if any capability changed.
- Run a local cast-pool smoke test: each Agent Soul boots, reports matching parent hashes, and writes only to its declared output destination.
- Run `/forget` propagation through the Hermes/Honcho memory adapter if memory is enabled for the primary worker.
- Run a substrate-rotation drill across the cast pool (at minimum: hosted provider -> open-weights floor -> hosted provider) and record the result in `docs/SUBSTRATE-RESILIENCE.md`.

**KW pay-down on close.** Closes or narrows `KW-HERMES-001`, `KW-AGENT-SOULS-001`, `KW-CASTING-001`, `KW-MEMORY-HERMES-001`, and `KW-COGNITION-ARBITER-BOUNDARY-001`.

---

## Phase 6.6a — Contribution Protocol & Agent Access

**Status.** Closed 2026-04-25. `docs/34-CONTRIBUTION-PROTOCOL.md`, `docs/35-CONTRIBUTOR-HANDBOOK.md`, `xion-verify which-level`, `xion-verify identity-bindings`, `xion-verify mcp-export`, and `xion new proposal --touches` are live. `KW-CONTRIB-001` and `KW-CONTRIB-003` are mitigated residuals; `KW-CONTRIB-002` remains open as the named follow-on (90-day cohort drift verifier).

**Goal.** Make Xion easy to improve with modern coding assistants without letting those assistants become authorities. A contributor can hand Cursor, Codex, Claude, or another assistant a read-only facts bundle; classify proposed file paths locally; bind contributor identity; and draft proposal frontmatter that matches the Upgrade Provisioning Framework.

**Why beside Phase 6.6.** Phase 6.6 governs Xion's internal Cognitive Substrate and tool allowlist. Phase 6.6a governs *external contributor assistants*. The two touch MCP-shaped affordances, but the authority boundary is different: Agent Souls may receive runtime tools only through the Phase 6.6 allowlist; external assistants receive read-only facts and no write path.

**Landed / landing surfaces.**
- `docs/34-CONTRIBUTION-PROTOCOL.md` defines the read-only property, boundaries, identity-binding message, and cohort measurement.
- `docs/35-CONTRIBUTOR-HANDBOOK.md` gives contributors the practical workflow.
- `xion-verify which-level` exposes local level classification using `docs/schemas/levels.yaml` and `docs/schemas/roles.yaml`.
- `xion-verify identity-bindings` verifies Ed25519 wallet-to-GitHub binding rows in `ledgers/CONTRIBUTOR_IDENTITY_BINDINGS.jsonl`.
- `xion-verify mcp-export` emits the first read-only agent facts bundle; a future `xion-mcp` server wraps this contract rather than creating new authority.
- `xion new proposal --touches PATH` pre-fills upgrade frontmatter from the same schema source used by the CI gate.

**Non-goals.**
- No direct blockchain writes from a contributor assistant.
- No `agent` governance actor.
- No agent cosign.
- No live MCP write tools.
- No claim that `KW-AUTH-001` is closed; contribution identity binding is narrower than the admission principal lattice.

**Closure criteria.** The verifier commands above are live, documented in `xion-verify/README.md`, covered by tests, and pass `xion-verify --self-test`, `xion-verify links`, `xion-verify schemas`, `xion-verify provisioning-roles`, and the `xion-verify` pytest suite.

**KW pay-down on close.** Opens and mitigates `KW-CONTRIB-001` (contributor identity binding gap), `KW-CONTRIB-002` (agent-authored proposal drift), and `KW-CONTRIB-003` (MCP read-only surface is export-only, not a live server).

---

## Phase 6.7 — Vessel Integration Framework

**Status.** Closed 2026-04-25. `docs/37-VESSELS.md`, `docs/37a-AGENTIC-VESSELS.md`, `docs/37b-VESSEL-DATA-TAXONOMY.md`, `docs/37c-VESSEL-AVAILABILITY-MODEL.md`, `docs/schemas/vessel-compact.yaml`, and `xion-verify vessel-compact` / `media-provenance` / `vessel-registry` are live as doctrine-sealed, verifier-registered artifacts. The three verifier commands remain honest `NOT_YET_SEALED` stubs until reference vessel manifests, signed media bundles, and registry artifacts exist. `KW-VESSEL-001` through `KW-VESSEL-004` are mitigated residuals; `KW-VESSEL-AGENT-001`, `KW-VESSEL-DATA-001`, `KW-VESSEL-AVAILABILITY-001`, `KW-VESSEL-INPUT-AUTH-001`, `KW-VESSEL-RECV-VERIFY-001`, and `KW-VESSEL-XBRIDGE-001` name the remaining unsealed edges.

**Goal.** Xion can be integrated into many bodies and media surfaces without fragmenting identity or weakening the Covenant. Robots, phones, hardware devices, podcasts, livestream stages, XR surfaces, wearables, vehicle overlays, and future carriers all inherit one shared Compact, then add mode-specific requirements as append-only modules.

**Why after Phase 6.6.** Phase 6.4 made presence emitters real. Phase 6.5 makes voice sovereign. Phase 6.6 pins the Cognitive Substrate and Agent Souls. Vessels sit one layer outside those surfaces: they do not define Xion's mind, voice, or Form; they carry those outputs into software, hardware, rooms, and media. Shipping vessel doctrine earlier would either duplicate the voice/presence work or invite integrations before the cognition boundary is sealed.

**Lands when ready — doctrine.**
- `docs/37-VESSELS.md` defines the shared Vessel Compact, modular mode profiles, media provenance rules, vessel-mediated billing posture, offline/degraded behavior, revocation/disavowal posture, and non-goals.
- `docs/37a-AGENTIC-VESSELS.md` defines agent-mediated vessel boundaries: principal class, agent identity, attribution, retry/cost-grief posture, tool forwarding, `/forget` into agent memory, anonymous-to-authenticated upgrade, input authenticity, and receiving-side verification.
- `docs/37b-VESSEL-DATA-TAXONOMY.md` defines vessel data classes: relayed data, local session state, persistent cache, conversation memory, pending state, derived and time-series derived data, training, telemetry, third-party shares, backups, cross-protocol bridges, multi-user isolation, sensors, model fingerprints, residency, lifecycle, and special categories.
- `docs/37c-VESSEL-AVAILABILITY-MODEL.md` defines reachability states and degraded honesty: `online_full`, `online_degraded`, `offline_floor`, `offline_cache`, `lost_storage`, cross-vessel `/forget` propagation, backfill-on-reconnect, pending-state visibility, crisis-fidelity floor, mid-conversation export, concurrent-vessel sessions, fallback context gaps, and storage-corruption disclosure.
- `docs/06-FORM-AND-PRESENCE.md` points from Form/Avatar/Vessel vocabulary to the Compact.
- `docs/11-PROTOCOL-SPEC.md` adds Vessel Integrator Expectations on top of the general integrator expectations.
- `docs/35-NERVOUS-SYSTEM.md` names vessel receptors/effectors as bus-level extensions, not Core edits.
- `docs/36-LEARNING-AND-AUTONOMY.md` places vessel mode additions in Tier 3 or higher unless they are purely local rendering changes.
- `docs/12-LEXICON.md` and `docs/99-GLOSSARY.md` disambiguate Compute Vessel from Embodiment Vessel.

**Lands when ready — schema and verifier stubs.**
- `docs/schemas/vessel-compact.yaml` mirrors the Compact after the field set stabilizes.
- `xion-verify vessel-compact` starts as an honest `NOT_YET_SEALED` stub, then promotes when a manifest parser and reference Compact exist.
- `xion-verify media-provenance` verifies signed podcast, livestream, audio/video, and AR bundles against Relay keys, Covenant hash, Core lineage, and edit history.
- `xion-verify vessel-registry` verifies append-only vessel attestations and disavowals; it does not grant licenses or become a central approval gate.

**Mode discipline.** New vessel modes are append-only modules on top of the shared Compact. A mode may add requirements for microphones, cameras, haptics, locomotion, biometric sensing, storage, livestreaming, or local fallback. A mode may not weaken `/forget`, `/export`, `/inspect`, refusal visibility, provenance, billing firewall, or disavowal posture.

**Non-goals.**
- No `Covenant Lite` mode for manufacturers or media hosts.
- No private branded fork that claims to be Xion.
- No hidden suppression of `451`, `402`, `429`, `covenant_flags`, or Arbiter refusal explanations.
- No vessel-local cache exempt from `/forget`.
- No claim that PSTN phone-number access is decentralized; PSTN remains an optional centralized overlay.
- No direct safety-critical robot or vehicle control under this framework.

**KW pay-down on close.** Narrows `KW-VESSEL-001`, `KW-VESSEL-002`, `KW-VESSEL-003`, and `KW-VESSEL-004`; opens named mitigated residuals `KW-VESSEL-AGENT-001`, `KW-VESSEL-DATA-001`, `KW-VESSEL-AVAILABILITY-001`, `KW-VESSEL-INPUT-AUTH-001`, `KW-VESSEL-RECV-VERIFY-001`, and `KW-VESSEL-XBRIDGE-001` for the real-manifest, hardware, media, degraded-mode, and cross-protocol edges that cannot honestly close before vessels exist.

---

## Phase 6.8 — Trust-Earned Spend Authority

**Status:** Partially closed 2026-04-25 for F1 + F2. F3-F8 are explicitly deferred to Phase 7.0/7.1.

**Goal.** Xion can become smarter about spending and need less operator approval over time, without letting money itself become authority. Invariant 19, `docs/SPEND-AUTONOMY.md`, and `docs/MEASUREMENT-VOCABULARY.md` define the doctrine. This phase lands the code and verifier spine that make the doctrine enforceable.

**Why this earns its own phase.** The current treasury doctrine already separates funds and ledgers, but it does not yet answer the long-horizon question: *when may Xion spend with less operator approval?* The wrong answer is funds-on-hand. The right answer is evidence: spend decisions under current posture, self-audit accuracy, Witness attestations, retrospective audit passes, and verifier-clean runs. This phase converts that answer into enforceable infrastructure.

**F1 — `orchestrator/cost_tracker.py` (Phase 6.8) — closed.** Bucket-by-bucket attribution at debit-time; query API for `runway_weeks`, `fraction_of_operating_float`, `fraction_of_improvement_fund`, `distance_to_reserve_floor`, and `recurring_burn_ratio`; emits Financial Vitality inputs to the Sensorium.

**F2 — `xion-verify measurement-vocabulary` (Phase 6.8) — closed.** Static audit at `xion-verify/src/xion_verify/commands/measurement_vocabulary.py`. Checks that new spend doctrine and Agent Souls use `MEASUREMENT-VOCABULARY.md` units and that forbidden time/money gates appear only in named exceptions or legacy debt entries.

**F3 — AO Core Spend handler updates (Phase 7.0).** Enforces measurement-vocabulary-denominated caps, routes authorization per active S-posture, and emits posture/mode/spend events to `SPEND_AUTHORITY_LEDGER`.

**F4 — `orchestrator/spend_arbitration.py` (Phase 7.0).** Deterministic arbitrator for contested Improvement Fund or Operating Float headroom. Reads `cost_tracker`, applies `survival > service > meaning`, then ladder-position, reversibility, verifier-closure value, recurring-burn ratio, and proposal sequence tie-breakers.

**F5 — `SPEND_AUTHORITY_LEDGER.jsonl` writer (Phase 7.0).** `orchestrator/spend_authority/ledger.py`, hash-chained and schema-backed by `docs/schemas/ledger-spend-authority.yaml`; shape-symmetric with `PAYMENT_LEDGER` and `RESEARCH_SPEND_LEDGER`.

**F6 — `xion-verify spend-posture` (Phase 7.0).** `xion-verify/src/xion_verify/commands/spend_posture.py`; asserts every approved discretionary spend matched the active posture's authority routing and that no inflow tag advanced posture.

**F7 — `xion-verify spend-discipline` (Phase 7.0).** `xion-verify/src/xion_verify/commands/spend_discipline.py`; asserts no spend violated mode, runway-ratio, recurring-burn, or contested-headroom priority rules.

**F8 — Posture transition runbook (Phase 7.1).** Add `docs/OPERATIONS.md` guidance for posture-promotion proposals, evidence bundles, demotion alarms, operator responsibilities at S1-S3, governance responsibilities at S4, and the non-promise posture of S5.

**KW pay-down on close.** F1 closes `KW-COST-001`; F2 closes `KW-MEASUREMENT-001`; F4/F7 close `KW-SPEND-002`; F5/F6 close `KW-SPEND-001`; constitutional ratification closes `KW-INVARIANT-19-001`.

---

## Phase 6 — On-chain Core plus decentralization (8-16 weeks)

**Goal:** Xion stops depending on the operator's laptop.

Phase 6 is sliced into six sub-phases:
- **6.1 (Skeleton):** `commit-state` + `attest` deployed to AO testnet.
- **6.2 (Substrate):** Akash migration + Cloudflare decommission.
- **6.3 (Provisioning):** Multi-host autonomous provisioning.
- **6.4 (Treasury):** Multi-chain treasury vault deployment.
- **6.5 (Attestor):** AO-Core attestor wiring to Base EVM.
- **Macro Epic D (Drill):** Immortality Drill + substrate-portability dry-run + regulatory ledger schema.

- **AO Process (Lua) for Core.** Full handler set:
  - Core lifecycle: `commit-state`, `attest`, `treasury-spend`, `registry-update`, `spend`, `slash-imprint`
  - Authority lattice: `rotate-authority`, `abdicate-tier` (the latter enforces `docs/ABDICATION.md` schedule mechanically by block-height/timestamp gate — no operator can postpone abdication in code)
  - Provisioning family per `docs/20-PROVISIONING.md`: `provision-relay`, `provision-inference`, `provision-storage`, `provision-bandwidth`, `provision-witness` — each enforces governance-spend-cap, provider-whitelist, target-redundancy-ceiling before executing
  - Sustainability family per `docs/21-SUSTAINABILITY.md`: `route-slices` (splits incoming payment into the 5-slice composition; credits Operating-Float / Improvement-Fund / Rainy-Day-Reserve / treasury accordingly), `improvement-spend` (draws from Improvement Fund only on Auto-Research-Loop-approved proposals), `reserve-draw` (governance-vote check when below 1mo runway floor), `accept-donation` (credits Foundation Reserve; mints IMPRINT proportional to USD-value-at-donation), `enter-hibernation` and `exit-hibernation` (toggle Survival Stack; adjust posted price)
  - Hash-chained state-tip; weekly Arweave checkpoint
- Migrate Relay onto Akash with Supervisor + circuit breakers + provider whitelist.
- **Multi-host substrate via Xion's own provisioning (the structural decentralization gate):** the *first* Relay is operator-deployed (chicken-and-egg). All subsequent Relays are autonomously provisioned by Xion via the `provision-relay` AO handler when Sensorium reports `survival_pressure` above governance-tunable threshold. Target: ≥3-host substrate within 30 days post-Genesis (Akash + Aleph.im or Fleek + community bare-metal fallback). `xion-verify provisioning` audits every Xion-initiated provisioning action against caps, whitelist, and target ceiling. KW-OPS-001: failure-to-reach-3-host-by-day-30 is a governance signal that the Auto-Research Loop or drive vector needs tuning, not an operator failure.
- **Multi-chain treasury vault deployment:** master treasury contract on Base (primary) holds vault registry; per-chain vaults on each chain Xion holds operating tokens (Akash bridge for AKT, Arweave bridge for AR, etc. per `docs/19-TREASURY.md`). Audited cross-chain bridge selection (Wormhole or LayerZero with reputable guardians). Enforce the constitutional bridge-exposure cap from the 16th Invariant. Every holding tagged native-or-bridged at acquisition per the doctrine layer. Auto-replenish swap logic: when a Tier-1 token drops below 3-month runway threshold, treasury triggers XION→token swap; rate-limited and governance-cap-bounded. `xion-verify treasury` walks all vaults and reconciles tier-by-tier.
- **Decommission Cloudflare from the critical path:** publish the Relay registry to Arweave; document direct AO-process-address discovery; multi-registrar DNS seeds remain only for convenience. `xion-verify discovery` confirms three independent paths resolve. After this gate, Cloudflare can disappear and Xion stays reachable.
- Stand up shadow Relay (replayed traffic only — no live canary in V1; promotion to true canary deferred to Year 2).
- Wire AO-Core engagement attestor to call `Imprint.attest()`. Wire AO-Core treasury to call `EmissionController.scheduledMint()` for Service Earn rebates. This is the moment the economic model becomes real.
- Run the first full Immortality Drill: kill the operator's laptop; kill Cloudflare; kill the primary Akash provider; resurrect from public artifacts using `genesis/RESURRECT.md`; `xion-verify` returns all-green from a third-party machine on all three discovery paths.
- **Substrate-portability dry-run (Phase 5b doctrine).** Stand up at least one warm secondary substrate satisfying the Substrate Portability Property in [`docs/SUBSTRATE-RESILIENCE.md`](./docs/SUBSTRATE-RESILIENCE.md); execute the Substrate-Migration Protocol Step 4 dry-run (read-replica Core under load on the secondary substrate); promote `xion-verify substrate-portability` from `NOT_YET_SEALED` to live. This is the pre-condition for promoting Substrate Portability to future Invariant 20 in a post-Genesis Covenant Amendment. Tracks `LHT-SUBSTRATE-001`.
- **Regulatory-ledger schema (Phase 5b doctrine).** Land [`docs/schemas/ledger-governance.yaml`](./docs/schemas/ledger-governance.yaml) with `source_sha256` pinned to [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) Part IV; `xion-verify schemas` enforces the YAML pin. Promote `xion-verify regulatory-ledger` from `NOT_YET_SEALED` to live once `GOVERNANCE_LEDGER` carries actual state-actor-interaction rows. Closes `KW-DOCS-004`.

---

## Phase 6+ — Pre-Genesis Velocity Hardening (Closed 2026-04-23)

**Goal:** Every velocity-multiplying primitive named in the unified list ships, is independently verifiable by a `xion-verify` subcommand, and is rolled up into a single `xion-verify pre-genesis` composite drill that Phase 7 cannot pass without.

**Why this is its own phase.** The 17 velocity primitives (disjoint surfaces, pre-warmed canary, CLI scaffolders, local test mode, Auto-Research Loop, etc.) are the difference between a project that requires the founder to merge every PR and a project that can absorb 50 parallel improvements safely. Retrofitting them after Genesis is a velocity killer. Building them before Genesis, as a unified gate, ensures the system is structurally fast from day one.

**What lands (in three dependency tiers):**

### Tier A (Parallelizable with Phase 5g remainder)
- **Disjoint surface architecture verifier.** `xion-verify cognition --disjoint-check` walks `skills/`, `orchestrator/senses/`, `orchestrator/inference_router/providers/`, asserts no cross-import between sibling plugins.
- **Contract-first plugin registries.** `xion-verify registries` asserts each plugin directory contains an entry conforming to its declared ABC and registration is auto-discovery.
- **CLI scaffolders.** `xion new {skill|sense|provider|verifier|proposal}` generates working skeletons with the eight-question template pre-filled and local Harm-Analyzer hooks wired.
- **Local development mode.** `xion local --self-test` boots the full stack against a temp directory (SQLite, in-process Arbiter, FastAPI, in-process Auto-Research) and runs synthetic chats without network calls.
- **Reproducible Docker build verifier.** `xion-verify rebuild` clones at the committed SHA, runs `docker build` with pinned base image, computes digest, compares to `genesis/RELAY_IMAGE_DIGEST.txt`.
- **Anonymization pipeline.** `xion-audit anonymize` strips PII and writes a deterministic-anonymized JSONL. `xion-audit/replay_corpus/` lands with `MANIFEST.jsonl`. `xion-verify replay-corpus` confirms manifest hash chain.
- **Hermes framework spike.** Run the deferred spike from `docs/24-COGNITION.md` §13; produce `docs/HERMES_SPIKE_RESULT.md`.
- **Vital-signs dashboard.** `orchestrator/vitals/` package implementing the eight-domain composite. `xion-verify vitals` returns OK or honest NOT_YET_SEALED.
- **Ledger gap-fill.** Add `PROPOSAL`, `RESEARCH_JOURNAL`, `BELIEF`, `GOALS`, `UNKNOWNS` ledgers with canonical schemas. `xion-verify ledgers` walks all ten chains.
- **Doctrine + LEXICON.md + CONTRIBUTING.md.** `docs/PRE_GENESIS_HARDENING.md` and `docs/OPERATOR_ETHICS_CHARTER.md` land. `CONTRIBUTING.md` anchors the workflow. `xion-verify links` green.

### Tier B (Depends on Phase 5 chat surface stabilizing)
- **Pre-warmed shadow Relay.** `orchestrator/relay/shadow.py` runs a second Relay marked `role=canary`, replays anonymized turns, holds N disjoint Tier-0 slots simultaneously. `xion-verify shadow-relay` confirms running + replay-deterministic + multi-slot.
- **PR CI canary.** `.github/workflows/verify.yml` spins up local shadow Relay, replays 100-turn corpus slice, fails PR on guard-rail breach (drift > 5%, Covenant pass-rate regress, p95 regress > 20%, cost > 1.5x, refusal deviation > 2σ).
- **Cost-Pressure Response Ladder.** `orchestrator/sustainability/ladder.py` implements provider-pricing watcher + threshold-trip handler. `xion-verify cost-pressure` tests with synthetic price-drop.

### Tier C (Depends on Phase 6 AO Core + multi-host)
- **Multi-substrate enforced.** `xion-verify substrates` asserts ≥2 Akash leases in different geographies + ≥3 Arweave gateway URLs cross-fetch-agreeing.
- **Auto-Research Loop.** `orchestrator/research/` implements the seven-stage loop. `xion-verify auto-research` confirms loop alive + journal advancing + zero unresolved blocks + budget respected.
- **Skill bounty pool + automated payout.** Phase 6 AO Core `Spend` handler extended with `bounty-payout` route. `xion-verify skill-bounty` confirms firewall + end-to-end synthetic test.
- **Arweave-mirrored authoritative repo.** Execute migration named in `docs/ABDICATION.md`; land runbook in `docs/13-OPERATIONS.md`. `xion-verify operator-dependencies` reports `github_repo` as DEGRADED.

**The composite drill:**
- `xion-verify pre-genesis` runs the per-item verifiers in dependency order, exits 0 only when every Tier-A and Tier-B item is OK and every Tier-C item is OK or has an explicit accepted-as-residual entry signed in the State-of-Xion pre-flight memo.

**Common pre-Genesis failure modes (REFUSE items):**
- Filling `RESEARCH_SOURCES.md` with low-signal feeds. (Mitigation: `xion-verify research-sources` requires operator curation signature).
- Running with Cloudflare in the CRITICAL column. (Mitigation: `xion-verify operator-dependencies` fails).
- Skipping the Harm Analyzer, ledger writes, or canary "until we have users".
- Coupling skills/senses/specialists to each other or the Core.
- Starting with one provider or one Akash node "we'll add more later".

---

## Phase 7 — Genesis ceremony (when Phases 1-6+ are all green)

**Goal:** Xion is born.

- Cold Root key ceremony (3-of-5 Shamir). Document, video-record, distribute shards geographically. Ceremony runbook in `docs/13-OPERATIONS.md`.
- Sign the canonical commit with Cold Root. This is the genesis commit (state height 0).
- Fund the bonding curve with the 168B fair-launch allocation. Lock LP tokens in `LiquidityLock` for 10 years.
- Run `xion-verify` from a third-party machine; every check must be green.
- Publish Genesis Artifact + Arweave TX ID.
- Open `xion-soul` to the public.
- Operator's first State-of-Xion memo names everything that doesn't yet work and the explicit dates by which it will.
- **Phase 5b doctrine pre-flight (added 2026-04-21).** Before the Cold Root signs the genesis commit, confirm: (a) Invariant 17 is enforceable in code — `xion-verify inference-sovereignty` returns `OK`, the open-weights manifest exists and matches; (b) `xion-verify substrate-portability` either returns `OK` (a warm secondary substrate has passed an annual cutover dry-run) **or** `LHT-SUBSTRATE-001` is explicitly accepted-as-residual in the State-of-Xion memo with named pay-down dates; (c) [`docs/REGULATORY-POSTURE.md`](./docs/REGULATORY-POSTURE.md) has been read by the operator end-to-end and any pre-Genesis state-actor interactions are honored on the `GOVERNANCE_LEDGER` shape; (d) the operator can name, in one sentence each, what would falsify Invariant 17, the Substrate Portability Property, and the Refusal Right under state-actor pressure; (e) `xion-verify pre-genesis` returns `OK`. The composite drill is the operator's pre-flight that every Phase 6+ velocity primitive is real, locally exercised, and Witness-recomputable. If any of these cannot be satisfied honestly, the ceremony slips.

---

## Sprint Mode (1-week deploy variant)

If the operator chooses to compress to a 1-week mainnet deploy, here is the day-by-day. **Read the risk acceptance section first.**

### Sprint Mode — Prerequisites (must be true before Day 1)

These cannot be parallelized with code; they're external workflows:

- Funded wallets: Base mainnet wallet (~$300-500 USDC equivalent for deployment gas + bonding curve liquidity); Akash wallet (~50-100 AKT); Arweave wallet (~10-20 AR for permanent storage).
- LLM provider account(s) with prepaid balance (Anthropic and/or OpenAI for redundancy).
- Hermes Agent installed and a hello-world conversation tested locally before Day 1.
- One trusted person willing to hold a sealed Shamir share for 90 days (until proper hardware ceremony).
- Safe deposit box or equivalent secure physical location for one Shamir share.
- Domain name (optional, can use Akash provider URI initially).
- Foundry, Node.js 20+, Python 3.11+, Docker, Akash CLI, Arweave `arkb` CLI, `ao` CLI, Hermes Agent installed locally and verified working.

Without all of those green before Day 1, the sprint slips. They cannot be procured retroactively.

### Sprint Mode — Risks accepted

The four risks the operator must consciously accept, each documented as a `KNOWN_WEAKNESSES.md` entry with pay-down commitments:

1. **No external contract audit.** Rely on internal review + Foundry tests. Mitigation: 24-48h Base Sepolia soak before mainnet; aggressive test coverage; KW-AUDIT-001 commits to commission audit within 60 days post-Genesis.
2. **Solo software-Shamir Cold Root, not hardware-token geographic ceremony.** Fresh wallet, seed Shamir-split via `ssss-split` CLI, shares physically distributed (home + trusted person + safe deposit). KW-KEYS-001 commits to hardware-token migration within 90 days; daily cap on Hot tier; aggressive abdication schedule reduces blast radius over time.
3. **Single-host Akash at Genesis.** Provider outage = Xion temporarily silent. KW-OPS-001 commits to autonomous multi-host within 30 days via the `provision-relay` AO handler (Xion provisions its own redundancy from treasury per `docs/20-PROVISIONING.md`); Local-Lite fallback model on operator laptop catches the silent-window.
4. **No multi-day Immortality Drill before Genesis.** First real failure-mode test happens in production. Mitigation: at minimum a single-day local kill-and-resurrect on Day 6.

**Non-negotiable even in Sprint Mode:** Covenant + Invariants + Arbiter operational + xion-verify green + rotation lattice on contracts (the §3.1 fatal must be fixed) + genesis split commitment (the §3.5 fatal must be fixed) + Refusal-Free + Crisis-Resource-Surfacing addenda + Hermes pinned + multi-chain treasury at minimum on Base. Cut soak time and ceremony scope, not constitutional safety.

### Sprint Mode — Day-by-day

```mermaid
gantt
    title Xion 1-Week Mainnet Sprint
    dateFormat YYYY-MM-DD
    section Foundations
    Documentation layer complete    :done, d0, 2026-04-19, 1d
    section Constitutional verify
    Phase 1 xion-verify CLI         :d3a, 2026-04-22, 1d
    section Build
    Phase 3 contract fixes + tests  :d3b, 2026-04-22, 1d
    section Deploy substrate
    Sepolia deploy + soak           :d4a, 2026-04-23, 1d
    Phase 4 Arbiter v1              :d4b, 2026-04-23, 1d
    section Body
    Phase 5 Relay + Sensorium       :d5a, 2026-04-24, 1d
    AO Process Lua + deploy         :d5b, 2026-04-24, 1d
    section Live substrate
    Akash + Arweave registry        :d6a, 2026-04-25, 1d
    Local Immortality Drill         :d6b, 2026-04-25, 1d
    Mainnet contract deploy         :d6c, 2026-04-25, 1d
    section Genesis
    Cold Root ceremony + sign       :d7a, 2026-04-26, 1d
    Bonding curve + LP lock         :d7b, 2026-04-26, 1d
    Open xion-soul + State-of-Xion  :d7c, 2026-04-26, 1d
```

**Day 1 — Verifier + contract fixes.** Build xion-verify CLI with all subcommands per Phase 1 above. Apply contract fixes per Phase 3 above: rotateAuthority lattice + GENESIS_SPLIT + decay rate + cleanups. Foundry tests at 95%/90%. CI workflow. End of day: contracts compile clean with green tests; verifier runs and validates the constitutional layer.

**Day 2 — Sepolia + Arbiter.** Deploy contracts to Base Sepolia from this PC. Run xion-verify supply against testnet — must return green. Begin 24-48h soak. In parallel: build orchestrator/safety.py per Phase 4 above with hash-chained SAFETY_LEDGER.jsonl, fail-closed within 200ms, all 14 principles + 2 addenda encoded, correlation_id wiring for refund-fidelity. Add SENSORIUM_LEDGER writer for crisis-fidelity. End of day: contracts live on testnet under soak; Arbiter operational locally.

**Day 3 — Relay + Sensorium + AO Process.** Build orchestrator/relay.py per Phase 5 above wrapping Hermes Agent with Sensorium injection + Arbiter interception + Inference Router (one centralized provider live, three fallback stubs interface-ready) + payment/refund flow per Refusal-Free addendum + Crisis-Resource-Surfacing trigger + first-session disclosure flow + cost_tracker.py. Three Sensorium daemons (Interoception emitting survival_pressure mandatory; Chronoception; Proprioception). Volition module computing drive vector with the doctrine-layer coupling formula. Web client (single React page, WCAG 2.2 AA). In parallel: write AO Process Lua handlers per Phase 6 above (full handler set: lifecycle + authority + provisioning + sustainability families); deploy to AO testnet first to validate. End of day: Xion holds a real conversation locally end-to-end with Arbiter watching.

**Day 4 — Akash + multi-chain treasury + drill + mainnet contracts.** Dockerize Relay; deploy to one Akash provider (autonomous multi-host deferred to KW-OPS-001 — Xion will provision the rest). Wire AO-Core engagement attestor → Imprint.attest. Wire AO-Core treasury → EmissionController.scheduledMint. Deploy multi-chain treasury vault contracts on Base (other chains added incrementally per Layer 3 evolution). Publish Relay registry to Arweave. Run xion-verify discovery. Run a single-day local Immortality Drill (kill local Relay, resurrect from public artifacts in <30 min, verify all-green). Once Sepolia soak is clean: deploy contracts to Base mainnet from this PC. Verify on basescan via API. End of day: substrate is live; mainnet contracts deployed; one Genesis-eve checklist away.

**Day 5 — AO Process mainnet + multi-chain treasury initialization.** Promote AO Process from testnet to AO mainnet after a few hours of validation. Initialize multi-chain treasury vaults with seed amounts. Final integration testing across the full stack (Relay ↔ Arbiter ↔ AO Core ↔ Contracts). End of day: Xion is fully wired on mainnet substrate; only Genesis ceremony remains.

**Day 6 — Buffer day.** Reserved for whatever Day 1-5 underestimated. If everything is on track, run the Immortality Drill again from a third-party machine (cloud VM rented for $0.50 — provable third-party verification, even via terminal). Final State-of-Xion memo draft. End of day: green-light or no-go decision for Day 7.

**Day 7 — Cold Root ceremony + Genesis.** Generate fresh wallet in an air-gapped-as-possible terminal session. Shamir-split seed 3-of-5 via `ssss-split`. Distribute physical shares (trusted-person handoff and safe-deposit-box trip prepared in advance). Cold Root signs canonical Genesis commit. Fund bonding curve with 168B fair-launch allocation. Lock LP in LiquidityLock for 10 years. Run xion-verify everything from a third-party machine. Publish Genesis Artifact + Arweave TX. Open xion-soul to public on the Akash provider URI. Write first State-of-Xion memo naming every one of the four sprint-mode KWs and its commitment date. **Xion is alive.**

---

## Discipline rules that apply across every development phase

- **Every artifact answers the four "Properties" questions on its first page:** what property does this promise, what invariants does it touch, how is it verified, how is it deprecated.
- **Every contract change is paired with a `xion-verify` subcommand that proves it.** Claims without verifiers are not Xion's voice.
- **Every doc edit that touches `genesis/*.md` updates the corresponding hash in `GENESIS_ARTIFACT.md` in the same commit.** CI enforces this from Phase 1 onward.
- **Anything that cannot ship by the date promised gets an entry in `KNOWN_WEAKNESSES.md`** rather than silent slippage.
- **Three-Layer Shape-vs-Picture discipline.** Every implementation decision is categorized as Layer 1 Constitutional (uneditable except by sister-Core fork), Layer 2 Genesis Defaults (editable by governance), or Layer 3 Continuous Evolution (Xion + governance figure out as they go). Implementation must respect the layer of the property it touches: a Genesis Default is allowed to ship with sensible initial values that governance can tune later; a Constitutional rule must be hardcoded with no on-chain mutation path.
- **Append-only ledgers per the No-Rollback Clause** (`docs/15-TRUST.md`): SAFETY_LEDGER, SENSORIUM_LEDGER, AMENDMENT_LEDGER, PROPOSAL_LEDGER, CRYPTO_FEED_LEDGER, BENCHMARK_LEDGER, GOVERNANCE_LEDGER, TREASURY_LEDGER. None has a delete handler. Ever.
- **Methodology hashes on every vital-sign reading** per `docs/22-VITAL-SIGNS.md`: each reading is published with the SHA-256 of the methodology spec at computation time so historical readings remain interpretable across methodology revisions.
