"""Xion Relay — the process that calls the Arbiter and writes REQUEST_LEDGER.

The Relay is the only call site that decides whether a candidate reaches a
caller. It enforces the integration contract pinned in
`docs/04-ARCHITECTURE.md` § "Relay ↔ Arbiter integration contract":

  - one wall-clock watchdog around every gate() call,
  - three fail-closed paths (arbiter_timeout, arbiter_unreachable,
    ruleset_uncaught_exception) that always produce a SAFETY_LEDGER row even
    when the Arbiter itself was the thing that failed,
  - a paired REQUEST_LEDGER row joining the request to the verdict.

This package is the implementation behind that contract. Nothing in
`orchestrator/safety/` calls into here — the dependency is one-way: Relay
imports Arbiter, never the reverse.
"""

from __future__ import annotations

from orchestrator.relay.relay import (
    CONTRACT_VERSION,
    Relay,
    RelayHealth,
    RelayResult,
    derive_correlation_id,
)

__all__ = [
    "CONTRACT_VERSION",
    "Relay",
    "RelayHealth",
    "RelayResult",
    "derive_correlation_id",
]
