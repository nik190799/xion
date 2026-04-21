"""`orchestrator.safety` — the Arbiter (Phase 4a).

The Arbiter is the only mechanism that holds Covenant Principle 3 ("refusal
as sacred") to its load-bearing meaning. Every prospective LLM output passes
through `gate()` before egress. Every verdict is hash-chained into
`SAFETY_LEDGER.jsonl`. The Arbiter is fail-closed by construction: if it
cannot return a verdict, the candidate cannot leave the Relay.

Property promised. No outbound token reaches a caller without a paired
`SAFETY_LEDGER` row whose `correlation_id` matches the caller's request.
Independently verifiable today by `xion-verify arbiter-up` (chain integrity);
in Phase 5 also by `xion-verify refund-fidelity` (ledger-to-ledger join).

Doctrine. `docs/04-ARCHITECTURE.md` § "The Arbiter (`safety.py`) — Covenant
enforcement pipeline" and § "Safety Ledger row schema". The schema is
canonicalized in `docs/schemas/ledger-safety.yaml` (status: canonical as of
Phase 4a).

Public surface (the only names other packages should import):

    from orchestrator.safety import gate, Verdict, Decision

Everything else is implementation detail. The library is the source of truth;
`orchestrator.safety.server` is a thin TCP loopback wrapper around the same
`gate()` for processes that want isolation.
"""

from __future__ import annotations

from orchestrator.safety.api import gate
from orchestrator.safety.types import Decision, Verdict

__all__ = ["Decision", "Verdict", "gate"]
