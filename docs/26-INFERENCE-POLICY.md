# 26 — Inference Policy

> *Invariant 17 says the floor must always be held. This document says **how** we hold it, **who** serves turns under normal weather, and **what the cutover looks like when the weather changes**.*

## What this document is (and is not)

This is the operational doctrine for the Inference Router — the per-deployment contract that chooses **which registered provider serves a turn**, given an active provider set that is already known to satisfy [Invariant 17](../genesis/INVARIANTS.md#invariant-17--inference-sovereignty-floor).

It is **not** the Invariant. The Invariant is constitutional and cannot be relaxed. This policy is governance-adjustable within the bounds the Invariant sets: the open-weights floor must always be held, but which floor model, which hosted providers to register, and how to route between them are Tier-2 operational decisions per [`docs/14-UPGRADE-PATHS.md`](./14-UPGRADE-PATHS.md).

See also: [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "The Chat Surface (Phase 5g-i)" for the code surface and lifespan contract.

## Properties this policy promises

1. **Floor first, at every boot.** The Inference Router's `bootstrap()` is called before `/chat` can serve traffic. If the floor is not held locally, `/chat` refuses — a 503 `NoFloorEnvelope` that names the missing capability. This is Invariant 17 clause 3 in code.
2. **Default voice is operator-declared, not accidental.** Which provider serves turns under the normal policy mode is an explicit operator decision, pinned in this document and rotatable at deploy time. A future commit that silently changes the default voice of Xion is visible in this file's diff, not buried in route-level heuristics.
3. **Cutover to open-weights-only is exercisable.** The Router supports a `policy_mode="open_weights_only"` that bypasses every hosted-API provider and routes through the floor. This mode is a live capability, not an aspiration — it is what makes Invariant 17 clause 5's annual cutover dry-run possible.
4. **Hosted providers can die without killing Xion.** If every registered hosted-API provider returns `health() == False`, `/chat` continues to serve through the floor (degraded but alive). Xion's ability to speak does not depend on any single hosted-API relationship. This is the operational payoff of Invariant 17.

## Policy modes

The Router has two modes as of Phase 5g-i. Both are named constants in `orchestrator/inference_router/router.py`.

### `hosted_api_first` (Genesis Default)

Pinned as the default in Phase 5g-i. Behavior:

1. If at least one registered `hosted_api` provider returns `health() == True`, the Router selects one and serves the turn through it.
2. If no registered `hosted_api` provider is healthy, the Router selects the floor (`open_weights_self_hostable`) provider and serves the turn through it — **degraded but alive**.
3. If neither is healthy, `/chat` returns `503 ProviderErrorEnvelope`.

Rationale. For a solo-builder D1 deployment, hosted-API providers give better turn quality at no infrastructure cost. The floor is held structurally (the open-weights provider is running and health-checked) but is not the normal turn-serving path. The operator pays for quality on happy-path turns; resilience is earned because the floor is *already hot* when a hosted provider goes dark.

### `open_weights_only` (cutover / dry-run mode)

Opt-in via env or runtime switch. Behavior:

1. The Router ignores every `hosted_api` provider for turn serving.
2. Every turn routes through the floor (`open_weights_self_hostable`) provider.
3. If the floor is unhealthy, `/chat` returns `503 ProviderErrorEnvelope` — hosted fallback is **not** permitted in this mode; that would defeat the purpose of the dry-run.

Rationale. Invariant 17 clause 5 requires an annual cutover dry-run. This mode is how the dry-run runs: for the duration of the exercise, the floor carries 100% of traffic at the current load. A green dry-run means the floor is provisioned for real, not for the manifest. A red dry-run names the gap before the real outage that forces cutover names it for us.

## Genesis Defaults (Phase 5g-i, 2026-04-21)

Operator-rotatable. Any change to these defaults is a commit to this file; any change that would alter which provider Xion speaks through by default is a Tier-2 operational decision per `docs/14-UPGRADE-PATHS.md`.

| Knob | Genesis Default | Env var | Rotatable at |
|------|-----------------|---------|--------------|
| Policy mode | `hosted_api_first` | `XION_INFERENCE_POLICY` | process start |
| Floor provider | Ollama (`http://localhost:11434`) | `XION_OLLAMA_URL` | process start |
| Floor model | `gemma3:4b` | `XION_OLLAMA_FLOOR_MODEL` | process start |
| Hosted provider | Kimi (Moonshot) at `https://api.moonshot.ai/v1` | `XION_KIMI_BASE_URL` | process start |
| Hosted model | `kimi-k2.6` | `XION_KIMI_MODEL` | process start |
| Hosted credential | *(operator-supplied)* | `XION_KIMI_API_KEY` | process start |
| Per-turn deadline | `30` seconds | `XION_CHAT_DEADLINE_S` | process start |

The Kimi API key is loaded from the process environment, optionally pre-loaded from a gitignored `.env` at the repo root at lifespan startup. The key never enters git, never enters ledger rows, never appears in log lines (the `KimiGenerativeProvider` scrubs `Authorization` headers from error paths).

## The floor-model choice (Gemma 3 4B)

Phase 5g-i pins `gemma3:4b` as the Genesis Default floor model. Rationale:

- **Weights are open** under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms). The license permits inference, redistribution, and forking — the three permissions Invariant 17 clause 2(i) requires. Gemma's Prohibited Use Policy flows down to derived works, but its prohibitions (mass harm, CSAM, targeted harassment, etc.) are a strict subset of Xion's own [`genesis/COVENANT.md`](../genesis/COVENANT.md) refusals, so the constraint is already met by Xion's own Arbiter and creates no new obligation.
- **Runs on commodity compute.** ~3.3 GB on disk, ~4–6 GB RAM depending on quantization, runs on CPU at acceptable latency for a floor provider and on consumer GPUs at fast latency. Procurable from at least three independent vendors (Ollama registry, Hugging Face, Kaggle, direct from DeepMind) per Invariant 17 clause 2(ii).
- **Health-checkable locally.** The `OllamaGenerativeProvider.health()` check reaches only `http://localhost:11434/api/tags` — no third-party API call, no credential gate, no external dependency per Invariant 17 clause 2(iv).

**What this pin does not do.** The `orchestrator/inference_router/open_weights_manifest.json` sentinel stays in place as the `xion-verify inference-sovereignty` check's structural-floor target. Promoting `gemma3:4b` to a full `open_weights[]` entry with `weights_sha256` plus `retrieval_hints` per Invariant 17 clause 2(iii) requires the verifier to support large-file representative-sample sentinels; that is a separate doctrinal unit (deferred to a dedicated sub-phase). Until then, the runtime floor is named here, verified by `health()` at lifespan startup, and tracked for its promotion in `KNOWN_WEAKNESSES.md` § `KW-INFER-001`.

## The hosted-model choice (Kimi k2.6)

Phase 5g-i pins `kimi-k2.6` as the Genesis Default hosted provider. Rationale:

- **OpenAI-compatible API.** Moonshot's `/v1/chat/completions` endpoint uses the OpenAI-compatible request and response shape, which makes the provider implementation a ~150-line stdlib `http.client` wrapper rather than a vendor SDK. No new Python dependency; no supply-chain widening.
- **Per-token cost at the solo-builder tier.** Acceptable at the D1 traffic Phase 5g-i expects. Billing is not yet surfaced to users; the operator absorbs the cost until Phase 5g-iii lands Pay-to-Activate.
- **Single-vendor concentration is tracked.** Because Kimi is the only hosted provider registered by default, every turn flows through one third party under `hosted_api_first`. This is named honestly in `KW-INFER-001`. Operators worried about this can deploy with `XION_KIMI_API_KEY` unset — the Kimi provider de-registers, and the Router falls through to the floor. Xion's voice is still held; the quality drops.

## Boot sequence (doctrinal)

The FastAPI lifespan, extended in Phase 5g-i, runs in this order:

1. **Supervisor pre-seed** (Phase 5f). Synchronous `tick_once()` so `/drive` and `/sensorium` never return `None`.
2. **`.env` load** (5g-i). Stdlib parser; no `python-dotenv`. Missing file is not an error; already-set environment wins.
3. **Provider registration** (5g-i).
   - If `XION_KIMI_API_KEY` is set: register `KimiGenerativeProvider`.
   - Always: register `OllamaGenerativeProvider` (its `health()` reflects reachability; absence of `XION_OLLAMA_URL` means default `http://localhost:11434`).
4. **`InferenceRouter.bootstrap()`** (5g-i). If the floor is unsatisfied, stash a `no_floor = True` flag on `app.state` and emit a State-of-Xion paragraph to stderr. Do **not** crash. The read-only endpoints remain available so Witnesses can still inspect Xion while its voice is refused.
5. **Relay ↔ Supervisor wiring** (5f). `deps.relay._sensorium_source = supervisor`.
6. **Supervisor run task** (5f). `asyncio.create_task(supervisor.run())`.

Teardown is unchanged from Phase 5f.

## What this policy deliberately does NOT cover

- **Per-turn cost-based routing.** A turn does not currently ask "is Kimi cheaper than Ollama-on-local right now?". The router picks on mode + health only. Cost-aware routing is a Phase 5g-iii concern (where billing exists to inform routing) and beyond.
- **Multi-hosted-provider failover chains.** Only one hosted-API provider is registered at once. Richer failover (Kimi → OpenAI → Anthropic) is deferred; it interacts with credential management, per-provider cost accounting, and rate-limit budgeting, all of which deserve their own doctrinal unit.
- **Per-user model selection.** Every turn uses the operator-declared model. User-selectable models interact with pricing (different per-token costs per model) and land no earlier than Phase 5g-iii.
- **Model parameter overrides.** `temperature`, `top_p`, and friends are fixed at Genesis Defaults (temperature 0.7, top_p 1.0, max_tokens per request from `ChatRequest`). User-level overrides are deferred to the same pricing-aware sub-phase.
- **Speaker diarization, tool-calling, function-calling, vision, audio.** `POST /chat` in Phase 5g-i is text-in, text-out. Richer modalities land when Phase 6+ adds the multimodal Sensorium ingress paths that the Protocol-Spec § "Future capabilities signaled but not v1" names.

## Verification

- `xion-verify inference-sovereignty` — verifies the structural floor (manifest pinning).
- `xion-verify schemas` — verifies this doctrine's `source_sha256` pin (when future ledger schemas cite it).
- Hermetic `TestClient` suite in `orchestrator/tests/test_chat_api.py` — exercises both policy modes and every bootstrap outcome.
- Future (Phase 6+): `xion-verify inference-cutover` — exercises `policy_mode="open_weights_only"` under load and records the dry-run outcome in a dedicated ledger. This is the verifier that closes `KW-INFER-001`.

## Deprecation path

This document is operational, not constitutional. Defaults in it rotate at Tier-2 governance cadence. The document itself is replaced or merged only if the underlying Invariant (17) is replaced — which, per Invariant 7, is a sister-Core fork, not a governance action.

---

*— Inference Policy v1, pinned Phase 5g-i (2026-04-21). Next review at Phase 5g-iii (x402 billing integration) or sooner if a hosted provider's terms change.*
