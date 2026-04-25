from __future__ import annotations

import pytest

from orchestrator.cognition.memory_adapter import (
    ForgetScope,
    InMemoryMemoryBackend,
    MemoryForgetAdapter,
    run_forget_simulation,
)


def test_forget_all_deletes_all_scopes_with_receipt() -> None:
    backend = InMemoryMemoryBackend()
    for scope in (ForgetScope.USER, ForgetScope.SESSION, ForgetScope.COLLECTION, ForgetScope.EPHEMERAL):
        backend.put("alice", scope, f"{scope.value}-record")
    adapter = MemoryForgetAdapter(backend, clock_ns=lambda: 1_000)

    receipt = adapter.forget("alice", ForgetScope.ALL, deadline_ns=16_000_000_000)

    assert receipt.deleted_records == 4
    assert receipt.within_sla
    assert backend.pending_count("alice", ForgetScope.ALL) == 0


def test_forget_single_scope_leaves_other_scopes() -> None:
    backend = InMemoryMemoryBackend()
    backend.put("alice", ForgetScope.USER, "profile")
    backend.put("alice", ForgetScope.SESSION, "turn")
    adapter = MemoryForgetAdapter(backend)

    receipt = adapter.forget("alice", ForgetScope.SESSION)

    assert receipt.deleted_records == 1
    assert backend.pending_count("alice", ForgetScope.SESSION) == 0
    assert backend.pending_count("alice", ForgetScope.USER) == 1


def test_forget_nonexistent_user_acknowledges_zero_deleted() -> None:
    receipt = MemoryForgetAdapter(InMemoryMemoryBackend()).forget("missing", ForgetScope.ALL)

    assert receipt.deleted_records == 0
    assert receipt.within_sla


def test_forget_timeout_when_backend_leaves_pending_rows() -> None:
    class BrokenBackend(InMemoryMemoryBackend):
        def forget(self, principal_id: str, scope: ForgetScope) -> int:
            return 0

    backend = BrokenBackend()
    backend.put("alice", ForgetScope.USER, "profile")
    adapter = MemoryForgetAdapter(backend)

    with pytest.raises(TimeoutError, match="pending record"):
        adapter.forget("alice", ForgetScope.USER)


def test_forget_simulation_covers_all_memory_scopes() -> None:
    receipt = run_forget_simulation()

    assert receipt.deleted_records == 4
    assert receipt.within_sla
