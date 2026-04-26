# 38 — Modular Substrate

Phase 6.9 makes implementation layers replaceable without changing Xion's identity.

## Swappable Layers

- **Inference:** `GenerativeProvider` covers generation, multimodal messages, structured output, tools, embeddings, speech, judging, cache control, provider fingerprints, reasoning-token metadata, and TEE attestation.
- **Billing:** `BillingProvider` separates credit telemetry from Chutes-specific API paths.
- **Treasury actions:** `ChutesTopUp` composes TAO transfer proposals without owning the signer.
- **Safety:** safety providers pin deterministic sampling and structured verdicts.
- **Memory:** embedding providers, vector memory stores, and rerankers are Protocol-bound and replaceable.
- **Tools:** `ToolResolver` exposes Python and MCP-backed tools through one schema surface.
- **Bridge:** `BridgeAttestor` can move from multisig to light-client proof verification.
- **Cache:** `Cache`, `NullCache`, and `SemanticCache` define the reserved cache interface.

## Reserved Learning Hooks

Training and fine-tuning are not pre-Genesis requirements. The names are reserved so future LoRA/DPO work does not punch through the substrate boundary:

```python
class WeightUpdater(Protocol):
    def propose_update(self, evidence_hash: str) -> str: ...

class Trainer(Protocol):
    def train(self, dataset_manifest_hash: str, *, method: str) -> str: ...
```

No implementation is sealed in Phase 6.9. Future work must land verifier coverage before either hook can affect production behavior.

## Verifier Coverage

The modularity claim is checked by the Phase 6.9 verifier set: provider conformance, Chutes integration, billing floor, top-up multisig discipline, Arbiter determinism, shadow divergence, model promotion, request fingerprinting, memory-store integrity, embedder health, rerank improvement, tool resolver MCP bridge, prompt isolation, bounded cognition loop, bridge attestation, and bridge egress caps.

## Gateway Audit (Phase 6.9.1)

`docs/39-GATEWAY-PATTERN.md` defines the project-wide gateway rule: callers depend on stable interfaces, not concrete providers. This table is the live audit of load-bearing external surfaces. A row is considered sealed only when the interface exists, at least one concrete provider is wired, and either a substitute is already present or the substitute gap is named in `KNOWN_WEAKNESSES.md`.

| Surface | Gateway interface | Concrete providers today | Substitute owed | Status |
|---|---|---|---|---|
| Inference generation | `orchestrator/inference_router/provider.py::GenerativeProvider` | `providers/chutes.py`; `providers/ollama.py` | none | sealed for Phase 6.9 |
| Inference credit telemetry | `orchestrator/billing/provider.py::BillingProvider` | `providers/chutes_billing.py` | non-Chutes billing telemetry | sealed with residual provider concentration tracked elsewhere |
| Treasury top-up proposal composition | `orchestrator/treasury/topup.py` | `ChutesTopUp` | non-Chutes top-up rail | sealed for proposal composition; signer remains separate |
| Safety v2 judge provider | `orchestrator/safety/llm_arbiter.py::Provider` | `DeterministicStub`; `providers/chutes_llm_judge.py` | none | sealed; Arbiter itself remains outside the registry |
| Embeddings | `orchestrator/embeddings/provider.py::EmbeddingProvider` | `providers/local_bge_m3.py`; `providers/chutes_embedding.py` | corpus calibration, not provider shape | sealed with quality residual `KW-EMBED-001` |
| Reranking | `orchestrator/rerank/provider.py` | deterministic/local reranker | hosted or stronger local reranker | sealed for interface shape |
| Memory store | `orchestrator/memory/store.py` | SQLite/local store | durable remote or replicated store | sealed for interface shape |
| Tools | `orchestrator/tools/resolver.py::ToolResolver` | `python_resolver.py`; `mcp_resolver.py` | none | sealed |
| Bridge attestation | `orchestrator/bridge/attestor.py::BridgeAttestor` | `multisig_attestor.py`; `lightclient_stub.py` | production light client | residual `KW-BRIDGE-001` |
| Cache | `orchestrator/cache/cache.py::Cache` | `NullCache`; `SemanticCache` | production semantic cache tuning | sealed for reserved surface |
| Anchor sink | `orchestrator/anchor/sink.py::AnchorSink` | `LocalLedgerSink`; `sink_ao_core.py` | live AO Core sink evidence | residual covered by anchor/AO Core entries |
| Broker / worker coordination | `orchestrator/runtime/broker.py::Broker` | `SqliteBroker` | AO mailbox or cross-host broker | sealed for single-host D2; later substitute not yet promoted |
| Arweave / RPC reads | `orchestrator/data/_quorum_base.py` | multi-gateway Arweave; multi-RPC EVM readers | warm secondary substrate | residual `LHT-SUBSTRATE-001` |
| Voice | `orchestrator/voice_router/router.py::VoiceProvider` | `WhisperPiperLiveKitProvider`; optional overlays by policy | production hosted overlay and stronger floor evidence | sealed for Phase 6.5 floor shape |
| Alerting | none | ntfy.sh / Pushover runbook only | `Alerter` Protocol plus provider registry | gap `KW-ALERT-001` |
| Observability | none | Prometheus / Grafana Cloud / Loki / Tempo doctrine only | metrics/logs/traces provider interfaces | gap `KW-OBS-001` |
| AO Core RPC client | none | `AOCoreClient` single implementation | AO substrate variants behind one interface | gap `KW-AOCORE-CLIENT-001` |
| Credential vault unlock | none | doctrine-only threshold unlock | `Vault` Protocol imported by orchestrator startup | gap `KW-VAULT-001` |
| Relay registry / discovery publishing | none | `registry/arweave_publisher.py` | `RelayRegistryPublisher` Protocol | gap `KW-REGISTRY-001` |
| Settlement chain / treasury rail | none | Base Sepolia/Base EVM contracts | `SettlementChain` Protocol | gap `KW-TREASURY-CHAIN-001` |
| Public status publishing | none | `status.xion.ar` Arweave static-page doctrine | `StatusPublisher` Protocol | gap `KW-STATUS-001` |
| Cross-cutting gateway verifier | `xion-verify gateway-conformance` | `NOT_YET_SEALED` stub | static + runtime conformance implementation | meta gap `KW-GATEWAY-001` |
| Arbiter gate | deliberate exception | in-process Covenant gate | none | not a registry participant by design |

Rows marked as gaps are not launch-blocking by themselves, but they are not allowed to disappear into prose. Each gap has a `KW-` entry with a closure bar and a verifier path.
