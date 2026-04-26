# Sovereign Profile

> Status: operational doctrine for `XION_PROFILE=sovereign`.

## Four Properties

- **What property does this promise?** In sovereign mode, Xion refuses centralized single-vendor SaaS credentials and centralized provider registrations before the API process accepts traffic.
- **What Invariants does it touch?** Strengthens Invariant 17 by holding the local open-weights floor and allowing only Chutes/Bittensor plus Ollama in the inference path. Strengthens Invariant 6 by allowing only local/stub or Chutes/Bittensor Arbiter v2 providers.
- **How is it verified?** `xion-verify sovereign-profile` checks the profile name, deleted provider modules, provider exports, and sovereign-mode environment refusals.
- **How is it deprecated?** When Bittensor validator-direct access lands, Chutes becomes a replaceable gateway and this profile's allowed hosted surface is updated through this document and `KNOWN_WEAKNESSES.md`.

## Refusal Table

When `XION_PROFILE=sovereign`, the FastAPI lifespan refuses to start if:

- `XION_OPENROUTER_API_KEY` is set.
- `OPENAI_API_KEY` is set.
- `XION_LLM_ARBITER_PROVIDER` is anything except unset, `deterministic-stub`, or `chutes-llm-judge`.
- `XION_AO_GATEWAY_URL` points outside local AO localnet.
- `XION_ANCHOR_WALLET_JWK_PATH` is set.
- `XION_ANCHOR_SINK=ao_core` points at a non-local AO gateway.
- `XION_BASE_RPC_URLS` is set with fewer than three endpoints.
- `XION_ARWEAVE_GATEWAYS` is set with fewer than two gateways.

The profile is deliberately a boot-time posture, not a handler-level conditional. If a forbidden surface is configured, Xion refuses the process before serving any route.

## Chutes Residual

Chutes remains allowed as a gateway into Bittensor SN64, not as a centralized model provider. The gateway liveness dependency is tracked in `KW-CHUTES-GATEWAY-001`; the local Ollama floor remains the fail-closed sovereign floor.
