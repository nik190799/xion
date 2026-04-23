"""Phase 5g+: cross-cutting coordination primitives.

This package hosts mechanisms that cut across the ``api`` / ``supervisor`` /
``safety`` / ``billing`` boundaries and therefore do not belong inside any
one of them. Phase 5g+ lands the SQLite-WAL broker ([`broker.py`]) as the
first inhabitant; future locks, coordination widgets, and cross-worker
primitives slot in here alongside it.

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "Multi-worker coherence (Phase 5g+)"
    docs/33-MULTI-WORKER.md (operational doctrine)

Public surface:
    - :class:`orchestrator.runtime.broker.BrokerConfig`
    - :class:`orchestrator.runtime.broker.RateCheck`
    - :class:`orchestrator.runtime.broker.Broker` (Protocol)
    - :class:`orchestrator.runtime.broker.SqliteBroker`
    - :func:`orchestrator.runtime.broker.load_broker_from_env`
"""

from orchestrator.runtime.broker import (
    Broker,
    BrokerConfig,
    BrokerError,
    RateCheck,
    SqliteBroker,
    load_broker_from_env,
)

__all__ = [
    "Broker",
    "BrokerConfig",
    "BrokerError",
    "RateCheck",
    "SqliteBroker",
    "load_broker_from_env",
]
