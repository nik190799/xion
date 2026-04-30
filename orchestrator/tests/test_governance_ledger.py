from __future__ import annotations

from orchestrator.governance import append_governance_row, iter_rows, verify_chain


def test_governance_ledger_appends_hash_chained_rows(tmp_path):
    path = tmp_path / "GOVERNANCE_LEDGER.jsonl"

    first = append_governance_row(
        path,
        interaction_class="A",
        state_actor_identifier="audit-firm",
        jurisdiction="US",
        demand_summary_hash="a" * 64,
        demand_artifact_uri="file://audit-intake",
        covenant_principles_touched=[],
        invariants_touched=[],
        response_category="comply-with-disclosure",
        response_artifact_uri="file://response",
        user_notification="not-applicable",
        linked_safety_ledger_seq=None,
        date="2026-04-29",
    )
    second = append_governance_row(
        path,
        interaction_class="B",
        state_actor_identifier="regulator",
        jurisdiction="US",
        demand_summary_hash="b" * 64,
        demand_artifact_uri="file://demand",
        covenant_principles_touched=["13"],
        invariants_touched=["6"],
        response_category="refuse",
        response_artifact_uri="file://response-2",
        user_notification="notified",
        linked_safety_ledger_seq=None,
        date="2026-04-29",
    )

    rows = list(iter_rows(path))
    assert rows == [first, second]
    assert second["prev_hash"] == first["this_hash"]
    assert verify_chain(path) == []
