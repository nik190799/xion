"""Hermes/Honcho memory forget adapter.

The adapter is deliberately backend-shaped rather than backend-specific. Phase
6.6.b needs a verifiable /forget contract before user memory may rely on any
external memory substrate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

FORGET_SLA_NS = 15_000_000_000


class ForgetScope(str, Enum):
    USER = "user"
    SESSION = "session"
    COLLECTION = "collection"
    EPHEMERAL = "ephemeral"
    ALL = "all"


@dataclass(frozen=True)
class ForgetReceipt:
    principal_id: str
    scope: ForgetScope
    requested_utc_ns: int
    acknowledged_utc_ns: int
    deleted_records: int
    backend_id: str

    @property
    def elapsed_ns(self) -> int:
        return self.acknowledged_utc_ns - self.requested_utc_ns

    @property
    def within_sla(self) -> bool:
        return 0 <= self.elapsed_ns <= FORGET_SLA_NS


class MemoryBackend(Protocol):
    backend_id: str

    def forget(self, principal_id: str, scope: ForgetScope) -> int:
        """Delete records for principal_id/scope and return deleted count."""

    def pending_count(self, principal_id: str, scope: ForgetScope) -> int:
        """Return records still visible after a forget attempt."""


@dataclass
class InMemoryMemoryBackend:
    """Deterministic backend used by tests and `xion-verify cognition --forget-sim`."""

    backend_id: str = "in-memory-sim"
    records: dict[str, dict[ForgetScope, list[str]]] = field(default_factory=dict)

    def put(self, principal_id: str, scope: ForgetScope, value: str) -> None:
        self.records.setdefault(principal_id, {}).setdefault(scope, []).append(value)

    def forget(self, principal_id: str, scope: ForgetScope) -> int:
        scopes = self._scopes_for(scope)
        user_records = self.records.setdefault(principal_id, {})
        deleted = 0
        for scoped in scopes:
            deleted += len(user_records.pop(scoped, []))
        return deleted

    def pending_count(self, principal_id: str, scope: ForgetScope) -> int:
        scopes = self._scopes_for(scope)
        user_records = self.records.get(principal_id, {})
        return sum(len(user_records.get(scoped, [])) for scoped in scopes)

    @staticmethod
    def _scopes_for(scope: ForgetScope) -> tuple[ForgetScope, ...]:
        if scope == ForgetScope.ALL:
            return (
                ForgetScope.USER,
                ForgetScope.SESSION,
                ForgetScope.COLLECTION,
                ForgetScope.EPHEMERAL,
            )
        return (scope,)


class MemoryForgetAdapter:
    """Synchronous forget adapter with an acknowledgement deadline."""

    def __init__(self, backend: MemoryBackend, *, clock_ns=time.time_ns) -> None:
        self._backend = backend
        self._clock_ns = clock_ns

    @property
    def backend_id(self) -> str:
        return self._backend.backend_id

    def forget(
        self,
        principal_id: str,
        scope: ForgetScope | str = ForgetScope.ALL,
        *,
        deadline_ns: int | None = None,
    ) -> ForgetReceipt:
        if not principal_id:
            raise ValueError("principal_id must be non-empty")
        parsed_scope = scope if isinstance(scope, ForgetScope) else ForgetScope(scope)
        requested = self._clock_ns()
        deadline = requested + FORGET_SLA_NS if deadline_ns is None else deadline_ns
        deleted = self._backend.forget(principal_id, parsed_scope)
        acknowledged = self.wait_for_ack(principal_id, parsed_scope, deadline_ns=deadline)
        return ForgetReceipt(
            principal_id=principal_id,
            scope=parsed_scope,
            requested_utc_ns=requested,
            acknowledged_utc_ns=acknowledged,
            deleted_records=deleted,
            backend_id=self._backend.backend_id,
        )

    def wait_for_ack(self, principal_id: str, scope: ForgetScope, *, deadline_ns: int) -> int:
        acknowledged = self._clock_ns()
        if acknowledged > deadline_ns:
            raise TimeoutError("memory forget acknowledgement exceeded deadline")
        pending = self._backend.pending_count(principal_id, scope)
        if pending:
            raise TimeoutError(f"memory forget left {pending} pending record(s)")
        return acknowledged


def run_forget_simulation() -> ForgetReceipt:
    backend = InMemoryMemoryBackend()
    principal_id = "forget-sim-user"
    for scope in (ForgetScope.USER, ForgetScope.SESSION, ForgetScope.COLLECTION, ForgetScope.EPHEMERAL):
        backend.put(principal_id, scope, f"{scope.value}-record")
    adapter = MemoryForgetAdapter(backend)
    receipt = adapter.forget(principal_id, ForgetScope.ALL)
    if not receipt.within_sla:
        raise TimeoutError("forget simulation exceeded SLA")
    return receipt


__all__ = [
    "FORGET_SLA_NS",
    "ForgetReceipt",
    "ForgetScope",
    "InMemoryMemoryBackend",
    "MemoryBackend",
    "MemoryForgetAdapter",
    "run_forget_simulation",
]
