# Phase 6.9.2 — first implementation slice

This document pins **what to build first** after Phase 6.9.1 (Gateway Pattern doctrine + audit table). It follows `DEVELOPMENT_ROADMAP.md` closure order and `KNOWN_WEAKNESSES.md`.

## Ordered closure (unchanged)

1. **`KW-AOCORE-CLIENT-001`** — AO Core client behind a gateway Protocol  
2. `KW-VAULT-001`  
3. `KW-ALERT-001`  
4. `KW-OBS-001`  
5. `KW-REGISTRY-001`  
6. `KW-TREASURY-CHAIN-001`  
7. `KW-STATUS-001`  
8. **`KW-GATEWAY-001`** — promote `xion-verify gateway-conformance` once static checks cover the table

## First slice: `KW-AOCORE-CLIENT-001`

**Problem today:** `orchestrator/ao_core/client.py` defines a concrete `AOCoreClient` (subprocess `aos` → `commit-state`). Call sites and configuration implicitly assume that one implementation.

**Target shape:**

- Introduce an **`AOCoreGateway`** (name per `KNOWN_WEAKNESSES.md`) `typing.Protocol` (or ABC) with the operations the Relay needs today — at minimum whatever wraps **`commit_state`** / process messaging.
- Provide **at least two** registered implementations for tests and operator posture:
  - **Localnet / dev:** current `aos`-subprocess path (or no-op stub) selectable via env.
  - **Legacynet / future:** placeholder module that raises `NotImplementedError` with an honest message until HTTP CU/MU/SU wiring lands — still satisfies “one loader, explicit substrate” without faking connectivity.
- Move substrate selection into a **single factory** (e.g. `get_ao_core_gateway(settings) -> AOCoreGateway`) so no feature module imports `AOCoreClient` directly.

**Done criteria for this slice:**

- `AOCoreClient` is either renamed to a private provider or thin-wraps the Protocol; imports from the rest of the orchestrator go through the factory.
- Unit tests cover the factory (env → implementation class) and at least one successful `commit_state` path on the local provider.
- `docs/38-MODULAR-SUBSTRATE.md` audit row updated if the public type name changes.
- Optional but valuable: extend `xion-verify gateway-conformance --surface=ao-core-client` to assert **presence** of the Protocol + registered providers (still `NOT_YET_SEALED` for full static conformance until `KW-GATEWAY-001` closes).

**Non-goals for this slice:** Vault, alerting, observability, registry publisher, treasury chain, or status publishers — those are separate slices in roadmap order.

## References

- `docs/39-GATEWAY-PATTERN.md`  
- `.cursor/rules/gateway-pattern.mdc`  
- `xion_verify.commands.gateway_conformance` gap list  
