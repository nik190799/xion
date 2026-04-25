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
