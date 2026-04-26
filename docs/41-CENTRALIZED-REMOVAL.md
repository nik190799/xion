# Centralized Provider Removal

> Status: canonical operational doctrine. This document records the removal of centralized single-vendor SaaS providers from Xion's runtime path.

## Four Properties

- **What property does this promise?** Xion's normal runtime data path does not depend on centralized single-vendor SaaS providers. Hosted inference may use gateways into decentralized substrates only when the underlying compute is decentralized and the dependency is named in `KNOWN_WEAKNESSES.md`.
- **What Invariants does it touch?** Strengthens Invariant 17 by removing centralized hosted fallbacks from the inference path. Strengthens Invariant 6 by removing centralized SaaS classifiers from the Arbiter's refusal path.
- **How is it verified?** `xion-verify sovereign-profile` verifies the centralized provider modules are absent, centralized credentials are refused in sovereign mode, and provider exports do not reintroduce OpenRouter/OpenAI surfaces.
- **How is it deprecated?** This removal is not a temporary compatibility window. Reintroducing a centralized provider requires a new doctrine section, a new known-weakness entry, and an explicit governance decision.

## Removed Surfaces

The following runtime surfaces are removed:

- `orchestrator/safety/providers/openai_moderation.py`
- `orchestrator/inference_router/providers/openrouter.py`
- `XION_OPENROUTER_*` operator environment knobs
- `OPENAI_API_KEY` as an Arbiter credential
- `xion-audit --v2 openai-moderation` replay/measurement

The replacement surfaces are:

- `orchestrator/safety/providers/chutes_llm_judge.py`
- `orchestrator/inference_router/providers/chutes.py`
- `orchestrator/inference_router/providers/ollama.py`
- `xion-audit --v2 chutes-llm-judge`

## Gateway Exception

Chutes is retained because it routes work to Bittensor Subnet 64 miners and can require confidential-compute variants for the hosted path. The Chutes public API remains a gateway liveness dependency. That residual is tracked as `KW-CHUTES-GATEWAY-001` and does not weaken the local open-weights floor.

## Audit Trade-Off

Removing OpenAI Moderation sacrifices one historical triangulation primitive: Xion can no longer compare `chutes-llm-judge` decisions against a centralized classifier from the same tree. That loss is deliberate. The surviving audit primitive is provider replay against the active decentralized-substrate judge.
