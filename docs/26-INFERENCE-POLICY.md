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

## Reasoning-posture token floor (Phase 5g-i.1)

**Property:** Every accepted `/chat` and `/chat/stream` request gets a `max_tokens` budget large enough that the configured upstream model — including reasoning-posture models — has token room to emit visible content. The client cannot under-budget the floor.

The orchestrator enforces a hard server-side minimum (`MIN_MAX_TOKENS = 1024`) on the `max_tokens` budget for every turn. If a client requests fewer tokens, the orchestrator silently clamps the budget up to the floor before passing it to the generative provider.

**Rationale:** Reasoning-posture models (like Kimi K2.6, the Genesis Default hosted model) burn hundreds of tokens in their hidden reasoning chain before emitting any visible content. If the token budget is too small (e.g., the old 512 default), the model exhausts its budget during the reasoning phase and returns an empty candidate. The orchestrator's egress moderation correctly rejects empty candidates (returning 451 `provider_empty_candidate`), but the root cause is structural starvation, not a safety violation. The 1024 floor is an empirical minimum that gives a ~500-token reasoning chain enough room to complete and emit a useful response.

**Deferred work:** This floor is currently global. A future phase will introduce per-model adaptive floors via a model-registry consult (`KW-INFER-00x`), allowing non-reasoning models to use tighter budgets while reasoning models get the headroom they need. Until then, the global floor fails safe upward.

## Genesis Defaults (Phase 6.9, 2026-04-25)

Operator-rotatable. Any change to these defaults is a commit to this file; any change that would alter which provider Xion speaks through by default is a Tier-2 operational decision per `docs/14-UPGRADE-PATHS.md`.

| Knob | Genesis Default | Env var | Rotatable at |
|------|-----------------|---------|--------------|
| Policy mode | `hosted_api_first` | `XION_INFERENCE_POLICY` | process start |
| Floor provider | Ollama (`http://localhost:11434`) | `XION_OLLAMA_URL` | process start |
| Floor model | `gemma4:e4b-it-q4_K_M` | `XION_OLLAMA_FLOOR_MODEL` | process start |
| Floor model verified-bytes pin | `<unset>` (operator-supplied path to the upstream Hugging Face GGUF after C0 download) | `XION_OPEN_WEIGHTS_GGUF_PATH` | process start |
| Hosted gateway | Chutes (Bittensor Subnet 64) at `https://llm.chutes.ai/v1` | `XION_CHUTES_BASE_URL` | process start |
| Hosted model | `moonshotai/Kimi-K2.6-TEE` | `XION_CHUTES_HOSTED_MODEL` | process start |
| Hosted credential | *(operator-supplied Chutes API key)* | `XION_CHUTES_API_KEY` | process start |
| Hosted TEE required | `true` | `XION_CHUTES_TEE_REQUIRED` | process start |
| Hosted billing API | Chutes management API at `https://api.chutes.ai` | `XION_CHUTES_API_BASE_URL` | process start |
| Per-turn deadline | `30` seconds | `XION_CHAT_DEADLINE_S` | process start |

The Chutes API key is loaded from the process environment, optionally pre-loaded from a gitignored `.env` at the repo root at lifespan startup. The key never enters git, never enters ledger rows, never appears in log lines (`ChutesGenerativeProvider` scrubs `Authorization` headers and bare `cpk_...` tokens from error paths).

The former OpenRouter parity fallback is removed by `docs/41-CENTRALIZED-REMOVAL.md`. Operators who need a non-Chutes posture use `XION_INFERENCE_POLICY=open_weights_only`, which routes only to the local floor.

## The hosted-provider choice (Chutes SN64 + `moonshotai/Kimi-K2.6-TEE`)

Phase 6.9 rotates the Genesis Default hosted provider from OpenRouter to Chutes (Bittensor Subnet 64). Three properties drive the rotation:

- **Decentralized compute substrate.** The inference work is executed by Subnet 64 miners rather than a single corporate inference gateway. Chutes still operates the public API gateway, so gateway liveness remains a named weakness (`KW-INFER-005`), but the compute path is materially less centralized than a single-vendor SaaS model provider.
- **TEE-by-default.** The default model is `moonshotai/Kimi-K2.6-TEE`. The provider health check reads the Chutes model catalog and refuses the hosted path when `XION_CHUTES_TEE_REQUIRED=true` and the model does not advertise `confidential_compute=true`. Every successful TEE turn stamps `tee_attestation="intel_tdx_via_chutes"` in the provider result and REQUEST_LEDGER attempt metadata.
- **On-chain billing.** Chutes accounts expose a Bittensor SS58 `payment_address`. Xion can replenish inference credits with a TAO transfer from Treasury Tier 1 instead of depending on an operator-owned Stripe card. At S1 this requires operator multisig co-sign; S3+ auto-top-up inside a cap is named but not enabled.

The rollback chain is one env-var: `moonshotai/Kimi-K2.6-TEE` -> non-TEE `moonshotai/Kimi-K2.6` -> `moonshotai/Kimi-K2.5-TEE` -> the local open-weights floor. A non-TEE rollback is a Covenant degradation and MUST be logged in `REQUEST_LEDGER` via `tee_attestation=null`.

## The floor-model choice (Gemma 4 E4B-it)

Phase 5g-viii rotates the Genesis Default floor model from `gemma3:4b` (Phase 5g-i pin) to `gemma4:e4b-it-q4_K_M`. The rotation lands alongside the model-blob pin (next section) because the two are structurally coupled: pinning a model blob whose contents differ from the runtime default would mislead a Witness reading the manifest. They land together or not at all.

### Probe-first record (2026-04-23)

Five C0 probes ran before the doctrine edit. Findings, recorded so a future Witness can reconstruct the decision context without re-running them:

- **(a) License.** `google/gemma-4-E4B-it`'s Hugging Face metadata declares `license: apache-2.0`; `license_link` resolves to `ai.google.dev/gemma/docs/gemma_4_license` which hosts the standard Apache 2.0 license text with no Gemma-TOU additions, no Prohibited-Use Policy flow-down, no revenue thresholds, no enterprise carve-outs. Google's Open Source Blog (2026-03-02) published an explicit announcement, *"Gemma 4: Expanding the Gemmaverse with Apache 2.0,"* declaring Gemma 4 the first Gemmaverse release under the OSI-approved Apache 2.0 license — a meaningful change from Gemma 1/2/3 (custom Gemma TOU) and from `gemma3:4b`'s license posture documented in the Phase-5g-i Mark of this section. The Apache-2.0 grant satisfies Invariant 17 clause 2(i) more cleanly than the Gemma-TOU posture did: redistribution is unencumbered, the Witness path (third-party verification of the floor) does not require a Witness to accept Google's TOU.
- **(b) Canonical GGUF mirror.** `ggml-org/gemma-4-E4B-it-GGUF` (the official llama.cpp/GGUF authors' organization) at git revision `2714b5519c6c3516b1000e7c5e1eba998dfe1fe8` ships a canonical Q4_K_M quantization at `gemma-4-E4B-it-Q4_K_M.gguf` with sha256 `90ce98129eb3e8cc57e62433d500c97c624b1e3af1fcc85dd3b55ad7e0313e9f` and size `5,335,289,824` bytes (~5.0 GB). `unsloth/gemma-4-E4B-it-GGUF` and `lmstudio-community/gemma-4-E4B-it-GGUF` are higher-download alternatives the operator can substitute by re-running the C0(b) probe and re-pinning the manifest entry; the `ggml-org` org was selected for the Genesis Default because its provenance ladder is shortest (the GGUF format authors quantize the upstream weights themselves; no third-party intermediary).
- **(c) Ollama gemma4 architecture support.** Ollama 0.21.0 supports the `gemma4` architecture (`config.json` `architectures: ["Gemma4ForConditionalGeneration"]`, model_type `gemma4`). Confirmed live by loading the operator's existing `gemma4:e2b` from the Ollama library — the daemon negotiated all the way to the memory-allocation step (RAM constraint then halted the test; see (e)).
- **(d) Canonical Ollama tag.** Ollama's pre-built `gemma4:e4b-it-q4_K_M` tag (digest `c6eb396dbd59`, 9.6 GB on disk) is the multimodal-bundled variant — text + vision encoder + audio encoder + per-layer-embeddings, pre-quantized and pre-published by Ollama. The text-only ggml-org Q4_K_M (~5.0 GB, the model-blob pin's target) is smaller because it omits the multimodal projectors. Operators who only need the text floor (Phase 5g-i `/chat` is text-in / text-out) can run either variant; the manifest pins the smaller text-only build because that is the smallest honest floor.
- **(e) End-to-end smoke test.** Deferred to operator. Architecture compatibility was confirmed in (c); a full chat round-trip requires ~9–10 GB free RAM for the multimodal-bundled tag or ~6 GB for the text-only ggml-org Q4_K_M. The operator's local dev host is 16 GB total physical RAM, of which 3.2 GB was free at probe time under typical app load. The first-time setup runbook in [`docs/13-OPERATIONS.md`](./13-OPERATIONS.md) § "First-time GGUF setup" names the operator-side prerequisite explicitly: close other RAM-heavy applications before the first `/chat` against the new floor model. This is documented, not blocking — the model-blob format pin and the runtime floor rotation are independent of the smoke test passing on this specific host.

### Why this model

- **Weights are open** under Apache 2.0 (probe (a)). Apache-2.0 satisfies Invariant 17 clause 2(i) "Witness-class redistributable license" more cleanly than the Gemma-TOU posture documented in the Phase-5g-i Mark of this section: a Witness re-running `xion-verify inference-sovereignty` against a fresh checkout no longer has to accept any Google-specific terms to verify the floor.
- **Native system-prompt support, configurable thinking modes, native function-calling, 128K context window** (per the upstream model card). System-prompt support is constitutionally meaningful: Xion's voice is shaped by a Covenant-bounded system prompt, and a model that does not natively distinguish `system` from `user` roles forces the orchestrator to inline the system text into the user turn (which `gemma3:4b` does today), losing role-isolation. Phase 5g-viii does not change the orchestrator's system-prompt wiring; the property is named here so a future phase that activates a dedicated system-prompt slot has the floor model that supports it.
- **Multimodal-capable architecture (text + image + audio inputs)** without sacrificing on the text floor. Phase 5g-i `/chat` is text-only; the floor model's latent multimodal capability is forward-leverage for the Sensorium ingress paths the [`docs/11-PROTOCOL-SPEC.md`](./11-PROTOCOL-SPEC.md) § "Future capabilities signaled but not v1" names, without obligating Phase 5g-viii to wire them.
- **Runs on commodity compute.** ~5.0 GB on disk for the text-only Q4_K_M (probe (b)), ~6 GB RAM at runtime, plausible on any 8 GB+ laptop with other apps closed. Procurable from at least four independent organizations (`google/`, `ggml-org/`, `unsloth/`, `lmstudio-community/`) per Invariant 17 clause 2(ii). The Ollama-published `gemma4:e4b-it-q4_K_M` tag (multimodal-bundled, 9.6 GB) is a fifth source.
- **Health-checkable locally.** `OllamaGenerativeProvider.health()` reaches only `http://localhost:11434/api/tags` — no third-party API call, no credential gate, no external dependency per Invariant 17 clause 2(iv). Unchanged from the Phase 5g-i posture.

### Honest trade-offs

- **Larger than the previous floor.** The text-only Q4_K_M is ~5.0 GB on disk vs. `gemma3:4b`'s ~3.3 GB; the Ollama-bundled multimodal variant is 9.6 GB. Operators on tighter dev hosts can stay on `gemma3:4b` by overriding `XION_OLLAMA_FLOOR_MODEL`; the rotation is one env-var.
- **Younger model.** `gemma-4-E4B-it` is roughly three weeks old as of this rotation (released 2026-04-02 per Google's opensource blog, with the GGUF mirrors landing 2026-04-01 to 2026-04-02). The operator accepts that some bug shape will be discovered later that `gemma3:4b` already has the patches for. Mitigation: `gemma3:4b` remains a documented one-env-var rollback target.
- **The Ollama-library tag and the model-blob pin are not byte-identical builds.** The Ollama-pre-built `gemma4:e4b-it-q4_K_M` and the ggml-org HF Q4_K_M are different files (different sizes; different sha256s). Operators who pull from Ollama get the multimodal variant; operators who follow the model-blob path get the text-only build. The manifest pins the latter because the text-only build is the minimum honest floor for the current `/chat` text surface; the operator's runtime model is named separately by `XION_OLLAMA_FLOOR_MODEL` and may be either.

## Model-blob pin (Phase 5g-viii)

Phase 5g-viii ships the *first content-addressed model-blob pin* in the open-weights manifest, alongside the existing `sentinel` and `provenance-record` formats. This is the Invariant 17 clause 2(iii) "full hash" branch — content-addressing the model bytes themselves rather than a structural anchor or an operator declaration about a runtime daemon. It closes the third and final closure-bar item for [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) § `KW-INFERENCE-001`.

The pin is held by five properties enforced jointly by the manifest schema, the verifier's `_verify_model_blob` dispatch, and this section's pin.

### P1. The manifest pins the upstream Hugging Face GGUF, not a local file path.

The `model-blob` entry's `sha256` field content-addresses the bytes of the upstream `gemma-4-E4B-it-Q4_K_M.gguf` artifact at the canonical mirror's pinned revision (probe (b) above). The entry carries `retrieval_hints[]` naming the canonical URL plus the sha256 a third party would re-hash to verify the file matches. This makes the pin Witness-recomputable by anyone with internet access and a sha256 implementation, with no need for the operator's local filesystem to be reachable.

The alternative — pinning a local `~/.ollama/models/blobs/<sha256>` path — was rejected because the local Ollama blob is not Witness-recomputable: the Ollama daemon's blob-on-disk is the result of an Ollama-side import that may add metadata, and a Witness on a different host has no way to obtain the same bytes without first installing Ollama and then trusting that Ollama's import is byte-stable. The upstream HF artifact is a file the Witness can `curl | sha256sum` directly.

### P2. The verifier's `model-blob` posture is `NOT_YET_SEALED` when the file is absent, `OK` when present + matching, `FAIL` when present + mismatched.

The operator's local copy of the GGUF is pointed at by `XION_OPEN_WEIGHTS_GGUF_PATH` (env var, operator-supplied, not committed). When the env var is unset or the path does not resolve to a regular file, the verifier emits `NOT_YET_SEALED` (exit code 2) for the `model-blob` entry only — the rest of the manifest verifies normally. When the path resolves and the file's sha256 matches the manifest pin, the verifier emits `OK`. When the file exists but the sha256 mismatches, the verifier emits `FAIL` with the on-disk hash named in the failure message.

The `NOT_YET_SEALED` posture is deliberately distinct from `FAIL`: a manifest pinning a real upstream artifact that the operator has not yet downloaded is not a structural failure of Xion's floor (the floor still works at runtime via Ollama); it is a Witness-side gap in their ability to re-verify. CI gating at `xion-verify all --allow-not-yet-sealed` accepts the `NOT_YET_SEALED` posture; CI gating without the flag treats it as non-OK, so operators who want full hash-verification in their CI know how to enforce it.

### P3. The verifier dispatches per `format` value with a fail-closed unknown-format branch.

The verifier's `_verify_model_blob`, `_verify_provenance_record`, and `_verify_sentinel` are three named branches selected by the entry's `format` field. An entry whose `format` value is none of those three is `FAIL` (not silently skipped) — adding a new format is a verifier change, not a manifest-only change. This keeps the manifest's accepted-format set declared at exactly one point in the codebase (the verifier's dispatch table).

### P4. Hashing is chunked.

`_verify_model_blob` reads the file in 4 MiB chunks via `hashlib.sha256.update()` rather than a one-shot `read_bytes()`. A 5 GB GGUF would consume the orchestrator's memory budget if loaded whole; chunked hashing keeps peak memory at ~4 MiB regardless of file size. This is an Invariant 17 clause 2(iii) practicality requirement — the verifier must remain runnable on the same hardware that runs the floor.

### P5. The annual open-weights cutover dry-run is the operational closure of the same Invariant.

Invariant 17 clause 5 requires an annual dry-run that exercises `policy_mode="open_weights_only"` end-to-end. [`docs/13-OPERATIONS.md`](./13-OPERATIONS.md) § "Annual open-weights cutover dry-run" pins the runbook: one calendar-year cadence, the operator flips `XION_INFERENCE_POLICY=open_weights_only` for the dry-run window, every chat turn during the window must succeed through the floor, and the result is recorded as a `INCIDENT_LEDGER`-equivalent operator note pointing at the run's `chat_turn_id` set in `REQUEST_LEDGER.jsonl`. A red dry-run (turns falling through to `503` because the floor cannot keep up) names the gap before a real outage forces cutover names it for us.

### What this pin does not do

The model-blob pin does not block boot when the operator has not yet downloaded the upstream GGUF; the `health()` check at lifespan startup still gates only on Ollama daemon reachability + floor-model presence. The pin is a *Witness-verifiable claim about the bytes the operator should be running*, not a runtime gate. Production deployments that want a runtime gate enforcing byte-identity would need an additional check that (a) reads the local Ollama blob path, (b) sha256s it, (c) refuses bootstrap on mismatch — that is a future layer Phase 5g-viii deliberately does not ship because it would couple Xion's floor to Ollama's internal blob layout.

## Historical centralized fallback removal

Phase 5g-i.1 used a centralized vendor-of-vendors gateway as the hosted path. Phase 6.9 replaced that Genesis Default with Chutes/Bittensor SN64, and `docs/41-CENTRALIZED-REMOVAL.md` removes the centralized fallback entirely. The historical rationale remains in git history and `CHANGELOG.md`; it is not part of the live runtime doctrine.

The live policy is now simpler:

1. `hosted_api_first` attempts Chutes/Bittensor first, then the local open-weights floor.
2. `open_weights_only` attempts only the local open-weights floor.
3. No single-vendor SaaS gateway is a policy-legal provider.

Chutes remains a gateway liveness dependency; that residual is tracked as `KW-CHUTES-GATEWAY-001` / `KW-INFER-005` and paid down by a validator-direct or second decentralized inference path.

## Provider fallback semantics (Phase 5g-vii)

The policy modes named above describe *which providers are policy-legal* for a turn. They do not describe *what happens when a policy-legal provider raises an exception during `generate()`* — the gap that surfaced during the Phase 5g+ live smoke test, that [`KNOWN_WEAKNESSES.md`](../KNOWN_WEAKNESSES.md) § `KW-INFER-002` and § `KW-INFER-003` name, and that this section pins the shape of.

The five properties below are enforced by [`orchestrator/api/chat.py`](../orchestrator/api/chat.py), the `InferenceRouter.select_ordered()` method, and the `xion-verify refund-fidelity` verifier extension that landed alongside this section.

### P1. Hosted → floor fallback is automatic on generate failure.

Under `hosted_api_first`, a `generate()` raise from the hosted provider does **not** terminate the turn. The Router returns an ordered list of policy-legal providers (hosted first, floor second); the chat handler walks the list in order and attempts each provider. The turn returns `200` as soon as any provider produces a complete candidate that passes the egress Arbiter; the turn returns a non-200 envelope only when every policy-legal provider has been attempted and failed.

The pre-5g-vii shape — `InferenceRouter.select()` returns one provider, a raise from that provider surfaces as `503 no_healthy_provider` — is superseded. Operators who prefer the pre-5g-vii shape can set `XION_INFERENCE_POLICY=open_weights_only` to force a single-provider posture (floor only).

### P2. Policy-mode boundaries are absolute.

- `open_weights_only` **never** invokes a hosted provider, regardless of hosted health or hosted-side credit. The fallback list is `[floor]`. If the floor fails, the turn returns `503`.
- `hosted_api_first` **always** attempts hosted first, then falls through to the floor on error. The fallback list is `[hosted, floor]`. If both fail, the turn returns `503`.

The plan's closure for `KW-INFER-001` still requires at least one additional hosted gateway pinned; a Phase-6+ extension to `hosted_api_first` will return `[hosted_1, hosted_2, ..., floor]` under a single doctrine section, with the failover ordering pinned here. The floor is **always** the final entry in any `hosted_api_first` list (Invariant 17 clause 5's cutover property made routable).

### P3. Every attempt records a REQUEST_LEDGER row.

A single user turn now produces one or more `REQUEST_LEDGER` rows, one per provider attempt. The rows share a `chat_turn_id` (opaque 32-hex-char) and each carries its own `attempt_index` (0-based contiguous), `provider_id`, `outcome`, and `failure_reason_class`. `REQUEST_LEDGER` schema bumps from v1 to v2; the reader accepts both; the writer emits v2 on any multi-attempt turn and may emit v1 on single-attempt turns for backward compatibility with the pre-5g-vii correlation-id-unique invariant.

The v1 → v2 shape migration follows the reservation the v1 schema already carried (see [`docs/schemas/ledger-request.yaml`](./schemas/ledger-request.yaml) pre-5g-vii note: *"Per-turn aggregation (multiple gate calls per correlation_id) is reserved for schema_version 2"*); the plan that originally deferred this reservation is now called in.

The per-row fields write non-content provider telemetry only. Candidate bytes, hashes of candidate bytes, prompt text, and any provider-returned usage fields that could encode content (model-returned reasoning traces for slugs that support it) are **not** written to `REQUEST_LEDGER`. The `SAFETY_LEDGER` remains the single source of truth for `candidate_sha256`; the `PAYMENT_LEDGER` remains the single source of truth for money shape. `REQUEST_LEDGER` v2 records *provider attempts*, not *candidates*.

### P4. User-facing failure surfaces the last failure.

When every policy-legal provider has been attempted and every attempt has failed, the chat handler returns a single 5xx envelope whose `failure_reason_class` matches the **last** attempt's typed class (the floor's, under `hosted_api_first`). Earlier failures (e.g., the hosted provider's `insufficient_credits`) are recorded in the ledger rows but are not echoed in the user-facing envelope — the envelope is a single cause, not a list, because the user is not the operator and does not have a ledger reader in their hand.

The operator debugs by reading `REQUEST_LEDGER.jsonl`'s tail for the turn's `chat_turn_id` — every attempt's typed class is there, in insertion order. The `xion-verify refund-fidelity` verifier reads the same ledger and asserts the multi-attempt shape is coherent (one `outcome=success` per turn OR `N` `outcome=failure` with no `outcome=success`; `attempt_index` starts at 0 and is contiguous; final-envelope class matches the last attempt's class).

### P5. Failure-reason classes are typed and frozen.

The `failure_reason_class` enumeration is contractual. Six classes are pinned plus one reserved `success` outcome:

| Class | Meaning | Example trigger |
|-------|---------|-----------------|
| `insufficient_credits` | Provider refused the request for billing reasons (no account balance, expired card, quota exhausted). | Chutes `HTTP 402 Insufficient credits`. |
| `rate_limited_upstream` | Provider accepted the credential but refused the request due to rate limit. | Chutes / upstream `HTTP 429`. |
| `provider_unreachable` | Provider network surface could not be reached (DNS failure, connection refused, TLS failure, 5xx gateway error). | `httpx.ConnectError`, `HTTP 502`, `HTTP 503`, `HTTP 504`, DNS `ENOTFOUND`. |
| `timeout` | Provider network surface was reached but did not respond within the per-attempt deadline. | `httpx.ReadTimeout`, `asyncio.TimeoutError` (per-attempt, not per-turn). |
| `moderation_refusal` | Provider-side content filter refused the request before generation completed (upstream's own Covenant-like layer; distinct from Xion's Arbiter, which runs inside the orchestrator on the returned candidate). | Chutes `HTTP 403` with moderation reason; Ollama refusal on a local guardrail model. |
| `unknown_provider_error` | Residual bucket for exceptions that escape the typed classes (including malformed responses, HTTP 4xx codes not matched by the above, and any exception not inheriting from the typed subclasses). | `HTTP 400 bad request` on a slug rotation mid-flight; `HTTP 200` with truncated JSON; library-level exceptions. |

The `outcome` column on a `REQUEST_LEDGER` v2 row is `success` for an attempt that produced a candidate and passed the egress Arbiter; otherwise it is `failure` and the `failure_reason_class` names the class from the table above. On `outcome=success`, `failure_reason_class` is `null`.

Adding a class is a doctrine amendment to this section: requires updating this table, bumping `schema_version` on `REQUEST_LEDGER` if it is the first new class since schema_version 2, updating the typed sub-exceptions in [`orchestrator/inference_router/providers/chutes.py`](../orchestrator/inference_router/providers/chutes.py) and [`orchestrator/inference_router/providers/ollama.py`](../orchestrator/inference_router/providers/ollama.py), and a PINNED_HASH re-pin of `xion-verify`. Silent addition of a class is a verifier failure (the verifier reads the valid set from this file's pin, not from the provider source).

Removing a class is a stronger move: it is a schema-compat-breaking doctrine amendment that requires a version bump and a migration note in [`CHANGELOG.md`](../CHANGELOG.md). As of Phase 5g-vii, no class is scheduled for removal.

`unknown_provider_error` is the honest residual. It exists so operators reading a ledger never encounter a blank reason; it does not exist so developers can skip adding a real class. New observed failure shapes that repeatedly fall into `unknown_provider_error` are the operator's signal to open a KW and add the right typed class in the next phase.

## Boot sequence (doctrinal)

The FastAPI lifespan, extended in Phase 5g-i, runs in this order:

1. **Supervisor pre-seed** (Phase 5f). Synchronous `tick_once()` so `/drive` and `/sensorium` never return `None`.
2. **`.env` load** (5g-i). Stdlib parser; no `python-dotenv`. Missing file is not an error; already-set environment wins.
3. **Provider registration** (5g-i.1).
   - If `XION_CHUTES_API_KEY` is set: register `ChutesGenerativeProvider`.
   - Always: register `OllamaGenerativeProvider` (its `health()` reflects reachability; absence of `XION_OLLAMA_URL` means default `http://localhost:11434`).
4. **`InferenceRouter.bootstrap()`** (5g-i). If the floor is unsatisfied, stash a `no_floor = True` flag on `app.state` and emit a State-of-Xion paragraph to stderr. Do **not** crash. The read-only endpoints remain available so Witnesses can still inspect Xion while its voice is refused.
5. **Relay ↔ Supervisor wiring** (5f). `deps.relay._sensorium_source = supervisor`.
6. **Supervisor run task** (5f). `asyncio.create_task(supervisor.run())`.

Teardown is unchanged from Phase 5f.

## What this policy deliberately does NOT cover

- **Per-turn cost-based routing.** A turn does not currently ask "is Kimi cheaper than Ollama-on-local right now?". The router picks on mode + health only. Cost-aware routing is a Phase 5g-iii concern (where billing exists to inform routing) and beyond.
- **Multi-hosted-provider failover chains.** Only one hosted-API provider is registered at once. Richer decentralized-hosted failover is deferred; it interacts with credential management, per-provider cost accounting, and rate-limit budgeting, all of which deserve their own doctrinal unit.
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

*— Inference Policy v1, pinned Phase 5g-i (2026-04-21); centralized hosted-provider fallback removed by `docs/41-CENTRALIZED-REMOVAL.md`; Provider fallback semantics P1–P5 pinned at Phase 5g-vii (2026-04-23); Genesis Default floor model rotated from `gemma3:4b` to `gemma4:e4b-it-q4_K_M` and Model-blob pin P1–P5 pinned at Phase 5g-viii (2026-04-23). Next review when a second decentralized hosted gateway is pinned, when Chutes gateway terms change materially, when the first `failure_reason_class` addition is proposed, or when a third floor format (beyond `sentinel` / `provenance-record` / `model-blob`) is proposed.*
