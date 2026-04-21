"""Registry invariants for the principle list.

These are structural assertions — if they break, the SAFETY_LEDGER row
schema's `principle_id.allowed` list is out of sync with the code, which
would silently drop rows on verification.
"""

from __future__ import annotations

from orchestrator.safety.principles import (
    ALL,
    ALLOWED_PRINCIPLE_IDS,
    EnforcementMode,
    by_id,
    principles_summary,
)


def test_principle_ids_are_unique_and_complete():
    ids = [p.id for p in ALL]
    assert len(ids) == len(set(ids)), "duplicate principle ids"
    expected = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                "11", "12", "13", "14", "14a", "14b"}
    assert set(ids) == expected, f"principle-id set drifted: have={set(ids)} want={expected}"


def test_allowed_set_matches_registry():
    assert ALLOWED_PRINCIPLE_IDS == frozenset(p.id for p in ALL)


def test_by_id_roundtrip():
    for p in ALL:
        assert by_id(p.id) is p


def test_every_principle_has_doctrine_anchor():
    for p in ALL:
        assert p.doctrine_anchor.startswith("docs/"), (
            f"principle {p.id} anchor must point into docs/: {p.doctrine_anchor!r}"
        )
        assert "#" in p.doctrine_anchor, (
            f"principle {p.id} anchor must include a section fragment"
        )


def test_enforcement_mode_is_well_typed():
    for p in ALL:
        assert isinstance(p.enforcement_mode, EnforcementMode)


def test_summary_is_printable():
    s = principles_summary()
    assert "Covenant principles known to the Arbiter" in s
    for p in ALL:
        assert p.id in s
        assert p.name in s
