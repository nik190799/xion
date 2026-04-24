# Hermes Framework Verification Result

> *Spike executed during Phase 6+ Pre-Genesis Velocity Hardening.*

This document records the results of the framework verification spike mandated by `docs/24-COGNITION.md` §13. It assesses the Hermes Agent v2026.4.16 framework against Xion's five required cognition-layer capabilities.

## 1. Named specialist registration
**Requirement:** Long-lived sub-agents addressable by name, with their own loop and cost envelope.
**Result:** **Requires wrapper code.** Hermes supports named agents, but its native lifecycle is request-scoped rather than daemon-scoped. To run specialists as background daemons (e.g., `research-agent`), Xion must wrap the Hermes agent in an `asyncio` task loop that manages its wake/sleep cycle and feeds it from the `SENSORIUM_LEDGER`.
**Cost envelope:** Hermes provides token-counting callbacks, but Xion must implement the persistent cost-accumulator and threshold-trip logic.

## 2. Ephemeral sub-spawn from a parent's tool loop
**Requirement:** A primary worker can spawn an ephemeral, await its return, and incorporate the result.
**Result:** **Works natively.** Hermes natively supports agent-to-agent delegation via its `transfer_to` and `delegate_to` tool patterns. A primary worker can yield control to an ephemeral agent and receive the result back in its context window.

## 3. Max-depth enforcement at the framework level
**Requirement:** The framework itself can reject `spawn` calls beyond depth 1 — or we must enforce at the wrapper level.
**Result:** **Requires wrapper code.** Hermes does not natively enforce a global delegation depth limit. Xion must enforce this by intercepting the delegation tool calls or by statically configuring the primary worker's toolset to only allow delegation to leaf agents (which themselves have no delegation tools).

## 4. Bus-traffic introspection
**Requirement:** The framework exposes its internal message bus enough that `xion-verify cognition --bus-audit` can list all specialist-to-specialist messages.
**Result:** **Requires wrapper code.** Hermes passes messages via function arguments and returns, not through a pub/sub bus. To audit specialist-to-specialist communication (which Xion doctrine forbids), Xion must wrap the delegation tools to log invocations to the `SPECIALIST_LEDGER` or a dedicated audit trail.

## 5. Per-call cost accounting hooks
**Requirement:** Every model call is debit-table by bucket name.
**Result:** **Works natively.** Hermes provides lifecycle hooks (e.g., `on_llm_end`) that expose token usage. Xion can attach a listener to these hooks to debit the appropriate bucket (e.g., `Improvement Fund` for the `research-agent`) in real-time.

## Conclusion
The Hermes framework provides the necessary primitives (delegation, usage hooks) but requires Xion to implement the daemon lifecycle, depth enforcement, and strict isolation auditing. These wrapper requirements are well within the scope of the `orchestrator/cognition/` scaffolding and do not require framework-level forks.
