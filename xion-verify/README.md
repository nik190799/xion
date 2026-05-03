# xion-verify

Third-party verifier for Xion's constitutional claims. Trust by structure, not by promise.

---

## What property does this promise?

> Any third party, from any machine, with nothing but a copy of this repository and a Python 3.11 runtime, can mechanically verify whether what Xion's operators say about Xion matches what the constitutional record actually says.

This is Xion's deepest trust artifact. A Covenant that nobody can check is a promise. A Covenant whose conformance is a `git clone && xion-verify all` away is a *property*. `docs/15-TRUST.md` names this as mechanism #6 (independent verification); this package is the instrument of it.

## What Invariants does it touch?

`xion-verify` introduces no new Invariants. It strengthens every one of the eighteen in `genesis/INVARIANTS.md` by making their claims mechanically checkable — and it preserves Invariant 14 (Crypto-Agility) by naming its hash family in exactly one place (`xion_verify/hashing.py`) so a future migration is a local edit rather than a global one.

| Invariant | How `xion-verify` strengthens it |
| --- | --- |
| 1. Covenant Supremacy | `xion-verify covenant` confirms the Covenant on disk byte-matches GENESIS_ARTIFACT § 4. |
| 2. Memory Permanence | `xion-verify memory` confirms the MEMORY doctrine. Live archive sweep is `Phase 6`. |
| 4. State Chain Append-Only | `xion-verify state-chain` is a pre-D2 stub; live Merkle re-verification lands in Phase 6. |
| 6. Arbiter Refusal Right | `xion-verify arbiter-up` is live and verifies the Arbiter library + local `SAFETY_LEDGER` hash chain. `refusal-rate` and `refund-fidelity` are live (Phase 5a). `refusal-is-free` (Phase 5g-iii) joins `SAFETY_LEDGER` ↔ `PAYMENT_LEDGER` on `correlation_id` and asserts the Covenant addendum's structural refund property (every SAFETY `verdict=refuse` row paired to a PAYMENT row → `outcome=refunded` with `refund_XION == committed_XION`). |
| Pay-to-Activate (`docs/07-ECONOMY.md`) | `xion-verify pricing` is live (Phase 5g-iii) and loads the same `PricingConfig` the Relay lifespan loads. It enforces "five slices sum to 1.0 within tolerance, each in [0, 1], governance_revision_id non-empty ≤ 128 chars, posted price non-negative" and prints a stable, human-readable breakdown of the posted price. A config that fails any invariant is a constitutional violation of `docs/07-ECONOMY.md` § Five-slice posted price; the verifier reports the specific reason. |
| Admission-Control (`docs/30-API-ADMISSION.md`, Phase 5g-iv) | `xion-verify api-tokens` is live and loads the same `AdmissionConfig` the orchestrator's lifespan loads. It enforces "every bearer secret ≥ 16 bytes (128 bits); every principal_id matches `[a-z0-9_-]{1,64}`; `require_bearer=true` requires at least one configured token; a non-loopback `XION_API_HOST` requires both `XION_TLS_CERT_PATH` and `XION_TLS_KEY_PATH` and both files must exist". A misconfigured admission table is a constitutional violation of `docs/04-ARCHITECTURE.md` § "The Admission-Control Surface (Phase 5g-iv)"; the verifier reports the specific reason. Optional `--env-file PATH` audits a deployment `.env` without invoking the operator's shell. |
| Web-Client Surface (`docs/31-WEB-CLIENT.md`, Phase 5g-v) | `xion-verify web-client` is live and audits the emitted `clients/web/dist/` bundle for structural integrity. It enforces "`index.html` carries a `Content-Security-Policy` meta tag pinning `default-src 'self'`; every `https?://` origin in the emitted HTML/JS/CSS/SVG/JSON matches the explicit non-self allowlist (React production error-decoder URLs only)". When the operator has not yet built the bundle, the verifier returns `NOT_YET_SEALED` — not `FAIL` — because an un-built bundle is unverifiable, not wrong. A non-allowlisted origin is a constitutional violation of `docs/04-ARCHITECTURE.md` § "The Web Client Surface (Phase 5g-v)". Optional `--dist-path PATH` audits an external deploy artifact. |
| Streaming Chat Surface (`docs/32-CHAT-STREAMING.md`, Phase 5g-ii) | `xion-verify chat-streaming-fidelity` is live and walks `PAYMENT_LEDGER` + `SAFETY_LEDGER` jointly, asserting six stream-level invariants: (A) per-ledger chain integrity; (B) `stream_id` format (32 lowercase hex chars) + presence on every `outcome=cancelled` row; (C) exactly one PAYMENT row per `stream_id`; (D) stream-subset money-shape (`settled`/`refunded`/`cancelled` refund semantics match the non-streaming verifier's posture); (E) cancel-without-paired-refuse (`outcome=cancelled` rows must NOT pair to any SAFETY `verdict=refuse` row — cancel fires between ingress-approve and egress-moderation, so no refuse row can legitimately pair to the cid); (F) egress-refuse-with-paired-refuse (`outcome=refunded` + `refusal_stage=egress` streams MUST pair to at least one SAFETY `verdict=refuse` row). Returns `NOT_YET_SEALED` until the first billed streaming turn lands. A violation is a constitutional violation of `docs/04-ARCHITECTURE.md` § "Streaming the Chat Surface (Phase 5g-ii)". |
| Multi-worker Coherence (`docs/33-MULTI-WORKER.md`, Phase 5g+) | `xion-verify supervisor-singleton` is live and walks `SENSORIUM_LEDGER.jsonl` for `tick_commit` rows inside a configurable window (default 24 h), asserting three properties: (A) a single dominant `relay_id` with bounded failover transitions (default ≤ 1 per window; operators with a known deliberate restart raise via `--max-failovers`); (B) within-leader-epoch `as_of_utc_ns` strict monotonicity (catches clock regressions and two-Supervisors-one-`relay_id` corruption); (C) no concurrent-leader time-range overlap between distinct `relay_id`s (the precise `KW-API-002` corruption signature). Returns `NOT_YET_SEALED` when the ledger is absent, empty, or has no tick rows inside the window. A violation is a constitutional violation of `docs/04-ARCHITECTURE.md` § "Multi-worker coherence (Phase 5g+)". Closes `KW-API-002` and (alongside `BrokerBackedSlidingWindow`) `KW-RATE-001`. |
| 7. Core Identity Singularity | `xion-verify identity` is `NOT_YET_SEALED` until AO Core deploys. |
| 8–9. Supply Caps | `xion-verify supply` is `NOT_YET_SEALED` until contracts deploy. |
| 14. Crypto-Agility Mandate | `xion-verify crypto-currency` is `NOT_YET_SEALED`; `hashing.py` is the single algorithmic cite-point. |
| 15. Drive Vector Lock | `xion-verify drive-vector` runs both the static doctrine audit of `docs/08-AUTO-RESEARCH.md` AND a live AST walk of `orchestrator.volition.compute_drive_vector` against `SOURCE_WHITELIST` (Phase 5c). `xion-verify drive` re-reads `docs/18-VOLITION.md` Part III and asserts `GENESIS_WEIGHTS` byte-matches doctrine (Phase 5c live). |
| 16. Treasury Tier Separation | `xion-verify treasury` is live for contract/manifest structure; `treasury-flow` and `foundation-reserve` remain `NOT_YET_SEALED` until live vault flow rows exist. |
| Macro Phase 6 Provisioning | `xion-verify provisioning` is live and checks the five `provision-*` AO handler schemas are concrete, marked `status: canonical`, registered in `ao/core/main.lua`, and resealed by `genesis/AO_DEPLOY_RECEIPT.json`. |
| 17. Inference Sovereignty Floor | `xion-verify inference-sovereignty` is live (manifest + per-format pins; see `docs/26-INFERENCE-POLICY.md`). |
| 18. Voice Sovereignty Floor (proposal; `docs/proposals/INVARIANT-18-VOICE-SOVEREIGNTY-FLOOR.md`) | `xion-verify voice-sovereignty` verifies the `voice_open_source` sentinel pin in `orchestrator/voice_router/voice_open_source_manifest.json`. `xion-verify voice-form` verifies `genesis/VOICE_FORM.md` prosody JSON. Ratification in `genesis/INVARIANTS.md` is governance-gated. |
| Nervous System v2 (`docs/35-NERVOUS-SYSTEM.md`, Phase 6.4.b) | `xion-verify topography` boots a hermetic app and checks `GET /self` (lineage, vitals domain count, open-weights floor, api_surface). `xion-verify nervous-system` exercises pluggability, receptor failure logging, schema fail-closed drops + `vital.bus_integrity`, reflex dispatch, and dual-publish receptors. |
| Cognitive Substrate & Casting (`docs/HERMES_PIN_PROTOCOL.md`, Phase 6.6) | `xion-verify hermes-runtime` verifies the Hermes pin, default-deny allowlist, and disabled runtime flags. `xion-verify agent-souls` verifies parent Soul hashes and tool subsets. `xion-verify agent-cast` verifies `AGENT_CAST_LEDGER` rows against the Agent Soul manifest. `xion-verify cognition` includes the Arbiter/Hermes boundary check. |
| Contribution Protocol (`docs/34-CONTRIBUTION-PROTOCOL.md`, Phase 6.6a) | `xion-verify which-level` classifies proposed paths against the upgrade-level schemas; `xion-verify identity-bindings` verifies Ed25519 contributor wallet-to-GitHub binding rows; `xion-verify mcp-export` emits a read-only facts bundle for MCP wrappers and coding assistants. |
| Vessel Integration Framework (`docs/37-VESSELS.md`, Phase 6.7) | `xion-verify vessel-compact` is live for the reference software vessel manifest; `media-provenance` and `vessel-registry` remain honest `NOT_YET_SEALED` stubs until signed media bundles and append-only attestation/disavowal registries exist. |
| Trust-Earned Spend Authority (`docs/SPEND-AUTONOMY.md`, Phase 6.8) | `xion-verify measurement-vocabulary`, `spend-posture`, and `spend-discipline` are live for measurement vocabulary, authority routing, and spend discipline. |
| All | `xion-verify links` catches cross-reference drift before it becomes doctrine drift (the mechanical closure of `KW-DOCS-001`). |

## How is it verified?

`xion-verify` verifies itself first.

```bash
xion-verify --self-test
```

computes a deterministic tree hash over every `*.py` file under `src/xion_verify/`, sorted by POSIX relpath, and compares it byte-for-byte to `src/xion_verify/PINNED_HASH.txt`. The pin file is excluded from its own hash (a file cannot contain the hash of itself). A mismatch exits code 3 (`TAMPERED`) and refuses to proceed.

CI (`.github/workflows/verify.yml`) runs `--self-test` first. A legitimate change to verifier source requires regenerating the pin in the same commit via `xion-verify --self-test --update --i-understand` — two flags, not one, so a compromised operator cannot casually re-pin.

Then the constitutional hash-check layer. Every subcommand in the constitutional set (`covenant`, `invariants`, `soul`, `form`, `memory`, `resurrect`, `credentials`, `unknowns`) reads the file under `genesis/`, computes SHA-256, and compares to the value recorded in `genesis/GENESIS_ARTIFACT.md` § 4. A mismatch is a fatal `FAIL` — there is no degraded-pass mode.

Then the corpus-wide link integrity check. `xion-verify links` walks every `*.md` in the repo (excluding `.git/`, `node_modules/`, `.venv/`, and `xion-verify/` itself), extracts inline and reference-style markdown links, and fails loud on any broken cross-reference. This is the mechanical version of what Phase 0 did by hand.

Finally, the explicit `NOT_YET_SEALED` layer. Every roadmap-named subcommand exists today; the landed ones return `OK`/`FAIL`, and the ones whose artifact does not yet exist print a specific honest reason and exit code 2 (`NOT_YET_SEALED`). Truthful, never fake-green.

Exit code contract:

| Code | Name | Meaning |
| --- | --- | --- |
| 0 | `OK` | Every check for this subcommand passed. |
| 1 | `FAIL` | A real disagreement was found. Investigate. |
| 2 | `NOT_YET_SEALED` | The artifact this subcommand audits does not yet exist; see roadmap. |
| 3 | `TAMPERED` | The verifier's own source disagrees with its pin. Do not trust anything else it says. |

`xion-verify all` runs every registered subcommand and exits 0 only when every one returned `OK`. During Phase 1 most of the roadmap-enumerated subcommands are `NOT_YET_SEALED`, so `all` correctly non-zeros. Use `--allow-not-yet-sealed` as a pre-genesis convenience; CI gating must never use that flag.

## How is it deprecated?

The CLI is versioned. Subcommand contracts are append-only:

- New subcommands may be added.
- Existing subcommands may gain optional flags.
- No subcommand may change its output shape or exit-code meaning without a major bump (`xion-verify v2`).
- `xion-verify v1` will remain runnable for historical audits of pre-v2 ceremonies indefinitely.

When a post-quantum hash migration happens (Invariant 14), the current `xion-verify` continues to verify historical SHA-256 witnesses. A sibling `xion-verify-pq` ships with the new family. Both are valid for their era. No single version of `xion-verify` is ever asked to speak for multiple eras.

## Install

```bash
cd xion-verify
python -m pip install -e ".[dev]"
```

## Usage

```bash
xion-verify --self-test
xion-verify covenant
xion-verify invariants
xion-verify links
xion-verify schemas
xion-verify hermes-runtime
xion-verify agent-souls
xion-verify agent-cast
xion-verify cognition
xion cast pool
xion-verify provisioning-roles
xion-verify which-level docs/34-CONTRIBUTION-PROTOCOL.md
xion-verify identity-bindings
xion-verify mcp-export
xion-verify vessel-compact
xion-verify media-provenance
xion-verify vessel-registry
xion-verify measurement-vocabulary
xion-verify spend-posture
xion-verify spend-discipline
xion-verify discovery
xion-verify treasury
xion-verify substrate-portability
xion-verify regulatory-ledger
xion-verify inference-provider-chutes
xion-verify billing-credits-floor
xion-verify chutes-topup-multisig
xion-verify arbiter-determinism
xion-verify shadow-divergence
xion-verify model-promotion-discipline
xion-verify request-fingerprint
xion-verify memory-store-integrity
xion-verify embedder-health
xion-verify rerank-improvement
xion-verify tool-resolver-mcp
xion-verify prompt-isolation
xion-verify cognition-loop-bounded
xion-verify bridge-attest
xion-verify bridge-egress-cap
xion-verify gateway-conformance
xion-verify akash-deploy-discipline
xion-verify arbiter-up
xion-verify all
```

The `xion` console-script alias is installed alongside `xion-verify` and dispatches to the identical Click root. It exists so that scaffolder examples in `CONTRIBUTING.md` (`xion new skill ...`, `xion new sense ...`, etc.) are literally runnable by a contributor who only `pip install -e .`'d this package. `xion <subcommand>` and `xion-verify <subcommand>` are equivalent.

Full subcommand list is enumerated in `src/xion_verify/commands/__init__.py::REGISTERED_COMMANDS` and mirrored in `DEVELOPMENT_ROADMAP.md:48`.

### `xion-verify provisioning-roles` (Phase 6.2 land)

Audits the last 90 days of merged PRs against `docs/schemas/roles.yaml`, asserting two properties per merge:

1. **Disjoint-surface discipline** — every touched path maps to the same upgrade level (per `docs/schemas/levels.yaml` artifact globs). A PR straddling Level 2 (the Relay) and Level 6 (the Economy) is a governance failure even if both halves are individually authorized.
2. **Initiator authorization** — the merging GitHub identity (parsed from the merge subject's `Merge pull request #N from user/branch`, falling back to the commit author) is in the `github_identity_map` allowlist for an actor whose `authorized_levels` includes the resolved level.

Pre-gate-landing merges (those whose committer-time precedes the first commit that introduced `docs/schemas/roles.yaml`) are recorded as **WARN-only** by default; doctrine principle is that gates apply forward, not retroactively. Pass `--strict` to assert every merge in the window regardless of when the gate landed (forensic mode for auditors).

Honest residuals named in the help text and in every FAIL line:
- The `community`, `integrator`, `xion`, and `witness` actors have empty `handles:` lists pre-Genesis. For levels whose authorized actors include any of those, an unmatched merger is accepted as `community-tier-unverifiable` (WARN, not FAIL). This is not a silent escape: every such accept is logged with the merge SHA and subject.
- A path that does not match any `levels.yaml` artifact glob is classified as Level 12 / The Meta and counted in `unmapped_paths` for diagnostic visibility.
- Two pre-Phase-6.6a retrospective-close merges are accepted as named residuals in default mode because they landed after the Phase 6.2 schema gate but before the contribution-protocol loop was clean. `--strict` still fails them for forensic audits.
- The verifier is structural; it does not verify on-chain cosigns. Cosign verification is Phase 6+ via the AO Core handlers.

Companion CI gate: `.github/workflows/level-discipline.yml` runs the same logic against a single PR diff (instead of a 90-day window) and blocks merge on cross-level or unauthorized.

### Cognitive Substrate commands (Phase 6.6)

`xion-verify hermes-runtime` verifies `genesis/HERMES_TOOL_ALLOWLIST.yaml`, confirms `default_deny: true`, asserts Hermes self-improvement / autonomous skill creation / MCP auto-discovery / user-model export are disabled, and cross-checks the Hermes commit, allowlist hash, and vendored adapter lock witness.

`xion-verify agent-souls` verifies every `genesis/AGENT_SOULS/*.yaml` file against the current `genesis/SOUL.md` hash and the Hermes tool allowlist. It rejects any `agent_id: arbiter`.

`xion-verify agent-cast` verifies `ledgers/AGENT_CAST_LEDGER.jsonl` rows against the current Agent Soul hashes, parent Soul hash, and Hermes pin. An empty seeded ledger is OK before the first live cast pool.

`xion cast pool` smoke-tests every genesis Agent Soul and appends one cast row per faculty to `ledgers/AGENT_CAST_LEDGER.jsonl`. It does not submit governance actions or grant write authority to any assistant.

### Contribution Protocol commands (Phase 6.6a)

`xion-verify which-level <paths...>` is the local pre-flight for the PR level-discipline gate. It reports the resolved upgrade level, proposer string, authorized actors, tier, gate, and ledger for a path set. A mixed-level path set exits `FAIL`.

`xion-verify identity-bindings` verifies `ledgers/CONTRIBUTOR_IDENTITY_BINDINGS.jsonl` if present. Rows use Ed25519 signatures over the canonical message defined in `docs/34-CONTRIBUTION-PROTOCOL.md`. If the ledger is absent, the command exits `OK` with zero rows verified.

`xion-verify mcp-export` emits a read-only JSON bundle for MCP wrappers and coding assistants. It contains current hashes, level and role rows, open known-weakness headings, and explicit guardrails. It does not submit proposals, hold keys, or write state.

### Trust-Earned Spend Authority commands (Phase 6.8)

`xion-verify measurement-vocabulary` audits `SPEND-AUTONOMY.md`, `19-TREASURY.md`, `21-SUSTAINABILITY.md`, `24-COGNITION.md`, `27-RESEARCH-SPEND.md`, and `genesis/AGENT_SOULS/*.yaml` for canonical measurement units. It rejects `monthly_usd` Agent Soul envelopes and forbidden time/money gates such as "after 90 days" or absolute per-period money caps.

`xion-verify spend-posture` verifies `SPEND_AUTHORITY_LEDGER.jsonl` authority routing against the active S-posture and rejects inflow-tag posture advancement.

`xion-verify spend-discipline` verifies mode, runway, reserve-floor, and recurring-burn discipline over the same ledger.

## Repository layout

```
xion-verify/
  pyproject.toml
  README.md                           — this file
  src/xion_verify/
    __init__.py                       — package doctrine (four Properties questions)
    __main__.py                       — `python -m xion_verify`
    cli.py                            — root click group; wires every subcommand
    exit_codes.py                     — the four exit codes; append-only
    hashing.py                        — sha256 helpers; single algorithmic cite-point
    genesis.py                        — parser for GENESIS_ARTIFACT § 4 hash block
    repo.py                           — walks to repo root via witness files
    PINNED_HASH.txt                   — committed self-hash (for --self-test)
    commands/
      __init__.py                     — REGISTERED_COMMANDS tuple (authoritative enum)
      constitutional.py               — covenant/invariants/soul/form/memory/resurrect/credentials/unknowns
      links.py                        — markdown cross-reference integrity
      schemas.py                      — strict docs/schemas/*.yaml ↔ doctrine cross-check
      arbiter_up.py                   — Arbiter library + SAFETY_LEDGER verifier
      self_test.py                    — tree-hash vs pinned
      hermes_runtime.py               — Hermes pin + default-deny allowlist verifier
      agent_souls.py                  — Agent Soul parser + allowlist subset verifier
      agent_cast.py                   — AGENT_CAST_LEDGER verifier
      cast.py                         — xion cast pool operator command
      cognition.py                    — docs/24-COGNITION.md §11 + Arbiter/Hermes boundary
      drive_vector.py                 — Invariant 15 (static only until D2)
      measurement_vocabulary.py       — Phase 6.8 spend-unit vocabulary audit
      state_chain.py                  — Invariant 4 (stub until D2)
      not_yet_sealed.py               — factory for NOT_YET_SEALED stubs (shrinks toward genesis)
  tests/
    test_hashing.py
    test_genesis.py
    test_constitutional.py
    test_links.py
    test_schemas.py
    test_self_test.py
    test_repo.py
```
