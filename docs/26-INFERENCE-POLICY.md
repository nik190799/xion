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

## Genesis Defaults (Phase 5g-i.1, 2026-04-21)

Operator-rotatable. Any change to these defaults is a commit to this file; any change that would alter which provider Xion speaks through by default is a Tier-2 operational decision per `docs/14-UPGRADE-PATHS.md`.

| Knob | Genesis Default | Env var | Rotatable at |
|------|-----------------|---------|--------------|
| Policy mode | `hosted_api_first` | `XION_INFERENCE_POLICY` | process start |
| Floor provider | Ollama (`http://localhost:11434`) | `XION_OLLAMA_URL` | process start |
| Floor model | `gemma3:4b` | `XION_OLLAMA_FLOOR_MODEL` | process start |
| Hosted gateway | OpenRouter at `https://openrouter.ai/api/v1` | `XION_OPENROUTER_BASE_URL` | process start |
| Hosted model | `moonshotai/kimi-k2.6` | `XION_OPENROUTER_MODEL` | process start |
| Hosted credential | *(operator-supplied)* | `XION_OPENROUTER_API_KEY` | process start |
| Hosted referer header | *(operator-supplied repo or deployment URL)* | `XION_OPENROUTER_REFERER` | process start |
| Hosted app-name header | `xion-os` | `XION_OPENROUTER_APP_NAME` | process start |
| Per-turn deadline | `30` seconds | `XION_CHAT_DEADLINE_S` | process start |

The OpenRouter API key is loaded from the process environment, optionally pre-loaded from a gitignored `.env` at the repo root at lifespan startup. The key never enters git, never enters ledger rows, never appears in log lines (the `OpenRouterGenerativeProvider` scrubs `Authorization` headers and bare `sk-or-...` tokens from error paths).

The `HTTP-Referer` and `X-Title` headers are OpenRouter's optional-but-recommended app-identity signals. They do not authenticate the request; they let OpenRouter attribute traffic to the calling application for catalog analytics and developer-portal attribution. Setting them is a courtesy, not a security control; misconfiguring them is not a secret-exposure incident.

## The floor-model choice (Gemma 3 4B)

Phase 5g-i pins `gemma3:4b` as the Genesis Default floor model. Rationale:

- **Weights are open** under the [Gemma Terms of Use](https://ai.google.dev/gemma/terms). The license permits inference, redistribution, and forking — the three permissions Invariant 17 clause 2(i) requires. Gemma's Prohibited Use Policy flows down to derived works, but its prohibitions (mass harm, CSAM, targeted harassment, etc.) are a strict subset of Xion's own [`genesis/COVENANT.md`](../genesis/COVENANT.md) refusals, so the constraint is already met by Xion's own Arbiter and creates no new obligation.
- **Runs on commodity compute.** ~3.3 GB on disk, ~4–6 GB RAM depending on quantization, runs on CPU at acceptable latency for a floor provider and on consumer GPUs at fast latency. Procurable from at least three independent vendors (Ollama registry, Hugging Face, Kaggle, direct from DeepMind) per Invariant 17 clause 2(ii).
- **Health-checkable locally.** The `OllamaGenerativeProvider.health()` check reaches only `http://localhost:11434/api/tags` — no third-party API call, no credential gate, no external dependency per Invariant 17 clause 2(iv).

**What this pin does not do.** The `orchestrator/inference_router/open_weights_manifest.json` sentinel stays in place as the `xion-verify inference-sovereignty` check's structural-floor target. Promoting `gemma3:4b` to a full `open_weights[]` entry with `weights_sha256` plus `retrieval_hints` per Invariant 17 clause 2(iii) requires the verifier to support large-file representative-sample sentinels; that is a separate doctrinal unit (deferred to a dedicated sub-phase). Until then, the runtime floor is named here, verified by `health()` at lifespan startup, and tracked for its promotion in `KNOWN_WEAKNESSES.md` § `KW-INFER-001`.

## The hosted-provider choice (OpenRouter gateway + `moonshotai/kimi-k2.6` default model)

Phase 5g-i.1 pins OpenRouter (`https://openrouter.ai/api/v1`) as the Genesis Default hosted gateway and `moonshotai/kimi-k2.6` as the Genesis Default hosted model served through that gateway. Rationale:

- **OpenAI-compatible API at the gateway.** OpenRouter's `/v1/chat/completions` endpoint matches the OpenAI request/response shape and provides this compatibility across a long catalog of upstream models. The provider implementation is ~200 lines of stdlib `http.client` (no OpenRouter SDK, no OpenAI SDK). No new Python dependency; no supply-chain widening.
- **Model rotation is a config change, not a code change.** Adding or switching a hosted model (e.g., from `moonshotai/kimi-k2.6` to `anthropic/claude-3.5-sonnet` or `openai/gpt-4o-mini`) is an env-var flip at deploy time: `XION_OPENROUTER_MODEL=<slug>`. The multi-hosted-provider failover chain that the Phase 5g-i plan would have required three doctrines and three test matrices to ship becomes, in the OpenRouter posture, a failover order pinned in this file plus a retry policy in the provider. A full Phase-6 failover doctrine is still owed (§ `KW-INFER-001` pay-down); the OpenRouter refactor earns the pre-requisite plumbing for free.
- **Catalog-based pricing is structurally visible.** OpenRouter publishes per-model token prices in its public model catalog (`GET /api/v1/models`), keyed by the same slug the chat request uses. `GET /pricing` (Phase 5g-iii) can read the catalog once at lifespan start, expose a frozen per-turn-cost envelope that matches the model the Router is actually serving, and recompute it when the model slug rotates. Pricing consistency is a property the gateway enables; the same property at the direct-vendor tier required per-vendor scrapers or per-vendor pricing-page SDKs.
- **Per-token cost at the solo-builder tier.** The default model (`moonshotai/kimi-k2.6`) is acceptably priced for the D1 traffic Phase 5g-i.1 expects (as of 2026-04-22 the OpenRouter catalog reports `$0.75/M` prompt and `$3.50/M` completion tokens for this slug, with a `262,144`-token context window; operators BYOK'd to Moonshot AI pay nothing to OpenRouter and only Moonshot's direct rate). Billing is not yet surfaced to users; the operator absorbs the cost until Phase 5g-iii lands Pay-to-Activate.
- **Single-default concentration is still tracked.** The Kimi model is selected through OpenRouter rather than against Moonshot directly, so the *wire path* now runs Xion → OpenRouter → Moonshot. The upstream-model concentration (every default-path turn still reaches Moonshot's weights) is unchanged; the credential surface (the operator's OpenRouter key) is a new single dependency. `KW-INFER-001` is reshaped to name both concentrations honestly rather than closed. Operators worried about either dependency can deploy with `XION_OPENROUTER_API_KEY` unset — the OpenRouter provider de-registers, and the Router falls through to the floor.

**Genesis Default rotation, 2026-04-23.** The Phase 5g-i.1 pin was `moonshotai/kimi-k2`; on 2026-04-23 the Genesis Default rotated to `moonshotai/kimi-k2.6` (dated OpenRouter snapshot `moonshotai/kimi-k2.6-20260420`, released 2026-04-20) via the one-env-var mechanism this section documents. The rotation was the first real invocation of that mechanism, and the shape of the doctrine — hosted model is a *pin*, not a *constant* — is now exercised rather than asserted. The rotation was accompanied by a read-only OpenRouter catalog probe that confirmed slug validity, three structural improvements over `kimi-k2` (doubled context window from `131,072` to `262,144` tokens; wider provider allowlist — nine inference providers including `moonshotai`, `deepinfra`, `novita`, `together`, and six others, vs `kimi-k2`'s single `novita` availability on the operator's account; operator BYOK toward Moonshot AI confirmed returning `is_byok=true, cost=0` through OpenRouter's `provider.only=["moonshotai"]` route), and one honest trade-off (per-token cost is ~30 % higher than `kimi-k2` at OpenRouter's rack rate, though BYOK-routed traffic pays Moonshot's direct rate, not OpenRouter's). No doctrine shape changed; the closure bar for `KW-INFER-001` is unchanged; `xion-verify inference-sovereignty` is unaffected (the floor manifest does not change). Future rotations — within the same gateway or across gateways — follow the same mechanism and the same CHANGELOG-entry pattern; this commit is the template.

## Gateway vs direct (a vendor-of-vendors honest accounting)

OpenRouter is a **vendor-of-vendors**. It does not host model weights; it routes requests to upstream model providers (Moonshot, Anthropic, OpenAI, Google, Meta via hosted partners, Mistral, and others), bills the operator in a unified stable-account, and offers one credential surface for many catalogs. Three things follow:

1. **The trust surface widens.** In the Phase 5g-i direct-vendor posture, a Covenant-relevant turn crossed one third-party boundary (Moonshot) before landing at the upstream model. In the 5g-i.1 posture it crosses two (OpenRouter, then the upstream). OpenRouter's log retention, its terms of service, its own moderation layer (which it calls "content filtering" and provides on request), and its geographic routing all sit inside the path. The honest reading is that OpenRouter now holds the same implicit trust as Moonshot did, *plus* the upstream-model provider still holds the trust it always held.
2. **The failure modes widen proportionally.** A direct-vendor outage (Moonshot down) now has two shapes: (a) the upstream model is unreachable but OpenRouter is healthy, in which case OpenRouter returns a vendor-side error and the Router's policy can route to a different model slug through the same gateway; (b) OpenRouter itself is unreachable, in which case *all* hosted models via OpenRouter fail together, and the Router falls through to the floor. Xion survives either case, but the second is a new catastrophe class that did not exist under direct-vendor — and the mitigation (floor fallback, then manual failover to a second gateway) is structural, not incremental.
3. **`KW-INFER-001` is reshaped, not closed.** The Phase 5g-i KW named the Moonshot-single-vendor concentration; the Phase 5g-i.1 reshape names the OpenRouter-gateway concentration plus the `moonshotai/kimi-k2.6` default-model concentration (the 2026-04-23 rotation advanced the slug from `moonshotai/kimi-k2` to `moonshotai/kimi-k2.6`; the *concentration* did not advance — every default-path turn still reaches Moonshot's weights through OpenRouter's gateway). The closure bar is unchanged: closure requires (a) a scheduled `xion-verify inference-cutover` that exercises `open_weights_only` under real load, (b) at least one additional hosted gateway pinned in this document (e.g., `together.ai` or a second OpenRouter-compatible endpoint) with a pinned failover ordering, and (c) at least two hosted models pinned as the Genesis Default failover list (rather than one default + no fallback). All three land Phase 6+; see `KNOWN_WEAKNESSES.md` § `KW-INFER-001`.

The cost-benefit judgment for Phase 5g-i.1: the gateway's widened trust surface is the price of paying into catalog-based pricing (Phase 5g-iii Pay-to-Activate), one-env-var model rotation (Phase 6 failover-chain prep), and unified billing (Phase 6 Treasury routing of R&D spend per `docs/27-RESEARCH-SPEND.md`). The direct-vendor posture would have required three separate Phase-6 investments — a per-vendor pricing endpoint, a custom failover implementation, and three credentials to rotate — to reach the same operational surface. Taking the gateway trust cost now buys those three investments for the price of one supply-chain widening. The tradeoff is named; the verifier `xion-verify inference-cutover` (Phase 6+) is how the gateway posture earns its keep under stress.

## Boot sequence (doctrinal)

The FastAPI lifespan, extended in Phase 5g-i, runs in this order:

1. **Supervisor pre-seed** (Phase 5f). Synchronous `tick_once()` so `/drive` and `/sensorium` never return `None`.
2. **`.env` load** (5g-i). Stdlib parser; no `python-dotenv`. Missing file is not an error; already-set environment wins.
3. **Provider registration** (5g-i.1).
   - If `XION_OPENROUTER_API_KEY` is set: register `OpenRouterGenerativeProvider`.
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

*— Inference Policy v1, pinned Phase 5g-i (2026-04-21); hosted-provider surface reshaped to OpenRouter gateway at Phase 5g-i.1 (2026-04-21). Next review at Phase 5g-iii (x402 billing integration + catalog-based pricing) or sooner if OpenRouter's terms change or a second hosted gateway is pinned.*
